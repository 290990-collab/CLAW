import tempfile
import unittest
from pathlib import Path

from fwbuild import assemble, kernel

FRONTMATTER = "---\nname: implementer\nmodel: opus\neffort: high\n---\n"

SOURCE = (
    "---\nname: implementer\nmodel: opus\n---\n\n"
    "## Method\n\nDo the thing.\n\n"
    "## Project context\n\n[TO FILL IN]\n"
)


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

    def test_kernel_region_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(self._method_dir(d), "1.0.0", "## The project\n")
            self.assertEqual(kernel.verify(out), "OK")

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


class TestBuildAgent(unittest.TestCase):
    def test_frontmatter_is_outside_kernel_region(self):
        out = assemble.build_agent(FRONTMATTER, "## Method\n", "## Domain\n", "1.0.0")
        region = kernel.parse(out)
        self.assertNotIn("model: opus", region.body)
        self.assertTrue(out.startswith("---\n"))

    def test_changing_model_does_not_cause_drift(self):
        a = assemble.build_agent(FRONTMATTER, "## Method\n", "## Domain\n", "1.0.0")
        b = a.replace("model: opus", "model: sonnet")
        self.assertEqual(kernel.verify(b), "OK")

    def test_editing_method_causes_drift(self):
        a = assemble.build_agent(FRONTMATTER, "## Method\n", "## Domain\n", "1.0.0")
        b = a.replace("## Method", "## Changed method")
        self.assertEqual(kernel.verify(b), "DRIFT")

    def test_domain_block_outside_region(self):
        out = assemble.build_agent(FRONTMATTER, "## Method\n", "## Domain\n", "1.0.0")
        self.assertNotIn("Domain", kernel.parse(out).body)
        self.assertIn("## Domain", out)


class TestSplitSource(unittest.TestCase):
    def test_returns_three_parts(self):
        fm, method, domain = assemble.split_source(SOURCE)
        self.assertIn("name: implementer", fm)
        self.assertIn("Do the thing", method)
        self.assertIn("TO FILL IN", domain)

    def test_method_excludes_domain_block(self):
        _, method, _ = assemble.split_source(SOURCE)
        self.assertNotIn("TO FILL IN", method)

    def test_horizontal_rule_in_body_does_not_break_parsing(self):
        text = SOURCE.replace("Do the thing.", "Do the thing.\n\n---\n\nThen verify.")
        fm, method, _ = assemble.split_source(text)
        self.assertIn("name: implementer", fm)
        self.assertIn("Then verify", method)

    def test_round_trips_through_build_agent(self):
        fm, method, domain = assemble.split_source(SOURCE)
        built = assemble.build_agent(fm, method, domain, "1.0.0")
        self.assertEqual(kernel.verify(built), "OK")


class TestInstalledCycles(unittest.TestCase):
    def test_detects_only_the_cycles_actually_present(self):
        """`--down` reassembles from `coordinator/`: without detecting the
        cycles already installed it would delete them, and the project does not
        record its profile."""
        root = Path(__file__).resolve().parents[2]
        design = (root / "cycles" / "design.md").read_text(encoding="utf-8")
        found = assemble.installed_cycles(design, root)
        self.assertEqual([p.stem for p in found], ["design"])
        self.assertEqual(assemble.installed_cycles("## Delegation", root), [])


class TestInstalledOrchestration(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def _module(self, name):
        return (self.ROOT / "orchestrations" / f"{name}.md").read_text(encoding="utf-8")

    def test_detects_the_one_present(self):
        found = assemble.installed_orchestration(self._module("agent-teams"), self.ROOT)
        self.assertEqual(found.stem, "agent-teams")

    def test_region_without_a_module_is_an_error(self):
        """No module recognised usually means a heading renamed in the source:
        falling back on the default would rewrite the wrong model at `--down`,
        in silence. The choice goes back to whoever reassembles."""
        with self.assertRaises(ValueError) as e:
            assemble.installed_orchestration("## Delegation", self.ROOT)
        self.assertIn("orchestration_file", str(e.exception))

    def test_two_modules_are_an_error(self):
        """One orchestration per project: with two, picking one would be
        guessing which one the user wanted."""
        body = self._module("agent-teams") + self._module("orchestrator-worker")
        with self.assertRaises(ValueError):
            assemble.installed_orchestration(body, self.ROOT)


if __name__ == "__main__":
    unittest.main()
