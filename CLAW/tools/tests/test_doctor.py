import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fwbuild import assemble, doctor, kernel
from fwbuild import settings as fw_settings

AGENT_FM = "---\nname: {n}\nmodel: opus\neffort: high\n---\n"
# The source's version, not a literal: `VERSION_MISMATCH` compares the project
# with the source, and a fixed value would make the suite fail at the first
# VERSION bump.
VERSION = (Path(__file__).resolve().parents[2] / "VERSION").read_text(
    encoding="utf-8"
).strip()


def make_project(
    tmp,
    *,
    agents=("explorer",),
    routing=("explorer",),
    manifest_agents=None,
    fable=False,
    state=True,
    orchestration=True,
    leak=False,
    markers=True,
    settings=True,
    hooks=True,
    guides=(),
    manifest=True,
    accepted=None,
):
    root = Path(tmp)
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "shared").mkdir(parents=True)
    if manifest:
        data = {
            "version": VERSION,
            "profile": "software",
            "orchestration": "orchestrator-worker",
            "agents": list(agents if manifest_agents is None else manifest_agents),
            "guides": list(guides),
            "hooks": ["config_protection", "block_no_verify"],
        }
        if accepted is not None:
            data["accepted"] = accepted
        (root / ".claude" / "claw.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
    if settings:
        closed = [n for n in fw_settings.HOOKS if n not in fw_settings.OPTIONAL_HOOKS]
        wired = fw_settings.hooks(closed) if hooks else {}
        (root / ".claude" / "settings.json").write_text(json.dumps(wired), encoding="utf-8")
        (root / ".claude" / "hooks").mkdir()
        for n in closed if hooks else ():
            (root / ".claude" / "hooks" / f"{n}.py").write_text("pass\n", encoding="utf-8")
    for rel in guides:
        g = root / ".claude" / "shared" / rel
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_text("# guide", encoding="utf-8")
    (root / "docs").mkdir(parents=True)
    cell = ("fable" if fable else "opus") + " high"
    rows = "\n".join(f"| where | `{n}` | {cell} |" for n in routing)
    if orchestration:
        # The routing table lives in the coordinator's guide, not in CLAUDE.md:
        # it is content the subagents must not pay for. The guide has no marker.
        (root / ".claude" / "shared" / "orchestration.md").write_text(
            assemble.build_document_from_text(
                "## Delegation\n",
                VERSION,
                "| Situation | Agent | Model |\n|---|---|---|\n" + rows + "\n",
                markers=False,
            ),
            encoding="utf-8",
        )
    project = "## The project\n\nA trial project.\n"
    if leak:
        project += "\n## The code cycle\n\nExplorer, then architect.\n"
    (root / "CLAUDE.md").write_text(
        assemble.build_document_from_text("## Method\n", VERSION, project, markers=markers),
        encoding="utf-8",
    )
    for n in agents:
        model = "fable" if fable else "opus"
        fm = AGENT_FM.format(n=n).replace("model: opus", f"model: {model}")
        (root / ".claude" / "agents" / f"{n}.md").write_text(
            kernel.normalize(fm) + "\n" + kernel.wrap("## Method\n", VERSION),
            encoding="utf-8",
        )
    if state:
        for f in ("TODO.md", "status.md", "roadmap.md"):
            (root / "docs" / f).write_text("# empty\n", encoding="utf-8")
    return root


def hand_built_fixture(test):
    """`make_project` is not an installation the source generated, so
    GENERATED_DIFF would fire on every file of it: tests built on it switch the
    check off. The ones that exercise it install for real, without this."""
    patch = mock.patch.object(doctor, "_generated_diff", return_value=[])
    patch.start()
    test.addCleanup(patch.stop)


def strip_markers(text):
    return re.sub(r"<!-- /?FRAMEWORK:KERNEL[^>]*-->", "", text)


def codes(findings):
    return {f.code for f in findings}


class TestDoctor(unittest.TestCase):
    def setUp(self):
        hand_built_fixture(self)

    def test_clean_project_has_no_findings(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(doctor.check(make_project(d)), [])

    def test_detects_agent_in_the_manifest_without_file(self):
        """The roster is what `claw.json` records: a card that went missing is
        found there, and a card only the routing table names is not a roster
        member."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, agents=("explorer",), manifest_agents=("explorer", "frontend"))
            found = [f for f in doctor.check(p) if f.code == "ROSTER_MISSING"]
            self.assertEqual([f.severity for f in found], ["ERROR"])
            self.assertIn("frontend", found[0].message)
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, agents=("explorer",), routing=("explorer", "frontend"))
            self.assertNotIn("ROSTER_MISSING", codes(doctor.check(p)))

    def test_detects_missing_state_files(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, state=False))
            self.assertIn("STATE_MISSING", codes(found))

    def test_detects_fable(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("FABLE", codes(doctor.check(make_project(d, fable=True))))

    def test_detects_missing_orchestration_guide(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, orchestration=False))
            self.assertIn("SHARED_MISSING", codes(found))

    def test_detects_coordinator_content_leaking_into_claude_md(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, leak=True))
            self.assertIn("COORDINATOR_LEAK", codes(found))

    def test_detects_deploy_infra_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d,
                agents=("explorer", "deploy", "infra"),
                routing=("explorer", "deploy", "infra"),
            )
            self.assertIn("EXCLUSIVE", codes(doctor.check(p)))

    def test_detects_stripped_kernel_markers(self):
        """Without the markers in `CLAUDE.md` an update cannot tell the
        framework's text from the project's and refuses: the installation is
        stuck, and nothing else says so."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / "CLAUDE.md"
            f.write_text(strip_markers(f.read_text(encoding="utf-8")), encoding="utf-8")
            self.assertIn("KERNEL_MISSING", codes(doctor.check(p)))

    def test_a_card_without_its_markers_is_not_flagged(self):
        """Cards are regenerated whole: there is no project text in them that
        the marker protects. Only `CLAUDE.md` has a region."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / ".claude" / "agents" / "explorer.md"
            f.write_text(strip_markers(f.read_text(encoding="utf-8")), encoding="utf-8")
            self.assertNotIn("KERNEL_MISSING", codes(doctor.check(p)))

    def test_detects_dangling_shared_pointer_in_an_agent(self):
        """Almost every pointer to a guide lives in the agents: checking them
        only in CLAUDE.md leaves the majority uncovered."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / ".claude" / "agents" / "explorer.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "See `.claude/shared/core/absent.md`.",
                encoding="utf-8",
            )
            self.assertIn("SHARED_MISSING", codes(doctor.check(p)))

    def _rewrap(self, f, version):
        """Rewrites a file's kernel region at another version, leaving the hash
        consistent: it is the case no other check sees."""
        text = f.read_text(encoding="utf-8")
        r = kernel.parse(text)
        f.write_text(
            text[: r.start] + kernel.wrap(r.body, version) + text[r.end + 1 :],
            encoding="utf-8",
        )

    def test_detects_missing_settings_file(self):
        """`settings.json` carries the profile's permissions, among them the
        prohibition on reading secrets: absent, that prohibition does not
        exist."""
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, settings=False))
            self.assertIn("SETTINGS_MISSING", codes(found))

    def test_detects_closed_hooks_not_wired(self):
        """An installation born before the hooks has none of their checks, and
        nothing else says so."""
        with tempfile.TemporaryDirectory() as d:
            found = [f for f in doctor.check(make_project(d, hooks=False)) if f.code == "HOOKS_MISSING"]
            self.assertEqual({f.severity for f in found}, {"WARN"})
            self.assertEqual(len(found), 2)

    def test_detects_a_wired_hook_whose_script_is_gone(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / ".claude" / "hooks" / "block_no_verify.py").unlink()
            found = [f for f in doctor.check(p) if f.code == "HOOKS_MISSING"]
            self.assertEqual([f.severity for f in found], ["ERROR"])
            self.assertIn("block_no_verify", found[0].message)

    def test_detects_shared_guide_nobody_cites(self):
        """The inverse of SHARED_MISSING: a guide installed and never cited is
        context paid for and never opened."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, guides=("core/never-cited.md",))
            self.assertIn("SHARED_ORPHAN", codes(doctor.check(p)))

    def test_cited_shared_guide_is_not_an_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, guides=("core/cited.md",))
            f = p / "CLAUDE.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "`.claude/shared/core/cited.md`",
                encoding="utf-8",
            )
            self.assertNotIn("SHARED_ORPHAN", codes(doctor.check(p)))

    def test_detects_missing_manifest(self):
        """Without `claw.json` `/claw` cannot find the source and
        the fleet report does not count the project: it is not a clean
        installation."""
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, manifest=False))
            self.assertIn("MANIFEST_MISSING", codes(found))

    def test_detects_manifest_without_the_choices(self):
        """Without the profile and the lists, an update has nothing to
        regenerate from: a manifest from before 3.0 must say so, not look
        healthy."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / ".claude" / "claw.json").write_text(
                json.dumps({"source": "framework", "version": VERSION}),
                encoding="utf-8",
            )
            found = [f for f in doctor.check(p) if f.code == "MANIFEST_MISSING"]
            self.assertEqual([f.severity for f in found], ["WARN"])
            for key in ("profile", "orchestration", "agents", "guides", "hooks"):
                self.assertIn(key, found[0].message)

    def test_accepted_warning_becomes_a_note(self):
        """The valve: a warning the project declares it accepts stays printed
        and stops blocking, instead of keeping a CI red forever until somebody
        learns to ignore it."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d,
                guides=("core/never-cited.md",),
                accepted={"SHARED_ORPHAN": "deliberate, only a future agent cites it"},
            )
            found = [f for f in doctor.check(p) if f.code == "SHARED_ORPHAN"]
            self.assertEqual([f.severity for f in found], ["NOTE"])
            self.assertFalse([f for f in found if f.blocking])

    def test_accepted_does_not_cover_errors(self):
        """A warning is a judgement, and on a judgement a project may be right.
        An error is a broken installation: it stays broken."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d, state=False, accepted={"STATE_MISSING": "I live with it"}
            )
            found = doctor.check(p)
            self.assertIn("STATE_MISSING", {f.code for f in found if f.severity == "ERROR"})
            self.assertIn("ACCEPTED_UNUSED", codes(found))

    def test_accepted_without_a_reason_does_not_apply(self):
        """A waiver without a reason is not a waiver: it is seen, not applied."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d, guides=("core/never-cited.md",), accepted={"SHARED_ORPHAN": "  "}
            )
            found = doctor.check(p)
            self.assertIn("SHARED_ORPHAN", {f.code for f in found if f.severity == "WARN"})
            self.assertIn("ACCEPTED_UNUSED", codes(found))

    def test_accepted_that_matches_nothing_is_reported(self):
        """A waiver outliving its finding silences the next one."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, accepted={"TOKEN_BUDGET": "monorepo"})
            self.assertEqual(codes(doctor.check(p)), {"ACCEPTED_UNUSED"})

    def test_accepted_can_be_scoped_to_one_file(self):
        """`CODE:fragment` covers the finding whose message names that file and
        no other: a waiver for one file must not silence the same code elsewhere."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, accepted={"PERSONAL_PATH:.claude/settings.json": "local waiver"})
            home = "C:" + "\\Users\\"
            (p / ".claude" / "settings.json").write_text(
                json.dumps({"env": {"PRJ": home + "jsmith"}}), encoding="utf-8"
            )
            found = [f for f in doctor.check(p) if f.code == "PERSONAL_PATH"]
            self.assertEqual([f.severity for f in found], ["NOTE"])

    def test_detects_version_skew_between_documents(self):
        """Two documents of the same project at different versions: the hash
        matches on both, because each matches its own method."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            self._rewrap(p / ".claude" / "agents" / "explorer.md", "0.3.0")
            self.assertIn("VERSION_MISMATCH", codes(doctor.check(p)))

    def test_detects_a_manifest_left_on_the_previous_version(self):
        """The version in `claw.json` is the one readable without opening a
        generated document — the fleet report starts from it: if it stays on the
        previous one, the finding says so."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            path = p / ".claude" / "claw.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["version"] = "0.3.0"
            path.write_text(json.dumps(data), encoding="utf-8")
            found = [f for f in doctor.check(p) if f.code == "VERSION_MISMATCH"]
            self.assertEqual([f.severity for f in found], ["WARN"])
            self.assertIn("claw.json", found[0].message)

    def test_detects_installation_behind_the_source(self):
        """An old but internally consistent method: it is the fork between
        projects, and the hash does not see it."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            tracked = [p / "CLAUDE.md"] + list((p / ".claude" / "agents").glob("*.md"))
            for f in tracked:
                self._rewrap(f, "0.3.0")
            self.assertEqual(codes(doctor.check(p)), {"VERSION_MISMATCH"})

    def test_detects_bidi_control_in_an_agent(self):
        """A bidirectional control reverses on screen the text that follows: the
        model reads one instruction, whoever reviews the card sees another."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / ".claude" / "agents" / "explorer.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "Read \u202evne.\n", encoding="utf-8"
            )
            self.assertIn("UNSAFE_UNICODE", codes(doctor.check(p)))

    def test_emoji_variation_selector_and_leading_bom_are_not_unsafe(self):
        """U+FE0F composes emoji and sits in the source itself; the BOM at the
        start of a file is written by editors. Flagging them would make
        `--strict` fail on a healthy installation."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / "docs" / "status.md").write_text(
                "\ufeff# Status\n\nClosed \u2714\ufe0f\n", encoding="utf-8"
            )
            self.assertNotIn("UNSAFE_UNICODE", codes(doctor.check(p)))

    def test_detects_personal_path_but_not_a_placeholder(self):
        """A user's folder does not exist on the machine of whoever clones; an
        example's `YourName` belongs to nobody. `settings.json` is JSON, and
        JSON doubles the backslashes."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            settings = p / ".claude" / "settings.json"
            home = "C:" + "\\Users\\"
            settings.write_text(
                json.dumps({"env": {"PRJ": home + "YourName"}}), encoding="utf-8"
            )
            self.assertNotIn("PERSONAL_PATH", codes(doctor.check(p)))
            settings.write_text(
                json.dumps({"env": {"PRJ": home + "jsmith"}}), encoding="utf-8"
            )
            self.assertIn("PERSONAL_PATH", codes(doctor.check(p)))

    def test_shared_user_folders_are_not_personal_and_case_does_not_hide_one(self):
        """`Public`, `Shared`, `Default`, `All Users` are on every machine and
        belong to nobody; on Windows `c:\\users\\` is the same folder as
        `C:\\Users\\`."""
        shared = (
            "C:" + "/Users/" + "Public",
            "/Users/" + "Shared",
            "C:" + "\\Users\\" + "Default",
            "C:" + "\\Users\\" + "All Users",
        )
        for text in shared:
            with self.subTest(text=text):
                self.assertIsNone(doctor.PERSONAL_PATH_RE.search(text))
        self.assertIsNotNone(doctor.PERSONAL_PATH_RE.search("c:" + "\\users\\" + "jsmith"))

    def test_a_scanned_file_that_is_not_utf8_is_still_scanned(self):
        """The user's skills and hooks are only scanned: one saved in cp1252
        must not bring down the doctor, nor `fwbuild report`."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            home = ("C:" + "\\Users\\" + "jsmith").encode("utf-8")
            hooks = p / ".claude" / "hooks"
            hooks.mkdir(exist_ok=True)
            (hooks / "mine.py").write_bytes(b"# citt\xe0\n")
            (p / ".claude" / "skills" / "mine").mkdir(parents=True)
            (p / ".claude" / "skills" / "mine" / "SKILL.md").write_bytes(
                b"name: mine\ncitt\xe0 " + home + b"\n"
            )
            self.assertEqual(codes(doctor.check(p)), {"PERSONAL_PATH"})

    def test_an_uninstall_archive_is_not_checked(self):
        """The archive keeps the cards as they were, pointers included: it is
        material to consult, not an installation. Scanning it would give errors
        no change to the project can remove."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            old = p / doctor.ARCHIVE_DIR / ".claude" / "agents" / "old.md"
            old.parent.mkdir(parents=True)
            old.write_text("See `.claude/shared/core/lost.md`.\n", encoding="utf-8")
            self.assertEqual(doctor.check(p), [])


class TestRulesUnknown(unittest.TestCase):
    def setUp(self):
        hand_built_fixture(self)

    def _found(self, text):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            if text is not None:
                (p / ".claude" / "user-rules.md").write_text(text, encoding="utf-8")
            return [f for f in doctor.check(p) if f.code == "RULES_UNKNOWN"]

    def test_a_section_for_nobody_is_reported_and_named(self):
        """`## explorr` is a typo: the rule under it reaches no card, and its
        author believes it is in force."""
        found = self._found("## All\n\nrule\n\n## explorr\n\nrule\n")
        self.assertEqual([f.severity for f in found], ["WARN"])
        self.assertIn("## explorr", found[0].message)
        self.assertIn("user-rules.md", found[0].message)

    def test_text_before_the_first_section_is_reported(self):
        """Stray text is parsed and applied to nobody."""
        found = self._found("a rule with no heading\n\n## All\n\nrule\n")
        self.assertEqual(len(found), 1)
        self.assertIn("before the first", found[0].message)

    def test_a_file_that_does_not_parse_is_reported_once(self):
        """A duplicate section or an override under All makes `update` refuse;
        the doctor must say what and where, not stay silent."""
        found = self._found("## All\n\na\n\n## All\n\nb\n")
        self.assertEqual(len(found), 1)
        self.assertIn("## All", found[0].message)
        found = self._found("## All\n\nmodel: opus\n")
        self.assertEqual(len(found), 1)
        self.assertIn("under '## All'", found[0].message)

    def test_a_clean_file_and_a_missing_file_are_silent(self):
        """A known agent's section and `## All` are what the file is for; no
        file at all is the normal state of a project with no rules."""
        self.assertEqual(self._found("## All\n\nrule\n\n## explorer\n\nmodel: sonnet\n\nrule\n"), [])
        self.assertEqual(self._found(None), [])


class TestGeneratedDiff(unittest.TestCase):
    """Against real installs: the check compares with what the source generates."""

    def _install(self, d):
        from tests.test_lifecycle import install

        return install(d)

    def _diff(self, root):
        return [f for f in doctor.check(root) if f.code == "GENERATED_DIFF"]

    def test_a_fresh_install_has_no_difference(self):
        """The regeneration is the installer's own: any finding here would be
        the check disagreeing with the writer."""
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(self._diff(self._install(d)), [])

    def test_a_hand_edited_card_is_named(self):
        """An edit in a generated card is lost at the next update; the finding
        must name the file so it can be moved to user-rules.md."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            card = root / ".claude" / "agents" / "explorer.md"
            card.write_bytes(card.read_bytes() + b"\nA hand-written rule.\n")
            found = self._diff(root)
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].severity, "WARN")
            self.assertIn(".claude/agents/explorer.md", found[0].message)
            self.assertIn("--keep-version", found[0].message)

    def test_a_user_rules_edit_not_regenerated_is_named(self):
        """The rule is in user-rules.md but not yet in CLAUDE.md: the project
        believes it is in force."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            rules_file = root / ".claude" / "user-rules.md"
            rules_file.write_bytes(rules_file.read_bytes() + b"\n## explorer\n\nNew rule.\n")
            found = self._diff(root)
            self.assertEqual([f.message.split(":")[0] for f in found], [".claude/agents/explorer.md"])

    def test_the_project_part_of_claude_md_is_not_compared(self):
        """Only the two framework regions are the framework's: what the owner
        wrote in CLAUDE.md changes at will."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            claude = root / "CLAUDE.md"
            claude.write_bytes(claude.read_bytes() + b"\n## My notes\n\nWritten by the owner.\n")
            self.assertEqual(self._diff(root), [])

    def test_a_card_in_the_manifest_that_the_source_lacks_is_a_finding(self):
        """An agent listed in `claw.json.agents` with no source card made the
        regeneration fail, and the check vanished without a word: the failure
        must be a finding naming the cause. ROSTER_MISSING is not involved."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            path = root / ".claude" / "claw.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["agents"].append("my-own-agent")
            path.write_text(json.dumps(data), encoding="utf-8")
            (root / ".claude" / "agents" / "my-own-agent.md").write_text("---\nname: x\n---\n", encoding="utf-8")
            found = self._diff(root)
            self.assertEqual(len(found), 1)
            self.assertIn("cannot regenerate to compare", found[0].message)
            self.assertIn("my-own-agent", found[0].message)
            self.assertNotIn("ROSTER_MISSING", {f.code for f in doctor.check(root)})

    def test_nothing_is_compared_when_the_versions_differ(self):
        """At another version every file differs by design: VERSION_MISMATCH
        speaks, GENERATED_DIFF would only repeat it once per file."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            path = root / ".claude" / "claw.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["version"] = "0.0.1"
            path.write_text(json.dumps(data), encoding="utf-8")
            card = root / ".claude" / "agents" / "explorer.md"
            card.write_bytes(card.read_bytes() + b"\nedit\n")
            self.assertEqual(self._diff(root), [])


if __name__ == "__main__":
    unittest.main()
