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


class TestManifest(unittest.TestCase):
    def test_manifest_carries_the_choices_and_no_source(self):
        """The choices are everything an update regenerates from; a `source` or
        a `frontmatter` record would be a second place saying where the files
        came from."""
        m = source.manifest(
            "1.2.3", "software", "orchestrator-worker", ["explorer"], ["core/a.md"], ["config_protection"]
        )
        self.assertEqual(
            m,
            {
                "version": "1.2.3",
                "profile": "software",
                "orchestration": "orchestrator-worker",
                "agents": ["explorer"],
                "guides": ["core/a.md"],
                "hooks": ["config_protection"],
            },
        )

    def test_settings_record_is_written_even_when_empty(self):
        """An empty record and an absent one say different things: the second
        means "do not touch"."""
        m = source.manifest("1", "p", "o", [], [], [], settings_added={})
        self.assertEqual(m["settings_added"], {})
        self.assertNotIn("settings_added", source.manifest("1", "p", "o", [], [], []))

    def test_accepted_waivers_are_carried_over(self):
        m = source.manifest("1", "p", "o", [], [], [], accepted={"SHARED_ORPHAN": "why"})
        self.assertEqual(m["accepted"], {"SHARED_ORPHAN": "why"})

    def test_read_manifest_is_none_when_absent_or_broken(self):
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            self.assertIsNone(source.read_manifest(prj))
            (prj / ".claude").mkdir()
            (prj / ".claude" / "claw.json").write_text("{", encoding="utf-8")
            self.assertIsNone(source.read_manifest(prj))

    def test_accepted_keeps_entries_without_a_reason(self):
        """Discarding them here would make them vanish silently: whoever
        matches them against the findings must be able to report them."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            (prj / ".claude").mkdir()
            (prj / ".claude" / "claw.json").write_text(
                json.dumps({"accepted": {"A": "a reason", "B": "  ", "C": 3}}),
                encoding="utf-8",
            )
            self.assertEqual(
                source.accepted(prj), {"A": "a reason", "B": "", "C": ""}
            )


if __name__ == "__main__":
    unittest.main()
