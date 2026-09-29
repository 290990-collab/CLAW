import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from fwbuild import cli, source, upgrade
from tests.test_doctor import make_project

FRAMEWORK = Path(__file__).resolve().parents[2]
VERSION = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()


def _fake_source(parent: Path) -> Path:
    """A root `source.resolve` accepts, without copying the framework."""
    root = parent / "fw"
    for rel in source.REQUIRED:
        if rel == "VERSION":
            root.mkdir(exist_ok=True)
            (root / rel).write_text("9.9.9\n", encoding="utf-8")
        else:
            (root / rel).mkdir(parents=True, exist_ok=True)
    return root


class TestDoctorCommand(unittest.TestCase):
    def test_exit_zero_on_clean_project(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_project(d)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["doctor", str(root)]), 0)

    def test_exit_one_when_error_finding(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_project(d, placeholder=True)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["doctor", str(root)]), 1)

    def test_prints_finding_codes(self):
        with tempfile.TemporaryDirectory() as d:
            root = make_project(d, placeholder=True)
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["doctor", str(root)])
            self.assertIn("PLACEHOLDER", buf.getvalue())

    def test_strict_exits_one_on_warning_only(self):
        """Step 6 of the installation says any finding leaves it incomplete:
        without --strict that rule would stay prose only."""
        with tempfile.TemporaryDirectory() as d:
            root = make_project(d, settings=False)
            with redirect_stdout(io.StringIO()):
                self.assertEqual(cli.main(["doctor", str(root)]), 0)
                self.assertEqual(cli.main(["doctor", "--strict", str(root)]), 1)


class TestSourceCommand(unittest.TestCase):
    def test_prints_root_and_version(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(cli.main(["source", str(FRAMEWORK)]), 0)
        self.assertIn(f"v{VERSION}", buf.getvalue())

    def test_exit_one_and_says_what_is_missing(self):
        """The gate exists to stop **before** a folder has been created: it
        must say what is missing, not only that something is wrong."""
        with tempfile.TemporaryDirectory() as d:
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["source", d]), 1)
            self.assertIn("method", buf.getvalue())

    def test_says_whether_the_source_has_been_promoted(self):
        """A source with no record is taken to be intact by an update by replacement and
        replaced: what `--up` promoted is lost there, and until now no command
        said so beforehand."""
        with tempfile.TemporaryDirectory() as d:
            root = _fake_source(Path(d))
            buf = io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(cli.main(["source", str(root)]), 0)
            self.assertIn("no upstream record", buf.getvalue())
            upgrade.write_record(root, "1.2.3", "edition", "github.com/x/y")
            buf = io.StringIO()
            with redirect_stdout(buf):
                cli.main(["source", str(root)])
            self.assertIn("base v1.2.3", buf.getvalue())
            self.assertIn("github.com/x/y", buf.getvalue())

    def test_explicit_path_is_the_only_candidate(self):
        """Where the "no fallback" rule is really decided."""
        self.assertEqual(cli._bases(Path("/x")), [Path("/x")])

    def test_env_var_comes_before_home(self):
        """The "single master" way: without it, only the source in the project
        remains."""
        with patch.dict(os.environ, {"CLAUDE_FRAMEWORK": "/master"}):
            self.assertEqual(cli._bases(None)[1], Path("/master"))


if __name__ == "__main__":
    unittest.main()
