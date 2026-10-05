"""The divergence report across many projects.

`doctor` answers "does this installation hold?". This answers a question a
single person does not ask and a company does: **how many versions of the
method are out there, and where**. Across forty repositories divergence is not
visible by looking at one repository at a time — it is visible only by
aggregating, and that is exactly the defect the framework exists to avoid.

It duplicates no check: it calls `doctor` on every project found and lines up
the results.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from . import doctor, kernel

MARKER = Path(".claude") / "framework.json"
# The directories that contain no projects and are expensive to walk.
SKIP = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}


@dataclass(frozen=True)
class Project:
    """An installation found, with what is needed to compare it with the others."""

    path: Path
    declared: str | None
    installed: list[str]
    findings: list[doctor.Finding]
    measure: doctor.Measure | None

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def version(self) -> str:
        """The version to show: the files', not the declared one.

        `framework.json` says where the project was born from; the kernel
        region says what it contains now. When they diverge the second counts —
        the first gets updated by forgetting about it.
        """
        if self.installed:
            return "/".join(sorted(set(self.installed)))
        return self.declared or "?"

    @property
    def errors(self) -> int:
        return sum(1 for f in self.findings if f.severity == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for f in self.findings if f.severity == "WARN")

    @property
    def notes(self) -> int:
        """The declared waivers. Counted apart: they are decisions already
        taken, not work to do, and adding them to the warnings would ruin the
        column that tells you which project to fix."""
        return sum(1 for f in self.findings if f.severity == "NOTE")

    @property
    def drifted(self) -> bool:
        return any(f.code == "KERNEL_DRIFT" for f in self.findings)


@dataclass
class Survey:
    projects: list[Project] = field(default_factory=list)
    source_version: str | None = None

    @property
    def versions(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for p in self.projects:
            out[p.version] = out.get(p.version, 0) + 1
        return dict(sorted(out.items()))

    @property
    def behind(self) -> list[Project]:
        """The projects that are not on the source's version.

        Without a source version there is no "behind": the distribution is
        reported and that is all, instead of electing the most widespread
        version as a reference. The majority is not a reference.
        """
        if self.source_version is None:
            return []
        return [p for p in self.projects if p.version != self.source_version]

    @property
    def clean(self) -> bool:
        return not self.behind and all(
            not any(f.blocking for f in p.findings) for p in self.projects
        )


def discover(roots, depth: int = 2) -> list[Path]:
    """The installed projects under these paths.

    You descend `depth` levels and no further: a fleet report is pointed at a
    folder of repositories, not at the disk. A bottomless search over a home
    directory would make the command unusable exactly where it is needed.
    """
    found: list[Path] = []

    def walk(d: Path, left: int) -> None:
        if (d / MARKER).is_file():
            found.append(d)
            return
        if left <= 0:
            return
        try:
            children = sorted(c for c in d.iterdir() if c.is_dir())
        except OSError:
            return
        for c in children:
            if c.name not in SKIP:
                walk(c, left - 1)

    for root in roots:
        walk(Path(root), depth)
    return found


def _declared(root: Path) -> str | None:
    try:
        data = json.loads((root / MARKER).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    version = data.get("version")
    return version if isinstance(version, str) else None


def _installed(root: Path) -> list[str]:
    out: list[str] = []
    claude = root / "CLAUDE.md"
    files = [claude] if claude.is_file() else []
    agents = root / ".claude" / "agents"
    if agents.is_dir():
        files += sorted(agents.glob("*.md"))
    for f in files:
        region = kernel.parse(f.read_text(encoding="utf-8"))
        if region is not None and region.version not in out:
            out.append(region.version)
    return out


def inspect(root: Path) -> Project:
    root = Path(root)
    claude = root / "CLAUDE.md"
    return Project(
        path=root,
        declared=_declared(root),
        installed=_installed(root),
        findings=doctor.check(root),
        measure=doctor.measure(claude.read_text(encoding="utf-8"))
        if claude.is_file()
        else None,
    )


def survey(roots, depth: int = 2, source_version: str | None = None) -> Survey:
    return Survey(
        projects=[inspect(p) for p in discover(roots, depth)],
        source_version=source_version,
    )


def as_dict(s: Survey) -> dict:
    return {
        "source_version": s.source_version,
        "projects": [
            {
                "path": str(p.path),
                "name": p.name,
                "version": p.version,
                "declared": p.declared,
                "errors": p.errors,
                "warnings": p.warnings,
                "notes": p.notes,
                "drifted": p.drifted,
                "tokens": None if p.measure is None else p.measure.tokens,
                "findings": [
                    {"code": f.code, "severity": f.severity, "message": f.message}
                    for f in p.findings
                ],
            }
            for p in s.projects
        ],
        "versions": s.versions,
        "behind": [p.name for p in s.behind],
        "clean": s.clean,
    }
