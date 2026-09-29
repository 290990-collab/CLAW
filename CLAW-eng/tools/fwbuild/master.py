"""The master: the git clone the source lives in, and the user-level skills it serves.

Upgrading is git's job: fetch, show what arrives, merge. A change promoted with
`--up` is a commit, and git carries it through the merge or stops on the
conflict. The `/claw` skill is copied into the user's skills with `<FW>` written as the
master's path: one skill for every project, no search for the source, no path
to type. `claw` on the PATH is a launcher of this source's `claw.py`.
"""

import os
import shutil
import subprocess
import zipfile
from pathlib import Path

USER_SKILLS = ("claw",)
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


def export(fw: Path, ref: str, dest: Path) -> None:
    """The source as it stands at `ref`, written into `dest`: the version a
    plan is computed against before it is merged."""
    prefix = git(fw, "rev-parse", "--show-prefix")
    archive = Path(dest) / "source.zip"
    # From a subdirectory, `git archive <ref>:<prefix>` fails ("current working
    # directory is untracked"): it runs from the clone's root.
    top = Path(git(fw, "rev-parse", "--show-toplevel"))
    git(top, "archive", "--format=zip", "-o", str(archive), f"{ref}:{prefix}")
    with zipfile.ZipFile(archive) as z:
        z.extractall(dest)
    archive.unlink()


def merge(fw: Path, ref: str = "@{u}") -> list[str]:
    """Merges `ref`, the tracked branch by default: fast-forward, else a merge
    commit. Returns the conflicted files, empty on success; on conflict the
    merge stays open for the user to resolve. Any other failure raises."""
    if _run(fw, "merge", "--ff-only", ref).returncode == 0:
        return []
    out = _run(fw, "merge", "--no-edit", ref)
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


def _launchers(bin_dir: Path) -> list[Path]:
    """`claw` for POSIX shells, and `claw.cmd` too on Windows, where PowerShell
    and cmd find a command by its extension."""
    names = ["claw", "claw.cmd"] if os.name == "nt" else ["claw"]
    return [Path(bin_dir) / n for n in names]


def launcher_plan(bin_dir: Path) -> list[tuple[str, str]]:
    """`(action, file)` for every launcher."""
    return [("overwrite" if p.exists() else "create", str(p)) for p in _launchers(bin_dir)]


def install_launcher(fw: Path, bin_dir: Path, python: str) -> None:
    """`claw <args>` runs this source's `claw.py` with the Python that ran the
    setup: a second Python on the machine does not change which one runs it."""
    script = Path(fw).resolve() / "claw.py"
    Path(bin_dir).mkdir(parents=True, exist_ok=True)
    for p in _launchers(bin_dir):
        if p.suffix == ".cmd":
            p.write_text(f'@"{Path(python)}" "{script}" %*\r\n', encoding="utf-8")
        else:
            p.write_text(
                f'#!/bin/sh\nexec "{Path(python).as_posix()}" "{script.as_posix()}" "$@"\n',
                encoding="utf-8",
                newline="\n",
            )
            p.chmod(0o755)


def on_path(bin_dir: Path) -> bool:
    folders = os.environ.get("PATH", "").split(os.pathsep)
    target = os.path.normcase(str(Path(bin_dir).resolve()))
    return any(f and os.path.normcase(str(Path(f).resolve())) == target for f in folders)
