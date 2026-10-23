import io
import tempfile
import unittest
from contextlib import redirect_stdout

from fwbuild import cli
from tests.test_doctor import make_project


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


if __name__ == "__main__":
    unittest.main()
