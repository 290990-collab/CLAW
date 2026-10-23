import hashlib
import io
import json
import re
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import assemble, cli, doctor, kernel, lifecycle, rules, settings, source

FRAMEWORK = Path(__file__).resolve().parents[2]
VERSION = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
ARCHIVE = doctor.ARCHIVE_DIR.as_posix() + "/"
SETTINGS = ".claude/settings.json"
MANIFEST = ".claude/claw.json"
USER_RULES = ".claude/user-rules.md"
ORCHESTRATION = ".claude/shared/orchestration.md"


def install(d, orchestration=trial_install.ORCHESTRATION) -> Path:
    root = Path(d) / "trial"
    with redirect_stdout(io.StringIO()):
        trial_install.install(root, orchestration)
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


def reason(ops, path: str) -> str:
    return " ".join(op.reason for op in ops if op.path == path)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def text(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def generated(root: Path, fw: Path = FRAMEWORK) -> dict[str, str]:
    """What the source generates for the installation as it stands."""
    choices = lifecycle.installed_choices(read_json(root / MANIFEST))
    rl = rules.parse(text(root / USER_RULES)) if (root / USER_RULES).is_file() else rules.Rules()
    return assemble.generate(fw, choices, rl, text(root / "CLAUDE.md"))


def run_update(root: Path, fw: Path = FRAMEWORK, **changes):
    ops = lifecycle.plan_update(root, fw, **changes)
    lifecycle.apply_update(root, fw, ops, **changes)
    return ops


def routed(root: Path) -> set[str]:
    """The agents the coordinator's roster table names."""
    return set(doctor.ROUTING_AGENT_RE.findall(text(root / ORCHESTRATION)))


def edit(path: Path, old: str, new: str) -> None:
    body = text(path)
    assert old in body, old
    path.write_bytes(body.replace(old, new, 1).encode("utf-8"))


def source_copy(d) -> Path:
    """A throwaway source, to be changed like a new release would."""
    fw = Path(d) / "fw"
    shutil.copytree(FRAMEWORK, fw, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache"))
    return fw


class TestInstallPlan(unittest.TestCase):
    def test_the_plan_names_every_file_the_install_writes(self):
        """The plan is what the user approves, and the uninstall starts from the
        same list: a file the installation writes and the plan does not name is
        written without approval and stays after the uninstall."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            chosen = trial_install.choices()
            ops = lifecycle.plan_install(prj, FRAMEWORK, chosen)
            lifecycle.apply_install(prj, FRAMEWORK, ops, chosen)
            planned = {op.path for op in ops if op.action != lifecycle.KEEP}
            self.assertEqual(set(tree(prj)), planned)

    def test_install_plan_on_a_project_with_its_own_material(self):
        """On a project that already had its own instructions, permissions and
        agents the plan must say "merge" and "keep", not "overwrite"; and a
        second installation over the first is not an installation."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            agents = prj / ".claude" / "agents"
            agents.mkdir(parents=True)
            (prj / "CLAUDE.md").write_bytes(b"# My instructions\n")
            (prj / SETTINGS).write_text('{"env": {"A": "1"}}', encoding="utf-8")
            (agents / "mine.md").write_text("---\nname: mine\n---\n", encoding="utf-8")
            (agents / "explorer.md").write_text("old\n", encoding="utf-8")
            (prj / "AGENTS.md").write_text("# Another tool\n", encoding="utf-8")
            chosen = trial_install.choices()

            ops = lifecycle.plan_install(prj, FRAMEWORK, chosen)
            got = actions(ops)
            self.assertEqual(got["CLAUDE.md"], lifecycle.MERGE)
            self.assertEqual(got[SETTINGS], lifecycle.MERGE)
            self.assertEqual(got[".claude/agents/mine.md"], lifecycle.KEEP)
            self.assertEqual(got["AGENTS.md"], lifecycle.KEEP)
            self.assertEqual(got[".claude/agents/explorer.md"], lifecycle.OVERWRITE)
            self.assertEqual(got["docs/TODO.md"], lifecycle.CREATE)
            self.assertEqual(got[USER_RULES], lifecycle.CREATE)
            # What changes a file that was there is read by name; the rest is counted.
            shown = lifecycle.render(ops)
            self.assertIn(".claude/agents/explorer.md", shown)
            self.assertNotIn("docs/TODO.md", shown)

            lifecycle.apply_install(prj, FRAMEWORK, ops, chosen)
            self.assertEqual(read_json(prj / SETTINGS)["env"]["A"], "1")
            self.assertTrue(text(prj / "CLAUDE.md").startswith("<!-- FRAMEWORK:KERNEL"))
            self.assertIn("# My instructions\n", text(prj / "CLAUDE.md"))
            with self.assertRaises(ValueError):
                lifecycle.plan_install(prj, FRAMEWORK, chosen)

    def test_a_claude_md_without_the_marker_becomes_the_project_part_whole(self):
        """The file the owner wrote is theirs: not one line of it may be lost or
        reordered, and the generated `## Shared guides` must be the only one."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            project = "# Mine\n\nUse tabs.\n\n## Shared guides\n\nmy own list\n"
            (prj / "CLAUDE.md").write_bytes(project.encode("utf-8"))
            chosen = trial_install.choices()
            lifecycle.apply_install(prj, FRAMEWORK, lifecycle.plan_install(prj, FRAMEWORK, chosen), chosen)
            out = text(prj / "CLAUDE.md")
            region = kernel.parse(out)
            self.assertEqual(out[region.end :].strip("\n"), project.strip("\n"))
            self.assertIn("## Shared guides", region.body)

    def test_install_applies_the_rules_already_there_and_never_rewrites_them(self):
        """A reinstall after an uninstall meets the user's rules file: applying
        it keeps their rules, overwriting it loses them. Without one, an empty
        file is created for them to fill."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            (prj / ".claude").mkdir()
            rules_text = "## All\n- be brief\n\n## tester\nmodel: opus\n- run it twice\n"
            (prj / USER_RULES).write_bytes(rules_text.encode("utf-8"))
            chosen = trial_install.choices()
            ops = lifecycle.plan_install(prj, FRAMEWORK, chosen)
            self.assertEqual(actions(ops)[USER_RULES], lifecycle.KEEP)
            lifecycle.apply_install(prj, FRAMEWORK, ops, chosen)

            self.assertEqual((prj / USER_RULES).read_bytes(), rules_text.encode("utf-8"))
            self.assertIn("- be brief", text(prj / "CLAUDE.md"))
            card = text(prj / ".claude" / "agents" / "tester.md")
            self.assertIn("run it twice", card)
            self.assertIn("model: opus\n", card)
            self.assertRegex(text(prj / ORCHESTRATION), r"\| `tester` \| opus ")

        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            chosen = trial_install.choices()
            lifecycle.apply_install(prj, FRAMEWORK, lifecycle.plan_install(prj, FRAMEWORK, chosen), chosen)
            self.assertEqual((prj / USER_RULES).read_bytes(), b"")
            self.assertNotIn(kernel.USER_RULES_OPEN, text(prj / "CLAUDE.md"))

    def test_install_refuses_a_plan_made_for_other_choices(self):
        """An approval given to one roster must not install another."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            chosen = trial_install.choices()
            ops = lifecycle.plan_install(prj, FRAMEWORK, chosen)
            other = {**chosen, "agents": chosen["agents"][:-1]}
            with self.assertRaises(ValueError):
                lifecycle.apply_install(prj, FRAMEWORK, ops, other)
            self.assertEqual(tree(prj), {})

    def test_install_refuses_a_tree_that_changed_after_the_plan(self):
        """A `CLAUDE.md` written between plan and apply would be taken as the
        project part without anyone having read it. Nothing is written."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            chosen = trial_install.choices()
            ops = lifecycle.plan_install(prj, FRAMEWORK, chosen)
            (prj / "CLAUDE.md").write_text("# Later\n", encoding="utf-8")
            before = tree(prj)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_install(prj, FRAMEWORK, ops, chosen)
            self.assertIn("CLAUDE.md", str(e.exception))
            self.assertEqual(tree(prj), before)


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
            rules_before = (root / USER_RULES).read_bytes()

            self.uninstall(root)

            left = {rel for rel in tree(root) if not rel.startswith(ARCHIVE)}
            self.assertEqual(
                left,
                {
                    "CLAUDE.md",
                    SETTINGS,
                    USER_RULES,
                    "docs/TODO.md",
                    "docs/status.md",
                    "docs/roadmap.md",
                    "src/app.py",
                },
            )
            self.assertEqual(read_json(root / SETTINGS), {"env": {"A": "1"}})
            self.assertEqual(text(root / "CLAUDE.md"), trial_install.PROJECT_SECTIONS)
            self.assertEqual((root / USER_RULES).read_bytes(), rules_before)
            self.assertFalse((root / ".claude" / "agents").exists())
            archive = root / doctor.ARCHIVE_DIR
            self.assertTrue((archive / ".claude" / "claw.json").is_file())
            # Equal to what the source generates, so nobody's work: gone, not archived.
            self.assertFalse((archive / ".claude" / "agents").exists())

    def test_uninstall_archives_a_card_that_differs_from_what_is_generated(self):
        """A card someone edited holds their work; a card with their rules in it
        is not an edit, because the rules file survives."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            explorer = root / ".claude" / "agents" / "explorer.md"
            explorer.write_text(text(explorer) + "\nmy note\n", encoding="utf-8")
            note = explorer.read_bytes()

            ops = self.uninstall(root)

            self.assertEqual(actions(ops)[".claude/agents/explorer.md"], lifecycle.ARCHIVE)
            self.assertEqual((root / doctor.ARCHIVE_DIR / ".claude" / "agents" / "explorer.md").read_bytes(), note)
            self.assertEqual(actions(ops)[".claude/agents/tester.md"], lifecycle.REMOVE)
            self.assertFalse((root / ".claude" / "agents" / "tester.md").exists())

    def test_uninstall_never_deletes_what_it_did_not_write(self):
        """A file disappears from the project only if it was identical to what
        the source generates; everything else either stays or ends up in the
        archive with the same content."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            for rel in (".claude/hooks/config_protection.py", ".claude/hooks/gateguard.py"):
                p = root / rel
                p.write_text(p.read_text(encoding="utf-8") + "\n# my note\n", encoding="utf-8")
            mine = root / ".claude" / "skills" / "mine" / "SKILL.md"
            mine.parent.mkdir(parents=True)
            mine.write_text("name: mine\n", encoding="utf-8")
            (root / ".claude" / "hooks" / "mine.py").write_text("pass\n", encoding="utf-8")
            (root / ".claude" / "shared" / "mine.md").write_text("# mine\n", encoding="utf-8")
            expected = generated(root)
            before = tree(root)

            ops = self.uninstall(root)

            after = tree(root)
            self.assertEqual(
                actions(ops)[".claude/hooks/config_protection.py"], lifecycle.ARCHIVE
            )
            archived = {rel[len(ARCHIVE) :] for rel in after if rel.startswith(ARCHIVE)}
            for rel in archived:
                self.assertEqual(after[ARCHIVE + rel], before[rel], rel)
            gone = sorted(set(before) - set(after) - archived)
            self.assertTrue(gone)
            for rel in gone:
                if rel == "CLAUDE.md":
                    continue
                self.assertIn(rel, expected, f"{rel}: deleted without being generated")
                self.assertEqual(
                    hashlib.sha256(expected[rel].encode("utf-8")).hexdigest(), before[rel], rel
                )
            for rel in (mine, root / ".claude" / "hooks" / "mine.py", root / ".claude" / "shared" / "mine.md"):
                self.assertTrue(rel.is_file(), rel)

    def test_uninstall_refuses_a_plan_the_tree_has_outgrown(self):
        """The approved plan holds for the tree it was made on: a hook touched
        up afterwards is no longer "identical to the source", and deleting it
        because it was yesterday deletes today's work. The refusal comes before
        the first byte is written, not halfway."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            skill = root / ".claude" / "hooks" / "block_no_verify.py"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nnote\n", encoding="utf-8")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_uninstall(root, FRAMEWORK, ops)
            self.assertIn(".claude/hooks/block_no_verify.py", str(e.exception))
            self.assertEqual(tree(root), before)

            (root / doctor.ARCHIVE_DIR).mkdir()
            with self.assertRaises(ValueError):
                lifecycle.plan_uninstall(root, FRAMEWORK)

    def test_uninstall_refuses_a_plan_outgrown_outside_its_removals(self):
        """A card touched up after the plan would end up in the archive without
        anyone approving it, and a `CLAUDE.md` left without markers would make
        the execution fail after `settings.json` has already been rewritten: a
        half-done uninstall."""
        retouches = {
            "CLAUDE.md": lambda body: body.replace(kernel.CLOSE, ""),
            ".claude/agents/explorer.md": lambda body: body + "\nnote\n",
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
        delete project code. Every removal is re-checked against what the
        source generates, and the refusal comes before the first byte is
        written."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
            (root / ".claude" / "hooks" / "mine.py").write_text("pass\n", encoding="utf-8")
            skill = root / ".claude" / "hooks" / "config_protection.py"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nnote\n", encoding="utf-8")
            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            before = tree(root)
            for rel in ("src/app.py", ".claude/hooks/mine.py", ".claude/hooks/config_protection.py"):
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
        blocks every `git` command and linter-configuration edit, forever and without a
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


class TestUpdate(unittest.TestCase):
    def test_a_fresh_installation_has_nothing_to_update(self):
        """What install writes, update must find already right: a plan that
        lists files on an untouched installation is a generator that does not
        agree with itself, and every update would rewrite the project."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            self.assertEqual(lifecycle.plan_update(root, FRAMEWORK), [])

    def test_update_never_writes_the_rules_the_project_part_or_the_state(self):
        """These three are the project's: the rules file by definition, the rest
        of `CLAUDE.md` because it holds their words, `docs/` because it holds
        the state. An update that touched one would lose work with no finding."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / "docs" / "TODO.md").write_text("# TODO\n\nmine\n", encoding="utf-8")
            rules_before = (root / USER_RULES).read_bytes()
            todo_before = (root / "docs" / "TODO.md").read_bytes()

            run_update(root, add=["frontend"], remove=["runner"], orchestration="agent-teams")

            self.assertEqual((root / USER_RULES).read_bytes(), rules_before)
            self.assertEqual((root / "docs" / "TODO.md").read_bytes(), todo_before)
            out = text(root / "CLAUDE.md")
            self.assertEqual(out[kernel.parse(out).end :].strip("\n").split(kernel.USER_RULES_OPEN)[0].strip("\n"),
                             trial_install.PROJECT_SECTIONS.strip("\n"))
            self.assertIn("- Commit messages in English, no signature.", out)

    def test_add_and_remove_an_agent(self):
        """The card, the roster row, the guides it cites and `claw.json` move
        together; a card left behind after a removal is still read by the
        coordinator's routing."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            card = root / ".claude" / "agents" / "frontend.md"

            ops = run_update(root, add=["frontend"])

            self.assertEqual(actions(ops)[".claude/agents/frontend.md"], lifecycle.CREATE)
            self.assertIn("frontend", read_json(root / MANIFEST)["agents"])
            self.assertIn("frontend", routed(root))
            self.assertEqual(doctor.check(root), [])
            self.assertIn("frontend", lifecycle.update_summary(root, FRAMEWORK, remove=["frontend"]))

            ops = run_update(root, remove=["frontend"])

            self.assertEqual(actions(ops)[".claude/agents/frontend.md"], lifecycle.REMOVE)
            self.assertFalse(card.exists())
            self.assertNotIn("frontend", read_json(root / MANIFEST)["agents"])
            self.assertNotIn("frontend", routed(root))
            self.assertEqual(doctor.check(root), [])

    def test_add_and_remove_a_guide(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            guide = root / ".claude" / "shared" / "domain" / "llm-guide.md"

            run_update(root, add=["domain/llm-guide.md"])

            self.assertTrue(guide.is_file())
            self.assertIn(".claude/shared/domain/llm-guide.md", text(root / "CLAUDE.md"))
            self.assertIn("domain/llm-guide.md", read_json(root / MANIFEST)["guides"])
            self.assertEqual(doctor.check(root), [])

            run_update(root, remove=["domain/llm-guide.md"])

            self.assertFalse(guide.exists())
            self.assertFalse(guide.parent.exists())
            self.assertNotIn("llm-guide", text(root / "CLAUDE.md"))
            self.assertEqual(doctor.check(root), [])

    def test_requested_changes_are_validated_before_any_plan(self):
        """A name that does not exist, an agent every installation needs, two
        agents that exclude each other, a guide a card of the roster cites: each
        would produce a plan that cannot be carried out, or one that undoes
        itself at the next update."""
        bad = {
            "unknown agent": {"add": ["no-such-agent"]},
            "unknown guide": {"add": ["core/no-such.md"]},
            "already installed": {"add": ["explorer"]},
            "not installed": {"remove": ["frontend"]},
            "guide not installed": {"remove": ["domain/llm-guide.md"]},
            "an agent of every installation": {"remove": ["tester"]},
            "exclusive pair": {"add": ["deploy", "infra"]},
            "guide the roster cites": {"remove": ["core/security-guide.md"]},
            "unknown profile": {"profile_name": "nope"},
            "unknown orchestration": {"orchestration": "nope"},
            "gateguard value": {"gateguard": "maybe"},
        }
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            before = tree(root)
            for label, changes in bad.items():
                with self.subTest(label):
                    with self.assertRaises((ValueError, FileNotFoundError)):
                        lifecycle.plan_update(root, FRAMEWORK, **changes)
            self.assertEqual(tree(root), before)

    def test_profile_change_unmerges_the_old_settings_and_merges_the_new(self):
        """The framework's entries follow the profile in both directions, and the
        user's stay: a permission the old profile added and the new one does not
        want must not outlive the change."""
        extra = "Read(./**/dumps/**)"
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            data = read_json(root / SETTINGS)
            data["permissions"]["deny"].append("Read(./mine/**)")
            write_json(root / SETTINGS, data)

            ops = run_update(root, profile_name="data")

            self.assertEqual(actions(ops)[SETTINGS], lifecycle.MERGE)
            self.assertIn("software → data", reason(ops, SETTINGS))
            deny = read_json(root / SETTINGS)["permissions"]["deny"]
            self.assertIn(extra, deny)
            self.assertIn("Read(./mine/**)", deny)
            self.assertEqual(read_json(root / MANIFEST)["profile"], "data")
            self.assertIn(extra, read_json(root / MANIFEST)["settings_added"]["permissions"]["deny"])

            run_update(root, profile_name="software")

            deny = read_json(root / SETTINGS)["permissions"]["deny"]
            self.assertNotIn(extra, deny)
            self.assertIn("Read(./mine/**)", deny)
            self.assertNotIn(extra, json.dumps(read_json(root / MANIFEST)["settings_added"]))
            self.assertEqual(doctor.check(root), [])

    def test_profile_change_brings_the_new_roster_and_drops_the_old_one(self):
        """Changing the field changes who works there: a roster left as it was
        keeps the old field's agents and lacks the new one's, and the guides
        and cycles of the new field would have nobody to use them."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            before = read_json(root / MANIFEST)
            self.assertIn("comment-analyzer", before["agents"])
            header = lifecycle.update_summary(root, FRAMEWORK, profile_name="web")
            self.assertIn("+frontend", header)
            self.assertIn("−comment-analyzer", header)

            run_update(root, profile_name="web")

            now = read_json(root / MANIFEST)
            for name in ("frontend", "visual-director", "deploy"):
                self.assertIn(name, now["agents"])
                self.assertTrue((root / ".claude" / "agents" / f"{name}.md").is_file())
            self.assertNotIn("comment-analyzer", now["agents"])
            self.assertFalse((root / ".claude" / "agents" / "comment-analyzer.md").exists())
            self.assertIn("domain/design-guide.md", now["guides"])
            self.assertIn("The design cycle", text(root / ORCHESTRATION))
            self.assertEqual(doctor.check(root), [])

    def test_an_extra_the_user_added_survives_a_profile_change(self):
        """An agent chosen beyond the old field is the user's choice, not the
        field's: dropping it with the field's own agents loses a decision."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            run_update(root, add=["perf-analyst", "domain/llm-guide.md"])

            run_update(root, profile_name="web")

            now = read_json(root / MANIFEST)
            self.assertIn("perf-analyst", now["agents"])
            self.assertIn("domain/llm-guide.md", now["guides"])

    def test_remove_wins_over_the_new_profile_in_the_same_call(self):
        """`--profile web --remove deploy` asks for the field without one of its
        agents: the removal applies on top of the profile, not before it."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            run_update(root, profile_name="web", remove=["deploy"])
            agents = read_json(root / MANIFEST)["agents"]
            self.assertIn("frontend", agents)
            self.assertNotIn("deploy", agents)

    def test_a_differing_user_value_stays_and_is_named(self):
        """The user's own value for a key the framework also sets is theirs:
        overwriting it silently changes their setup, dropping it from the plan
        hides that it is not the framework's."""
        key = "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH"
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            data = read_json(root / SETTINGS)
            data["env"][key] = "3"
            data["env"]["MINE"] = "x"
            write_json(root / SETTINGS, data)

            ops = lifecycle.plan_update(root, FRAMEWORK, add=["frontend"])
            self.assertIn(key, reason(ops, SETTINGS))
            lifecycle.apply_update(root, FRAMEWORK, ops, add=["frontend"])

            env = read_json(root / SETTINGS)["env"]
            self.assertEqual((env[key], env["MINE"]), ("3", "x"))

    def test_keep_version_is_refused_when_the_source_has_another_version(self):
        """`--keep-version` applies without a second look because nothing the
        new release brings is in the plan. Another version means it is, and the
        plan must be read."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            manifest = read_json(root / MANIFEST)
            manifest["version"] = "1.0.0"
            write_json(root / MANIFEST, manifest)
            before = tree(root)
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["update", str(root), "--add", "frontend", "--keep-version"])
            self.assertEqual(code, 1)
            self.assertIn("--keep-version", out.getvalue())
            self.assertEqual(tree(root), before)

    def test_keep_version_plans_and_applies_in_one_call(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["update", str(root), "--add", "frontend", "--keep-version"])
            self.assertEqual(code, 0, out.getvalue())
            self.assertTrue((root / ".claude" / "agents" / "frontend.md").is_file())
            self.assertIn("agents +frontend", out.getvalue())
            self.assertEqual(doctor.check(root), [])

    def test_keep_version_is_refused_when_it_would_overwrite_a_hand_edit(self):
        """`--keep-version` applies with no ok: a plan line that destroys the
        user's edit would go through unseen. It must stop and leave the tree."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            explorer = root / ".claude" / "agents" / "explorer.md"
            explorer.write_text(text(explorer) + "\nmy own rule\n", encoding="utf-8")
            before = tree(root)
            out = io.StringIO()
            with redirect_stdout(out):
                code = cli.main(["update", str(root), "--add", "frontend", "--keep-version"])
            self.assertEqual(code, 1)
            self.assertIn("edited by hand", out.getvalue())
            self.assertEqual(tree(root), before)

    def test_a_hand_edited_card_is_named_in_the_plan(self):
        """An edit made to a generated file is lost at the update, by design; the
        plan has to say so, or the user finds out when their change is gone."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            explorer = root / ".claude" / "agents" / "explorer.md"
            explorer.write_text(text(explorer) + "\nmy own rule\n", encoding="utf-8")

            ops = lifecycle.plan_update(root, FRAMEWORK)

            self.assertEqual(actions(ops), {".claude/agents/explorer.md": lifecycle.OVERWRITE})
            self.assertIn("modified by hand", reason(ops, ".claude/agents/explorer.md"))
            self.assertIn("user-rules.md", reason(ops, ".claude/agents/explorer.md"))
            lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertNotIn("my own rule", text(explorer))
            self.assertEqual(lifecycle.plan_update(root, FRAMEWORK), [])

    def test_a_change_in_the_rules_is_not_called_a_hand_edit(self):
        """Editing `user-rules.md` and updating is the normal way to change a
        rule: the files that differ differ because of it. Calling that a hand
        edit would tell the user their own change is a loss."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rules_file = root / USER_RULES
            rules_file.write_bytes(
                (text(rules_file) + "\n## explorer\neffort: high\n- be terse\n").encode("utf-8")
            )
            edit(rules_file, "- Commit messages in English, no signature.", "- Commit messages in English.")

            ops = lifecycle.plan_update(root, FRAMEWORK)

            self.assertEqual(
                set(actions(ops)),
                {"CLAUDE.md", ".claude/agents/explorer.md", ORCHESTRATION},
            )
            for path in actions(ops):
                self.assertNotIn("by hand", reason(ops, path), path)
            lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertIn("be terse", text(root / ".claude" / "agents" / "explorer.md"))
            self.assertIn("effort: high\n", text(root / ".claude" / "agents" / "explorer.md"))
            self.assertEqual(lifecycle.plan_update(root, FRAMEWORK), [])

    def test_update_refuses_a_claude_md_without_the_marker(self):
        """Without the marker nobody can tell the framework's text from the
        project's: guessing would delete one or duplicate the other. The refusal
        names the cause; nothing is written."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            claude = root / "CLAUDE.md"
            claude.write_text(re.sub(r"<!-- /?FRAMEWORK:KERNEL[^>]*-->", "", text(claude)), encoding="utf-8")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.plan_update(root, FRAMEWORK, add=["frontend"])
            self.assertIn("marker", str(e.exception))
            self.assertEqual(tree(root), before)

    def test_apply_writes_nothing_when_the_tree_changed_after_the_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            ops = lifecycle.plan_update(root, FRAMEWORK, add=["frontend"])
            edit(root / "CLAUDE.md", "## Current state\n", "## Current state\n\nlater\n")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_update(root, FRAMEWORK, ops, add=["frontend"])
            self.assertIn("CLAUDE.md", str(e.exception))
            self.assertEqual(tree(root), before)

    def test_apply_refuses_a_plan_made_for_other_changes(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            ops = lifecycle.plan_update(root, FRAMEWORK, add=["frontend"])
            before = tree(root)
            with self.assertRaises(ValueError):
                lifecycle.apply_update(root, FRAMEWORK, ops, add=["perf-analyst"])
            self.assertEqual(tree(root), before)

    def test_a_new_release_brings_its_text_and_keeps_the_project(self):
        """A source one release ahead: the method text and the version move, the
        project part, the rules and the state do not."""
        with tempfile.TemporaryDirectory() as d:
            fw = source_copy(d)
            root = install(d)
            manifest = read_json(root / MANIFEST)
            manifest["version"] = "2.0.0"
            write_json(root / MANIFEST, manifest)
            edit(fw / "method" / "20-evidence.md", "Every action starts", "Each action starts")
            (fw / "VERSION").write_text("9.9.9\n", encoding="utf-8")
            project = trial_install.PROJECT_SECTIONS.strip("\n")

            ops = lifecycle.plan_update(root, fw)
            self.assertEqual(reason(ops, "CLAUDE.md"), "v2.0.0 → v9.9.9")
            self.assertEqual(reason(ops, MANIFEST), "v2.0.0 → v9.9.9")
            lifecycle.apply_update(root, fw, ops)

            out = text(root / "CLAUDE.md")
            self.assertIn("Each action starts", out)
            self.assertEqual(kernel.parse(out).version, "9.9.9")
            self.assertIn(project, out)
            self.assertIn("- Commit messages in English, no signature.", out)
            self.assertEqual(read_json(root / MANIFEST)["version"], "9.9.9")
            self.assertEqual(kernel.parse(text(root / ".claude" / "agents" / "tester.md")).version, "9.9.9")
            self.assertEqual(lifecycle.plan_update(root, fw), [])

    def test_gateguard_goes_on_and_off_with_its_script_and_its_entry(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "prj"
            root.mkdir()
            chosen = {**trial_install.choices(), "hooks": ["config_protection", "block_no_verify"]}
            lifecycle.apply_install(root, FRAMEWORK, lifecycle.plan_install(root, FRAMEWORK, chosen), chosen)
            script = root / ".claude" / "hooks" / "gateguard.py"
            self.assertFalse(script.exists())

            run_update(root, gateguard="on")
            self.assertTrue(script.is_file())
            self.assertIn("gateguard", json.dumps(read_json(root / SETTINGS)["hooks"]))
            self.assertIn("gateguard", read_json(root / MANIFEST)["hooks"])
            self.assertEqual(lifecycle.plan_update(root, FRAMEWORK), [])

            run_update(root, gateguard="off")
            self.assertFalse(script.exists())
            self.assertNotIn("gateguard", json.dumps(read_json(root / SETTINGS)["hooks"]))
            self.assertEqual(doctor.check(root), [])

    def test_orchestration_change_moves_the_guide_and_the_settings(self):
        """The agent-teams variables belong to the orchestration: they go in with
        it and out with it, or a project that left agent teams keeps them on."""
        env = settings.ORCHESTRATION_SETTINGS["agent-teams"]["env"]
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            run_update(root, orchestration="agent-teams")
            self.assertIn("## Orchestration: Agent teams", text(root / ORCHESTRATION))
            for key, value in env.items():
                self.assertEqual(read_json(root / SETTINGS)["env"][key], value)
            self.assertEqual(doctor.check(root), [])

            run_update(root, orchestration="orchestrator-worker")
            self.assertNotIn("Agent teams", text(root / ORCHESTRATION))
            for key in env:
                self.assertNotIn(key, read_json(root / SETTINGS)["env"])

    def test_a_stale_hook_entry_is_replaced_not_doubled(self):
        """An entry written by an older release, or touched up, launches the same
        script as the current one: merging the current entry beside it would run
        the hook twice."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            data = read_json(root / SETTINGS)
            entry = data["hooks"]["PreToolUse"][0]["hooks"][0]
            name = lifecycle._hook_name(entry)
            current = entry["command"]
            old = "echo old-release; exit 0"
            entry["command"] = old + f" # .claude/hooks/{name}.py"
            write_json(root / SETTINGS, data)
            manifest = read_json(root / MANIFEST)
            manifest["settings_added"]["hooks"]["PreToolUse"][0]["hooks"][0] = entry
            write_json(root / MANIFEST, manifest)

            ops = run_update(root)

            self.assertEqual(actions(ops)[SETTINGS], lifecycle.MERGE)
            body = (root / SETTINGS).read_text(encoding="utf-8")
            self.assertNotIn(old, body)
            self.assertEqual(body.count(f".claude/hooks/{name}.py"), 1)
            commands = [h["command"] for g in read_json(root / SETTINGS)["hooks"]["PreToolUse"] for h in g["hooks"]]
            self.assertIn(current, commands)
            self.assertNotIn(old, (root / MANIFEST).read_text(encoding="utf-8"))

    def test_update_puts_back_what_went_missing(self):
        """The repair that used to be a command of its own: a file the choices
        name and the tree lacks is created again, the state files included."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            gone = [".claude/hooks/block_no_verify.py", ".claude/agents/runner.md", "docs/status.md"]
            for rel in gone:
                (root / rel).unlink()
            data = read_json(root / SETTINGS)
            del data["hooks"]
            write_json(root / SETTINGS, data)

            ops = run_update(root)

            for rel in gone:
                self.assertEqual(actions(ops)[rel], lifecycle.CREATE, rel)
            self.assertEqual(actions(ops)[SETTINGS], lifecycle.MERGE)
            self.assertEqual(doctor.check(root), [])
            self.assertEqual(lifecycle.plan_update(root, FRAMEWORK), [])

    def test_a_manifest_without_the_choices_cannot_be_updated(self):
        """A claw.json from before 3.0 records no roster: regenerating from it
        would install a roster nobody chose."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            write_json(root / MANIFEST, {"source": "x", "version": "2.7.0", "profile": "software"})
            with self.assertRaises(ValueError) as e:
                lifecycle.plan_update(root, FRAMEWORK)
            self.assertIn("agents", str(e.exception))


class TestUpdateLeavesNoResidue(unittest.TestCase):
    """An updated installation is byte for byte the fresh installation of its
    final choices: whatever an update forgets to take away — a card, a guide,
    a cycle, a roster row, a settings entry, a hook — shows up as a difference."""

    SEQUENCES = {
        "agent and guide in and out": [
            {"add": ["frontend", "domain/llm-guide.md"]},
            {"remove": ["frontend", "domain/llm-guide.md"]},
        ],
        "profile there and back": [{"profile_name": "web"}, {"profile_name": "software"}],
        "profile to another field": [{"profile_name": "data"}, {"profile_name": "web"}],
        "orchestration there and back": [
            {"orchestration": "agent-teams"},
            {"orchestration": "orchestrator-worker"},
        ],
        "gateguard off and on": [{"gateguard": "off"}, {"gateguard": "on"}],
        "everything at once": [
            {"add": ["perf-analyst", "domain/llm-guide.md"]},
            {"profile_name": "data", "orchestration": "agent-teams"},
            {"gateguard": "off", "remove": ["domain/llm-guide.md"]},
            {"profile_name": "web", "remove": ["deploy"]},
        ],
    }

    def test_an_updated_installation_equals_a_fresh_one(self):
        for label, steps in self.SEQUENCES.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                root = install(d)
                for changes in steps:
                    run_update(root, **changes)
                final = lifecycle.installed_choices(read_json(root / MANIFEST))

                fresh = Path(d) / "fresh"
                (fresh / ".claude").mkdir(parents=True)
                (fresh / "CLAUDE.md").write_bytes(trial_install.PROJECT_SECTIONS.encode("utf-8"))
                (fresh / USER_RULES).write_bytes(trial_install.USER_RULES.encode("utf-8"))
                lifecycle.apply_install(fresh, FRAMEWORK, lifecycle.plan_install(fresh, FRAMEWORK, final), final)

                updated, new = tree(root), tree(fresh)
                diff = sorted(
                    rel for rel in updated.keys() | new.keys() if updated.get(rel) != new.get(rel)
                )
                self.assertEqual(diff, [])


if __name__ == "__main__":
    unittest.main()
