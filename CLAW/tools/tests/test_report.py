import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from fwbuild import cli, kernel, report

# Absolute and not relative import: `unittest discover -s tests` loads the
# modules as top-level, and a `.test_doctor` in there has no parent package.
# The two runners must give the same number.
from tests.test_doctor import VERSION, make_project


def installed(tmp, name, version=VERSION, declared=None):
    """A project `discover` can find: the marker plus the fixture's files.

    `make_project` builds a valid installation but does not write
    `framework.json` — it is the file that says "there is an installation
    here", and without it the report has nothing to start from.
    """
    root = Path(tmp) / name
    root.mkdir(parents=True)
    make_project(root)
    if version != VERSION:
        for f in [root / "CLAUDE.md"] + sorted(
            (root / ".claude" / "agents").glob("*.md")
        ):
            t = f.read_text(encoding="utf-8")
            r = kernel.parse(t)
            if r is not None:
                f.write_text(
                    t[: r.start] + kernel.wrap(r.body, version) + t[r.end + 1 :],
                    encoding="utf-8",
                )
    (root / ".claude" / "framework.json").write_text(
        json.dumps(
            {
                "source": "framework",
                "version": declared or version,
                "profile": "software",
            }
        ),
        encoding="utf-8",
    )
    return root


class TestDiscovery(unittest.TestCase):
    def test_finds_projects_below_the_given_path(self):
        with tempfile.TemporaryDirectory() as d:
            installed(d, "alpha")
            installed(d, "beta")
            found = report.discover([d])
            self.assertEqual(sorted(p.name for p in found), ["alpha", "beta"])

    def test_a_project_path_is_itself_a_result(self):
        """Pointing the command at a single repository must work: it is how you
        try it before pointing it at forty."""
        with tempfile.TemporaryDirectory() as d:
            root = installed(d, "alpha")
            self.assertEqual(report.discover([root]), [root])

    def test_the_search_stops_at_the_declared_depth(self):
        """A fleet report is pointed at a folder of repositories. Bottomless,
        over a home directory, the command becomes unusable exactly where it is
        needed."""
        with tempfile.TemporaryDirectory() as d:
            deep = Path(d) / "a" / "b" / "c"
            deep.mkdir(parents=True)
            installed(deep, "alpha")
            self.assertEqual(report.discover([d], depth=2), [])
            self.assertEqual(len(report.discover([d], depth=4)), 1)

    def test_a_project_is_not_searched_through(self):
        """Once the marker is found you stop descending: a project containing
        another would count twice, and a repo's subfolders are the expensive
        part to walk."""
        with tempfile.TemporaryDirectory() as d:
            outer = installed(d, "alpha")
            installed(outer, "vendored")
            self.assertEqual(report.discover([d]), [outer])


class TestSurvey(unittest.TestCase):
    def test_the_version_shown_is_the_one_in_the_files(self):
        """`framework.json` says where the project was born from, the kernel
        region says what it contains now. When they diverge the second counts:
        the first gets updated by forgetting about it."""
        with tempfile.TemporaryDirectory() as d:
            root = installed(d, "alpha", version="0.9.0", declared="1.0.0")
            p = report.inspect(root)
            self.assertEqual(p.declared, "1.0.0")
            self.assertEqual(p.version, "0.9.0")

    def test_projects_off_the_source_version_are_listed_as_behind(self):
        with tempfile.TemporaryDirectory() as d:
            installed(d, "alpha")
            installed(d, "beta", version="0.9.0")
            s = report.survey([d], source_version=VERSION)
            self.assertEqual([p.name for p in s.behind], ["beta"])
            self.assertEqual(s.versions, {"0.9.0": 1, VERSION: 1})
            self.assertFalse(s.clean)

    def test_without_a_source_version_there_is_no_direction(self):
        """The majority is not a reference: without a source version the
        distribution is reported, not an invented "behind"."""
        with tempfile.TemporaryDirectory() as d:
            installed(d, "alpha")
            installed(d, "beta", version="0.9.0")
            s = report.survey([d])
            self.assertEqual(s.behind, [])
            self.assertEqual(len(s.versions), 2)

    def test_a_fleet_on_one_version_and_without_findings_is_clean(self):
        with tempfile.TemporaryDirectory() as d:
            installed(d, "alpha")
            installed(d, "beta")
            s = report.survey([d], source_version=VERSION)
            self.assertEqual(s.behind, [])
            self.assertTrue(s.clean, [f for p in s.projects for f in p.findings])

    def test_manual_edits_to_the_method_are_counted(self):
        """Drift is the entry that makes the report useful: a method modified
        by hand in one repo is the fork at its first step."""
        with tempfile.TemporaryDirectory() as d:
            root = installed(d, "alpha")
            c = root / "CLAUDE.md"
            c.write_text(
                c.read_text(encoding="utf-8").replace("Method", "Changed method"),
                encoding="utf-8",
            )
            self.assertTrue(report.inspect(root).drifted)


class TestReportCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def test_json_carries_every_project_and_the_aggregate(self):
        with tempfile.TemporaryDirectory() as d:
            installed(d, "alpha")
            installed(d, "beta", version="0.9.0")
            code, out = self._run(["report", "--json", d])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertEqual(len(payload["projects"]), 2)
            self.assertEqual(payload["behind"], ["beta"])
            self.assertFalse(payload["clean"])

    def test_strict_fails_when_a_project_diverges(self):
        """Without `--strict` the report is a report. With it, it is a CI gate:
        that is the difference between seeing the divergence and not letting it
        through."""
        with tempfile.TemporaryDirectory() as d:
            installed(d, "alpha", version="0.9.0")
            self.assertEqual(self._run(["report", "--strict", d])[0], 1)
            self.assertEqual(self._run(["report", d])[0], 0)

    def test_nothing_found_says_what_it_was_looking_for(self):
        """An empty report without an explanation reads as "all fine"."""
        with tempfile.TemporaryDirectory() as d:
            code, out = self._run(["report", d])
            self.assertEqual(code, 0)
            self.assertIn("framework.json", out)


if __name__ == "__main__":
    unittest.main()
