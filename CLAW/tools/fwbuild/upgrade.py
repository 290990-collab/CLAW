"""Bringing a new release over a source the user has modified.

`--up` exists because the source gets modified: whoever does it faces a flat
choice at the next release — overwrite and lose their own work, or stay behind
forever. One datum is enough to avoid it: **which release that copy came
from**. The number in `VERSION` is not enough, because `--up` increments it
and from then on it matches nothing published.

The comparison is over three trees and the classification has four outcomes, no
more: they are the only possible combinations, and they treat a deletion as any
other change (an absent file is a content like the others).
"""

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

RECORD = "upstream.json"

# Not framework content: they would show up as "your additions" at every
# comparison, and noise is something one learns to ignore.
SKIP = {"__pycache__", ".git", ".pytest_cache"}


@dataclass(frozen=True)
class Plan:
    """What to do, path by path, relative to each tree's root."""

    theirs: list[str] = field(default_factory=list)
    yours: list[str] = field(default_factory=list)
    same: list[str] = field(default_factory=list)
    conflict: list[str] = field(default_factory=list)


def read_record(root: Path) -> dict | None:
    """The source's record, or `None` if absent or unreadable.

    The two are not told apart: for whoever is upgrading they are the same
    fault, namely no declared base, and the answer is the same.
    """
    try:
        data = json.loads((Path(root) / RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def write_record(root: Path, base: str, edition: str, repo: str) -> dict:
    """Writes the record. The caller decides *when*: at the first `--up` it
    carries the release being left, after an upgrade the one just taken."""
    data = {"base": base, "edition": edition, "repo": repo}
    (Path(root) / RECORD).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return data


def base_version(root: Path) -> str:
    """The release to compare from.

    With no record it falls back to `VERSION`, and the fallback is **right**
    exactly in the case where the record is missing: no `--up` was ever done, so
    `VERSION` is still a published number.
    """
    record = read_record(root)
    if record and isinstance(record.get("base"), str) and record["base"].strip():
        return record["base"].strip()
    return (Path(root) / "VERSION").read_text(encoding="utf-8").strip()


def _digest(path: Path) -> str | None:
    """A file's fingerprint, or `None` if it is not there. Absence is a content:
    it is what classifies a deletion without one more branch."""
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _paths(root: Path) -> set[str]:
    root = Path(root)
    return {
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and not SKIP & set(p.parts)
    }


def classify(base: Path, yours: Path, theirs: Path) -> Plan:
    """The three trees compared path by path.

    `yours` is the source the user works with, `theirs` the new release, `base`
    the one `yours` started from. Nothing is written: applying is a decision,
    and the tooling does not take decisions.
    """
    base, yours, theirs = Path(base), Path(yours), Path(theirs)
    plan = Plan()
    for rel in sorted(_paths(base) | _paths(yours) | _paths(theirs)):
        b = _digest(base / rel)
        y = _digest(yours / rel)
        t = _digest(theirs / rel)
        if y == t:
            plan.same.append(rel)
        elif y == b:
            plan.theirs.append(rel)
        elif t == b:
            plan.yours.append(rel)
        else:
            plan.conflict.append(rel)
    return plan
