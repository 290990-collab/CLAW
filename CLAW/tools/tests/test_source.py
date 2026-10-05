import json
import tempfile
import unittest
from pathlib import Path

from fwbuild import source

FRAMEWORK = Path(__file__).resolve().parents[1]


def make_root(base: Path, *, drop: str = "") -> Path:
    """A fake framework root: the mandatory entries, minus the named one.

    Fictitious roots and not the real one: the search must be testable without
    depending on where the framework running the tests is installed.
    """
    for entry in source.REQUIRED:
        if entry == drop:
            continue
        if entry == "VERSION":
            base.mkdir(parents=True, exist_ok=True)
            (base / entry).write_text("9.9.9\n", encoding="utf-8")
        else:
            (base / entry).mkdir(parents=True, exist_ok=True)
    return base


class TestMissing(unittest.TestCase):
    def test_real_framework_is_a_valid_root(self):
        self.assertEqual(source.missing(FRAMEWORK.parent), [])

    def test_reports_what_is_absent(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_root(Path(d) / "maimed", drop="profiles")
            self.assertEqual(source.missing(root), ["profiles"])

    def test_unrelated_directory_is_not_a_framework(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(source.missing(Path(d)), list(source.REQUIRED))


class TestResolve(unittest.TestCase):
    def test_finds_root_passed_directly(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_root(Path(d) / "fw")
            self.assertEqual(source.resolve([root]), root)

    def test_finds_framework_subdirectory(self):
        """Source copied inside the project: the project root is passed."""
        with tempfile.TemporaryDirectory() as d:
            root = make_root(Path(d) / "framework")
            self.assertEqual(source.resolve([Path(d)]), root)

    def test_first_valid_candidate_wins(self):
        with tempfile.TemporaryDirectory() as d:
            master = make_root(Path(d) / "master")
            self.assertEqual(source.resolve([Path(d) / "empty", master]), master)

    def test_single_invalid_candidate_raises(self):
        """The rule "path given but invalid: an error, no fallback" is not a
        special case of the resolver: it is the caller that passes a single
        candidate. A silent fallback masks a wrong path."""
        with tempfile.TemporaryDirectory() as d:
            make_root(Path(d) / "elsewhere")
            with self.assertRaises(LookupError):
                source.resolve([Path(d) / "wrong"])

    def test_error_names_what_is_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_root(Path(d) / "maimed", drop="agents")
            with self.assertRaises(LookupError) as e:
                source.resolve([root])
            self.assertIn("agents", str(e.exception))


class TestManifest(unittest.TestCase):
    def test_manifest_carries_source_version_and_profile(self):
        """Without the profile an installation no longer knows what it is made of and the permissions
        cannot be regenerated."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d) / "prj"
            fw = prj / "framework"
            fw.mkdir(parents=True)
            m = source.manifest(prj, fw, "1.2.3", "software")
            self.assertEqual(
                m, {"source": "framework", "version": "1.2.3", "profile": "software"}
            )

    def test_read_manifest_is_none_when_absent_or_broken(self):
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            self.assertIsNone(source.read_manifest(prj))
            (prj / ".claude").mkdir()
            (prj / ".claude" / "framework.json").write_text("{", encoding="utf-8")
            self.assertIsNone(source.read_manifest(prj))

    def test_accepted_keeps_entries_without_a_reason(self):
        """Discarding them here would make them vanish silently: whoever
        matches them against the findings must be able to report them."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            (prj / ".claude").mkdir()
            (prj / ".claude" / "framework.json").write_text(
                json.dumps({"accepted": {"A": "a reason", "B": "  ", "C": 3}}),
                encoding="utf-8",
            )
            self.assertEqual(
                source.accepted(prj), {"A": "a reason", "B": "", "C": ""}
            )


if __name__ == "__main__":
    unittest.main()
