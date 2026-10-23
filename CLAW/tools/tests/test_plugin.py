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

    def test_source_is_reached_through_the_plugin_root_only_in_skill_md(self):
        """The plugin root is substituted in `SKILL.md` text and nowhere else: an
        action file (opened with Read) that carried `${CLAUDE_PLUGIN_ROOT}` would
        hand the model a literal, unresolvable path. `claw setup` and the master
        path are the old way in; a surviving mention sends the user to a command
        that no longer exists."""
        skill = FRAMEWORK / "skills" / "claw"
        self.assertIn("${CLAUDE_PLUGIN_ROOT}", (skill / "SKILL.md").read_text(encoding="utf-8"))
        for action in sorted((skill / "actions").glob("*.md")):
            text = action.read_text(encoding="utf-8")
            self.assertNotIn("${CLAUDE_PLUGIN_ROOT}", text, action.name)
        for path in sorted(FRAMEWORK.rglob("*")):
            if (
                not path.is_file()
                or path.suffix not in (".md", ".py", ".toml", ".json")
                or "__pycache__" in path.parts
                or path == Path(__file__).resolve()
            ):
                continue
            text = path.read_text(encoding="utf-8")
            for old in ("claw setup", "claw.py setup", "~/.claude/CLAW"):
                self.assertNotIn(old, text, f"{old!r} in {path.relative_to(FRAMEWORK)}")

    def test_the_skill_may_read_its_own_folder_unasked(self):
        """The plugin's folder is outside the project: without the grant every
        `/claw` asks permission to read its own action file, and `claude -p`
        refuses it outright (observed on 2.1.309)."""
        head = (FRAMEWORK / "skills" / "claw" / "SKILL.md").read_text(encoding="utf-8").split("\n---", 1)[0]
        self.assertIn("\nallowed-tools: Read(${CLAUDE_PLUGIN_ROOT}/**)", head)


if __name__ == "__main__":
    unittest.main()
