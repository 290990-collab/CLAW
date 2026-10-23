import re
import unittest
from pathlib import Path

from fwbuild import assemble, doctor, kernel, rules

FRAMEWORK = Path(__file__).resolve().parents[2]
CHOICES = {
    "profile": "library",
    "orchestration": "orchestrator-worker",
    "agents": ["explorer", "tester", "implementer"],
    "guides": [],
    "hooks": ["config_protection", "block_no_verify"],
}
NO_RULES = rules.Rules()
PROJECT = "## The project\n\nA library. HARD: no deps.\n\n## Commands\n\n`make test`\n"
TESTER = ".claude/agents/tester.md"


def gen(rl=NO_RULES, claude_md=None, **choices):
    return assemble.generate(FRAMEWORK, {**CHOICES, **choices}, rl, claude_md)


def with_project() -> str:
    return gen()["CLAUDE.md"] + "\n" + PROJECT


class TestGenerate(unittest.TestCase):
    def test_generating_twice_gives_the_same_text(self):
        """One producer means one answer: a clock, a dict order or a read that
        differs between calls would make every update rewrite files."""
        self.assertEqual(gen(), gen())

    def test_regenerating_from_its_own_output_is_a_fixed_point(self):
        """An update feeds the file back in: if the output changed, the project
        part would grow or lose a blank line at every update."""
        rl = rules.parse("## All\n- be brief\n")
        first = gen(rl, with_project())["CLAUDE.md"]
        self.assertEqual(gen(rl, first)["CLAUDE.md"], first)

    def test_project_part_survives_byte_for_byte(self):
        """CLAUDE.md outside the regions is the user's: a rewrite there loses
        their work with no finding."""
        rl = rules.parse("## All\n- be brief\n")
        out = gen(rl, with_project())["CLAUDE.md"]
        self.assertIn(PROJECT.rstrip("\n"), out)
        self.assertEqual(out.count("## The project"), 1)

    def test_an_agent_rule_changes_only_that_agent(self):
        """A rule under `## tester` landing in another card, or in CLAUDE.md,
        applies it to a recipient that never asked."""
        base = gen()
        out = gen(rules.parse("## tester\n- run pytest -x\n"))
        changed = {p for p in base if base[p] != out[p]}
        self.assertEqual(changed, {TESTER})
        self.assertIn("run pytest -x", out[TESTER])

    def test_empty_rules_add_nothing(self):
        """A region with a title and no body is text every spawn pays for."""
        base = gen()
        empty = gen(rules.parse("## All\n\n## tester\n\n"))
        self.assertEqual(base, empty)
        self.assertNotIn(kernel.USER_RULES_OPEN, base["CLAUDE.md"])

    def test_all_block_is_the_last_thing_in_claude_md(self):
        """Last place wins on conflict, and the title says so: a project part
        added after the region would outrank the user's own rules."""
        out = gen(rules.parse("## All\n- be brief\n"), with_project())["CLAUDE.md"]
        self.assertTrue(out.endswith(kernel.USER_RULES_CLOSE + "\n"))
        self.assertLess(out.index(PROJECT.strip()), out.index(kernel.USER_RULES_OPEN))
        self.assertIn(assemble.USER_RULES_TITLE, out)

    def test_removing_all_rules_removes_the_region(self):
        """A deleted rule must disappear on the next generate, not stay as a
        stale region nobody can find."""
        with_rules = gen(rules.parse("## All\n- be brief\n"), with_project())["CLAUDE.md"]
        self.assertNotIn(kernel.USER_RULES_OPEN, gen(NO_RULES, with_rules)["CLAUDE.md"])

    def test_override_changes_only_the_frontmatter_and_the_roster_cell(self):
        """An override that leaked into the body, or left the roster saying the
        old model, makes the coordinator route by a model that is not used."""
        base, out = gen(), gen(rules.parse("## tester\nmodel: opus\neffort: low\n"))
        a, b = base[TESTER], out[TESTER]
        self.assertEqual(a.split("\n---\n", 1)[1], b.split("\n---\n", 1)[1])
        self.assertIn("model: opus\n", b)
        self.assertIn("effort: low\n", b)
        self.assertNotIn("model: opus", a)
        orch = ".claude/shared/orchestration.md"
        self.assertRegex(out[orch], r"\| `tester` \| opus low \|")
        changed = {p for p in base if base[p] != out[p]}
        self.assertEqual(changed, {TESTER, orch})

    def test_override_under_all_is_refused(self):
        """Reaching generate with it would mean the parse was skipped."""
        with self.assertRaises(ValueError):
            rules.parse("## All\nmodel: opus\n")

    def test_roster_table_keeps_the_agent_in_the_second_column(self):
        """The doctor reads the agent name from the second column: a changed
        column order makes every card an orphan."""
        text = gen()[".claude/shared/orchestration.md"]
        names = {m.group(1) for m in doctor.ROUTING_AGENT_RE.finditer(text)}
        self.assertTrue(set(CHOICES["agents"]) <= names)

    def test_cards_carry_no_project_block(self):
        """The source block is dropped: its placeholder in an installation is a
        file the doctor would ask to fill in."""
        for path, text in gen().items():
            if path.startswith(".claude/agents/"):
                self.assertNotIn(assemble.DOMAIN_HEADING, text, path)
                self.assertNotIn("[TO FILL IN", text, path)

    def test_guides_cited_by_the_roster_are_added(self):
        """An agent installed with a dead pointer is SHARED_MISSING on a file
        nobody wrote."""
        out = gen(agents=["explorer", "tester", "implementer", "frontend"])
        cited = [p for p in out if p.startswith(".claude/shared/") and p.endswith(".md")
                 and not p.endswith("orchestration.md")]
        self.assertTrue(cited)
        for p in cited:
            self.assertIn(p, out["CLAUDE.md"])

    def test_state_templates_are_marked_create_only(self):
        """An update that rewrote `docs/TODO.md` would erase the project's state."""
        out = gen()
        docs = [p for p in out if assemble.is_create_only(p)]
        self.assertEqual(sorted(docs), sorted(f"docs/{n}" for n in assemble.STATE_FILES))
        self.assertFalse(any(assemble.is_create_only(p) for p in out if p not in docs))

    def test_copied_files_equal_their_source_bytes(self):
        """Guides, styles and hooks are copies: a normalised line ending would
        show as a change in every project on every update."""
        out = gen()
        src = FRAMEWORK / "hooks" / "config_protection.py"
        self.assertEqual(out[".claude/hooks/config_protection.py"].encode("utf-8"), src.read_bytes())
        self.assertTrue(re.search(r"^---", out[".claude/output-styles/reporting.md"]))


if __name__ == "__main__":
    unittest.main()
