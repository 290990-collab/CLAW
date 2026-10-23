"""Validating the source root and reading the project manifest."""

import json
from pathlib import Path

# The source folders Claude Code would load by themselves as plugin components
# (`agents/`, `output-styles/`) under another name; the project folders
# `.claude/agents/` and `.claude/output-styles/` keep theirs.
CARDS_DIR = "cards"
STYLES_DIR = "styles"

# What the installation cannot even begin without.
REQUIRED = (
    "VERSION",
    "method",
    "coordinator",
    "orchestrations",
    CARDS_DIR,
    "profiles",
    "templates",
    "skills",
    "hooks",
    "tools/fwbuild",
)


def missing(root: Path) -> list[str]:
    """The mandatory entries that are absent. Empty = it is a framework root."""
    return [r for r in REQUIRED if not (Path(root) / r).exists()]


MANIFEST = Path(".claude") / "claw.json"

# What `generate` needs to rebuild an installation, in the order the file shows it.
MANIFEST_LISTS = ("agents", "guides", "hooks")


def manifest(
    version: str,
    profile_name: str,
    orchestration: str,
    agents: list[str],
    guides: list[str],
    hooks: list[str],
    settings_added: dict | None = None,
    accepted: dict | None = None,
) -> dict:
    """The contents of `.claude/claw.json`: the installation's choices.

    Everything `assemble.generate` takes besides the user's rules lives here, so
    an update can rebuild the files from the source without inferring anything
    from the tree.

    `settings_added` is what the installation actually added to
    `settings.json`: the only piece of that file the uninstall may remove. It is
    written only if present — an empty record and an absent one say different
    things, and the second means "do not touch". `accepted` is the project's:
    it is carried over, never invented.
    """
    data = {
        "version": version,
        "profile": profile_name,
        "orchestration": orchestration,
        "agents": list(agents),
        "guides": list(guides),
        "hooks": list(hooks),
    }
    if settings_added is not None:
        data["settings_added"] = settings_added
    if accepted:
        data["accepted"] = accepted
    return data


def read_manifest(project_root: Path) -> dict | None:
    """The manifest as read, or `None` if absent or unreadable.

    The two are deliberately not told apart: for whoever reads the project they
    are the same failure — `/claw` cannot find the source — and the
    doctor reports them under the same code.
    """
    try:
        data = json.loads((Path(project_root) / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def accepted(project_root: Path) -> dict[str, str]:
    """The waivers declared in the manifest: `code` or `code:fragment` → reason.

    **All** of them are returned, empty reason included: discarding them here
    would make them vanish silently, and a waiver that does not apply is the
    thing the doctor must say, not hide. What becomes of them is decided by
    whoever matches them against the findings.
    """
    data = read_manifest(project_root) or {}
    raw = data.get("accepted")
    if not isinstance(raw, dict):
        return {}
    return {str(k): (v.strip() if isinstance(v, str) else "") for k, v in raw.items()}
