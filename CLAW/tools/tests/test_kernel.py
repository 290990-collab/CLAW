import unittest

from fwbuild import kernel


class TestNormalize(unittest.TestCase):
    def test_crlf_becomes_lf(self):
        self.assertEqual(kernel.normalize("a\r\nb"), "a\nb\n")

    def test_trailing_whitespace_stripped(self):
        self.assertEqual(kernel.normalize("a   \nb\t\n"), "a\nb\n")

    def test_ends_with_single_newline(self):
        self.assertEqual(kernel.normalize("a\n\n\n"), "a\n")


class TestDigest(unittest.TestCase):
    def test_stable_across_line_endings(self):
        self.assertEqual(kernel.digest("x\ny\n"), kernel.digest("x\r\ny\r\n"))

    def test_stable_across_trailing_whitespace(self):
        self.assertEqual(kernel.digest("x\ny\n"), kernel.digest("x  \ny \n"))

    def test_changes_when_text_changes(self):
        self.assertNotEqual(kernel.digest("x\n"), kernel.digest("y\n"))

    def test_is_eight_hex_chars(self):
        d = kernel.digest("x\n")
        self.assertEqual(len(d), 8)
        self.assertTrue(all(c in "0123456789abcdef" for c in d))


class TestWrapParse(unittest.TestCase):
    def test_round_trip_preserves_body(self):
        body = "## Method\n\nRule one.\n"
        region = kernel.parse(kernel.wrap(body, "1.0.0"))
        self.assertEqual(region.body, kernel.normalize(body))
        self.assertEqual(region.version, "1.0.0")

    def test_parse_returns_none_without_marker(self):
        self.assertIsNone(kernel.parse("no marker here\n"))

    def test_wrapped_text_contains_declared_digest(self):
        body = "body\n"
        self.assertIn(kernel.digest(body), kernel.wrap(body, "1.0.0"))


class TestVerify(unittest.TestCase):
    def test_ok_when_untouched(self):
        self.assertEqual(kernel.verify(kernel.wrap("body\n", "1.0.0")), "OK")

    def test_drift_when_body_edited(self):
        text = kernel.wrap("body\n", "1.0.0").replace("body", "modified body")
        self.assertEqual(kernel.verify(text), "DRIFT")

    def test_missing_when_no_region(self):
        self.assertEqual(kernel.verify("text only\n"), "MISSING")

    def test_no_drift_from_line_ending_change(self):
        text = kernel.wrap("a\nb\n", "1.0.0").replace("\n", "\r\n")
        self.assertEqual(kernel.verify(text), "OK")


if __name__ == "__main__":
    unittest.main()
