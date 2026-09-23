"""The master: the git clone the source lives in, and the user-level skills it serves.

Upgrading is git's job: fetch, show what arrives, merge. A change promoted with
`--up` is a commit, and git carries it through the merge or stops on the
conflict. The skills that run before any project exists — `claw-install`,
`claw-comply` — are copied into the user's skills with `<FW>` written as the
master's path: no search for the source, no path to type.
"""

import shutil
import subprocess
from pathlib import Path

USER_SKILLS = ("claw-install", "claw-comply")
TOKEN = "<FW>"


def _run(fw: Path, *args: str) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(fw), *args], capture_output=True, text=True, encoding="utf-8"
        )
    except FileNotFoundError as e:
        raise RuntimeError("git not found") from e


def git(fw: Path, *args: str, check: bool = True) -> str:
    out = _run(fw, *args)
    if out.returncode != 0:
        if check:
            raise RuntimeError(f"git {' '.join(args)}: {(out.stderr or out.stdout).strip()}")
        return ""
    return out.stdout.strip()


def is_clone(fw: Path) -> bool:
    try:
        return git(fw, "rev-parse", "--is-inside-work-tree", check=False) == "true"
    except RuntimeError:
        return False


def upstream(fw: Path) -> str:
    """The tracked branch, empty if none."""
    return git(fw, "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}", check=False)


def lines(fw: Path, *args: str) -> list[str]:
    return [line for line in git(fw, *args).splitlines() if line]


def since(fw: Path, version: str) -> list[str] | None:
    """The commits on the source after the one that set `VERSION` to `version`;
    `None` if no commit ever declared it."""
    for commit in lines(fw, "log", "--format=%H", "--", "VERSION"):
        if git(fw, "show", f"{commit}:./VERSION", check=False).strip() == version:
            return lines(fw, "log", "--oneline", f"{commit}..HEAD", "--", ".")
    return None


def merge(fw: Path) -> list[str]:
    """Merges the tracked branch: fast-forward, else a merge commit. Returns
    the conflicted files, empty on success; on conflict the merge stays open
    for the user to resolve. Any other failure raises."""
    if _run(fw, "merge", "--ff-only", "@{u}").returncode == 0:
        return []
    out = _run(fw, "merge", "--no-edit", "@{u}")
    if out.returncode == 0:
        return []
    conflicts = lines(fw, "diff", "--name-only", "--diff-filter=U")
    if not conflicts:
        raise RuntimeError(f"git merge: {(out.stderr or out.stdout).strip()}")
    return conflicts


def skill_plan(fw: Path, home: Path) -> list[tuple[str, str]]:
    """`(action, folder)` for every user-level skill."""
    return [
        ("overwrite" if (home / name).exists() else "create", str(home / name))
        for name in USER_SKILLS
    ]


def install_skills(fw: Path, home: Path) -> None:
    for name in USER_SKILLS:
        dest = home / name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(fw / "skills" / name, dest)
        for p in dest.rglob("*.md"):
            p.write_text(
                p.read_text(encoding="utf-8").replace(TOKEN, Path(fw).resolve().as_posix()),
                encoding="utf-8",
            )
