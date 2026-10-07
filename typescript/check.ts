import { existsSync, readFileSync, realpathSync, readdirSync, statSync } from "node:fs";
import { resolve, relative, isAbsolute, extname, dirname, basename } from "node:path";

const root = process.cwd();
function fail(message: string): never {
	throw new Error(message);
}

function table(value: unknown, label: string): Record<string, unknown> {
	if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be a table`);
	return value as Record<string, unknown>;
}

const COMPLETION_TIMEOUT_KEY = "completion_timeout_seconds";
const MAX_COMPLETION_TIMEOUT_SECONDS = 9007199254740991;

function completionTimeoutMisplaced(node: unknown, factTable: object): boolean {
	// The exact key is supported only as a direct key of the parsed [fact] table.
	// Traversing the parsed document (tables and arrays) rejects the same key at
	// the root and in other, nested, or array-embedded tables; dotted keys and
	// table headers are indistinguishable after parsing, which is intentional.
	if (Array.isArray(node)) return node.some((item) => completionTimeoutMisplaced(item, factTable));
	if (!node || typeof node !== "object") return false;
	return Object.entries(node).some(([key, child]) =>
		key === COMPLETION_TIMEOUT_KEY ? node !== factTable : completionTimeoutMisplaced(child, factTable),
	);
}

function completionBudget(fact: Record<string, unknown>): void {
	// Optional outer budget for the declared fact.test_command completion scope
	// only; absent means unconfigured (no default, no ratchet). This validates the
	// fact alone: timeout execution and enforcement stay outside this checker.
	if (!(COMPLETION_TIMEOUT_KEY in fact)) return;
	const budget = fact[COMPLETION_TIMEOUT_KEY];
	if (typeof budget !== "number" || !Number.isSafeInteger(budget) || budget < 1 || budget > MAX_COMPLETION_TIMEOUT_SECONDS) {
		fail(`fact.${COMPLETION_TIMEOUT_KEY} must be an integer from 1 to ${MAX_COMPLETION_TIMEOUT_SECONDS}`);
	}
	const testCommand = fact.test_command;
	if (typeof testCommand !== "string" || !testCommand.trim()) fail(`fact.${COMPLETION_TIMEOUT_KEY} requires a nonblank fact.test_command`);
}

function localPath(value: unknown, label: string): string {
	if (typeof value !== "string" || !value.trim() || isAbsolute(value)) fail(`${label} must be a repository-relative path`);
	const path = resolve(root, value as string);
	if (!existsSync(path)) fail(`${label} does not exist: ${value}`);
	const rel = relative(realpathSync(root), realpathSync(path));
	if (rel === ".." || rel.startsWith("../") || isAbsolute(rel)) fail(`${label} escapes the repository`);
	return path;
}

function sourceFiles(path: string): string[] {
	// Directory traversal never follows links or dependency/cache directories.
	try {
		return readdirSync(path, { withFileTypes: true }).flatMap((item) => {
			if (item.isSymbolicLink() || ["node_modules", ".git", ".gajaestack"].includes(item.name)) return [];
			const child = resolve(path, item.name);
			return item.isDirectory() ? sourceFiles(child) : /\.[cm]?[jt]sx?$/.test(extname(child)) ? [child] : [];
		});
	} catch (error) {
		if ((error as NodeJS.ErrnoException).code !== "ENOTDIR") throw error;
		return /\.[cm]?[jt]sx?$/.test(extname(path)) ? [path] : [];
	}
}

function tool(name: string): string {
	const path = resolve(root, "node_modules", ".bin", name);
	if (!existsSync(path)) fail(`missing executable: ${path}; provision it through the consumer's native dependency process`);
	return path;
}

function run(name: string, args: string[]): number {
	// Bun runs the installed JS launchers directly; Node and downloads are not required.
	const result = Bun.spawnSync([process.execPath, tool(name), ...args], { cwd: root, stdout: "inherit", stderr: "inherit" });
	return result.exitCode;
}

function failureStatus(error: unknown): number {
	const message = error instanceof Error ? error.message : String(error);
	return message.includes("missing executable:") ? 127 : 2;
}

function elapsed(from: number): number {
	return Math.max(0, Math.round(performance.now() - from));
}

function reportPhase(enabled: boolean, phase: string, files: number | null, status: number, from: number): void {
	// Timing is stderr-only so native stdout/errors stay byte-identical and no
	// run ever writes a timing artifact. Scope phases report discovery (counts
	// and status) separately from the native check phases they precede.
	if (!enabled) return;
	const count = files === null ? "" : ` files=${files}`;
	console.error(`gajaestack timing: ${phase}${count} status=${status} elapsed_ms=${elapsed(from)}`);
}

type GitChanges = { paths: string[] } | { status: number; message: string };

function changedFiles(): GitChanges {
	// Quick mode unions staged, unstaged and untracked entries from NUL-terminated
	// porcelain status (rename/copy origins ride in a separate raw NUL field;
	// their deletion is ignored by intersection, but invalidation must still see
	// them). --no-optional-locks keeps status from rewriting the git index, and
	// there is deliberately no fallback: when Git cannot report changes the run
	// fails visibly instead of pretending to cover changed files.
	const exec = (args: string[]): { ok: boolean; output: string; status: number; detail: string } => {
		try {
			const result = Bun.spawnSync(["git", "--no-optional-locks", ...args], { cwd: root, stdout: "pipe", stderr: "pipe" });
			// Strict decoding fails safely on invalid UTF-8 instead of silently
			// substituting characters that would corrupt changed-path matching.
			const decode = (bytes: Uint8Array): string => new TextDecoder("utf-8", { fatal: true }).decode(bytes);
			return {
				ok: result.exitCode === 0,
				output: decode(result.stdout),
				status: result.exitCode ?? 1,
				detail: decode(result.stderr).trim(),
			};
		} catch (error) {
			const missing = (error as NodeJS.ErrnoException)?.code === "ENOENT";
			return { ok: false, output: "", status: missing ? 127 : 2, detail: error instanceof Error ? error.message : String(error) };
		}
	};
	const status = exec(["status", "--porcelain", "-z", "--untracked-files=all"]);
	if (!status.ok) {
		return { status: status.status, message: `quick mode cannot determine changed files (no Git fallback): ${status.detail || `git status exited ${status.status}`}` };
	}
	const top = exec(["rev-parse", "--show-toplevel"]);
	if (!top.ok) {
		return { status: top.status, message: `quick mode cannot determine changed files (no Git fallback): ${top.detail || `git rev-parse --show-toplevel exited ${top.status}`}` };
	}
	const toplevel = top.output.replace(/\r?\n$/, "");
	const paths: string[] = [];
	const entries = status.output.split("\0");
	let index = 0;
	while (index < entries.length) {
		const entry = entries[index];
		index += 1;
		if (entry.length < 4) continue;
		const code = entry.slice(0, 2);
		paths.push(resolve(toplevel, entry.slice(3)));
		if (code.includes("R") || code.includes("C")) {
			// The origin is a bare path in its own NUL field; keep it so a renamed
			// away shared input still invalidates, and let intersection drop it
			// when the origin no longer exists on disk.
			const origin = entries[index];
			index += 1;
			if (origin) paths.push(resolve(toplevel, origin));
		}
	}
	return { paths };
}

type Invalidation = { files: Set<string>; dirs: Set<string>; unenumerable: boolean };

function biomeNamed(path: string): boolean {
	// A nested Biome config can affect its descendants without being an extends
	// entry; any changed Biome-named config conservatively expands the scope.
	const name = basename(path);
	return name === "biome.json" || name === "biome.jsonc";
}

function configInvalidation(config: string): Invalidation {
	// Conservative invalidation without reimplementing native config semantics:
	// routing facts, the Biome config and this checker script always expand
	// quick mode to the full selected lint scope. Local `extends` and `plugins`
	// references are tracked (directories by prefix, so a local .grit plugin
	// change counts), `extends` chains are followed while they remain readable
	// local paths, and any unreadable config or non-local reference marks the
	// dependencies unenumerable, after which any changed file expands the scope
	// rather than being silently missed by changed-only coverage.
	const invalidation: Invalidation = {
		files: new Set([resolve(root, ".gajaestack/routing.toml"), config, import.meta.path]),
		dirs: new Set(),
		unenumerable: false,
	};
	const track = (dependency: string): void => {
		try {
			if (statSync(dependency).isDirectory()) {
				invalidation.dirs.add(dependency);
				return;
			}
		} catch {
			// A missing dependency cannot be stat'ed; keep the exact path so its
			// deletion still appears in status and matches.
		}
		invalidation.files.add(dependency);
	};
	const visit = (path: string, seen: Set<string>): void => {
		if (seen.has(path)) return;
		seen.add(path);
		let document: unknown;
		try {
			document = JSON.parse(readFileSync(path, "utf8"));
		} catch {
			invalidation.unenumerable = true;
			return;
		}
		if (!document || typeof document !== "object" || Array.isArray(document)) {
			invalidation.unenumerable = true;
			return;
		}
		for (const field of ["extends", "plugins"] as const) {
			const value = (document as Record<string, unknown>)[field];
			if (value === undefined) continue;
			const entries = Array.isArray(value) ? value : [value];
			for (const entry of entries) {
				if (typeof entry !== "string" || !(entry.startsWith("./") || entry.startsWith("../") || isAbsolute(entry))) {
					// Package-style or malformed references cannot be enumerated as
					// repository files; treat every change as possibly relevant.
					invalidation.unenumerable = true;
					continue;
				}
				const dependency = resolve(dirname(path), entry);
				track(dependency);
				if (field === "extends" && existsSync(dependency)) visit(dependency, seen);
			}
		}
	};
	visit(config, new Set());
	return invalidation;
}

async function runChecks(quick: boolean, binding: boolean, timing: boolean): Promise<number> {
	try {
		const document = table(Bun.TOML.parse(await Bun.file(resolve(root, ".gajaestack/routing.toml")).text()), "routing");
		const fact = table(document.fact, "fact");
		const selected = fact?.selected_components;
		if (fact?.schema_version !== 1 || !Array.isArray(selected) || !selected.includes("typescript")) fail("fact schema_version=1 and selected component typescript are required");
		if (binding && !selected.includes("typescript-guard")) fail("Bun preload requires explicit typescript-guard selection");
		if (completionTimeoutMisplaced(document, fact)) fail(`fact.${COMPLETION_TIMEOUT_KEY} is supported only as a direct [fact] key`);
		completionBudget(fact);
		const options = table(document.typescript, "typescript");
		if (!options || options.schema_version !== 1 || typeof options.typecheck !== "boolean" || typeof options.lint !== "boolean") fail("[typescript] requires schema_version=1 and explicit typecheck/lint booleans");
		if (binding && !options.typecheck && !options.lint) fail("required Bun preload has no selected checks");
		const required = document.required;
		if (binding && (!Array.isArray(required) || required.includes("ts-typecheck") !== options.typecheck || required.includes("ts-lint") !== options.lint)) fail("preload checks must be explicitly listed in required and enabled consistently");
		if (options.typecheck && !quick) {
			const scope = performance.now();
			let scoped = false;
			try {
				const config = localPath(options.tsconfig, "tsconfig");
				const command = [process.execPath, tool("tsc"), "--project", config, "--showConfig"];
				const discovered = Bun.spawnSync(command, { cwd: root, stdout: "pipe", stderr: "inherit" });
				if (discovered.exitCode !== 0) {
					process.stdout.write(discovered.stdout);
					reportPhase(timing, "typecheck-scope", null, discovered.exitCode, scope);
					return discovered.exitCode;
				}
				const project = table(JSON.parse(discovered.stdout.toString()), "tsconfig");
				if (!Array.isArray(project.files) || project.files.length === 0) fail("tsconfig selects no files; no typecheck coverage");
				reportPhase(timing, "typecheck-scope", project.files.length, 0, scope);
				scoped = true;
				console.log(`Typecheck: ${project.files.length} project files (tsconfig scope, not transpilation)`);
				const phase = performance.now();
				const status = run("tsc", ["--noEmit", "--incremental", "false", "--project", config]);
				reportPhase(timing, "typecheck", project.files.length, status, phase);
				if (status !== 0) return status;
			} catch (error) {
				if (!scoped) reportPhase(timing, "typecheck-scope", null, failureStatus(error), scope);
				throw error;
			}
		}
		if (options.lint) {
			const scope = performance.now();
			let scoped = false;
			try {
				const config = localPath(options.biome_config, "biome_config");
				if (!Array.isArray(options.paths) || options.paths.length === 0) fail("lint paths must not be empty");
				const declared = [...new Set(options.paths.flatMap((path: unknown) => sourceFiles(localPath(path, "lint path"))))];
				if (!declared.length) fail("selected lint scope contains no source files; no coverage");
				let files: string[] = declared;
				if (quick) {
					// Quick mode is lint-only: intersect changed files with the declared
					// scope, or expand to the full declared scope when a shared input
					// changed. An empty intersection is an explicit no-op, never a pass.
					const changes = changedFiles();
					if (!("paths" in changes)) {
						reportPhase(timing, "lint-scope", null, changes.status, scope);
						console.error(`gajaestack: ${changes.message}`);
						return changes.status;
					}
					const changed = new Set(changes.paths);
					const invalidation = configInvalidation(config);
					const hits = changes.paths.filter(
						(path) =>
							biomeNamed(path) ||
							invalidation.files.has(path) ||
							[...invalidation.dirs].some((dir) => path.startsWith(`${dir}/`)),
					);
					const expand = hits.length > 0 || (invalidation.unenumerable && changes.paths.length > 0);
					if (expand) {
						const reasons = hits.map((path) => relative(root, path));
						if (invalidation.unenumerable) reasons.push("files possibly covered by unenumerable Biome config dependencies");
						console.log(`Quick scope expanded to full selected scope: changed ${reasons.join(", ")}`);
					} else {
						files = declared.filter((path) => changed.has(path));
						if (!files.length) {
							reportPhase(timing, "lint-scope", 0, 0, scope);
							console.log(changes.paths.length ? "No changed files match the selected lint paths; nothing to check." : "No changed files; nothing to check.");
							console.log("No coverage; this no-op is not a lint pass.");
							return 0;
						}
					}
				}
				reportPhase(timing, "lint-scope", files.length, 0, scope);
				scoped = true;
				tool("biome");
				console.log(`Lint: ${files.length} selected source files`);
				const phase = performance.now();
				const status = run("biome", ["lint", `--config-path=${config}`, ...files]);
				reportPhase(timing, "lint", files.length, status, phase);
				if (status !== 0) return status;
			} catch (error) {
				if (!scoped) reportPhase(timing, "lint-scope", null, failureStatus(error), scope);
				throw error;
			}
		}
		if (!options.lint && (quick || !options.typecheck)) console.log("No checks selected for this mode; no coverage (not a check pass).");
		return 0;
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		console.error(`gajaestack: ${message}`);
		return failureStatus(error);
	}
}

export async function check(quick = false, binding = false, timing = false): Promise<number> {
	// Timing is opt-in through --timing or GAJAESTACK_TIMING=1; the environment
	// path exists for the native preload, which passes no arguments. The total
	// line carries the final exit status on stderr for every outcome.
	const enabled = timing || process.env.GAJAESTACK_TIMING === "1";
	const started = performance.now();
	const status = await runChecks(quick, binding, enabled);
	if (enabled) console.error(`gajaestack timing: total status=${status} elapsed_ms=${elapsed(started)}`);
	return status;
}

if (import.meta.main) {
	const args = process.argv.slice(2);
	const quick = args.filter((arg) => arg === "--quick").length;
	const timing = args.filter((arg) => arg === "--timing").length;
	if (args.some((arg) => arg !== "--quick" && arg !== "--timing") || quick > 1 || timing > 1) {
		console.error("usage: bun .gajaestack/typescript/check.ts [--quick] [--timing]");
		process.exit(2);
	}
	process.exit(await check(quick > 0, false, timing > 0));
}
