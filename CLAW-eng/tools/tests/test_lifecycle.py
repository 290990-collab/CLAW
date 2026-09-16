import hashlib
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import doctor, kernel, lifecycle, settings, source

FRAMEWORK = Path(__file__).resolve().parents[2]
VERSION = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
ARCHIVE = doctor.ARCHIVE_DIR.as_posix() + "/"
SETTINGS = ".claude/settings.json"


def install(d) -> Path:
    root = Path(d) / "trial"
    with redirect_stdout(io.StringIO()):
        trial_install.install(root)
    return root


def tree(root: Path) -> dict[str, str]:
    """Every file under `root`, relative, with the fingerprint of its content."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def actions(ops) -> dict[str, str]:
    return {op.path: op.action for op in ops}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestInstallPlan(unittest.TestCase):
    def test_the_plan_names_every_file_the_install_writes(self):
        """The plan is what the user approves, and the uninstall starts from the
        same list: a file the installation writes and the plan does not name is
        written without approval and stays after the uninstall."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            _, roster, guides, hooks = trial_install.choices()
            self.assertEqual(
                sorted(tree(root)), lifecycle.targets(FRAMEWORK, roster, guides, hooks)
            )

    def test_install_plan_on_a_project_with_its_own_material(self):
        """On a project that already had its own instructions, permissions and
        agents the plan must say "merge" and "keep", not "overwrite"; and a
        second installation over the first is not an installation."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            agents = prj / ".claude" / "agents"
            agents.mkdir(parents=True)
            (prj / "CLAUDE.md").write_text("# My instructions\n", encoding="utf-8")
            (prj / SETTINGS).write_text('{"env": {"A": "1"}}', encoding="utf-8")
            (agents / "mine.md").write_text("---\nname: mine\n---\n", encoding="utf-8")
            (agents / "explorer.md").write_text("old\n", encoding="utf-8")
            (prj / "AGENTS.md").write_text("# Another tool\n", encoding="utf-8")
            _, roster, guides, hooks = trial_install.choices()
            targets = lifecycle.targets(FRAMEWORK, roster, guides, hooks)

            ops = lifecycle.plan_install(prj, targets)
            got = actions(ops)
            self.assertEqual(got["CLAUDE.md"], lifecycle.MERGE)
            self.assertEqual(got[SETTINGS], lifecycle.MERGE)
            self.assertEqual(got[".claude/agents/mine.md"], lifecycle.KEEP)
            self.assertEqual(got["AGENTS.md"], lifecycle.KEEP)
            self.assertEqual(got[".claude/agents/explorer.md"], lifecycle.OVERWRITE)
            self.assertEqual(got["docs/TODO.md"], lifecycle.CREATE)
            # What changes a file that was there is read by name; the rest is counted.
            text = lifecycle.render(ops)
            self.assertIn(".claude/agents/explorer.md", text)
            self.assertNotIn("docs/TODO.md", text)

            (prj / ".claude" / "framework.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                lifecycle.plan_install(prj, targets)


class TestUninstall(unittest.TestCase):
    def uninstall(self, root: Path):
        ops = lifecycle.plan_uninstall(root, FRAMEWORK)
        lifecycle.apply_uninstall(root, FRAMEWORK, ops)
        return ops

    def test_uninstall_leaves_only_the_project_and_an_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
            data = read_json(root / SETTINGS)
            data["env"] = {"A": "1"}
            write_json(root / SETTINGS, data)
            claude = (root / "CLAUDE.md").read_text(encoding="utf-8")

            self.uninstall(root)

            left = {rel for rel in tree(root) if not rel.startswith(ARCHIVE)}
            self.assertEqual(
                left,
                {
                    "CLAUDE.md",
                    SETTINGS,
                    "docs/TODO.md",
                    "docs/status.md",
                    "docs/roadmap.md",
                    "src/app.py",
                },
            )
            self.assertEqual(read_json(root / SETTINGS), {"env": {"A": "1"}})
            self.assertEqual(
                (root / "CLAUDE.md").read_text(encoding="utf-8"),
                claude[kernel.parse(claude).end :].lstrip("\n"),
            )
            self.assertFalse((root / ".claude" / "agents").exists())
            archive = root / doctor.ARCHIVE_DIR
            self.assertTrue((archive / ".claude" / "framework.json").is_file())
            self.assertTrue((archive / ".claude" / "agents" / "explorer.md").is_file())

    def test_uninstall_never_deletes_what_it_did_not_write(self):
        """A file disappears from the project only if it was identical to the
        source; everything else either stays or ends up in the archive with the
        same content."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            for rel in (".claude/skills/framework-sync/SKILL.md", ".claude/hooks/gateguard.py"):
                p = root / rel
                p.write_text(p.read_text(encoding="utf-8") + "\n# my note\n", encoding="utf-8")
            mine = root / ".claude" / "skills" / "mine" / "SKILL.md"
            mine.parent.mkdir()
            mine.write_text("name: mine\n", encoding="utf-8")
            (root / ".claude" / "hooks" / "mine.py").write_text("pass\n", encoding="utf-8")
            before = tree(root)

            ops = self.uninstall(root)

            after = tree(root)
            self.assertEqual(
                actions(ops)[".claude/skills/framework-sync/SKILL.md"], lifecycle.ARCHIVE
            )
            archived = {rel[len(ARCHIVE) :] for rel in after if rel.startswith(ARCHIVE)}
            for rel in archived:
                self.assertEqual(after[ARCHIVE + rel], before[rel], rel)
            gone = sorted(set(before) - set(after) - archived)
            self.assertTrue(gone)
            originals = {
                ".claude/skills/": FRAMEWORK / "skills",
                ".claude/hooks/": FRAMEWORK / "hooks",
            }
            for rel in gone:
                prefix = next((p for p in originals if rel.startswith(p)), None)
                self.assertIsNotNone(prefix, f"{rel}: deleted without coming from the source")
                original = originals[prefix] / rel[len(prefix) :]
                self.assertEqual(
                    hashlib.sha256(original.read_bytes()).hexdigest(), before[rel], rel
                )
            self.assertTrue(mine.is_file())
            self.assertTrue((root / ".claude" / "hooks" / "mine.py").is_file())

    def test_uninstall_refuses_a_plan_the_tree_has_outgrown(self):
        """The approved plan holds for the tree it was made on: a skill touched
        up afterwards is no longer "identical to the source", and deleting it
        because it was yesterday deletes today's work. The refusal comes before
        the first byte is written, not halfway."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            skill = root / ".claude" / "skills" / "framework-doctor" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nnote\n", encoding="utf-8")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_uninstall(root, FRAMEWORK, ops)
            self.assertIn(".claude/skills/framework-doctor/SKILL.md", str(e.exception))
            self.assertEqual(tree(root), before)

            (root / doctor.ARCHIVE_DIR).mkdir()
            with self.assertRaises(ValueError):
                lifecycle.plan_uninstall(root, FRAMEWORK)

    def test_uninstall_refuses_a_plan_outgrown_outside_its_removals(self):
        """`_removable` re-checks only the "remove" entries. A card touched up
        after the plan would end up in the archive without anyone approving
        it, and a `CLAUDE.md` left without markers makes the execution fail
        after `settings.json` has already been rewritten: a half-done
        installation."""
        retouches = {
            "CLAUDE.md": lambda text: text.replace(kernel.CLOSE, ""),
            ".claude/agents/explorer.md": lambda text: text + "\nnote\n",
        }
        for rel, retouch in retouches.items():
            with self.subTest(rel=rel), tempfile.TemporaryDirectory() as d:
                root = install(d)
                ops = lifecycle.plan_uninstall(root, FRAMEWORK)
                p = root / rel
                p.write_text(retouch(p.read_text(encoding="utf-8")), encoding="utf-8")
                before = tree(root)
                with self.assertRaises(ValueError) as e:
                    lifecycle.apply_uninstall(root, FRAMEWORK, ops)
                self.assertIn(rel, str(e.exception))
                self.assertEqual(tree(root), before)

    def test_uninstall_refuses_to_move_what_it_never_plans_to(self):
        """The plan is a saved file: an "archive" or a "merge" written by hand
        with the right digest would move project code into the archive, or a
        file outside the root. The refusal comes before the first byte is
        written."""
        forged = (
            ("src/app.py", lifecycle.ARCHIVE),
            ("../outside.txt", lifecycle.ARCHIVE),
            ("src/app.py", lifecycle.MERGE),
        )
        for rel, action in forged:
            with self.subTest(rel=rel, action=action), tempfile.TemporaryDirectory() as d:
                root = install(d)
                (root / "src").mkdir()
                (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
                (Path(d) / "outside.txt").write_text("not the project's\n", encoding="utf-8")
                ops = lifecycle.plan_uninstall(root, FRAMEWORK)
                before = tree(Path(d))
                digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
                plan = [*ops, lifecycle.Operation(rel, action, "", digest)]
                with self.assertRaises(ValueError) as e:
                    lifecycle.apply_uninstall(root, FRAMEWORK, plan)
                self.assertIn(rel, str(e.exception))
                self.assertEqual(tree(Path(d)), before)

    def test_uninstall_refuses_a_removal_the_source_does_not_justify(self):
        """A "remove" put into the plan by hand, with the right digest, would
        delete project code. Every removal is re-checked against the source,
        and the refusal comes before the first byte is written."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
            (root / ".claude" / "hooks" / "mine.py").write_text("pass\n", encoding="utf-8")
            skill = root / ".claude" / "skills" / "framework-sync" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nnote\n", encoding="utf-8")
            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            before = tree(root)
            for rel in ("src/app.py", ".claude/hooks/mine.py", ".claude/skills/framework-sync/SKILL.md"):
                with self.subTest(rel=rel):
                    forged = [op for op in ops if op.path != rel]
                    forged.append(lifecycle.Operation(rel, lifecycle.REMOVE, "", before[rel]))
                    with self.assertRaises(ValueError) as e:
                        lifecycle.apply_uninstall(root, FRAMEWORK, forged)
                    self.assertIn(rel, str(e.exception))
                    self.assertEqual(tree(root), before)

    def test_uninstall_drops_a_framework_hook_the_user_retouched(self):
        """A hook entry with a touched-up timeout is no longer equal to the
        record, and `unmerge` leaves it; without a record none is removed. But
        the script it points to goes away: a closed hook without its script
        blocks every Edit and every Bash of the project, forever and without a
        finding."""
        cases = {
            "timeout touched up": lambda data, manifest: data["hooks"]["PreToolUse"][0][
                "hooks"
            ][0].update(timeout=30),
            "no record": lambda data, manifest: manifest.pop("settings_added"),
        }
        for label, retouch in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                root = install(d)
                data = read_json(root / SETTINGS)
                manifest = read_json(root / source.MANIFEST)
                retouch(data, manifest)
                write_json(root / SETTINGS, data)
                write_json(root / source.MANIFEST, manifest)
                first = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
                name = re.search(r"\.claude/hooks/(\w+)\.py", first).group(1)

                ops = self.uninstall(root)

                named = [op for op in ops if op.path == SETTINGS and name in op.reason]
                self.assertTrue(named, "the removed entry does not appear in the plan")
                self.assertNotIn(".claude/hooks/", (root / SETTINGS).read_text(encoding="utf-8"))


class TestRepair(unittest.TestCase):
    def test_repair_restores_what_went_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            skill = ".claude/skills/framework-sync/SKILL.md"
            hook = ".claude/hooks/config_protection.py"
            for rel in (skill, hook, "docs/status.md"):
                (root / rel).unlink()
            data = read_json(root / SETTINGS)
            del data["hooks"]
            data["permissions"]["deny"].remove("Read(./**/*.pem)")
            write_json(root / SETTINGS, data)
            # A permission the record does not have: what the repair puts back
            # must get into it, or the uninstall will not remove it. The hooks
            # stay in the record: it is the only trace that says which are in use.
            manifest = read_json(root / source.MANIFEST)
            manifest["settings_added"]["permissions"]["deny"].remove("Read(./**/*.pem)")
            write_json(root / source.MANIFEST, manifest)

            ops = lifecycle.plan_repair(root, FRAMEWORK)
            got = actions(ops)
            for rel in (skill, hook, "docs/status.md"):
                self.assertEqual(got[rel], lifecycle.CREATE, rel)
            self.assertEqual(got[SETTINGS], lifecycle.MERGE)

            lifecycle.apply_update(root, FRAMEWORK, ops)

            self.assertEqual(doctor.check(root), [])
            self.assertEqual(
                (root / hook).read_bytes(),
                (FRAMEWORK / "hooks" / "config_protection.py").read_bytes(),
            )
            data = read_json(root / SETTINGS)
            self.assertIn("Read(./**/*.pem)", data["permissions"]["deny"])
            self.assertIn(".claude/hooks/config_protection.py", json.dumps(data))
            # What the repair put back is in the record: the uninstall removes it.
            record = read_json(root / source.MANIFEST)["settings_added"]
            self.assertEqual(settings.unmerge(data, record)[0], {})

    def test_repair_restores_the_variables_of_the_installed_orchestration(self):
        """The orchestration is not in the manifest: if recomputing the settings
        looks only at profile and hooks, an `agent-teams` project that lost a
        variable stays with the model switched off, and the repair says all is
        well."""
        env = settings.ORCHESTRATION_SETTINGS["agent-teams"]["env"]
        lost = sorted(env)[0]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trial"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root, orchestration="agent-teams")
            data = read_json(root / SETTINGS)
            del data["env"][lost]
            write_json(root / SETTINGS, data)

            ops = lifecycle.plan_repair(root, FRAMEWORK)
            self.assertEqual(actions(ops).get(SETTINGS), lifecycle.MERGE)
            lifecycle.apply_update(root, FRAMEWORK, ops)

            self.assertEqual(read_json(root / SETTINGS)["env"], env)
            self.assertEqual(doctor.check(root), [])

    def test_repair_refuses_without_the_coordinator_guide(self):
        """Without the guide the installed orchestration is unknown: recomputing
        the settings without its variables would lose them in silence."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / lifecycle.ORCHESTRATION).unlink()
            with self.assertRaises(ValueError) as e:
                lifecycle.plan_repair(root, FRAMEWORK)
            self.assertIn(lifecycle.ORCHESTRATION, str(e.exception))

    def test_repair_overwrites_nothing_and_refuses_an_old_install(self):
        """The repair puts back what is missing, it does not bring back to the
        source what the user changed; and on an installation of another version
        "what is missing" is measured against the wrong source."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            skill = ".claude/skills/framework-doctor/SKILL.md"
            (root / skill).write_text("name: framework-doctor\nmine\n", encoding="utf-8")
            ops = lifecycle.plan_repair(root, FRAMEWORK)
            self.assertNotIn(lifecycle.OVERWRITE, {op.action for op in ops})
            self.assertEqual(actions(ops)[skill], lifecycle.KEEP)
            before = tree(root)
            lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertEqual(tree(root), before)

            manifest = read_json(root / source.MANIFEST)
            manifest["version"] = "0.1.0"
            write_json(root / source.MANIFEST, manifest)
            with self.assertRaises(ValueError):
                lifecycle.plan_repair(root, FRAMEWORK)


class TestDown(unittest.TestCase):
    def test_down_plan_on_an_older_install(self):
        """`--down` also brings skills and hooks, not only the kernel regions. A
        region touched up by hand is lost, and the plan says so first."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            manifest = read_json(root / source.MANIFEST)
            manifest["version"] = "1.0.0"
            write_json(root / source.MANIFEST, manifest)
            claude = root / "CLAUDE.md"
            drifted = claude.read_text(encoding="utf-8").replace(
                "Evidence Before Action", "Evidence Before Action, my way"
            )
            claude.write_text(drifted, encoding="utf-8")
            agents = root / ".claude" / "agents"
            (agents / "obsolete.md").write_bytes((agents / "explorer.md").read_bytes())
            skill = ".claude/skills/framework-sync/SKILL.md"
            (root / skill).write_text("name: framework-sync\nold\n", encoding="utf-8")
            hook = ".claude/hooks/block_no_verify.py"
            (root / hook).unlink()
            before = tree(root)

            ops = lifecycle.plan_down(root, FRAMEWORK)

            self.assertEqual(tree(root), before)
            got = {op.path: op for op in ops}
            self.assertEqual(got["CLAUDE.md"].action, lifecycle.MERGE)
            self.assertIn("is lost", got["CLAUDE.md"].reason)
            self.assertNotIn("is lost", got[".claude/shared/orchestration.md"].reason)
            self.assertEqual(got[".claude/agents/obsolete.md"].action, lifecycle.KEEP)
            self.assertEqual(got[skill].action, lifecycle.OVERWRITE)
            self.assertEqual(got[hook].action, lifecycle.CREATE)
            self.assertEqual(got[".claude/framework.json"].action, lifecycle.MERGE)

            lifecycle.apply_update(root, FRAMEWORK, ops)

            self.assertEqual(
                (root / skill).read_bytes(),
                (FRAMEWORK / "skills" / "framework-sync" / "SKILL.md").read_bytes(),
            )
            self.assertTrue((root / hook).is_file())
            # The kernel regions belong to the skill's steps, not to this code.
            self.assertEqual(claude.read_text(encoding="utf-8"), drifted)
            self.assertEqual(read_json(root / source.MANIFEST)["version"], VERSION)

    def test_down_names_a_model_the_source_changed(self):
        """The front matter stays the project's: an agent downgraded in the
        source would stay on the old model, and the plan must name it."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rel = ".claude/agents/implementer.md"
            card = root / rel
            src = (FRAMEWORK / "agents" / "implementer.md").read_text(encoding="utf-8")
            model = re.search(r"^model:\s*(\S+)", src, re.MULTILINE).group(1)
            other = "opus" if model != "opus" else "sonnet"
            text = card.read_text(encoding="utf-8")
            card.write_text(text.replace(f"model: {model}", f"model: {other}", 1), encoding="utf-8")

            got = {op.path: op for op in lifecycle.plan_down(root, FRAMEWORK)}

            self.assertIn(f"model: {other} here, {model} in the source", got[rel].reason)
            self.assertNotIn("in the source", got[".claude/agents/explorer.md"].reason)

    def test_down_refuses_a_plan_the_tree_has_outgrown(self):
        """A skill the plan overwrites and that changed after the ok is no longer
        the one the user saw being replaced: overwriting it loses the later
        touch-up. The refusal comes before the first byte is written."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rel = ".claude/skills/framework-sync/SKILL.md"
            skill = root / rel
            skill.write_text("name: framework-sync\nold\n", encoding="utf-8")
            ops = lifecycle.plan_down(root, FRAMEWORK)
            self.assertEqual(actions(ops)[rel], lifecycle.OVERWRITE)
            skill.write_text("name: framework-sync\nold, touched up afterwards\n", encoding="utf-8")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertIn(rel, str(e.exception))
            self.assertEqual(tree(root), before)

    def test_down_brings_guides_and_style_keeping_the_project_block(self):
        """Guides and the style have no kernel region, and `--down` never touched
        them: a new rule in a guide reached no installed project. The text comes
        from the source, the block the project filled in stays."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            cases = {}
            for rel, src in (
                (".claude/shared/core/review-checklist.md", "shared/core/review-checklist.md"),
                (".claude/output-styles/reporting.md", "output-styles/reporting.md"),
            ):
                text = (FRAMEWORK / src).read_text(encoding="utf-8")
                heading = lifecycle.project_heading(text)
                self.assertIsNotNone(heading, src)
                p = root / rel
                installed = p.read_text(encoding="utf-8")
                block = installed[installed.rindex(heading) :]
                self.assertIsNone(doctor.PLACEHOLDER_RE.search(block), rel)
                p.write_text("# Old version\n\nearlier rule\n\n" + block, encoding="utf-8")
                cases[rel] = text[: text.rindex(heading)] + block

            ops = lifecycle.plan_down(root, FRAMEWORK)
            for rel in cases:
                self.assertEqual(actions(ops)[rel], lifecycle.MERGE, rel)

            lifecycle.apply_update(root, FRAMEWORK, ops)

            for rel, expected in cases.items():
                self.assertEqual((root / rel).read_text(encoding="utf-8"), expected, rel)

    def test_down_keeps_a_guide_whose_project_block_is_gone(self):
        """Without the block's heading `--down` cannot tell what belongs to the
        project, and replacing the whole file would erase the adaptation: it stays
        as it is, and the plan names it."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rel = ".claude/shared/core/testing-guide.md"
            heading = lifecycle.project_heading(
                (FRAMEWORK / "shared" / "core" / "testing-guide.md").read_text(encoding="utf-8")
            )
            p = root / rel
            p.write_text(p.read_text(encoding="utf-8").replace(heading, "## My notes"), encoding="utf-8")
            before = p.read_bytes()

            ops = lifecycle.plan_down(root, FRAMEWORK)
            got = {op.path: op for op in ops}
            self.assertEqual(got[rel].action, lifecycle.KEEP)
            self.assertIn("by hand", got[rel].reason)

            lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertEqual(p.read_bytes(), before)

    def test_every_placeholder_in_a_guide_sits_in_its_last_section(self):
        """`--down` recognises the project block by the placeholder in the last
        section. A section added after the block would move it, and that guide
        would stop updating in projects without anything failing."""
        paths = sorted((FRAMEWORK / "shared").rglob("*.md")) + sorted(
            (FRAMEWORK / "output-styles").glob("*.md")
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if doctor.PLACEHOLDER_RE.search(text):
                with self.subTest(path=path.relative_to(FRAMEWORK).as_posix()):
                    self.assertIsNotNone(lifecycle.project_heading(text))


if __name__ == "__main__":
    unittest.main()
