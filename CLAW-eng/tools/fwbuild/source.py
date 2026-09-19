"""Finding and validating the source root.

A downloadable product cannot hard-code one machine's path: you search in order
and validate before writing. The search is **pure** — the candidates are
assembled by the caller — because it is the only way to test it without
depending on where the framework running the tests lives.
"""

import json
from collections.abc import Sequence
from pathlib import Path

# What the installation cannot even begin without.
REQUIRED = (
    "VERSION",
    "method",
    "coordinator",
    "orchestrations",
    "agents",
    "profiles",
    "templates",
    "skills",
    "hooks",
    "tools/fwbuild",
)


def missing(root: Path) -> list[str]:
    """The mandatory entries that are absent. Empty = it is a framework root."""
    return [r for r in REQUIRED if not (Path(root) / r).exists()]


def resolve(bases: Sequence[Path]) -> Path:
    """The first valid root, trying `<base>` and then `<base>/framework`.

    The two shapes — source copied into the project and single master — are
    covered by the same probe, without one more rule.

    "Path given but invalid: an error, no fallback" is not a special case in
    here: it is the caller that, having one, passes a single candidate. A
    silent fallback masks a wrong path.
    """
    tried = []
    for base in bases:
        for cand in (Path(base), Path(base) / "framework"):
            gaps = missing(cand)
            if not gaps:
                return cand
            tried.append(
                f"{cand}: "
                + ("absent" if not cand.is_dir() else f"missing {', '.join(gaps)}")
            )
    raise LookupError("no valid source among:\n  " + "\n  ".join(tried))


def reference(project_root: Path, framework_root: Path) -> str:
    """How `.claude/framework.json` must cite the source.

    The first of the three supported ways is the source **inside** the project:
    there an absolute path is the machine of whoever installed it, and the
    first clone finds a `source` that does not exist. Relative to the project
    root, instead, it travels with the repository. Outside the project a
    relative path does not hold — the depth of the clone is unknown — and the
    absolute one remains the only writable form.

    It is here and not in the skill: a rule written only in prose gets
    disregarded.
    """
    project_root = Path(project_root).resolve()
    framework_root = Path(framework_root).resolve()
    if framework_root == project_root or project_root in framework_root.parents:
        return framework_root.relative_to(project_root).as_posix() or "."
    return str(framework_root)


def dereference(project_root: Path, recorded: str) -> Path:
    """The inverse: the `source` read from `framework.json` as a real path.

    A relative path resolves against the project root, not against the working
    directory: `claw-doctor` and `claw-sync` run from `<FW>/tools`,
    not from `<PRJ>`.
    """
    p = Path(recorded)
    return p if p.is_absolute() else (Path(project_root) / p).resolve()


MANIFEST = Path(".claude") / "framework.json"


def manifest(
    project_root: Path,
    framework_root: Path,
    version: str,
    profile_name: str,
    settings_added: dict | None = None,
    skills: dict[str, str] | None = None,
) -> dict:
    """The contents of `.claude/framework.json`.

    `source` and `version` say where the project was born. `profile` says what
    it is **made of**: without it, `SETTINGS_MISSING` prescribes regenerating
    the permissions "of the project's profile" that nobody can name any more,
    and a change of field has no starting point.

    `settings_added` is what the installation actually added to
    `settings.json`: the only piece of that file the uninstall may remove. It is
    written only if present — an empty record and an absent one say different
    things, and the second means "do not touch".

    `skills` is `skill name → package` for the skills of the connected
    packages: in the project they all sit at one level and where they come from
    is no longer visible. Without it the doctor cannot say which package is
    missing without reaching the source, which may not be there on the machine
    of whoever opens the project.
    """
    data = {
        "source": reference(project_root, framework_root),
        "version": version,
        "profile": profile_name,
    }
    if settings_added is not None:
        data["settings_added"] = settings_added
    if skills:
        data["skills"] = dict(skills)
    return data


def read_manifest(project_root: Path) -> dict | None:
    """The manifest as read, or `None` if absent or unreadable.

    The two are deliberately not told apart: for whoever reads the project they
    are the same failure — `claw-sync` cannot find the source — and the
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
