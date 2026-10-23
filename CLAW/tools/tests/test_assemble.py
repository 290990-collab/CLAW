import tempfile
import unittest
from pathlib import Path

from fwbuild import assemble, kernel, source

SOURCE = "---\nname: implementer\nmodel: opus\n---\n\n## Method\n\nDo the thing.\n"


class TestReadMethod(unittest.TestCase):
    def test_concatenates_in_filename_order(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "10-b.md").write_text("BETA\n", encoding="utf-8")
            (p / "00-a.md").write_text("ALPHA\n", encoding="utf-8")
            out = assemble.read_method(p)
            self.assertLess(out.index("ALPHA"), out.index("BETA"))

    def test_ignores_non_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "00-a.md").write_text("ALPHA\n", encoding="utf-8")
            (p / "notes.txt").write_text("NOISE\n", encoding="utf-8")
            self.assertNotIn("NOISE", assemble.read_method(p))


class TestBuildClaudeMd(unittest.TestCase):
    def _method_dir(self, tmp):
        p = Path(tmp)
        (p / "10-orchestration.md").write_text("## Orchestration\n", encoding="utf-8")
        return p

    def test_kernel_region_parses(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(self._method_dir(d), "1.0.0", "## The project\n")
            self.assertIsNotNone(kernel.parse(out))

    def test_project_sections_outside_region(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(self._method_dir(d), "1.0.0", "## The project\n")
            region = kernel.parse(out)
            self.assertNotIn("The project", region.body)
            self.assertIn("The project", out)

    def test_markers_off_emits_no_marker(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(
                self._method_dir(d), "1.0.0", "## The project\n", markers=False
            )
            self.assertNotIn("FRAMEWORK:KERNEL", out)
            self.assertIn("Orchestration", out)
            self.assertIn("The project", out)


class TestSplitSource(unittest.TestCase):
    def test_returns_front_matter_and_method(self):
        fm, method = assemble.split_source(SOURCE)
        self.assertIn("name: implementer", fm)
        self.assertTrue(method.startswith("## Method"))
        self.assertIn("Do the thing", method)

    def test_horizontal_rule_in_body_does_not_break_parsing(self):
        text = SOURCE.replace("Do the thing.", "Do the thing.\n\n---\n\nThen verify.")
        fm, method = assemble.split_source(text)
        self.assertIn("name: implementer", fm)
        self.assertIn("Then verify", method)

    def test_a_card_without_the_method_section_is_an_error(self):
        """A card with no `## Method` would be installed as a front matter and
        nothing else: an agent with no instructions."""
        with self.assertRaises(ValueError):
            assemble.split_source("---\nname: x\n---\n\nprose\n")


class TestAgentRows(unittest.TestCase):
    ROW = (
        'model = "opus"\neffort = "high"\nmaxTurns = 25\n'
        'tools = "Read, Grep"\ncolor = "blue"\n'
    )

    def _root(self, d, toml, cards=("a", "b")):
        root = Path(d)
        (root / source.CARDS_DIR).mkdir()
        (root / source.CARDS_DIR / "agents.toml").write_text(toml, encoding="utf-8")
        for name in cards:
            (root / source.CARDS_DIR / f"{name}.md").write_text(SOURCE, encoding="utf-8")
        return root

    def test_valid_rows_are_returned_with_int_maxturns(self):
        toml = f"[a]\n{self.ROW}\n[b]\nmodel = \"haiku\"\neffort = \"low\"\ntools = \"Read\"\ncolor = \"red\"\n"
        with tempfile.TemporaryDirectory() as d:
            rows = assemble.agent_rows(self._root(d, toml))
        self.assertEqual(set(rows), {"a", "b"})
        self.assertEqual(rows["a"]["maxTurns"], 25)
        self.assertIsInstance(rows["a"]["maxTurns"], int)
        self.assertEqual(rows["b"]["model"], "haiku")
        self.assertNotIn("maxTurns", rows["b"])

    def _rejects(self, toml, cards=("a",)):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                assemble.agent_rows(self._root(d, toml, cards))

    def test_unknown_key_is_rejected(self):
        self._rejects(f"[a]\n{self.ROW}efort = \"x\"\n")

    def test_bool_value_is_rejected(self):
        self._rejects(f"[a]\n{self.ROW.replace('maxTurns = 25', 'maxTurns = true')}")

    def test_nested_table_value_is_rejected(self):
        self._rejects(f"[a]\n{self.ROW}\n[a.extra]\nx = 1\n")

    def test_missing_required_key_is_rejected(self):
        no_color = self.ROW.replace('color = "blue"', "")
        self._rejects("[a]\n" + no_color)

    def test_row_without_card_is_rejected(self):
        self._rejects(f"[a]\n{self.ROW}\n[ghost]\n{self.ROW}", cards=("a",))

    def test_card_without_row_is_rejected(self):
        self._rejects(f"[a]\n{self.ROW}", cards=("a", "orphan"))


class TestRenderCard(unittest.TestCase):
    BODY = "\n## Method\n\nDo the thing.\n---\nrule above\n"
    TEXT = (
        "---\nname: implementer\n"
        "description: >\n  First line of the folded\n  block continues here.\n"
        "color: red\nmodel: sonnet\ntools: Read\nmaxTurns: 25\neffort: low\n"
        "---\n" + BODY
    )
    ROW = {"model": "opus", "effort": "high", "maxTurns": 40, "tools": "Read, Grep", "color": "blue"}

    def test_calibration_lines_rewritten_rest_untouched(self):
        out = assemble.render_card(self.TEXT, self.ROW)
        self.assertEqual(
            out,
            "---\nname: implementer\n"
            "description: >\n  First line of the folded\n  block continues here.\n"
            "model: opus\neffort: high\nmaxTurns: 40\ntools: Read, Grep\ncolor: blue\n"
            "---\n" + self.BODY,
        )

    def test_idempotent(self):
        once = assemble.render_card(self.TEXT, self.ROW)
        self.assertEqual(assemble.render_card(once, self.ROW), once)

    def test_row_without_maxturns_drops_the_line(self):
        row = {k: v for k, v in self.ROW.items() if k != "maxTurns"}
        out = assemble.render_card(self.TEXT, row)
        self.assertNotIn("maxTurns", out)
        self.assertIn("model: opus\neffort: high\ntools:", out)

    def test_missing_frontmatter_is_an_error(self):
        with self.assertRaises(ValueError) as e:
            assemble.render_card("no front matter\n", self.ROW)
        self.assertEqual(str(e.exception), "source without front matter")

    def test_unclosed_frontmatter_is_an_error(self):
        with self.assertRaises(ValueError) as e:
            assemble.render_card("---\nname: x\nmodel: opus\n", self.ROW)
        self.assertEqual(str(e.exception), "front matter not closed")


if __name__ == "__main__":
    unittest.main()
