import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import assemble, cli, doctor, kernel, lifecycle, profile, settings, source

FRAMEWORK = Path(__file__).resolve().parents[2]
SURFACE_ONLY = {"compliance-reviewer", "perf-analyst"}
CONF_PERCENT_RE = re.compile(r"CONF:.*%")


class TestRealFramework(unittest.TestCase):
    def test_version_file_exists(self):
        self.assertTrue((FRAMEWORK / "VERSION").is_file())

    def test_all_twenty_nine_agents_present(self):
        self.assertEqual(len(list((FRAMEWORK / "agents").glob("*.md"))), 29)

    def test_no_agent_declares_fable(self):
        for p in (FRAMEWORK / "agents").glob("*.md"):
            self.assertNotIn("model: fable", p.read_text(encoding="utf-8"), p.name)

    def test_effort_policy(self):
        """Never `max`; `xhigh` only on `opus`."""
        for p in (FRAMEWORK / "agents").glob("*.md"):
            text = p.read_text(encoding="utf-8")
            self.assertNotIn("effort: max", text, p.name)
            if "effort: xhigh" in text:
                self.assertIn("model: opus", text, p.name)

    def test_agent_colors_are_platform_values(self):
        """`color` has eight documented values. A setting the platform does not
        recognise does not fail, it is ignored, which is how it stays wrong
        forever."""
        valid = {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}
        for path in sorted((FRAMEWORK / "agents").glob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("color:"):
                    self.assertIn(line.split(":", 1)[1].strip(), valid, path.name)
                    break

    def test_read_only_reviewers_have_no_shell(self):
        """"Does not modify the code" over a shell is a promise, not a
        guarantee. For whoever has nothing to execute, removing it turns that
        into the card's configuration."""
        for name in (
            "security-reviewer",
            "compliance-reviewer",
            "data-quality-reviewer",
            "scientific-reviewer",
            "claim-reviewer",
        ):
            text = (FRAMEWORK / "agents" / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("tools: Read, Grep, Glob\n", text, name)

    def test_every_profile_denies_the_same_secrets(self):
        """A permission that depends on the field is a permission somebody
        forgot to copy."""
        needed = {
            "Read(./**/.env)",
            "Read(./**/.env.*)",
            "Read(./**/*.env)",
            "Read(./**/*.key)",
            "Read(./**/*.pem)",
        }
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            prof = profile.load(path)
            deny = set(prof.settings["permissions"]["deny"])
            self.assertEqual(needed - deny, set(), prof.name)

    def test_state_templates_use_one_placeholder_syntax(self):
        """The doctor recognises one placeholder syntax only: a second one would
        let a line to be filled survive the installation, with no finding."""
        for name in ("TODO.md", "status.md", "roadmap.md"):
            text = (FRAMEWORK / "templates" / name).read_text(encoding="utf-8")
            self.assertNotIn("{{", text, name)
            for line in text.splitlines():
                self.assertFalse(line.strip().startswith("<"), f"{name}: {line}")

    def test_profiles_declare_no_deferred_roster(self):
        """No field for agents "to be installed later": `roster` installs
        everything the profile lists, and such a field would say the opposite
        of what it does."""
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            self.assertNotIn("on_demand", path.read_text(encoding="utf-8"), path.name)

    def test_every_agent_splits_and_assembles(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        for p in sorted((FRAMEWORK / "agents").glob("*.md")):
            fm, method, domain = assemble.split_source(p.read_text(encoding="utf-8"))
            built = assemble.build_agent(fm, method, domain, version)
            self.assertEqual(kernel.verify(built), "OK", p.name)
            self.assertIn("[TO FILL IN", domain, p.name)

    def test_kernel_assembles_and_verifies(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        out = assemble.build_document(FRAMEWORK / "method", version, "## The project\n\nX\n")
        self.assertEqual(kernel.verify(out), "OK")

    def test_coordinator_guide_assembles_and_verifies(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        out = assemble.build_document(FRAMEWORK / "coordinator", version, "## Roster\n\nX\n")
        self.assertEqual(kernel.verify(out), "OK")

    def test_kernel_has_no_placeholders(self):
        for d in ("method", "coordinator"):
            text = assemble.read_method(FRAMEWORK / d)
            self.assertNotIn("TO FILL IN", text, d)
            self.assertNotIn("{{", text, d)

    def test_coordinator_content_is_not_in_common_kernel(self):
        """The common kernel is paid by every subagent at every spawn: what
        only whoever delegates needs must not end up in it. The list of titles
        is the doctor's, not a copy: two lists diverge silently."""
        common = assemble.read_method(FRAMEWORK / "method")
        for heading in doctor.COORDINATOR_ONLY:
            self.assertNotIn(heading, common, heading)

    def test_watched_headings_still_exist_where_they_belong(self):
        """COORDINATOR_LEAK compares strings: if a title is renamed at the
        source, the check stops seeing the section without anything failing.
        This test is what makes the rename visible."""
        sources = (
            assemble.read_method(FRAMEWORK / "coordinator")
            + (FRAMEWORK / "skills" / "claw-install" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            + assemble.read_method(FRAMEWORK / "orchestrations")
        )
        for heading in doctor.COORDINATOR_ONLY:
            self.assertIn(heading, sources, heading)

    def test_coordinator_guide_stays_under_budget(self):
        """The coordinator's guide has a ceiling too: it is on demand, not paid
        at every spawn, but without a threshold it is the next place where the
        method swells. The real artefact is measured, profile cycles
        included, with every orchestration: whoever installs chooses it, not
        the profile."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            for orch in sorted((FRAMEWORK / "orchestrations").glob("*.md")):
                text = assemble.read_method(
                    FRAMEWORK / "coordinator",
                    [orch, *assemble.cycle_files(FRAMEWORK, prof.cycles)],
                )
                self.assertLess(
                    len(text.split()),
                    assemble.COORDINATOR_WORD_BUDGET,
                    f"{prof.name} + {orch.stem}",
                )

    def test_common_kernel_stays_under_budget(self):
        """Threshold on the cost paid at every spawn. If it goes over, you do
        not add: you move it into shared/ or you compress."""
        self.assertLess(
            len(assemble.read_method(FRAMEWORK / "method").split()),
            assemble.METHOD_WORD_BUDGET,
        )

    def test_ten_delegation_rules_are_complete_and_in_one_place(self):
        coord = assemble.read_method(FRAMEWORK / "coordinator")
        numbered = re.findall(r"^(\d+)\. \*\*", coord, re.MULTILINE)
        self.assertEqual([int(n) for n in numbered[:10]], list(range(1, 11)))

    def test_variant_b_has_no_markers(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        for d, sentinel in (
            ("method", "Evidence Before Action"),
            ("coordinator", "delegation"),
        ):
            out = assemble.build_document(
                FRAMEWORK / d, version, "## The project\n\nX\n", markers=False
            )
            self.assertNotIn("FRAMEWORK:KERNEL", out, d)
            self.assertIn(sentinel, out, d)
            self.assertIn("The project", out, d)

    def test_every_profile_resolves_to_existing_agents(self):
        available = {p.stem for p in (FRAMEWORK / "agents").glob("*.md")}
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            names = profile.roster(prof, [], [])
            self.assertEqual([n for n in names if n not in available], [], prof.name)
            self.assertEqual(profile.check_exclusive(names), [], prof.name)

    def test_every_declared_cycle_exists(self):
        """A cycle declared in a profile and absent from cycles/ would make the
        profile promise a method the project does not receive."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            assemble.cycle_files(FRAMEWORK, prof.cycles)  # raises if missing

    def test_no_orphan_cycle_files(self):
        declared = set()
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            declared |= set(profile.load(path).cycles)
        on_disk = {p.stem for p in (FRAMEWORK / "cycles").glob("*.md")}
        self.assertEqual(on_disk - declared, set(), "cycles on disk no profile uses")

    def test_every_named_orchestration_exists(self):
        """The default, the profiles' recommendations and the settings keys
        name modules by name: a name without a file breaks the installation of
        whoever chooses it, and orphan keys would switch on a variable for an
        orchestration nobody can install."""
        assemble.orchestration_file(FRAMEWORK, assemble.DEFAULT_ORCHESTRATION)
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            for name in profile.load(path).recommended_orchestrations:
                assemble.orchestration_file(FRAMEWORK, name)  # raises if missing
        for name in settings.ORCHESTRATION_SETTINGS:
            assemble.orchestration_file(FRAMEWORK, name)

    def test_orchestration_headings_are_recognizable(self):
        """`installed_orchestration` recognises a module by its first heading
        inside the region: if that heading appeared in the coordinator's kernel,
        in a cycle or in another module, `--down` would find an orchestration
        the project does not have, or two, and would rewrite the wrong guide.
        The opposite direction holds too: a cycle's heading inside a module
        would make `installed_cycles` find a cycle the profile does not have."""
        modules = sorted((FRAMEWORK / "orchestrations").glob("*.md"))
        self.assertGreaterEqual(len(modules), 2)
        coordinator = assemble.read_method(FRAMEWORK / "coordinator")
        cycles = assemble.read_method(FRAMEWORK / "cycles")
        for p in modules:
            heading = p.read_text(encoding="utf-8").lstrip().splitlines()[0]
            self.assertTrue(heading.startswith("## "), p.name)
            others = "\n".join(
                q.read_text(encoding="utf-8") for q in modules if q != p
            )
            for where, text in (
                ("coordinator/", coordinator),
                ("cycles/", cycles),
                ("other modules", others),
            ):
                self.assertNotIn(heading, text, f"{p.name} in {where}")
        all_modules = assemble.read_method(FRAMEWORK / "orchestrations")
        for c in sorted((FRAMEWORK / "cycles").glob("*.md")):
            heading = c.read_text(encoding="utf-8").lstrip().splitlines()[0]
            self.assertNotIn(heading, all_modules, f"{c.name} in orchestrations/")

    def test_every_profile_shared_guide_exists(self):
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            for rel in prof.shared:
                self.assertTrue((FRAMEWORK / "shared" / rel).is_file(), f"{prof.name}: {rel}")

    def test_surface_only_agents_are_in_no_profile(self):
        """Compliance and performance are not fields: one software project can
        process personal data and another not. Who watches over them is chosen
        by the critical-surface question, not by the profile: putting them in a
        profile would install them in every project of the field, as a fixed
        cost."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            leaked = SURFACE_ONLY & set(prof.agents)
            self.assertEqual(leaked, set(), f"{prof.name}: {leaked} is chosen by question 2")

    def test_surface_only_agents_are_reachable_from_the_question(self):
        """Outside every profile, question 2 is their **only** way in. If a row
        of the table disappears, the agent stays in the catalogue and nobody
        reaches it any more: never installed, and no finding saying so."""
        skill = (FRAMEWORK / "skills" / "claw-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        block = skill[skill.index("**2. Critical surface**") : skill.index("**3. Assumed")]
        for name in sorted(SURFACE_ONLY):
            self.assertIn(f"`{name}`", block, name)

    def test_question_one_offers_every_profile(self):
        """Question 1 is the only way to choose a profile, and the table is
        written by hand: a profile without its row cannot be chosen, and no
        finding sees it — the defect sits in the skill, before an installation
        exists."""
        skill = (FRAMEWORK / "skills" / "claw-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        block = skill[
            skill.index("**1. Field of the project**") : skill.index("**2. Critical surface**")
        ]
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            self.assertIn(f"| `{profile.load(path).name}` |", block, path.name)

    def test_exclusive_pairs_declare_their_boundary(self):
        """`EXCLUSIVE` is a guard, not an explanation: it says the two do not
        coexist, not where the line runs. If the line lives only in the check,
        an agent activated by hand arrives without knowing what is not its own
        — and the boundary line is exactly the kind of prose that disappears in
        a rewrite, with nothing seeing it."""
        for a, b in profile.EXCLUSIVE:
            for one, other in ((a, b), (b, a)):
                text = (FRAMEWORK / "agents" / f"{one}.md").read_text(encoding="utf-8")
                self.assertIn(f"`{other}`", text, f"{one} does not name {other}")
                flat = " ".join(text.split())
                self.assertIn("never both", flat, one)

    def test_critical_surface_table_routes_to_agents_that_exist(self):
        """Question 2 of the questionnaire is a routing table, and it has the
        same way of breaking as the coordinator's: renaming an agent leaves the
        row that cites it standing, and whoever installs picks an answer that
        leads to no file. The doctor cannot help here: the defect is in the
        skill, before an installation exists."""
        skill = (FRAMEWORK / "skills" / "claw-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        block = skill[skill.index("**2. Critical surface**") : skill.index("**3. Assumed")]
        # More permissive than `doctor.ROUTING_AGENT_RE`, and on purpose: that
        # one accepts lowercase only, so a rename with a capital letter would
        # escape the row instead of making it fail.
        reviewers = re.findall(r"^\|[^|]*\|\s*`([^`]+)`\s*\|$", block, re.MULTILINE)
        self.assertGreaterEqual(len(reviewers), 3, "reviewer table not read")
        for name in reviewers:
            self.assertTrue((FRAMEWORK / "agents" / f"{name}.md").is_file(), name)

    def test_the_install_skill_protects_material_that_was_already_there(self):
        """Installation is the only step that can delete someone else's work:
        it writes `CLAUDE.md` and copies the three templates into `docs/`. On a
        project that already had instructions, the rule that prevents it lives
        only in the skill's prose — it would vanish in a rewrite, and the defect
        would show up with the files already lost, on the installer's machine."""
        text = (FRAMEWORK / "skills" / "claw-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        block = text[
            text.index("### Pre-existing material") : text.index(
                "### `CLAUDE.md` — project sections"
            )
        ]
        for path in (
            "CLAUDE.md",
            "TODO.md",
            "status.md",
            "roadmap.md",
            ".claude/skills/",
            ".claude/settings.json",
            ".claude/output-styles/",
            ".claude/hooks/",
        ):
            self.assertIn(path, block, path)

    def test_final_reviewer_asks_for_the_uncovered_critical_surface(self):
        """The surfaces without a dedicated reviewer (public contract,
        accessibility) have no agent and must not have one: they end up in the
        mandate of whoever verifies last. If the placeholder stops asking for
        them, whoever installs does not write them and the surface
        disappears."""
        text = (FRAMEWORK / "agents" / "final-reviewer.md").read_text(encoding="utf-8")
        _, _, domain = assemble.split_source(text)
        self.assertIn("critical surface", domain)

    def test_the_memory_skill_pairs_every_conflict_with_the_repo(self):
        """Memory lives outside the repository: no finding sees it, and a
        conflict declared without the line that contradicts it becomes an
        invented alarm that survives across sessions. The paired column is the
        only thing preventing that, and it is prose: it would vanish in a
        rewrite."""
        text = (FRAMEWORK / "skills" / "claw-memory" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        block = text[text.index("## Step 4") : text.index("## Step 5")]
        self.assertIn("| the repo says |", block)
        self.assertIn("does not get written", block)

    def test_every_skill_is_present_with_matching_name(self):
        for name in (
            "claw-install",
            "claw-doctor",
            "claw-sync",
            "claw-memory",
            "claw-comply",
            "claw-fair",
        ):
            p = FRAMEWORK / "skills" / name / "SKILL.md"
            self.assertTrue(p.is_file(), name)
            self.assertIn(f"name: {name}", p.read_text(encoding="utf-8"))

    def test_promoting_from_a_stale_project_is_forbidden(self):
        """Two projects on the same source promote in turn. Whoever promotes
        from an installation left behind has a region that differs from the
        source for two reasons: their own change and the one the other has
        already promoted. Step 1 compares two trees and does not tell them
        apart, so without the precondition the second one vanishes with no
        finding.

        Drift covers only what has a kernel region: a new guide in `shared/`
        has none, and without the line that names it, it stays invisible to the
        most common case of all, the addition."""
        text = (FRAMEWORK / "skills" / "claw-sync" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        block = text[text.index("## `--up") : text.index("## `--upgrade")]
        self.assertIn("aligned", block)
        self.assertIn("`.claude/framework.json`", block)
        self.assertIn("one thing at a time", block)
        self.assertIn("does not see new files", block)

    def test_state_templates_present(self):
        for name in ("TODO.md", "status.md", "roadmap.md"):
            self.assertTrue((FRAMEWORK / "templates" / name).is_file(), name)

    def test_every_profile_selects_the_style_that_exists(self):
        """`outputStyle` names the style by **name**, not by path: if the
        frontmatter is renamed on one side only, Claude Code finds nothing and
        falls back to Default without saying so. The style stays installed, the
        communication goes back to what it was, and no finding sees it.

        `keep-coding-instructions` matters too: without it a custom style
        **drops** the built-in software engineering instructions."""
        text = (FRAMEWORK / "output-styles" / "reporting.md").read_text(
            encoding="utf-8"
        )
        name = re.search(r"^name:\s*(.+)$", text, re.MULTILINE).group(1).strip()
        self.assertIn("keep-coding-instructions: true", text)
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            self.assertEqual(
                profile.load(path).settings.get("outputStyle"), name, path.name
            )

    def test_an_unfilled_response_style_is_a_finding(self):
        """The style has no kernel region and is not tracked: the only thing
        demanding that it be adapted is `_markdown_files` scanning it. Narrowing
        that list (it excludes skills and archive) would switch the check
        off without breaking anything, and the project block would stay empty on
        the installer's disk."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trial"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root)
            rel = ".claude/output-styles/reporting.md"
            self.assertEqual(doctor.check(root), [])
            (root / rel).write_text(
                (FRAMEWORK / "output-styles" / "reporting.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            codes = [(f.code, f.message) for f in doctor.check(root)]
            self.assertIn(("PLACEHOLDER", f"{rel}: placeholder not filled in"), codes)

    def test_review_checklist_keeps_generic_block_separable(self):
        text = (FRAMEWORK / "shared" / "core" / "review-checklist.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Generic block", text)
        self.assertIn("## Project block", text)
        self.assertLess(text.index("## Generic block"), text.index("## Project block"))

    def test_report_confidence_is_categorical_not_a_percentage(self):
        """An LLM's self-reported confidence is poorly calibrated: a percentage
        puts fake precision in the position the coordinator reads first. The
        format lives in a single place in the whole framework, and a single
        place gets rewritten by inattention: this test is what stops the old
        format from coming back without anyone seeing it."""
        for p in FRAMEWORK.rglob("*.md"):
            self.assertNotRegex(p.read_text(encoding="utf-8"), CONF_PERCENT_RE, str(p))

    def test_report_schema_carries_a_falsifier(self):
        """`REFUTE` is what makes a categorical judgement useful: without it,
        the coordinator reads a label and does not know what would refute it."""
        text = assemble.read_method(FRAMEWORK / "method")
        self.assertIn("CONF: HIGH | MEDIUM | LOW", text)
        self.assertIn("REFUTE:", text)

    def test_no_reference_to_source_projects(self):
        forbidden = ("RPLAN", "AbletonLoader", "FindShop", "Avalonia", "Typesense", "CVCS")
        for p in FRAMEWORK.rglob("*.md"):
            text = p.read_text(encoding="utf-8")
            for word in forbidden:
                self.assertNotIn(word, text, f"{p.name} cites {word}")

    def test_the_source_ships_no_personal_path_and_no_hidden_character(self):
        """The doctor looks at the installation, but what it finds there almost
        always comes from the source, which is copied verbatim. The regexes are
        its own: a copy would diverge in silence. Tests included — which is why
        their paths are built by concatenation and the characters are
        escapes."""
        for p in sorted(FRAMEWORK.rglob("*")):
            if not p.is_file() or p.suffix not in {".md", ".py", ".toml", ".json", ".jsonl"}:
                continue
            text = p.read_text(encoding="utf-8")
            rel = p.relative_to(FRAMEWORK).as_posix()
            self.assertNotRegex(text, doctor.PERSONAL_PATH_RE, rel)
            self.assertNotRegex(text, doctor.UNSAFE_CHARS_RE, rel)

    def test_sync_down_preserves_domain_cycles(self):
        """The `--down` procedure reassembles the coordinator's guide from the
        source: if it does not pass the cycles back, a `web` project loses the
        design cycle at every update, silently and with no findings."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        prof = profile.load(FRAMEWORK / "profiles" / "web.toml")
        installed = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            "## This project's roster",
            extra=assemble.cycle_files(FRAMEWORK, prof.cycles),
        )
        region = kernel.parse(installed)
        rebuilt = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            installed[region.end :],
            extra=assemble.installed_cycles(region.body, FRAMEWORK),
        )
        self.assertIn("The design cycle", rebuilt)

    def test_sync_down_preserves_the_orchestration(self):
        """Like the cycles, the orchestration sits inside the region and no file
        says which one it is: `--down` has to find it again, in the same order,
        for the reassembled region to verify. A region in which none is
        recognised is refused: the default in its place would hide a renamed
        heading."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        prof = profile.load(FRAMEWORK / "profiles" / "web.toml")
        teams = assemble.orchestration_file(FRAMEWORK, "agent-teams")
        installed = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            "## This project's roster",
            extra=[teams, *assemble.cycle_files(FRAMEWORK, prof.cycles)],
        )
        region = kernel.parse(installed)
        rebuilt = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            installed[region.end :],
            extra=[
                assemble.installed_orchestration(region.body, FRAMEWORK),
                *assemble.installed_cycles(region.body, FRAMEWORK),
            ],
        )
        self.assertIn("## Orchestration: Agent teams", rebuilt)
        self.assertIn("The design cycle", rebuilt)
        self.assertEqual(kernel.verify(rebuilt), "OK")
        self.assertEqual(kernel.parse(rebuilt).body, region.body)

        without = assemble.build_document(
            FRAMEWORK / "coordinator", version, "## This project's roster"
        )
        with self.assertRaises(ValueError):
            assemble.installed_orchestration(kernel.parse(without).body, FRAMEWORK)

    def test_unfilled_roadmap_is_detectable(self):
        """A state template with an unfilled skeleton is indistinguishable from
        absent state for whoever reads it at session start: it must contain a
        placeholder the doctor recognises."""
        text = (FRAMEWORK / "templates" / "roadmap.md").read_text(encoding="utf-8")
        self.assertRegex(text, doctor.PLACEHOLDER_RE)

    def test_status_template_is_deliberately_not_a_placeholder(self):
        """`status.md` is born empty by construction — you write in it when
        something closes. Flagging it would make Step 6 impossible to pass on a
        freshly made installation."""
        text = (FRAMEWORK / "templates" / "status.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, doctor.PLACEHOLDER_RE)


class TestInstalledBudget(unittest.TestCase):
    """`TOKEN_BUDGET`: the threshold on the part the source does not see."""

    def _installed(self, d, extra_words):
        root = Path(d) / "trial"
        with redirect_stdout(io.StringIO()):
            trial_install.install(root)
        if extra_words:
            claude = root / "CLAUDE.md"
            claude.write_text(
                claude.read_text(encoding="utf-8")
                + "\n## Extra\n\n"
                + ("word " * extra_words)
                + "\n",
                encoding="utf-8",
            )
        return root

    def test_measure_separates_kernel_from_project_sections(self):
        """The two parts have opposite disciplines — one with a ceiling on the
        source, the other with no ceiling at all — and the measurement is what
        distinguishes them. If they came back indistinct, the finding would look
        at the total and would not say whose the growth is."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        text = assemble.build_document(
            FRAMEWORK / "method", version, "## The project\n\none two three\n"
        )
        m = doctor.measure(text)
        self.assertTrue(m.has_region)
        self.assertEqual(
            m.kernel_words, len(assemble.read_method(FRAMEWORK / "method").split())
        )
        self.assertEqual(m.project_words, 6)
        self.assertEqual(m.total_words, m.kernel_words + 6)

    def test_measure_does_not_invent_a_split_without_markers(self):
        """The variant without markers is legitimate. Attributing everything to
        the project would fire the finding on a healthy installation."""
        m = doctor.measure("## The project\n\none two three\n")
        self.assertFalse(m.has_region)
        self.assertEqual(m.project_words, 0)

    def test_a_small_file_is_below_the_floor_and_stays_quiet(self):
        """The ratio on a tiny file is true and irrelevant: a warning about the
        cost of eleven tokens is noise, and a warning that always fires stops
        being read."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        text = assemble.build_document_from_text(
            "## Method\n\none\n", version, "## The project\n\n" + ("x " * 50) + "\n"
        )
        m = doctor.measure(text)
        self.assertGreater(m.project_words, m.kernel_words)
        self.assertLess(m.total_words, assemble.METHOD_WORD_BUDGET)

    def test_a_normal_install_is_under_budget(self):
        """If the finding fired on the reference installation it would be
        noise, and a warning that always fires stops being read."""
        with tempfile.TemporaryDirectory() as d:
            root = self._installed(d, 0)
            self.assertNotIn("TOKEN_BUDGET", [f.code for f in doctor.check(root)])

    def test_project_sections_larger_than_the_kernel_are_reported(self):
        """The threshold is the kernel, the only known quantity: the project
        does not write more than the method."""
        with tempfile.TemporaryDirectory() as d:
            root = self._installed(d, 1400)
            found = [f for f in doctor.check(root) if f.code == "TOKEN_BUDGET"]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].severity, "WARN")

    def test_old_report_format_is_reported_in_an_installed_project(self):
        """A project installed with the percentage format keeps it: the
        kernel region's hash matches, because it matches that very text, and
        the declared version is the one the project was born with. Without this
        finding no check sees it."""
        with tempfile.TemporaryDirectory() as d:
            root = self._installed(d, 0)
            claude = root / "CLAUDE.md"
            claude.write_text(
                claude.read_text(encoding="utf-8").replace(
                    "CONF: HIGH | MEDIUM | LOW", "CONF: <0-100" + "%>"
                ),
                encoding="utf-8",
            )
            self.assertIn("REPORT_FORMAT", [f.code for f in doctor.check(root)])

    def test_every_code_the_doctor_can_emit_is_documented(self):
        """A finding without an entry in the skill is a code whoever receives
        it does not know what to do with."""
        skill = (FRAMEWORK / "skills" / "claw-doctor" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        src = (FRAMEWORK / "tools" / "fwbuild" / "doctor.py").read_text(encoding="utf-8")
        emitted = set(re.findall(r'Finding\(\s*"([A-Z_]+)"', src))
        self.assertTrue(emitted)
        for code in sorted(emitted):
            self.assertIn("### `" + code + "`", skill, code)


class TestSourceReference(unittest.TestCase):
    """How `.claude/framework.json` cites the source."""

    def test_source_inside_the_project_is_recorded_relative(self):
        """The first of the three supported ways is the source inside the
        project: there an absolute path is the machine of whoever installed it,
        and it dies at the clone."""
        self.assertEqual(
            source.reference(Path("/prj"), Path("/prj/framework")), "framework"
        )

    def test_source_outside_the_project_stays_absolute(self):
        """Outside the project a relative path does not hold: the depth of the
        clone is unknown."""
        out = Path("/elsewhere/framework").resolve()
        self.assertEqual(source.reference(Path("/prj"), out), str(out))

    def test_recorded_reference_resolves_back(self):
        recorded = source.reference(Path("/prj"), Path("/prj/framework"))
        self.assertEqual(
            source.dereference(Path("/prj"), recorded),
            Path("/prj/framework").resolve(),
        )

    def test_install_records_a_portable_source(self):
        """The rule lives in the skill, that is, in prose: here it is checked
        on the artefact written."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trial"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root)
            recorded = json.loads(
                (root / ".claude" / "framework.json").read_text(encoding="utf-8")
            )["source"]
            self.assertEqual(
                source.dereference(root, recorded).resolve(), FRAMEWORK.resolve()
            )


class TestProfilesAreDistinguishable(unittest.TestCase):
    def test_every_profile_declares_its_critical_surface(self):
        """The field's critical surface is known before knowing the project: it
        is the only answer a profile can give on its own to the question of
        Step 3.2."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            self.assertTrue(prof.critical_surface.strip(), prof.name)

    def test_no_two_profiles_are_interchangeable(self):
        """Two profiles that differ only by `name` and `description` are a
        choice with no mechanical consequence."""
        seen = {}
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            prof = profile.load(path)
            key = (
                tuple(prof.agents),
                tuple(prof.cycles),
                tuple(prof.shared),
                repr(prof.settings),
                prof.critical_surface,
            )
            self.assertNotIn(key, seen, prof.name + " == " + str(seen.get(key)))
            seen[key] = prof.name

    def test_the_install_skill_starts_from_the_declared_surface(self):
        """A field no step reads is dead configuration."""
        text = (FRAMEWORK / "skills" / "claw-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("critical_surface", text)


class TestCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def _install(self, d):
        root = Path(d) / "trial"
        with redirect_stdout(io.StringIO()):
            trial_install.install(root)
        return root

    def test_doctor_json_carries_findings_and_measure(self):
        """The format for CI: a consumer that must not read prose."""
        with tempfile.TemporaryDirectory() as d:
            code, out = self._run(["doctor", "--json", str(self._install(d))])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["findings"], [])
            self.assertTrue(payload["measure"]["split"])
            self.assertGreater(payload["measure"]["tokens"], 0)

    def test_doctor_json_keeps_the_strict_exit_code(self):
        """`--json` is a format, not a posture: the exit code must be the same
        with the flag and without. On a clean installation it is 0."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            for argv in (
                ["doctor", str(root)],
                ["doctor", "--strict", str(root)],
                ["doctor", "--json", str(root)],
                ["doctor", "--strict", "--json", str(root)],
            ):
                with self.subTest(argv=" ".join(argv[:-1])):
                    self.assertEqual(self._run(argv)[0], 0)

            # And when there is a finding, both forms make it fail.
            (root / ".claude" / "settings.json").unlink()
            self.assertEqual(self._run(["doctor", "--strict", str(root)])[0], 1)
            self.assertEqual(
                self._run(["doctor", "--strict", "--json", str(root)])[0], 1
            )

    def test_install_writes_a_complete_manifest(self):
        """`framework.json` is the only place saying where the project was born
        and what it is made of: the proof looks at the written file, not at the
        prose prescribing it."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            data = json.loads(
                (root / ".claude" / "framework.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["profile"], "software")
            self.assertEqual(
                data["version"],
                (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip(),
            )
            self.assertTrue(data["source"])


class TestRealInstall(unittest.TestCase):
    def test_full_install_passes_doctor(self):
        """The rest of the suite checks the pieces; this checks **the act of
        installing**. It is the only test that falls if the installation, as a
        whole, stops passing Step 6."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trial"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root)
            self.assertEqual(doctor.check(root), [])

    def test_agent_teams_settings_go_in_and_come_out(self):
        """The `agent-teams` variables are the only part of the orchestration
        that lives outside the guide: they go into `settings.json` and into the
        record, or the uninstall leaves them switched on in a project that no
        longer has the framework."""
        env = settings.ORCHESTRATION_SETTINGS["agent-teams"]["env"]
        self.assertTrue(env)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "trial"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root, orchestration="agent-teams")
            data = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            record = json.loads(
                (root / ".claude" / "framework.json").read_text(encoding="utf-8")
            )["settings_added"]
            for key, value in env.items():
                self.assertEqual(data["env"][key], value, key)
                self.assertEqual(record["env"][key], value, key)
            guide = (root / ".claude" / "shared" / "orchestration.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                assemble.installed_orchestration(kernel.parse(guide).body, FRAMEWORK).stem,
                "agent-teams",
            )
            self.assertEqual(doctor.check(root), [])

            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            lifecycle.apply_uninstall(root, FRAMEWORK, ops)

            left = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            for key in env:
                self.assertNotIn(key, left.get("env", {}), key)


if __name__ == "__main__":
    unittest.main()
