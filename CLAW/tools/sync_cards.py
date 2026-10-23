"""Writes each agent card's calibration lines from `cards/agents.toml`.

Run it after editing the toml; `test_cards_match_agents_toml` fails until you do.
"""

from pathlib import Path

from fwbuild import assemble, source

FRAMEWORK = Path(__file__).resolve().parents[1]


def sync(framework_root: Path) -> list[str]:
    """Rewrites every card whose calibration differs from its row; returns their names."""
    rows = assemble.agent_rows(framework_root)
    changed = []
    for path in sorted((framework_root / source.CARDS_DIR).glob("*.md")):
        text = path.read_text(encoding="utf-8")
        norm = text.replace("\r\n", "\n")
        new = assemble.render_card(norm, rows[path.stem])
        if new != norm:
            if "\r\n" in text:
                new = new.replace("\n", "\r\n")
            path.write_bytes(new.encode("utf-8"))
            changed.append(path.stem)
    return changed


if __name__ == "__main__":
    changed = sync(FRAMEWORK)
    for name in changed:
        print(name)
    print(f"{len(changed)} cards changed")
