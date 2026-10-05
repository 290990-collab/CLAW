import tempfile
import unittest
from pathlib import Path

from fwbuild import upgrade


def tree(root: Path, files: dict[str, str]) -> Path:
    """A fake tree: relative path → content. Absent = not there."""
    root.mkdir(parents=True, exist_ok=True)
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    return root


class TestClassify(unittest.TestCase):
    def _plan(self, base, yours, theirs):
        d = Path(self.enterContext(tempfile.TemporaryDirectory()))
        return upgrade.classify(
            tree(d / "base", base), tree(d / "yours", yours), tree(d / "theirs", theirs)
        )

    def test_only_upstream_changed_is_taken(self):
        plan = self._plan({"a.md": "one"}, {"a.md": "one"}, {"a.md": "two"})
        self.assertEqual(plan.theirs, ["a.md"])

    def test_only_you_changed_is_kept(self):
        """This is the case the mode exists for: the line you promoted with
        `--up` must not vanish because a release came out."""
        plan = self._plan({"a.md": "one"}, {"a.md": "mine"}, {"a.md": "one"})
        self.assertEqual(plan.yours, ["a.md"])

    def test_both_changed_is_a_conflict(self):
        plan = self._plan({"a.md": "one"}, {"a.md": "mine"}, {"a.md": "two"})
        self.assertEqual(plan.conflict, ["a.md"])

    def test_the_same_addition_on_both_sides_is_nothing_to_do(self):
        """Your addition landed upstream, identical: it is not a conflict and
        must not be added twice. Without this case the comparison would ask you
        to decide what is already decided."""
        plan = self._plan({"a.md": "one"}, {"a.md": "mine"}, {"a.md": "mine"})
        self.assertEqual(plan.same, ["a.md"])
        self.assertEqual(plan.conflict, [])

    def test_a_file_you_added_is_kept_and_one_upstream_added_is_taken(self):
        plan = self._plan({}, {"mine.md": "x"}, {"theirs.md": "y"})
        self.assertEqual(plan.yours, ["mine.md"])
        self.assertEqual(plan.theirs, ["theirs.md"])

    def test_a_deletion_is_classified_like_any_other_change(self):
        """An absent file is a content: deleted upstream and untouched by you,
        the deletion is taken; deleted by you, it stays deleted."""
        plan = self._plan({"a.md": "x", "b.md": "x"}, {"a.md": "x"}, {"b.md": "x"})
        self.assertEqual(plan.theirs, ["a.md"])
        self.assertEqual(plan.yours, ["b.md"])

    def test_caches_are_not_your_additions(self):
        """They only exist where the code has run: they would show up as your
        addition at every comparison, over files nobody wrote."""
        plan = self._plan(
            {}, {"tools/__pycache__/x.pyc": "b", ".pytest_cache/v/nodeids": "[]"}, {}
        )
        self.assertEqual((plan.yours, plan.conflict), ([], []))


class TestRecord(unittest.TestCase):
    def test_the_base_falls_back_to_version_when_nothing_was_promoted(self):
        """With no record no `--up` was ever done, so `VERSION` is still a
        published number and is the right base."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "VERSION").write_text("1.3.1\n", encoding="utf-8")
            self.assertIsNone(upgrade.read_record(root))
            self.assertEqual(upgrade.base_version(root), "1.3.1")

    def test_the_record_wins_over_a_version_that_was_incremented(self):
        """`--up` increments `VERSION`: from then on the local number matches
        no release, and comparing against it means comparing against a tree
        that does not exist."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "VERSION").write_text("1.4.0\n", encoding="utf-8")
            upgrade.write_record(root, "1.3.1", "CLAW", "https://x/y.git")
            self.assertEqual(upgrade.base_version(root), "1.3.1")
            self.assertEqual(upgrade.read_record(root)["edition"], "CLAW")

    def test_an_unreadable_record_is_a_missing_one(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "VERSION").write_text("1.3.1\n", encoding="utf-8")
            (root / upgrade.RECORD).write_text("{ broken", encoding="utf-8")
            self.assertIsNone(upgrade.read_record(root))
            self.assertEqual(upgrade.base_version(root), "1.3.1")


if __name__ == "__main__":
    unittest.main()
