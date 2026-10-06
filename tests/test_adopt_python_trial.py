from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.adopt_python_trial as trial
from scripts.adopt_python_trial import AdoptionError, apply, main, prepare

KIT = Path(__file__).resolve().parents[1]
OWNERSHIP_SCHEMA = "gajaestack-adoption-ownership-v1"


def sha256_text(data: bytes) -> str:
    return "sha256-" + hashlib.sha256(data).hexdigest()


def kit_addendum_body() -> bytes:
    body = (KIT / "python/routing/AGENTS.md").read_bytes()
    return body if body.endswith(b"\n") else body + b"\n"


def addendum_span(version: str, body: bytes) -> bytes:
    return (
        f"<!-- gajaestack:routing-addendum begin version={version} "
        f"sha256={hashlib.sha256(body).hexdigest()} -->\n".encode("ascii")
        + body
        + b"<!-- gajaestack:routing-addendum end -->\n"
    )


class PythonTrialAdoptionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    @property
    def agents(self) -> Path:
        return self.root / "AGENTS.md"

    @property
    def facts(self) -> Path:
        return self.root / ".gajaestack/routing.toml"

    @property
    def ownership(self) -> Path:
        return self.root / ".gajaestack/ownership.json"

    @property
    def ruff_config(self) -> Path:
        return self.root / ".gajaestack/python-trial/ruff.toml"

    @property
    def ruff_helper(self) -> Path:
        return self.root / ".gajaestack/scripts/check_changed_python.py"

    def write_inventory(self, entries: dict) -> Path:
        self.ownership.parent.mkdir(parents=True, exist_ok=True)
        self.ownership.write_text(
            json.dumps(
                {"schema": OWNERSHIP_SCHEMA, "assets": entries}, indent=2, sort_keys=True
            )
            + "\n",
            encoding="utf-8",
        )
        return self.ownership

    # --- shared asset lifecycle -------------------------------------------------

    def test_selection_preview_and_apply_touch_only_selected_component(self) -> None:
        changes = prepare(self.root, ["ruff"])
        self.assertEqual(len(changes), 3)
        self.assertFalse(changes[0].destination.exists())

        adopted = apply(self.root, ["ruff"])
        self.assertEqual(
            adopted,
            [
                self.ruff_config,
                self.ruff_helper,
                self.ownership,
            ],
        )
        self.assertFalse((self.root / ".gajaestack/python-trial/mypy.ini").exists())
        self.assertFalse((self.root / "tests/rerg/test_percent_decoder_properties.py").exists())

    def test_reapplying_is_idempotent_and_hypothesis_is_separately_selected(
        self,
    ) -> None:
        adopted = apply(self.root, ["ruff"])
        original = adopted[0].read_bytes()
        self.assertEqual(apply(self.root, ["ruff"]), [])
        self.assertEqual(adopted[0].read_bytes(), original)

        property_test = apply(self.root, ["hypothesis"])
        self.assertEqual(
            property_test,
            [
                self.root / "tests/rerg/test_percent_decoder_properties.py",
                self.ownership,
            ],
        )
        self.assertFalse((self.root / ".gajaestack/python-trial/mypy.ini").exists())

    def test_ownership_record_states_source_version_and_hash_per_asset(self) -> None:
        apply(self.root, ["ruff", "mypy"])
        record = json.loads(self.ownership.read_text(encoding="utf-8"))
        self.assertEqual(record["schema"], OWNERSHIP_SCHEMA)
        config_bytes = (KIT / "python/ruff.toml").read_bytes()
        self.assertEqual(
            record["assets"][".gajaestack/python-trial/ruff.toml"],
            {
                "source": "python/ruff.toml",
                "version": "unreleased-overlay",
                "hash": sha256_text(config_bytes),
            },
        )
        self.assertEqual(
            set(record["assets"]),
            {
                ".gajaestack/python-trial/ruff.toml",
                ".gajaestack/scripts/check_changed_python.py",
                ".gajaestack/python-trial/mypy.ini",
            },
        )

    def test_existing_different_file_refuses_without_partial_writes(self) -> None:
        existing = self.ruff_config
        existing.parent.mkdir(parents=True)
        existing.write_text("owner config\n", encoding="utf-8")

        with self.assertRaisesRegex(AdoptionError, "refusing to overwrite"):
            apply(self.root, ["mypy", "ruff"])

        self.assertEqual(existing.read_text(encoding="utf-8"), "owner config\n")
        self.assertFalse((self.root / ".gajaestack/python-trial/mypy.ini").exists())
        self.assertFalse(self.ruff_helper.exists())
        self.assertFalse(self.ownership.exists())

    def test_directory_at_file_destination_is_a_collision(self) -> None:
        destination = self.ruff_config
        destination.mkdir(parents=True)

        with self.assertRaisesRegex(AdoptionError, "non-file destination"):
            apply(self.root, ["ruff"])

        self.assertTrue(destination.is_dir())

    def test_remove_preserves_locally_changed_file(self) -> None:
        adopted = apply(self.root, ["ruff"])[0]
        adopted.write_text("locally customized\n", encoding="utf-8")

        with self.assertRaisesRegex(AdoptionError, "refusing to overwrite locally changed"):
            apply(self.root, ["ruff"])
        with self.assertRaisesRegex(AdoptionError, "refusing to remove locally changed"):
            apply(self.root, ["ruff"], remove=True)

        self.assertEqual(adopted.read_text(encoding="utf-8"), "locally customized\n")

    def test_ruff_removal_includes_helper_and_preserves_local_helper_edits(self) -> None:
        adopted = apply(self.root, ["ruff"])
        config = self.ruff_config
        helper = self.ruff_helper
        self.assertEqual(adopted, [config, helper, self.ownership])

        helper.write_text("consumer-owned helper edit\n", encoding="utf-8")
        with self.assertRaisesRegex(AdoptionError, "refusing to remove locally changed"):
            apply(self.root, ["ruff"], remove=True)

        self.assertTrue(config.is_file())
        self.assertEqual(helper.read_text(encoding="utf-8"), "consumer-owned helper edit\n")

        helper.write_bytes((KIT / "scripts/check_changed_python.py").read_bytes())
        removed = apply(self.root, ["ruff"], remove=True)
        self.assertEqual(removed, [config, helper, self.ownership])
        self.assertFalse(config.exists())
        self.assertFalse(helper.exists())
        self.assertFalse(self.ownership.exists())

    def test_removing_one_component_preserves_another_selection(self) -> None:
        apply(self.root, ["ruff", "mypy"])
        mypy = self.root / ".gajaestack/python-trial/mypy.ini"

        apply(self.root, ["ruff"], remove=True)

        self.assertFalse(self.ruff_config.exists())
        self.assertTrue(mypy.is_file())
        record = json.loads(self.ownership.read_text(encoding="utf-8"))
        self.assertEqual(set(record["assets"]), {".gajaestack/python-trial/mypy.ini"})

    # --- ownership inventory boundary ------------------------------------------

    def test_identical_kit_bytes_never_imply_ownership(self) -> None:
        self.ruff_config.parent.mkdir(parents=True)
        kit_config = (KIT / "python/ruff.toml").read_bytes()
        self.ruff_config.write_bytes(kit_config)

        for options in ({}, {"remove": True}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(AdoptionError, "action required"):
                    prepare(self.root, ["ruff"], **options)

        self.assertEqual(self.ruff_config.read_bytes(), kit_config)
        self.assertFalse(self.ownership.exists())
        self.assertFalse(self.ruff_helper.exists())

    def test_reviewed_inventory_initializes_ownership_for_update(self) -> None:
        self.ruff_config.parent.mkdir(parents=True)
        legacy = b"# legacy reviewed config\n"
        self.ruff_config.write_bytes(legacy)
        record = self.write_inventory(
            {
                ".gajaestack/python-trial/ruff.toml": {
                    "source": "python/ruff.toml",
                    "version": "reviewed-legacy",
                    "hash": sha256_text(legacy),
                }
            }
        )

        adopted = apply(self.root, ["ruff"])
        self.assertEqual(adopted, [self.ruff_config, self.ruff_helper, record])
        kit_config = (KIT / "python/ruff.toml").read_bytes()
        self.assertEqual(self.ruff_config.read_bytes(), kit_config)

        document = json.loads(record.read_text(encoding="utf-8"))
        self.assertEqual(
            document["assets"][".gajaestack/python-trial/ruff.toml"],
            {
                "source": "python/ruff.toml",
                "version": "unreleased-overlay",
                "hash": sha256_text(kit_config),
            },
        )
        self.assertIn(
            ".gajaestack/scripts/check_changed_python.py", document["assets"]
        )

    def test_reviewed_inventory_allows_removal(self) -> None:
        self.ruff_config.parent.mkdir(parents=True)
        legacy = b"# legacy reviewed config\n"
        self.ruff_config.write_bytes(legacy)
        record = self.write_inventory(
            {
                ".gajaestack/python-trial/ruff.toml": {
                    "source": "python/ruff.toml",
                    "version": "reviewed-legacy",
                    "hash": sha256_text(legacy),
                }
            }
        )

        removed = apply(self.root, ["ruff"], remove=True)
        self.assertEqual(removed, [self.ruff_config, record])
        self.assertFalse(self.ruff_config.exists())
        self.assertFalse(record.exists())

    def test_inventory_with_old_version_and_current_kit_bytes_updates_record(self) -> None:
        self.ruff_config.parent.mkdir(parents=True)
        kit_config = (KIT / "python/ruff.toml").read_bytes()
        self.ruff_config.write_bytes(kit_config)
        record = self.write_inventory(
            {
                ".gajaestack/python-trial/ruff.toml": {
                    "source": "python/ruff.toml",
                    "version": "reviewed-legacy",
                    "hash": sha256_text(kit_config),
                }
            }
        )

        actions = {
            change.destination: change.action for change in prepare(self.root, ["ruff"])
        }
        self.assertEqual(actions[self.ruff_config], "update")
        self.assertEqual(actions[self.ruff_helper], "adopt")

        apply(self.root, ["ruff"])
        document = json.loads(record.read_text(encoding="utf-8"))
        entry = document["assets"][".gajaestack/python-trial/ruff.toml"]
        self.assertEqual(entry["version"], "unreleased-overlay")
        self.assertEqual(entry["hash"], sha256_text(kit_config))
        self.assertEqual(apply(self.root, ["ruff"]), [])

    def test_inventory_hash_mismatch_is_refused(self) -> None:
        self.ruff_config.parent.mkdir(parents=True)
        legacy = b"# legacy reviewed config\n"
        self.ruff_config.write_bytes(legacy)
        self.write_inventory(
            {
                ".gajaestack/python-trial/ruff.toml": {
                    "source": "python/ruff.toml",
                    "version": "reviewed-legacy",
                    "hash": sha256_text(b"different reviewed bytes\n"),
                }
            }
        )

        with self.assertRaisesRegex(AdoptionError, "locally changed"):
            prepare(self.root, ["ruff"])
        self.assertEqual(self.ruff_config.read_bytes(), legacy)

    def test_malformed_or_unsafe_ownership_record_refuses(self) -> None:
        destination_key = ".gajaestack/python-trial/ruff.toml"
        valid_entry = {
            "source": "python/ruff.toml",
            "version": "unreleased-overlay",
            "hash": sha256_text(b"whatever\n"),
        }
        cases = [
            ("not json", "malformed ownership record", "{not json"),
            (
                "wrong schema",
                "malformed ownership record",
                json.dumps({"schema": "gajaestack-adoption-ownership-v0", "assets": {}}),
            ),
            (
                "extra top-level key",
                "malformed ownership record",
                json.dumps({"schema": OWNERSHIP_SCHEMA, "assets": {}, "extra": 1}),
            ),
            (
                "missing version",
                "malformed ownership record",
                json.dumps(
                    {
                        "schema": OWNERSHIP_SCHEMA,
                        "assets": {
                            destination_key: {
                                "source": "python/ruff.toml",
                                "hash": valid_entry["hash"],
                            }
                        },
                    }
                ),
            ),
            (
                "bad hash",
                "malformed ownership record",
                json.dumps(
                    {
                        "schema": OWNERSHIP_SCHEMA,
                        "assets": {
                            destination_key: {**valid_entry, "hash": "sha256-zz"}
                        },
                    }
                ),
            ),
            (
                "unknown destination",
                "unknown destination",
                json.dumps(
                    {"schema": OWNERSHIP_SCHEMA, "assets": {"docs/other.md": valid_entry}}
                ),
            ),
            (
                "traversal path",
                "unsafe ownership record path",
                json.dumps(
                    {
                        "schema": OWNERSHIP_SCHEMA,
                        "assets": {"../outside.json": valid_entry},
                    }
                ),
            ),
            (
                "absolute path",
                "unsafe ownership record path",
                json.dumps(
                    {"schema": OWNERSHIP_SCHEMA, "assets": {"/etc/owned.json": valid_entry}}
                ),
            ),
            (
                "mixed source",
                "mixed source identity",
                json.dumps(
                    {
                        "schema": OWNERSHIP_SCHEMA,
                        "assets": {
                            destination_key: {
                                **valid_entry,
                                "source": "python/mypy.ini",
                            }
                        },
                    }
                ),
            ),
        ]
        self.ownership.parent.mkdir(parents=True, exist_ok=True)
        for name, pattern, payload in cases:
            with self.subTest(name=name):
                self.ownership.write_text(payload, encoding="utf-8")
                with self.assertRaisesRegex(AdoptionError, pattern):
                    prepare(self.root, ["ruff"])
                self.assertFalse(self.ruff_config.exists())
                self.assertEqual(self.ownership.read_text(encoding="utf-8"), payload)

    # --- routing addendum lifecycle ---------------------------------------------

    def test_routing_selection_adopts_facts_template_and_delimited_addendum(self) -> None:
        preview = prepare(self.root, ["routing"])
        self.assertEqual(
            [change.destination for change in preview],
            [self.facts, self.agents],
        )
        self.assertEqual(len(apply(self.root, ["routing"])), 2)

        text = self.agents.read_text(encoding="utf-8")
        self.assertTrue(
            text.startswith(
                "<!-- gajaestack:routing-addendum begin version=unreleased-overlay sha256="
            )
        )
        self.assertTrue(text.endswith("<!-- gajaestack:routing-addendum end -->\n"))
        self.assertIn("Keep quick iteration and completion checks distinct", text)
        self.assertIn(
            f"sha256={hashlib.sha256(kit_addendum_body()).hexdigest()} -->", text
        )

        policy = self.facts.read_text(encoding="utf-8")
        self.assertIn('required = ["pytest", "ruff-check"]', policy)
        self.assertIn('advisory = ["ruff-format", "mypy"]', policy)
        self.assertIn(
            'on_demand = ["mutation-testing", "profiling", "adversarial-review"]', policy
        )
        self.assertFalse((self.root / ".gajaestack/python-trial/ruff.toml").exists())
        self.assertFalse((self.root / ".gjc/skills").exists())
        self.assertEqual(apply(self.root, ["routing"]), [])

    def test_addendum_adoption_prepends_delimited_span_preserving_bytes(self) -> None:
        original = b"# consumer entry\n\nkeep this byte-for-byte\n"
        self.agents.write_bytes(original)

        adopted = apply(self.root, ["routing"])
        self.assertEqual(adopted, [self.facts, self.agents])
        self.assertEqual(
            self.agents.read_bytes(),
            addendum_span("unreleased-overlay", kit_addendum_body()) + original,
        )

    def test_existing_unmarked_instructions_are_not_a_collision(self) -> None:
        original = b"consumer-owned guidance\nsecond unmarked instruction\n"
        self.agents.write_bytes(original)
        self.facts.parent.mkdir(parents=True)
        kit_facts = (KIT / "python/routing.toml").read_bytes()
        self.facts.write_bytes(kit_facts)

        adopted = apply(self.root, ["routing"])
        self.assertEqual(adopted, [self.agents])
        content = self.agents.read_bytes()
        self.assertTrue(content.endswith(original))
        self.assertIn(b"gajaestack:routing-addendum begin", content)
        self.assertEqual(self.facts.read_bytes(), kit_facts)
        self.assertFalse(self.ownership.exists())

    def test_addendum_update_replaces_only_owned_span(self) -> None:
        apply(self.root, ["routing"])
        facts_bytes = self.facts.read_bytes()

        prefix = b"consumer instructions\n"
        old_body = b"older addendum guidance\n"
        suffix = b"\ntrailing consumer note\n"
        self.agents.write_bytes(prefix + addendum_span("reviewed-legacy", old_body) + suffix)

        preview = prepare(self.root, ["routing"])
        self.assertEqual([change.action for change in preview], ["update addendum"])
        self.assertEqual(apply(self.root, ["routing"]), [self.agents])

        content = self.agents.read_bytes()
        self.assertTrue(content.startswith(prefix))
        self.assertTrue(content.endswith(suffix))
        self.assertEqual(
            content[len(prefix) : len(content) - len(suffix)],
            addendum_span("unreleased-overlay", kit_addendum_body()),
        )
        self.assertNotIn(b"older addendum guidance", content)
        self.assertEqual(self.facts.read_bytes(), facts_bytes)

    def test_edited_addendum_span_refuses_update_and_removal(self) -> None:
        apply(self.root, ["routing"])
        tampered = self.agents.read_bytes().replace(
            b"Keep quick iteration", b"Keep sloppy iteration"
        )
        self.agents.write_bytes(tampered)

        for options in ({}, {"remove": True}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(AdoptionError, "edited addendum span"):
                    prepare(self.root, ["routing"], **options)
        self.assertEqual(self.agents.read_bytes(), tampered)

    def test_agents_without_trailing_newline_roundtrips_exactly(self) -> None:
        original = b"no trailing newline"
        self.agents.write_bytes(original)

        apply(self.root, ["routing"])
        content = self.agents.read_bytes()
        self.assertTrue(content.startswith(b"<!-- gajaestack:routing-addendum begin"))
        self.assertTrue(content.endswith(original))

        apply(self.root, ["routing"], remove=True)
        self.assertEqual(self.agents.read_bytes(), original)
        self.assertTrue(self.agents.is_file())

    def test_duplicate_or_malformed_addendum_markers_refuse_both_operations(self) -> None:
        valid = addendum_span("unreleased-overlay", kit_addendum_body())
        begin_line = (
            "<!-- gajaestack:routing-addendum begin version=x -->\n"
        ).encode("ascii")
        end_line = b"<!-- gajaestack:routing-addendum end -->\n"
        cases = {
            "duplicate": valid + b"\n" + valid,
            "begin without end": begin_line + b"body\n",
            "end without begin": end_line,
            "invalid begin line": begin_line + b"body\n" + end_line,
            "glued begin marker": b"intro " + valid,
            "reserved marker without begin or end": b"<!-- gajaestack:routing-addendum bogus -->\n",
        }
        for name, payload in cases.items():
            with self.subTest(name=name):
                self.agents.write_bytes(payload)
                for options in ({}, {"remove": True}):
                    with self.assertRaisesRegex(
                        AdoptionError, "malformed or duplicate addendum markers"
                    ):
                        prepare(self.root, ["routing"], **options)
                self.assertEqual(self.agents.read_bytes(), payload)

    def test_removal_keeps_agents_file_even_when_adoption_created_it(self) -> None:
        apply(self.root, ["routing"])
        facts_bytes = self.facts.read_bytes()

        removed = apply(self.root, ["routing"], remove=True)
        self.assertEqual(removed, [self.agents])
        self.assertTrue(self.agents.is_file())
        self.assertEqual(self.agents.read_bytes(), b"")
        self.assertEqual(self.facts.read_bytes(), facts_bytes)

    def test_removal_restores_preexisting_agents_bytes_exactly(self) -> None:
        original = b"# consumer entry\nkeep me\n"
        self.agents.write_bytes(original)
        apply(self.root, ["routing"])
        self.assertNotEqual(self.agents.read_bytes(), original)

        apply(self.root, ["routing"], remove=True)
        self.assertEqual(self.agents.read_bytes(), original)
        self.assertTrue(self.agents.is_file())

    def test_removal_never_touches_unmarked_consumer_instructions(self) -> None:
        original = b"unmarked consumer instructions\n"
        self.agents.write_bytes(original)

        self.assertEqual(prepare(self.root, ["routing"], remove=True), [])
        self.assertEqual(apply(self.root, ["routing"], remove=True), [])
        self.assertEqual(self.agents.read_bytes(), original)
        self.assertFalse(self.facts.exists())

    # --- consumer facts lifecycle ------------------------------------------------

    def test_facts_are_absent_only_and_survive_updates_and_removal(self) -> None:
        apply(self.root, ["routing"])
        kit_facts = (KIT / "python/routing.toml").read_bytes()
        self.assertEqual(self.facts.read_bytes(), kit_facts)

        self.agents.write_bytes(
            b"prefix\n" + addendum_span("reviewed-legacy", b"old body\n")
        )
        apply(self.root, ["routing"])
        self.assertEqual(self.facts.read_bytes(), kit_facts)

        apply(self.root, ["routing"], remove=True)
        self.assertTrue(self.facts.is_file())
        self.assertEqual(self.facts.read_bytes(), kit_facts)

    def test_incompatible_facts_require_action_without_rewrite(self) -> None:
        self.facts.parent.mkdir(parents=True)
        broken = b'required = ["pytest"]\n'
        self.facts.write_bytes(broken)

        with self.assertRaisesRegex(AdoptionError, "action required"):
            apply(self.root, ["routing"])
        self.assertEqual(self.facts.read_bytes(), broken)
        self.assertFalse(self.agents.exists())

        self.facts.write_bytes((KIT / "python/routing.toml").read_bytes())
        apply(self.root, ["routing"])
        self.assertTrue(self.agents.exists())

        broken = b'required = ["pytest"]\n'
        self.facts.write_bytes(broken)
        for options in ({}, {"remove": True}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(AdoptionError, "action required"):
                    prepare(self.root, ["routing"], **options)
        self.assertEqual(self.facts.read_bytes(), broken)
        self.assertIn(b"gajaestack:routing-addendum begin", self.agents.read_bytes())

    # --- path safety ---------------------------------------------------------------

    def test_symlink_destination_refuses_to_follow_target(self) -> None:
        outside = self.root.parent / f"{self.root.name}-outside"
        outside.write_text("keep\n", encoding="utf-8")
        self.addCleanup(outside.unlink, missing_ok=True)
        self.root.joinpath(".gajaestack").mkdir()
        self.root.joinpath(".gajaestack/python-trial").symlink_to(
            outside.parent, target_is_directory=True
        )

        with self.assertRaisesRegex(AdoptionError, "symlinked destination directory"):
            apply(self.root, ["ruff"])
        self.assertEqual(outside.read_text(encoding="utf-8"), "keep\n")

    def test_symlinked_consumer_root_refuses(self) -> None:
        link = self.root.parent / f"{self.root.name}-link"
        link.symlink_to(self.root, target_is_directory=True)
        self.addCleanup(link.unlink, missing_ok=True)

        with self.assertRaisesRegex(AdoptionError, "symlinked consumer root"):
            prepare(link, ["ruff"])
        with self.assertRaisesRegex(AdoptionError, "symlinked consumer root"):
            prepare(link, ["routing"])

    def test_parent_replaced_after_preview_is_rechecked_on_apply(self) -> None:
        prepare(self.root, ["ruff"])
        self.root.joinpath(".gajaestack").mkdir()
        self.root.joinpath(".gajaestack/python-trial").symlink_to(
            self.root, target_is_directory=True
        )

        with self.assertRaisesRegex(AdoptionError, "symlinked destination directory"):
            apply(self.root, ["ruff"])
        self.assertFalse(self.ruff_helper.exists())

    def test_destination_created_after_preview_is_rechecked_on_apply(self) -> None:
        prepare(self.root, ["ruff"])
        self.ruff_config.parent.mkdir(parents=True)
        self.ruff_config.write_bytes(b"consumer config\n")

        with self.assertRaisesRegex(AdoptionError, "unowned destination"):
            apply(self.root, ["ruff"])
        self.assertEqual(self.ruff_config.read_bytes(), b"consumer config\n")
        self.assertFalse(self.ruff_helper.exists())
        self.assertFalse(self.ownership.exists())

    def test_dangling_ownership_record_symlink_refuses(self) -> None:
        self.ownership.parent.mkdir(parents=True)
        self.ownership.symlink_to(self.root / "missing-record")

        with self.assertRaisesRegex(AdoptionError, "refusing symlink destination"):
            prepare(self.root, ["ruff"])
        self.assertFalse(self.ruff_config.exists())

    def test_owned_removal_does_not_require_current_kit_sources(self) -> None:
        apply(self.root, ["ruff"])
        stub_kit = self.root / "kit-stub"
        stub_kit.mkdir()

        with mock.patch.object(trial, "KIT_ROOT", stub_kit):
            removed = apply(self.root, ["ruff"], remove=True)

        self.assertEqual(removed, [self.ruff_config, self.ruff_helper, self.ownership])
        self.assertFalse(self.ruff_config.exists())
        self.assertFalse(self.ruff_helper.exists())
        self.assertFalse(self.ownership.exists())

    def test_io_failure_reports_honest_partial_changes(self) -> None:
        original_mkdir = Path.mkdir

        def failing_mkdir(self: Path, *args: object, **kwargs: object) -> None:
            if self.name == "scripts":
                raise OSError("simulated disk failure")
            original_mkdir(self, *args, **kwargs)

        with mock.patch.object(Path, "mkdir", failing_mkdir):
            with self.assertRaisesRegex(
                AdoptionError,
                "I/O error during adopt .*changed paths so far: .*ruff.toml.*"
                "may be partially written",
            ):
                apply(self.root, ["ruff"])

        self.assertTrue(self.ruff_config.exists())
        self.assertFalse(self.ruff_helper.exists())
        self.assertFalse(self.ownership.exists())

        # A failure before any write reports that nothing has changed yet.
        with tempfile.TemporaryDirectory() as other:
            other_root = Path(other)

            def failing_first(self: Path, *args: object, **kwargs: object) -> None:
                if self.name == "python-trial":
                    raise OSError("simulated disk failure")
                original_mkdir(self, *args, **kwargs)

            with mock.patch.object(Path, "mkdir", failing_first):
                with self.assertRaisesRegex(
                    AdoptionError, "I/O error during adopt .*changed paths so far: none"
                ):
                    apply(other_root, ["ruff"])
            self.assertFalse(
                (other_root / ".gajaestack/python-trial/ruff.toml").exists()
            )

    def test_missing_kit_source_refuses_without_writes(self) -> None:
        stub_kit = self.root / "kit-stub"
        stub_kit.mkdir()
        with mock.patch.object(trial, "KIT_ROOT", stub_kit):
            with self.assertRaisesRegex(AdoptionError, "cannot read kit component"):
                apply(self.root, ["ruff"])
        self.assertFalse(self.ruff_config.exists())
        self.assertFalse(self.ownership.exists())

    # --- CLI ------------------------------------------------------------------------

    def test_cli_defaults_to_preview_and_rejects_unknown_selection(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "--component", "ruff"])
        self.assertEqual(result, 0)
        self.assertIn("Would adopt", output.getvalue())
        self.assertFalse(self.ruff_config.exists())

        apply(self.root, ["ruff"])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(
                [
                    "--root",
                    str(self.root),
                    "--component",
                    "ruff",
                    "--remove",
                ]
            )
        self.assertEqual(result, 0)
        self.assertIn("Would remove", output.getvalue())
        self.assertTrue(self.ruff_config.exists())

        error = io.StringIO()
        with contextlib.redirect_stderr(error):
            result = main(
                [
                    "--root",
                    str(self.root),
                    "--component",
                    "ruff",
                    "--component",
                    "ruff",
                    "--apply",
                ]
            )
        self.assertEqual(result, 1)
        self.assertIn("must not be repeated", error.getvalue())

    def test_cli_preview_and_apply_report_adopt_and_update_actions(self) -> None:
        self.ruff_config.parent.mkdir(parents=True)
        legacy = b"# legacy reviewed config\n"
        self.ruff_config.write_bytes(legacy)
        self.write_inventory(
            {
                ".gajaestack/python-trial/ruff.toml": {
                    "source": "python/ruff.toml",
                    "version": "reviewed-legacy",
                    "hash": sha256_text(legacy),
                }
            }
        )

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "--component", "ruff"])
        self.assertEqual(result, 0)
        self.assertIn("Would adopt", output.getvalue())
        self.assertIn("Would update", output.getvalue())
        self.assertEqual(self.ruff_config.read_bytes(), legacy)

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(["--root", str(self.root), "--component", "ruff", "--apply"])
        self.assertEqual(result, 0)
        self.assertIn("Adopted", output.getvalue())
        self.assertIn("Updated", output.getvalue())
        self.assertEqual(
            self.ruff_config.read_bytes(), (KIT / "python/ruff.toml").read_bytes()
        )


class MechanicalAdoptionTests(unittest.TestCase):
    def test_python_binding_is_separate_and_prerequisite_removal_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apply(root, ["guard", "ruff"])
            binding = root / ".gajaestack/python/pytest_required_ruff.py"
            self.assertFalse(binding.exists())
            policy = (KIT / "python/routing.toml").read_text().split("\n[python]")[0].replace(
                'selected_components = ["mypy", "routing", "ruff"]',
                'selected_components = ["guard", "ruff", "required-ruff"]\n'
                'required_ruff_before_pytest = "active"',
            )
            policy += (
                '\n[python]\nschema_version = 1\npython_version = "3.12"\n'
                'imports = []\nexecutables = []\nruff_paths = ["app.py"]\n'
                'ruff_config = ".gajaestack/python-trial/ruff.toml"\n'
            )
            (root / ".gajaestack/routing.toml").write_text(policy)
            apply(root, ["required-ruff"])
            for dependency in ("guard", "ruff"):
                with self.assertRaisesRegex(AdoptionError, "remove the binding"):
                    prepare(root, [dependency], remove=True)
            apply(root, ["required-ruff"], remove=True)
            with self.assertRaisesRegex(AdoptionError, "remove the binding"):
                prepare(root, ["guard"], remove=True)
            policy = policy.replace(
                '["guard", "ruff", "required-ruff"]', '["guard", "ruff"]'
            ).replace('required_ruff_before_pytest = "active"\n', "")
            (root / ".gajaestack/routing.toml").write_text(policy)
            apply(root, ["guard"], remove=True)
            self.assertTrue((root / ".gajaestack/python-trial/ruff.toml").exists())
            self.assertEqual((root / ".gajaestack/routing.toml").read_text(), policy)

    def test_typescript_edited_asset_is_not_overwritten_or_removed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            apply(root, ["typescript"])
            asset = root / ".gajaestack/typescript/check.ts"
            asset.write_text("// consumer edit\n")
            for remove in (False, True):
                with self.assertRaisesRegex(AdoptionError, "locally changed"):
                    prepare(root, ["typescript"], remove=remove)
            self.assertEqual(asset.read_text(), "// consumer edit\n")

    def test_typescript_selection_preserves_native_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            originals = {
                "package.json": b'{"scripts":{"test":"bun test"}}\n',
                "tsconfig.json": b'{"compilerOptions":{"strict":true}}\n',
                "biome.json": b'{"linter":{"enabled":true}}\n',
                "bunfig.toml": b'[test]\nroot = "tests"\n',
            }
            for name, content in originals.items():
                (root / name).write_bytes(content)
            self.assertTrue(prepare(root, ["typescript"]))
            self.assertFalse((root / ".gajaestack").exists())
            apply(root, ["typescript"])
            self.assertFalse((root / ".gajaestack/python").exists())
            self.assertFalse((root / ".gajaestack/typescript/preload.ts").exists())
            self.assertEqual(apply(root, ["typescript"]), [])
            for name, content in originals.items():
                self.assertEqual((root / name).read_bytes(), content)
            apply(root, ["typescript"], remove=True)
            for name, content in originals.items():
                self.assertEqual((root / name).read_bytes(), content)

    def test_typescript_binding_requires_prerequisites_and_protects_removal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(AdoptionError, "requires component"):
                prepare(root, ["typescript-guard"])
            apply(root, ["typescript"])
            with self.assertRaisesRegex(AdoptionError, "reviewed consumer facts"):
                prepare(root, ["typescript-guard"])
            policy = (KIT / "python/routing.toml").read_text().split("\n[python]")[0]
            policy = policy.replace('required = ["pytest", "ruff-check"]', 'required = ["ts-typecheck"]')
            policy = policy.replace(
                'selected_components = ["mypy", "routing", "ruff"]',
                'selected_components = ["typescript", "typescript-guard"]',
            )
            policy += '\n[typescript]\nschema_version = 1\ntypecheck = true\nlint = false\ntsconfig = "tsconfig.json"\n'
            facts = root / ".gajaestack/routing.toml"
            facts.write_text(policy)
            apply(root, ["typescript-guard"])
            with self.assertRaisesRegex(AdoptionError, "remove the binding"):
                prepare(root, ["typescript"], remove=True)
            apply(root, ["typescript-guard"], remove=True)
            policy = policy.replace('["typescript", "typescript-guard"]', '["typescript"]')
            facts.write_text(policy)
            apply(root, ["typescript"], remove=True)
            self.assertEqual(facts.read_text(), policy)


if __name__ == "__main__":
    unittest.main()
