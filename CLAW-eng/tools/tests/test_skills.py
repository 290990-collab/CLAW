import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import cli, lifecycle, skills

FRAMEWORK = Path(__file__).resolve().parents[2]


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, text=True)


def repo(root: Path, layout: dict[str, str]) -> str:
    """A local repository with the skills described: `path → declared name`."""
    root.mkdir(parents=True)
    for rel, name in layout.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nname: {name}\n---\n\ntest\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    git("-C", str(root), "init", "--quiet")
    git("-C", str(root), "add", "-A")
    git(
        "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
        "commit", "--quiet", "-m", "test",
    )
    return str(root)


def framework(d: Path) -> Path:
    """A fake source with the only folder this module looks at."""
    fw = d / "fw"
    (fw / "skills" / "claw-doctor").mkdir(parents=True)
    (fw / "skills" / "claw-doctor" / "SKILL.md").write_text(
        "---\nname: claw-doctor\n---\n", encoding="utf-8"
    )
    return fw


class TestAdd(unittest.TestCase):
    def test_add_takes_every_skill_and_pins_the_commit(self):
        """The commit is the only thing that makes a package repeatable:
        without it "connected" does not say which version, and a change
        upstream rewrites the instructions with nobody seeing it."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            url = repo(d / "src", {"skills/alfa/SKILL.md": "alfa", "beta/SKILL.md": "beta"})
            pkg = skills.add(fw, url)
            self.assertEqual(pkg.skills, ["alfa", "beta"])
            self.assertEqual(len(pkg.commit), 40)
            self.assertTrue((fw / "skills" / pkg.name / "alfa" / "SKILL.md").is_file())
            self.assertTrue((fw / "skills" / pkg.name / "LICENSE").is_file())
            self.assertEqual(skills.installed(fw), {"alfa": pkg.name, "beta": pkg.name})

    def test_the_folder_name_does_not_decide_the_skill_name(self):
        """Claude Code invokes a skill by the name in the frontmatter:
        installing it under the folder name would make it unreachable."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            url = repo(d / "src", {"different-folder/SKILL.md": "real-name"})
            pkg = skills.add(fw, url)
            self.assertEqual(pkg.skills, ["real-name"])

    def test_a_name_already_connected_stops_the_add(self):
        """In the project the skills sit at one level only: two packages with
        the same name would overwrite each other, and the order of the copy
        would decide the winner."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            skills.add(fw, repo(d / "one", {"a/SKILL.md": "alfa"}))
            with self.assertRaises(ValueError) as e:
                skills.add(fw, repo(d / "two", {"b/SKILL.md": "alfa"}))
            self.assertIn("alfa", str(e.exception))
            self.assertEqual(sorted(skills.installed(fw)), ["alfa"])

    def test_a_framework_skill_name_stops_the_add(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            with self.assertRaises(ValueError):
                skills.add(fw, repo(d / "src", {"x/SKILL.md": "claw-doctor"}))

    def test_a_repo_without_skills_is_an_error(self):
        """An empty package connected in silence is a pool that does not work
        and no finding that says so."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            (d / "empty").mkdir()
            (d / "empty" / "README.md").write_text("nothing\n", encoding="utf-8")
            git("-C", str(d / "empty"), "init", "--quiet")
            git("-C", str(d / "empty"), "add", "-A")
            git(
                "-C", str(d / "empty"), "-c", "user.email=t@t", "-c", "user.name=t",
                "commit", "--quiet", "-m", "empty",
            )
            with self.assertRaises(ValueError):
                skills.add(fw, str(d / "empty"))
            self.assertEqual(skills.packages(fw), [])


class TestPool(unittest.TestCase):
    def test_only_what_is_outside_the_pool_is_hidden_from_the_model(self):
        """That is the pool: inside, the coordinator invokes it; outside, it
        stays with the user. An override on a pool skill would switch it off
        for the one who must be able to call it."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            skills.add(fw, repo(d / "src", {"a/SKILL.md": "alfa", "b/SKILL.md": "beta"}))
            skills.set_pool(fw, ["alfa"])
            self.assertEqual(skills.pool(fw), ["alfa"])
            self.assertEqual(
                skills.overrides(fw), {"skillOverrides": {"beta": "user-invocable-only"}}
            )

    def test_no_package_means_no_settings_entry(self):
        """Without packages the installation must be identical to before: an
        empty key would enter settings_added and the uninstall would remove an
        entry nobody put there."""
        with tempfile.TemporaryDirectory() as d:
            fw = framework(Path(d))
            self.assertEqual(skills.overrides(fw), {})

    def test_a_pool_name_that_is_not_connected_is_an_error(self):
        """A wrong name in the pool means that skill stays hidden from the
        coordinator: the fault is silent and nobody goes looking for it."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            skills.add(fw, repo(d / "src", {"a/SKILL.md": "alfa"}))
            skills.set_pool(fw, ["alfa", "alfaa"])
            with self.assertRaises(ValueError) as e:
                skills.pool(fw)
            self.assertIn("alfaa", str(e.exception))


class TestRemove(unittest.TestCase):
    def test_remove_takes_the_package_out_of_the_pool_too(self):
        """The pool outlives the disconnection: a name left in there would make
        every later installation fail."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            pkg = skills.add(fw, repo(d / "src", {"a/SKILL.md": "alfa"}))
            other = skills.add(fw, repo(d / "two", {"b/SKILL.md": "beta"}))
            skills.set_pool(fw, ["alfa", "beta"])
            self.assertEqual(skills.remove(fw, pkg.name), ["alfa"])
            self.assertEqual(skills.pool(fw), ["beta"])
            self.assertEqual([p.name for p in skills.packages(fw)], [other.name])

    def test_removing_something_that_is_not_a_package_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            fw = framework(Path(d))
            with self.assertRaises(ValueError):
                skills.remove(fw, "claw-doctor")
            self.assertTrue((fw / "skills" / "claw-doctor").is_dir())


class TestInstalledProject(unittest.TestCase):
    """The whole round on a real project: a package connected to a copy of the
    source, then repair and uninstall.

    The source is copied because connecting a package writes inside
    `<FW>/skills/`, and a test does not touch the framework it runs with."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.fw = d / "fw"
        shutil.copytree(
            FRAMEWORK, self.fw, ignore=shutil.ignore_patterns("__pycache__", ".git")
        )
        self.pkg = skills.add(self.fw, repo(d / "src", {"a/SKILL.md": "alfa"}))
        self.prj = d / "trial"
        with redirect_stdout(io.StringIO()):
            trial_install.install(self.prj)

    def tearDown(self):
        self.tmp.cleanup()

    def test_repair_brings_the_package_skill_in_flattened(self):
        """In the project the skills sit at one level: installed under the
        package name, Claude Code would not find it (tested)."""
        ops = lifecycle.plan_repair(self.prj, self.fw)
        rel = ".claude/skills/alfa/SKILL.md"
        self.assertEqual({op.path: op.action for op in ops}[rel], lifecycle.CREATE)
        lifecycle.apply_update(self.prj, self.fw, ops)
        self.assertEqual(
            (self.prj / rel).read_bytes(),
            (self.fw / "skills" / self.pkg.name / "alfa" / "SKILL.md").read_bytes(),
        )

    def test_a_skill_outside_the_pool_is_hidden_from_the_coordinator(self):
        """The pool lives in `settings.json`: without the entry the coordinator
        sees and invokes every connected skill, and the pool stays a sentence
        in a guide."""
        lifecycle.apply_update(self.prj, self.fw, lifecycle.plan_repair(self.prj, self.fw))
        data = json.loads((self.prj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data["skillOverrides"], {"alfa": "user-invocable-only"})
        record = json.loads(
            (self.prj / ".claude" / "framework.json").read_text(encoding="utf-8")
        )
        self.assertEqual(record["settings_added"]["skillOverrides"], {"alfa": "user-invocable-only"})
        self.assertEqual(record["skills"], {"alfa": self.pkg.name})

    def test_uninstall_removes_a_package_skill_it_recognises(self):
        """Identical to the source means "it holds nobody's work": without the
        inverse of the flattened path, the uninstall would take it for project
        material and leave it there."""
        lifecycle.apply_update(self.prj, self.fw, lifecycle.plan_repair(self.prj, self.fw))
        ops = lifecycle.plan_uninstall(self.prj, self.fw)
        rel = ".claude/skills/alfa/SKILL.md"
        self.assertEqual({op.path: op.action for op in ops}[rel], lifecycle.REMOVE)
        lifecycle.apply_uninstall(self.prj, self.fw, ops)
        self.assertFalse((self.prj / ".claude" / "skills" / "alfa").exists())


class TestCommand(unittest.TestCase):
    def test_list_works_on_a_framework_without_packages(self):
        """The normal case is "no package": if the command falls over there, it
        falls over for everyone who has not connected anything yet."""
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["skills", "list", "--source", str(FRAMEWORK)])
        self.assertEqual(code, 0)
        self.assertIn("no package connected", out.getvalue())


class TestSource(unittest.TestCase):
    def test_the_framework_itself_has_no_packages(self):
        """The published source carries no skills by others: if one shows up,
        an integration that had to stay local has ended up in git."""
        self.assertEqual(skills.packages(FRAMEWORK), [])


if __name__ == "__main__":
    unittest.main()
