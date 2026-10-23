import unittest

from fwbuild import kernel


class TestNormalize(unittest.TestCase):
    def test_crlf_becomes_lf(self):
        self.assertEqual(kernel.normalize("a\r\nb"), "a\nb\n")

    def test_trailing_whitespace_stripped(self):
        self.assertEqual(kernel.normalize("a   \nb\t\n"), "a\nb\n")

    def test_ends_with_single_newline(self):
        self.assertEqual(kernel.normalize("a\n\n\n"), "a\n")


class TestWrapParse(unittest.TestCase):
    def test_round_trip_preserves_body(self):
        body = "## Method\n\nRule one.\n"
        region = kernel.parse(kernel.wrap(body, "1.0.0"))
        self.assertEqual(region.body, kernel.normalize(body))
        self.assertEqual(region.version, "1.0.0")

    def test_parse_returns_none_without_marker(self):
        self.assertIsNone(kernel.parse("no marker here\n"))

    def test_the_marker_carries_the_version_and_no_hash(self):
        """A hash in the marker brings back the drift comparison this format
        dropped: the region is regenerated, never compared."""
        marker = kernel.wrap("body\n", "1.0.0").splitlines()[0]
        self.assertIn("v1.0.0", marker)
        self.assertNotIn("sha256", marker)

    def test_the_marker_points_to_the_rules_file_and_old_ones_are_still_read(self):
        """Installations in the field carry the old suffix, with or without a hash."""
        self.assertIn("edit .claude/user-rules.md instead", kernel.wrap("b\n", "3.0.0"))
        for marker in (
            "<!-- FRAMEWORK:KERNEL v2.7.0 — generated, do not edit by hand -->",
            "<!-- FRAMEWORK:KERNEL v3.0.0 — generated — edit .claude/user-rules.md instead -->",
        ):
            region = kernel.parse(f"{marker}\nbody\n<!-- /FRAMEWORK:KERNEL -->\n")
            self.assertEqual(region.body, "body\n", marker)

    def test_a_marker_with_a_hash_is_still_read(self):
        """Installations in the field carry `sha256:` markers; not reading them
        would make every one of them KERNEL_MISSING on the first update."""
        old = (
            "<!-- FRAMEWORK:KERNEL v1.0.0 sha256:a3f9c1e4 — generated, do not edit by hand -->\n"
            "body\n<!-- /FRAMEWORK:KERNEL -->\n"
        )
        region = kernel.parse(old)
        self.assertEqual((region.version, region.body), ("1.0.0", "body\n"))


if __name__ == "__main__":
    unittest.main()
