import unittest

from fwbuild import kernel, rules

EXAMPLE = """## All
- Commit messages in English, no signature.

## tester
model: sonnet
effort: high
- Run `pytest -q -x`, never the whole matrix.
"""


class TestParse(unittest.TestCase):
    def test_the_plan_example_is_read_as_written(self):
        """The file format is the user's contract: a section read wrongly applies
        a rule to the wrong recipient, or none."""
        r = rules.parse(EXAMPLE)
        self.assertEqual(r.all, "- Commit messages in English, no signature.")
        self.assertEqual(r.agents, {"tester": "- Run `pytest -q -x`, never the whole matrix."})
        self.assertEqual(r.overrides, {"tester": {"model": "sonnet", "effort": "high"}})
        self.assertEqual(r.stray, "")

    def test_override_lines_are_not_prose(self):
        """If `model:` stayed in the agent's text it would be printed in the card
        body as if it were a rule, on top of changing the frontmatter."""
        r = rules.parse("## tester\nmodel: opus\n- keep it short\n")
        self.assertNotIn("model:", r.agents["tester"])

    def test_empty_file_and_empty_sections_give_nothing(self):
        """An empty region written to CLAUDE.md for a blank file would be noise
        paid at every spawn."""
        for text in ("", "\n\n", "## All\n\n## tester\n   \n"):
            self.assertEqual(rules.parse(text), rules.Rules(), repr(text))

    def test_text_before_the_first_heading_is_stray(self):
        """It belongs to no recipient: applying it anywhere would be a guess."""
        r = rules.parse("remember this\n\n## All\n- x\n")
        self.assertEqual(r.stray, "remember this")
        self.assertEqual(r.all, "- x")

    def test_duplicate_section_is_an_error(self):
        """Keeping the last one silently drops the first one's rules."""
        with self.assertRaises(ValueError):
            rules.parse("## tester\n- a\n\n## tester\n- b\n")

    def test_override_under_all_is_an_error(self):
        """`## All` has no frontmatter: the line would be ignored and the user
        would believe every agent had changed model."""
        with self.assertRaises(ValueError):
            rules.parse("## All\nmodel: opus\n")

    def test_the_same_override_twice_is_an_error(self):
        """Two values for one key: which one wins must not depend on line order."""
        with self.assertRaises(ValueError):
            rules.parse("## tester\nmodel: opus\nmodel: haiku\n")

    def test_crlf_file_reads_like_lf(self):
        """The file is edited on Windows too."""
        self.assertEqual(rules.parse(EXAMPLE.replace("\n", "\r\n")), rules.parse(EXAMPLE))


class TestUserRulesRegion(unittest.TestCase):
    def test_strip_returns_the_text_without_the_region(self):
        """The project part must come back byte for byte, or each regeneration
        eats or adds a blank line."""
        text = "project\n\n" + kernel.wrap_user_rules("## T\n\n- a")
        rest, body = kernel.strip_user_rules(text)
        self.assertEqual(rest, "project\n\n")
        self.assertEqual(body, "## T\n\n- a\n")

    def test_no_region_is_none(self):
        """Absent and empty are different: only an absent region means nothing was written."""
        self.assertEqual(kernel.strip_user_rules("plain\n"), ("plain\n", None))

    def test_unclosed_region_is_an_error(self):
        """Taking the rest of the file as the region would delete the project part."""
        with self.assertRaises(ValueError):
            kernel.strip_user_rules(f"a\n{kernel.USER_RULES_OPEN}\nx\n")


if __name__ == "__main__":
    unittest.main()
