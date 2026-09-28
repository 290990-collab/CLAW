import io
import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import trial_install
from fwbuild import cli
from tests.test_master import IDENTITY, sh

FRAMEWORK = Path(__file__).resolve().parents[2]
LINE = "**Released upstream:** a rule that only the new version has."


class TestUpdate(unittest.TestCase):
    """`update` is the one command a user runs after a release: it must bring
    the project exactly the down it showed, or nothing."""

    def setUp(self):
        self._env = dict(os.environ)
        os.environ.update(IDENTITY)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def _world(self, d) -> tuple[Path, Path]:
        """A master cloned from an upstream that then releases 9.9.9, and a
        project installed from the version the master still has."""
        # Resolved as `cli.FW` is: git refuses Windows short names (ENRICO~1).
        d = Path(d).resolve()
        up = d / "up"
        shutil.copytree(FRAMEWORK, up / "CLAW-eng",
                        ignore=shutil.ignore_patterns("__pycache__", "_build"))
        sh(up, "init", "-q")
        sh(up, "add", ".")
        sh(up, "commit", "-q", "-m", "release")
        sh(d, "clone", "-q", str(up), str(d / "mine"))
        preamble = up / "CLAW-eng" / "method" / "00-preamble.md"
        preamble.write_text(preamble.read_text(encoding="utf-8") + f"\n{LINE}\n", encoding="utf-8")
        (up / "CLAW-eng" / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        sh(up, "commit", "-q", "-am", "9.9.9")
        prj = d / "prj"
        with redirect_stdout(io.StringIO()):
            trial_install.install(prj)
        return d / "mine" / "CLAW-eng", prj

    def _run(self, fw: Path, home: Path, argv: list[str]) -> tuple[int, str]:
        buf = io.StringIO()
        with patch.object(cli, "FW", fw), patch.object(cli, "SKILLS_HOME", home), \
                redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def _version(self, prj: Path) -> str:
        return json.loads((prj / ".claude" / "framework.json").read_text(encoding="utf-8"))["version"]

    def test_plan_writes_nothing_then_apply_brings_the_release(self):
        with tempfile.TemporaryDirectory() as d:
            fw, prj = self._world(d)
            home = Path(d) / "skills"
            before = self._version(prj)
            code, out = self._run(fw, home, ["update", str(prj)])
            self.assertEqual(code, 0, out)
            self.assertIn("1 incoming commits", out)
            self.assertEqual(self._version(prj), before)
            self.assertNotIn(LINE, (prj / "CLAUDE.md").read_text(encoding="utf-8"))

            code, out = self._run(fw, home, ["update", str(prj), "--apply"])
            self.assertEqual(code, 0, out)
            self.assertEqual((fw / "VERSION").read_text(encoding="utf-8").strip(), "9.9.9")
            self.assertEqual(self._version(prj), "9.9.9")
            self.assertIn(LINE, (prj / "CLAUDE.md").read_text(encoding="utf-8"))
            self.assertTrue((home / "claw-install" / "SKILL.md").is_file())
            self.assertEqual(self._run(fw, home, ["update", str(prj), "--apply"])[0], 1)

    def test_a_project_changed_after_the_plan_gets_no_down(self):
        with tempfile.TemporaryDirectory() as d:
            fw, prj = self._world(d)
            home = Path(d) / "skills"
            self.assertEqual(self._run(fw, home, ["update", str(prj)])[0], 0)
            claude = prj / "CLAUDE.md"
            claude.write_text(claude.read_text(encoding="utf-8") + "\nlocal note\n", encoding="utf-8")
            code, out = self._run(fw, home, ["update", str(prj), "--apply"])
            self.assertEqual(code, 1, out)
            self.assertIn("differs from the plan shown", out)
            self.assertNotIn(LINE, claude.read_text(encoding="utf-8"))
            self.assertEqual(self._version(prj), (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip())


if __name__ == "__main__":
    unittest.main()
