import { existsSync, realpathSync, readdirSync } from "node:fs";
import { resolve, relative, isAbsolute, extname } from "node:path";

const root = process.cwd();
function fail(message: string): never {
	throw new Error(message);
}

function table(value: unknown, label: string): Record<string, unknown> {
	if (!value || typeof value !== "object" || Array.isArray(value)) fail(`${label} must be a table`);
	return value as Record<string, unknown>;
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

export async function check(quick = false, binding = false): Promise<number> {
	try {
		const document = table(Bun.TOML.parse(await Bun.file(resolve(root, ".gajaestack/routing.toml")).text()), "routing");
		const fact = table(document.fact, "fact");
		const selected = fact?.selected_components;
		if (fact?.schema_version !== 1 || !Array.isArray(selected) || !selected.includes("typescript")) fail("fact schema_version=1 and selected component typescript are required");
		if (binding && !selected.includes("typescript-guard")) fail("Bun preload requires explicit typescript-guard selection");
		const options = table(document.typescript, "typescript");
		if (!options || options.schema_version !== 1 || typeof options.typecheck !== "boolean" || typeof options.lint !== "boolean") fail("[typescript] requires schema_version=1 and explicit typecheck/lint booleans");
		if (binding && !options.typecheck && !options.lint) fail("required Bun preload has no selected checks");
		const required = document.required;
		if (binding && (!Array.isArray(required) || required.includes("ts-typecheck") !== options.typecheck || required.includes("ts-lint") !== options.lint)) fail("preload checks must be explicitly listed in required and enabled consistently");
		if (options.typecheck && !quick) {
			const config = localPath(options.tsconfig, "tsconfig");
			const command = [process.execPath, tool("tsc"), "--project", config, "--showConfig"];
			const discovered = Bun.spawnSync(command, { cwd: root, stdout: "pipe", stderr: "inherit" });
			if (discovered.exitCode !== 0) { process.stdout.write(discovered.stdout); return discovered.exitCode; }
			const project = table(JSON.parse(discovered.stdout.toString()), "tsconfig");
			if (!Array.isArray(project.files) || project.files.length === 0) fail("tsconfig selects no files; no typecheck coverage");
			console.log(`Typecheck: ${project.files.length} project files (tsconfig scope, not transpilation)`);
			const status = run("tsc", ["--noEmit", "--incremental", "false", "--project", config]);
			if (status !== 0) return status;
		}
		if (options.lint) {
			const config = localPath(options.biome_config, "biome_config");
			if (!Array.isArray(options.paths) || options.paths.length === 0) fail("lint paths must not be empty");
			const files = [...new Set(options.paths.flatMap((path: unknown) => sourceFiles(localPath(path, "lint path"))))];
			if (!files.length) fail("selected lint scope contains no source files; no coverage");
			tool("biome");
			console.log(`Lint: ${files.length} selected source files`);
			const status = run("biome", ["lint", `--config-path=${config}`, ...files]);
			if (status !== 0) return status;
		}
		if (!options.lint && (quick || !options.typecheck)) console.log("No checks selected for this mode; no coverage (not a check pass).");
		return 0;
	} catch (error) {
		const message = error instanceof Error ? error.message : String(error);
		console.error(`gajaestack: ${message}`);
		return message.includes("missing executable:") ? 127 : 2;
	}
}

if (import.meta.main) {
	const args = process.argv.slice(2);
	if (args.some((arg) => arg !== "--quick") || args.length > 1) {
		console.error("usage: bun .gajaestack/typescript/check.ts [--quick]");
		process.exit(2);
	}
	process.exit(await check(args.includes("--quick")));
}
