import tempfile
import unittest
from pathlib import Path

from fwbuild import assemble, kernel

FRONTMATTER = "---\nname: implementer\nmodel: opus\neffort: high\n---\n"

SOURCE = (
    "---\nname: implementer\nmodel: opus\n---\n\n"
    "## Metodo\n\nFai la cosa.\n\n"
    "## Contesto di progetto\n\n[DA COMPILARE]\n"
)


class TestReadMethod(unittest.TestCase):
    def test_concatenates_in_filename_order(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "10-b.md").write_text("BETA\n", encoding="utf-8")
            (p / "00-a.md").write_text("ALFA\n", encoding="utf-8")
            out = assemble.read_method(p)
            self.assertLess(out.index("ALFA"), out.index("BETA"))

    def test_ignores_non_markdown(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / "00-a.md").write_text("ALFA\n", encoding="utf-8")
            (p / "notes.txt").write_text("RUMORE\n", encoding="utf-8")
            self.assertNotIn("RUMORE", assemble.read_method(p))


class TestBuildClaudeMd(unittest.TestCase):
    def _method_dir(self, tmp):
        p = Path(tmp)
        (p / "10-orchestration.md").write_text("## Orchestrazione\n", encoding="utf-8")
        return p

    def test_kernel_region_verifies(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(self._method_dir(d), "1.0.0", "## Il progetto\n")
            self.assertEqual(kernel.verify(out), "OK")

    def test_project_sections_outside_region(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(self._method_dir(d), "1.0.0", "## Il progetto\n")
            region = kernel.parse(out)
            self.assertNotIn("Il progetto", region.body)
            self.assertIn("Il progetto", out)

    def test_markers_off_emits_no_marker(self):
        with tempfile.TemporaryDirectory() as d:
            out = assemble.build_document(
                self._method_dir(d), "1.0.0", "## Il progetto\n", markers=False
            )
            self.assertNotIn("FRAMEWORK:KERNEL", out)
            self.assertIn("Orchestrazione", out)
            self.assertIn("Il progetto", out)


class TestBuildAgent(unittest.TestCase):
    def test_frontmatter_is_outside_kernel_region(self):
        out = assemble.build_agent(FRONTMATTER, "## Metodo\n", "## Dominio\n", "1.0.0")
        region = kernel.parse(out)
        self.assertNotIn("model: opus", region.body)
        self.assertTrue(out.startswith("---\n"))

    def test_changing_model_does_not_cause_drift(self):
        a = assemble.build_agent(FRONTMATTER, "## Metodo\n", "## Dominio\n", "1.0.0")
        b = a.replace("model: opus", "model: sonnet")
        self.assertEqual(kernel.verify(b), "OK")

    def test_editing_method_causes_drift(self):
        a = assemble.build_agent(FRONTMATTER, "## Metodo\n", "## Dominio\n", "1.0.0")
        b = a.replace("## Metodo", "## Metodo cambiato")
        self.assertEqual(kernel.verify(b), "DRIFT")

    def test_domain_block_outside_region(self):
        out = assemble.build_agent(FRONTMATTER, "## Metodo\n", "## Dominio\n", "1.0.0")
        self.assertNotIn("Dominio", kernel.parse(out).body)
        self.assertIn("## Dominio", out)


class TestSplitSource(unittest.TestCase):
    def test_returns_three_parts(self):
        fm, method, domain = assemble.split_source(SOURCE)
        self.assertIn("name: implementer", fm)
        self.assertIn("Fai la cosa", method)
        self.assertIn("DA COMPILARE", domain)

    def test_method_excludes_domain_block(self):
        _, method, _ = assemble.split_source(SOURCE)
        self.assertNotIn("DA COMPILARE", method)

    def test_horizontal_rule_in_body_does_not_break_parsing(self):
        text = SOURCE.replace("Fai la cosa.", "Fai la cosa.\n\n---\n\nPoi verifica.")
        fm, method, _ = assemble.split_source(text)
        self.assertIn("name: implementer", fm)
        self.assertIn("Poi verifica", method)

    def test_round_trips_through_build_agent(self):
        fm, method, domain = assemble.split_source(SOURCE)
        built = assemble.build_agent(fm, method, domain, "1.0.0")
        self.assertEqual(kernel.verify(built), "OK")


class TestInstalledCycles(unittest.TestCase):
    def test_detects_only_the_cycles_actually_present(self):
        """`--down` riassembla da `coordinator/`: senza rilevare i cicli già
        installati li cancellerebbe, e il progetto non registra il profilo."""
        root = Path(__file__).resolve().parents[2]
        design = (root / "cycles" / "design.md").read_text(encoding="utf-8")
        found = assemble.installed_cycles(design, root)
        self.assertEqual([p.stem for p in found], ["design"])
        self.assertEqual(assemble.installed_cycles("## Delega", root), [])


class TestInstalledOrchestration(unittest.TestCase):
    ROOT = Path(__file__).resolve().parents[2]

    def _module(self, name):
        return (self.ROOT / "orchestrations" / f"{name}.md").read_text(encoding="utf-8")

    def test_detects_the_one_present(self):
        found = assemble.installed_orchestration(self._module("agent-teams"), self.ROOT)
        self.assertEqual(found.stem, "agent-teams")

    def test_region_without_a_module_is_an_error(self):
        """Nessun modulo riconosciuto è di solito un titolo rinominato nel
        sorgente: ripiegare sul default riscriverebbe al `--down` il modello
        sbagliato, in silenzio. La scelta torna a chi riassembla."""
        with self.assertRaises(ValueError) as e:
            assemble.installed_orchestration("## Delega", self.ROOT)
        self.assertIn("orchestration_file", str(e.exception))

    def test_two_modules_are_an_error(self):
        """Un'orchestrazione per progetto: con due, sceglierne una sarebbe
        indovinare quale l'utente voleva."""
        body = self._module("agent-teams") + self._module("orchestrator-worker")
        with self.assertRaises(ValueError):
            assemble.installed_orchestration(body, self.ROOT)


if __name__ == "__main__":
    unittest.main()
