import json
import unittest
from pathlib import Path

FRAMEWORK = Path(__file__).resolve().parents[2]
REPO = FRAMEWORK.parent


def _json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class TestPluginLayout(unittest.TestCase):
    def test_manifest_name_and_version_follow_the_source(self):
        """`plugin.json` carries its own copy of the version: a release that
        bumps `VERSION` and not the manifest ships a plugin that reports the
        old number and never refreshes the cache."""
        manifest = _json(FRAMEWORK / ".claude-plugin" / "plugin.json")
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        self.assertEqual(manifest["name"], "claw")
        self.assertEqual(manifest["version"], version)

    def test_marketplace_entry_points_at_the_source_folder(self):
        """A `source` that does not resolve to the folder holding
        `.claude-plugin/plugin.json` makes the marketplace list a plugin that
        cannot be installed."""
        market = _json(REPO / ".claude-plugin" / "marketplace.json")
        self.assertNotIn("version", market["plugins"][0])
        entry = next(p for p in market["plugins"] if p["name"] == "claw")
        target = (REPO / entry["source"]).resolve()
        self.assertEqual(target, FRAMEWORK.resolve())
        self.assertTrue((target / ".claude-plugin" / "plugin.json").is_file())

    def test_no_component_folder_that_claude_code_loads_by_itself(self):
        """Claude Code loads these from a plugin root without being asked: an
        `agents/` or `output-styles/` there would put framework cards and
        styles in every session of whoever installs the plugin."""
        for rel in (
            "agents",
            "commands",
            "output-styles",
            "themes",
            "monitors",
            "workflows",
            "hooks/hooks.json",
        ):
            self.assertFalse((FRAMEWORK / rel).exists(), rel)

    def test_only_the_two_skills_are_discovered(self):
        """Every folder in `skills/` becomes a plugin skill: a package dropped
        there would be published as `/claw:<name>`."""
        found = sorted(p.name for p in (FRAMEWORK / "skills").iterdir())
        self.assertEqual(found, ["claw", "delegate"])

    def test_plugin_license_is_the_root_one(self):
        """The plugin folder is what gets copied to the cache: without its own
        LICENSE the copy ships unlicensed, and a stale one contradicts the root."""
        self.assertEqual(
            (FRAMEWORK / "LICENSE").read_bytes(), (REPO / "LICENSE").read_bytes()
        )


if __name__ == "__main__":
    unittest.main()
