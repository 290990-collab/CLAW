import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from fwbuild import master

FRAMEWORK = Path(__file__).resolve().parents[2]
IDENTITY = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
}


def sh(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def commit(repo: Path, name: str, text: str) -> None:
    (repo / name).write_text(text, encoding="utf-8")
    sh(repo, "add", name)
    sh(repo, "commit", "-q", "-m", name)


class TestMaster(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)
        os.environ.update(IDENTITY)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def clones(self, d) -> tuple[Path, Path]:
        """An upstream with one commit and a master cloned from it."""
        up, mine = Path(d) / "up", Path(d) / "mine"
        up.mkdir()
        sh(up, "init", "-q")
        commit(up, "VERSION", "1.0.0\n")
        commit(up, "a.md", "one\n")
        sh(Path(d), "clone", "-q", str(up), str(mine))
        return up, mine

    def test_merge_keeps_a_promotion_and_takes_the_release(self):
        with tempfile.TemporaryDirectory() as d:
            up, mine = self.clones(d)
            commit(up, "VERSION", "1.1.0\n")
            commit(mine, "b.md", "promoted\n")
            master.git(mine, "fetch", "--quiet")
            self.assertEqual(master.merge(mine), [])
            self.assertEqual((mine / "VERSION").read_text(encoding="utf-8"), "1.1.0\n")
            self.assertTrue((mine / "b.md").is_file())
            self.assertEqual(master.since(mine, "1.0.0")[-1].split(" ", 1)[1], "a.md")

    def test_merge_stops_on_a_conflict_and_names_it(self):
        with tempfile.TemporaryDirectory() as d:
            up, mine = self.clones(d)
            commit(up, "a.md", "theirs\n")
            commit(mine, "a.md", "mine\n")
            master.git(mine, "fetch", "--quiet")
            self.assertEqual(master.merge(mine), ["a.md"])

    def test_user_skills_carry_the_master_path(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            master.install_skills(FRAMEWORK, home)
            for name in master.USER_SKILLS:
                text = (home / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertNotIn(master.TOKEN, text, name)
                self.assertIn(FRAMEWORK.resolve().as_posix(), text, name)


if __name__ == "__main__":
    unittest.main()
