"""The skill packages connected to the framework.

Skills by other authors are not published with the framework: the socket is
here, the packages stay on the machine of whoever connects them. A package is a
repository, pinned to a commit, under `<FW>/skills/<package>/`.

The **pool** is the list of skills the coordinator may invoke on its own.
Everything connected and outside the pool stays invocable by the user and
invisible to the model: `skillOverrides` in `settings.json` does that, not a
rule written in prose.

In the installed project the skills all sit in `.claude/skills/<skill>/`: the
package level lives only here, because Claude Code does not discover a skill
nested any deeper.
"""

import re
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PACKAGE_FILE = "PACKAGE.toml"
POOL_FILE = "pool.toml"
# The prefix of the framework's own skills: they are published and do not come
# from a package. A package carrying one of the same name would cover it.
RESERVED = "framework-"
# How Claude Code names a skill: the installed folder takes this name.
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Package:
    """A connected repository: its name here, where it comes from, what it brings.

    `skills` is read from disk and not from `PACKAGE.toml`: the record says
    where the package comes from, but what is inside it is what the folders say.
    Two sources for the same fact drift apart, and the wrong copy would be the
    one the installation follows.
    """

    name: str
    repo: str
    commit: str
    skills: list[str]


def packages(framework_root: Path) -> list[Package]:
    """The connected packages. Empty means none, and that is the normal case."""
    base = Path(framework_root) / "skills"
    out = []
    for d in sorted(p for p in base.glob("*") if (p / PACKAGE_FILE).is_file()):
        data = tomllib.loads((d / PACKAGE_FILE).read_text(encoding="utf-8"))
        out.append(
            Package(
                name=d.name,
                repo=str(data.get("repo", "")),
                commit=str(data.get("commit", "")),
                skills=sorted(
                    s.name for s in d.iterdir() if (s / "SKILL.md").is_file()
                ),
            )
        )
    return out


def installed(framework_root: Path) -> dict[str, str]:
    """`skill name → package`: the inverse the flattened paths need.

    Two packages with the same skill are an error, not a precedence: in the
    project they land at the same path, and which of the two wins would depend
    on the order of the copy.
    """
    out: dict[str, str] = {}
    for pkg in packages(framework_root):
        for skill in pkg.skills:
            if skill in out:
                raise ValueError(
                    f"skill {skill!r} in two packages ({out[skill]} and {pkg.name}): "
                    "in the project they sit at the same path, drop one"
                )
            out[skill] = pkg.name
    return out


def source_dir(framework_root: Path, skill: str) -> Path | None:
    """The source folder of a package skill, or `None` if it is not one."""
    pkg = installed(framework_root).get(skill)
    return None if pkg is None else Path(framework_root) / "skills" / pkg / skill


def pool(framework_root: Path) -> list[str]:
    """The skills the coordinator may invoke on its own.

    A name matching nothing stops here: written by hand in a file, a typo would
    mean that skill stays hidden from the coordinator, and that is exactly the
    fault nobody would go looking for.
    """
    path = Path(framework_root) / "skills" / POOL_FILE
    if not path.is_file():
        return []
    names = [str(n) for n in tomllib.loads(path.read_text(encoding="utf-8")).get("skills", [])]
    known = installed(framework_root)
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(
            f"{POOL_FILE} names skills that are not connected: {', '.join(unknown)}"
        )
    return names


def overrides(framework_root: Path) -> dict:
    """The part of `settings.json` that keeps out what does not belong to the pool.

    Package skills only: the framework's own and the user's are not touched. No
    package connected → empty dict, so the installation stays the one from
    before instead of writing a key with no entries.
    """
    in_pool = set(pool(framework_root))
    out = {
        skill: "user-invocable-only"
        for skill in sorted(installed(framework_root))
        if skill not in in_pool
    }
    return {"skillOverrides": out} if out else {}


def set_pool(framework_root: Path, names: list[str]) -> None:
    path = Path(framework_root) / "skills" / POOL_FILE
    body = "".join(f'  "{n}",\n' for n in names)
    path.write_text(
        "# The skills the coordinator may invoke on its own. Local, not published.\n"
        + (f"skills = [\n{body}]\n" if names else "skills = []\n"),
        encoding="utf-8",
    )


def package_name(repo: str) -> str:
    """`<owner>-<repository>` from the source, so two `skills` do not collide.

    The last two parts and not the name alone: `skills` is the name of half the
    repositories out there, and two packages like that would land in the same
    folder. The backslash is a separator too, because the source can be a local
    Windows folder, and only what can be a folder name anywhere is kept.
    """
    parts = [p for p in re.split(r"[/\\:]", repo.rstrip("/\\").removesuffix(".git")) if p]
    name = "-".join(parts[-2:] if len(parts) >= 2 else parts[-1:]).lower()
    return re.sub(r"[^a-z0-9._-]+", "-", name).strip("-")


def add(framework_root: Path, repo: str, commit: str | None = None) -> Package:
    """Connect a repository: fetch it, pin it to a commit, copy its skills.

    Every folder with a `SKILL.md` is copied, under the name declared in the
    frontmatter — that is the one Claude Code invokes it by, and a folder named
    differently would install an unreachable skill. A name already connected
    stops everything before writing: in the project the skills sit at one level
    only and the second would cover the first.
    """
    fw = Path(framework_root)
    name = package_name(repo)
    dest = fw / "skills" / name
    if dest.exists():
        raise ValueError(f"{name} is already connected: disconnect it before reconnecting")

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        _git("clone", "--quiet", repo, str(clone))
        if commit:
            _git("-C", str(clone), "checkout", "--quiet", commit)
        resolved = _git("-C", str(clone), "rev-parse", "HEAD").strip()

        found: dict[str, Path] = {}
        for skill_md in sorted(clone.rglob("SKILL.md")):
            if ".git" in skill_md.parts:
                continue
            skill = _skill_name(skill_md)
            if skill in found:
                raise ValueError(
                    f"{repo} brings two skills named {skill!r}: they cannot be "
                    "installed together"
                )
            found[skill] = skill_md.parent
        if not found:
            raise ValueError(f"{repo}: no SKILL.md, there is nothing to connect")

        taken = set(installed(fw)) | {
            p.name for p in (fw / "skills").glob(f"{RESERVED}*")
        }
        clash = sorted(set(found) & taken)
        if clash:
            raise ValueError(
                "skill names already present, nothing was written: " + ", ".join(clash)
            )

        dest.mkdir(parents=True)
        for skill, src in found.items():
            shutil.copytree(src, dest / skill)
        for license_file in sorted(clone.glob("LICENSE*")):
            shutil.copyfile(license_file, dest / license_file.name)
        (dest / PACKAGE_FILE).write_text(
            f"repo = {_toml_str(repo)}\ncommit = {_toml_str(resolved)}\n"
            f"added = {_toml_str(date.today().isoformat())}\n",
            encoding="utf-8",
        )
    return next(p for p in packages(fw) if p.name == name)


def remove(framework_root: Path, name: str) -> list[str]:
    """Disconnect a package and take its skills out of the pool. Returns what went."""
    fw = Path(framework_root)
    dest = fw / "skills" / name
    if not (dest / PACKAGE_FILE).is_file():
        raise ValueError(f"{name} is not a connected package")
    gone = next(p.skills for p in packages(fw) if p.name == name)
    keep = [n for n in pool(fw) if n not in gone]
    shutil.rmtree(dest)
    if (fw / "skills" / POOL_FILE).is_file():
        set_pool(fw, keep)
    return gone


def shadowed(names: list[str]) -> list[str]:
    """Which of these names already has a personal skill, which would win.

    Precedence is the user's: `~/.claude/skills/<name>` covers the project's
    one. It is not a fault of the framework — it is the machine of whoever
    installs — but finding out later means having read the wrong skill.
    """
    home = Path.home() / ".claude" / "skills"
    return [n for n in names if (home / n / "SKILL.md").is_file()]


def _toml_str(value: str) -> str:
    """A TOML string written by hand: the source can be a local Windows folder,
    and there the backslash is an escape that does not read back."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _skill_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_NAME_RE.search(text)
    name = match.group(1) if match else skill_md.parent.name
    if not NAME_RE.fullmatch(name):
        raise ValueError(
            f"{skill_md}: name {name!r} is not installable (lowercase, digits and hyphens)"
        )
    return name


def _git(*args: str) -> str:
    """git with the real error in your face: a failed clone is not an empty package."""
    try:
        done = subprocess.run(
            ["git", *args], capture_output=True, text=True, encoding="utf-8", check=True
        )
    except FileNotFoundError as err:
        raise RuntimeError("git is not available: it is needed to connect a package") from err
    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"git {' '.join(args)} failed: {err.stderr.strip()}") from err
    return done.stdout
