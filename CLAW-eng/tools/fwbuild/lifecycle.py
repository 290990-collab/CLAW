"""The lifecycle of an installation: what gets written, what gets removed, what gets repaired.

Every mode that writes goes through a plan: one operation per file, computed
without touching anything, which the user reads before saying yes. Execution
receives the approved plan and does not compute another: it re-checks that the
tree is still the one the plan was made on, and if it is not it refuses before
writing the first byte. A plan approved on a tree that has changed in the
meantime is an approval given to something else.

The ownership rules are three. A file is deleted only if it is byte-for-byte
identical to the source, that is if it holds nobody's work. What the project
adapted — cards, guides, styles — is archived whole, never deleted. From
`settings.json` only what `settings_added` says the framework added is removed,
plus the hook entries that would point to a script that is gone.
"""

import copy
import hashlib
import json
import re
import shutil
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import assemble, doctor, kernel, profile, settings, source

CREATE = "create"
OVERWRITE = "overwrite"
MERGE = "merge"
KEEP = "keep"
REMOVE = "remove"
ARCHIVE = "archive"

# The order in which `render` counts. The first four change or remove content
# that was there: they are read by name, file by file.
ACTIONS = (OVERWRITE, MERGE, ARCHIVE, REMOVE, CREATE, KEEP)
DESTRUCTIVE = (OVERWRITE, MERGE, ARCHIVE, REMOVE)

CLAUDE_MD = "CLAUDE.md"
SETTINGS = ".claude/settings.json"
MANIFEST = source.MANIFEST.as_posix()
ORCHESTRATION = f".claude/{doctor.ORCHESTRATION}"

# Instructions of other tools: the installation does not touch them, but
# whoever approves the plan must know they are there and can contradict
# CLAUDE.md.
FOREIGN_INSTRUCTIONS = ("AGENTS.md", ".cursorrules", ".github/copilot-instructions.md")
# The `.claude/` folders where framework and project files live side by side.
SHARED_DIRS = ("agents", "skills", "output-styles", "hooks", "shared")

# A framework hook entry is recognised by the script it launches, not by the
# whole command text: that changes between releases, and the user touches it up.
HOOK_PATH_RE = re.compile(r"\.claude[\\/]+hooks[\\/]+([A-Za-z0-9_-]+)\.py")


@dataclass(frozen=True)
class Operation:
    """A project file and what happens to it.

    `digest` is the file's fingerprint when the plan was computed, empty if the
    file was not there: it is what execution re-checks before writing.
    """

    path: str
    action: str
    reason: str = ""
    digest: str = ""


def targets(
    framework_root: Path,
    roster: Sequence[str],
    guides: Sequence[str],
    hooks: Sequence[str],
) -> list[str]:
    """Every file the installation writes, relative to the project root."""
    fw = Path(framework_root)
    out = {CLAUDE_MD, ORCHESTRATION, SETTINGS, MANIFEST}
    out |= {f".claude/agents/{name}.md" for name in roster}
    out |= {f".claude/shared/{rel}" for rel in guides}
    out |= {f".claude/hooks/{name}.py" for name in hooks}
    out |= {f"docs/{name}" for name in doctor.STATE_FILES}
    out |= {rel for rel, _ in _skill_files(fw)}
    out |= {f".claude/output-styles/{p.name}" for p in _files(fw / "output-styles")}
    return sorted(out)


def plan_install(project_root: Path, targets: Sequence[str]) -> list[Operation]:
    """What the installation would do to this project, file by file.

    `CLAUDE.md`, `settings.json` and the state files already there are merged:
    they are the project's before they are the framework's. Every other target
    already present is overwritten, and the plan says so by name. The
    project's files that sit in the framework's folders stay, and are listed:
    whoever approves must know they will live side by side.
    """
    prj = Path(project_root)
    if (prj / MANIFEST).exists():
        raise ValueError(
            f"{MANIFEST} already exists: the project is installed — "
            "framework-sync --down or --repair, not a second installation"
        )
    mergeable = {CLAUDE_MD, SETTINGS} | {f"docs/{n}" for n in doctor.STATE_FILES}
    ops = []
    for rel in targets:
        if not (prj / rel).exists():
            ops.append(_op(prj, rel, CREATE))
        elif rel in mergeable:
            ops.append(_op(prj, rel, MERGE, "already there: merged, the content stays"))
        else:
            ops.append(_op(prj, rel, OVERWRITE, "already there: replaced"))
    wanted = set(targets)
    for area in SHARED_DIRS:
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            if rel not in wanted:
                ops.append(_op(prj, rel, KEEP, "not the framework's: stays as it is"))
    for rel in FOREIGN_INSTRUCTIONS:
        if (prj / rel).is_file():
            ops.append(
                _op(prj, rel, KEEP, "instructions of another tool: they stay, "
                    "and they can contradict CLAUDE.md")
            )
    return ops


def render(ops: Sequence[Operation]) -> str:
    """The plan to show: first what changes or removes something, by name, then
    the counts. A hundred "create" lines above one "overwrite" hide it."""
    lines = [
        f"{op.action:<11} {op.path}" + (f" — {op.reason}" if op.reason else "")
        for op in ops
        if op.action in DESTRUCTIVE
    ]
    counts = Counter(op.action for op in ops)
    lines.append(
        " · ".join(f"{a}: {counts[a]}" for a in ACTIONS if counts[a]) or "no operations"
    )
    return "\n".join(lines)


def plan_uninstall(project_root: Path, framework_root: Path) -> list[Operation]:
    """What the uninstall would do, file by file, without touching anything.

    The source is needed to know what is identical to the original: without it
    nothing could be deleted with certainty, and a plan that archives
    everything is not the one the user believes they are approving. An archive
    already there is a previous uninstall: writing over it would mix it with
    this one.
    """
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    gaps = source.missing(fw)
    if gaps:
        raise ValueError(
            f"source unreachable in {fw} (missing {', '.join(gaps)}): without it, "
            "nobody knows which files are identical to the original"
        )
    if (prj / doctor.ARCHIVE_DIR).exists():
        raise ValueError(
            f"{doctor.ARCHIVE_DIR.as_posix()} already exists: it is another uninstall, "
            "move it first"
        )

    ops = _settings_uninstall_ops(prj, manifest)
    claude = prj / CLAUDE_MD
    if claude.is_file():
        if kernel.parse(claude.read_text(encoding="utf-8")) is None:
            ops.append(_op(prj, CLAUDE_MD, KEEP, "no markers: no framework region"))
        else:
            ops.append(_op(prj, CLAUDE_MD, MERGE, "the kernel region goes, the rest stays"))

    for area in ("skills", "hooks"):
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            original = fw / area / p.relative_to(prj / ".claude" / area)
            if not original.is_file():
                ops.append(_op(prj, rel, KEEP, "not from the source: stays"))
            elif original.read_bytes() == p.read_bytes():
                ops.append(_op(prj, rel, REMOVE, "identical to the source"))
            else:
                ops.append(_op(prj, rel, ARCHIVE, "differs from the source: kept"))

    for area in ("agents", "shared", "output-styles"):
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            original = fw / area / p.relative_to(prj / ".claude" / area)
            if rel == ORCHESTRATION or original.is_file():
                ops.append(_op(prj, rel, ARCHIVE, "adapted to the project: kept"))
            else:
                ops.append(_op(prj, rel, KEEP, "not from the source: stays"))

    for name in doctor.STATE_FILES:
        if (prj / "docs" / name).is_file():
            ops.append(_op(prj, f"docs/{name}", KEEP, "project state"))
    ops.append(
        _op(prj, MANIFEST, ARCHIVE, "last: while it is there, framework-sync finds the source")
    )
    return ops


def apply_uninstall(
    project_root: Path, framework_root: Path, ops: Sequence[Operation]
) -> None:
    """Runs a `plan_uninstall` plan.

    All digests are re-checked **before** writing: a file changed after the
    plan stops everything, not only itself. Every removal is also re-checked
    against the source: the plan is a saved file, and a "remove" written by hand
    with the right digest would delete the project's work. Then, in this order:
    settings, `CLAUDE.md`, moves into the archive with the manifest last,
    removals, folders left empty.
    """
    prj, fw = Path(project_root), Path(framework_root)
    active = [op for op in ops if op.action != KEEP]
    _verify(prj, active)
    unjustified = sorted(
        op.path for op in active if op.action == REMOVE and not _removable(prj, fw, op.path)
    )
    if unjustified:
        raise ValueError(
            "removals of files not identical to the source, nothing was written: "
            + ", ".join(unjustified)
        )
    stray = sorted(
        f"{op.action} {op.path}"
        for op in active
        if (op.action == ARCHIVE and not _archivable(op.path))
        or (op.action == MERGE and op.path not in (CLAUDE_MD, SETTINGS))
    )
    if stray:
        raise ValueError(
            "operations the uninstall never plans, nothing was written: "
            + ", ".join(stray)
        )
    archive = prj / doctor.ARCHIVE_DIR
    if archive.exists():
        raise ValueError(f"{doctor.ARCHIVE_DIR.as_posix()} appeared after the plan: plan again")
    paths = {op.path for op in active}

    if SETTINGS in paths:
        record = (source.read_manifest(prj) or {}).get("settings_added")
        rest, _, _ = _uninstalled_settings(_read_json(prj / SETTINGS), record)
        _write_json(prj / SETTINGS, rest)

    if CLAUDE_MD in paths:
        claude = prj / CLAUDE_MD
        text = claude.read_text(encoding="utf-8")
        region = kernel.parse(text)
        claude.write_text(text[: region.start] + text[region.end :].lstrip("\n"), encoding="utf-8")

    moved = sorted(
        (op.path for op in active if op.action == ARCHIVE), key=lambda rel: rel == MANIFEST
    )
    for rel in moved:
        dest = archive / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        (prj / rel).rename(dest)
    removed = [op.path for op in active if op.action == REMOVE]
    for rel in removed:
        (prj / rel).unlink()
    _prune(prj, moved + removed)


def plan_repair(project_root: Path, framework_root: Path) -> list[Operation]:
    """Puts back what is missing, at the installed version. Nothing is overwritten.

    A skill or a hook that differs from the source is a local change and
    stays. At a different version "what is missing" would be measured against
    the wrong source: `--down` first.
    """
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    version = _version(fw)
    if manifest.get("version") != version:
        raise ValueError(
            f"installation at v{manifest.get('version')}, source at v{version}: "
            "framework-sync --down first, then --repair"
        )
    keep = (KEEP, "differs from the source: local change, not overwritten")
    ops = []
    for rel, original in _skill_files(fw):
        ops += _against_source(prj, rel, original, *keep)
    current = _current_settings(prj)
    in_use = _referenced_hooks(current) | _referenced_hooks(manifest.get("settings_added"))
    for name in settings.HOOKS:
        if name in in_use:
            ops += _against_source(prj, f".claude/hooks/{name}.py", _hook_source(fw, name), *keep)
    for name in doctor.STATE_FILES:
        if not (prj / "docs" / name).exists():
            ops.append(_op(prj, f"docs/{name}", CREATE, "missing: from the template, to fill in"))
    for ref in _cited_guides(prj):
        rel = f".claude/shared/{ref}"
        if (prj / rel).exists():
            continue
        if (fw / "shared" / ref).is_file():
            ops.append(_op(prj, rel, CREATE, "cited and missing: from the source, to fill in"))
        else:
            ops.append(_op(prj, rel, KEEP, "cited, missing from the source too: to be written"))
    settings_ops = _settings_update_ops(prj, fw, manifest, ops)
    if settings_ops:
        ops += settings_ops
        ops.append(_op(prj, MANIFEST, MERGE, "settings_added: what is added gets appended"))
    return ops


def plan_down(
    project_root: Path, framework_root: Path, hooks: Sequence[str] | None = None
) -> list[Operation]:
    """What a new version brings: kernel regions, skills, hooks, settings.

    The kernel regions are reassembled by the skill's steps, not by
    `apply_update`: here they are listed, and a touched-up region says the
    change will be lost. `hooks` are the hooks to have afterwards; `None` means
    those the project already uses — a project born without hooks does not get
    any in silence.
    """
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    version = _version(fw)
    ops = []
    for rel in _kernel_files(prj):
        text = (prj / rel).read_text(encoding="utf-8")
        region = kernel.parse(text)
        original = fw / "agents" / Path(rel).name
        is_agent = rel.startswith(".claude/agents/")
        if is_agent and not original.is_file():
            ops.append(_op(prj, rel, KEEP, "card no longer in the source: stays as it is"))
            continue
        note = _model_note(text, original.read_text(encoding="utf-8")) if is_agent else ""
        if region is None:
            ops.append(_op(prj, rel, KEEP, "no markers: no region to reassemble"))
        elif kernel.verify(text) == "DRIFT":
            ops.append(_op(prj, rel, MERGE, f"v{region.version} → v{version}, region "
                           f"edited by hand: the local change is lost{note}"))
        else:
            ops.append(_op(prj, rel, MERGE, f"v{region.version} → v{version}, rest unchanged{note}"))

    overwrite = (OVERWRITE, "differs from the source: updated")
    for rel, original in _skill_files(fw):
        ops += _against_source(prj, rel, original, *overwrite)
    if hooks is None:
        current = _current_settings(prj)
        in_use = _referenced_hooks(current) | _referenced_hooks(manifest.get("settings_added"))
        in_use |= {n for n in settings.HOOKS if _hook_after(prj, n, ())}
        hooks = [n for n in settings.HOOKS if n in in_use]
    unknown = [n for n in hooks if n not in settings.HOOKS]
    if unknown:
        raise ValueError(f"unknown hooks: {', '.join(unknown)}")
    for name in hooks:
        ops += _against_source(prj, f".claude/hooks/{name}.py", _hook_source(fw, name), *overwrite)
    ops += _settings_update_ops(prj, fw, manifest, ops)
    ops.append(_op(prj, MANIFEST, MERGE, f"version {manifest.get('version')} → {version}"))
    return ops


def apply_update(project_root: Path, framework_root: Path, ops: Sequence[Operation]) -> None:
    """Runs a `plan_repair` or `plan_down` plan.

    Files with a kernel region are skipped: the skill's steps rewrite them,
    keeping the project sections, and by the time this function runs they have
    already changed. For everything else the digests are re-checked before
    writing. Then: copies from the source, missing entries in `settings.json`,
    manifest — the source's version and the new delta appended to the record.
    """
    prj, fw = Path(project_root), Path(framework_root)
    active = [op for op in ops if op.action != KEEP and not _is_kernel_file(op.path)]
    _verify(prj, active)
    manifest = _manifest(prj)
    copies = [
        (op.path, _source_of(fw, op.path))
        for op in active
        if op.action in (CREATE, OVERWRITE) and op.path not in (SETTINGS, MANIFEST)
    ]
    paths = {op.path for op in active}

    for rel, original in copies:
        dest = prj / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, dest)

    added: dict = {}
    if SETTINGS in paths:
        current = _current_settings(prj)
        merged, added, _ = settings.merge(
            current, _framework_settings(prj, fw, manifest, (), current)
        )
        _write_json(prj / SETTINGS, merged)

    if MANIFEST in paths:
        data = dict(manifest)
        data["version"] = _version(fw)
        if added:
            record = data.get("settings_added")
            data["settings_added"] = settings.merge(
                record if isinstance(record, dict) else {}, added
            )[0]
        _write_json(prj / MANIFEST, data)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _op(prj: Path, rel: str, action: str, reason: str = "") -> Operation:
    return Operation(rel, action, reason, _digest(prj / rel))


def _files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file()) if directory.is_dir() else []


def _skill_files(fw: Path) -> list[tuple[str, Path]]:
    """The files of the lifecycle skills: path in the project, original."""
    base = fw / "skills"
    return [
        (f".claude/skills/{p.relative_to(base).as_posix()}", p)
        for skill in doctor.LIFECYCLE_SKILLS
        for p in _files(base / skill)
    ]


def _hook_source(fw: Path, name: str) -> Path:
    return fw / "hooks" / f"{name}.py"


def _kernel_files(prj: Path) -> list[str]:
    out = [rel for rel in (CLAUDE_MD, ORCHESTRATION) if (prj / rel).is_file()]
    agents = _files(prj / ".claude" / "agents")
    return out + [p.relative_to(prj).as_posix() for p in agents if p.suffix == ".md"]


MODEL_LINE_RE = re.compile(r"^(model|effort):[ \t]*(\S+)[ \t]*$", re.MULTILINE)


def _model_note(installed: str, original: str) -> str:
    """Model and effort live in the front matter, which stays the project's: a
    change in the source does not arrive on its own, and the plan names it."""
    def lines(text: str) -> dict[str, str]:
        head = re.match(r"---\n(.*?)\n---", text.replace("\r\n", "\n"), re.DOTALL)
        return dict(MODEL_LINE_RE.findall(head.group(1))) if head else {}
    here, there = lines(installed), lines(original)
    diff = [f"{k}: {here.get(k, '-')} here, {v} in the source"
            for k, v in there.items() if here.get(k) != v]
    return f"; {', '.join(diff)} — ask" if diff else ""


def _is_kernel_file(rel: str) -> bool:
    return rel in (CLAUDE_MD, ORCHESTRATION) or rel.startswith(".claude/agents/")


def _against_source(
    prj: Path, rel: str, original: Path, action: str, reason: str
) -> list[Operation]:
    """A file that must come from the source: missing → create, different → `action`."""
    p = prj / rel
    if not p.exists():
        return [_op(prj, rel, CREATE, "missing: from the source")]
    if p.read_bytes() != original.read_bytes():
        return [_op(prj, rel, action, reason)]
    return []


def _source_of(fw: Path, rel: str) -> Path:
    for prefix, area in (
        (".claude/skills/", "skills"),
        (".claude/hooks/", "hooks"),
        (".claude/shared/", "shared"),
        (".claude/output-styles/", "output-styles"),
    ):
        if rel.startswith(prefix):
            return fw / area / rel[len(prefix) :]
    name = rel.removeprefix("docs/")
    if rel.startswith("docs/") and name in doctor.STATE_FILES:
        return fw / "templates" / name
    raise ValueError(f"{rel}: no source file to copy it from")


def _verify(prj: Path, ops: Sequence[Operation]) -> None:
    changed = sorted({op.path for op in ops if _digest(prj / op.path) != op.digest})
    if changed:
        raise ValueError(
            "changed after the plan, nothing was written — plan again: "
            + ", ".join(changed)
        )


def _removable(prj: Path, fw: Path, rel: str) -> bool:
    """The rule of `plan_uninstall`: only a skill or a hook byte-for-byte
    identical to the source file at the same path is deleted."""
    if ".." in Path(rel).parts:
        return False
    for area in ("skills", "hooks"):
        prefix = f".claude/{area}/"
        if rel.startswith(prefix):
            original = fw / area / rel[len(prefix) :]
            p = prj / rel
            return original.is_file() and p.is_file() and original.read_bytes() == p.read_bytes()
    return False


def _archivable(rel: str) -> bool:
    """The only files `plan_uninstall` archives: inside the framework's folders
    in `.claude/`, plus the manifest. An "archive" written by hand moves neither
    project code nor files outside the root."""
    if ".." in Path(rel).parts:
        return False
    return rel == MANIFEST or any(rel.startswith(f".claude/{area}/") for area in SHARED_DIRS)


def _prune(prj: Path, rels: Sequence[str]) -> None:
    """Removes the folders the move left empty, from the bottom."""
    dirs = {d for rel in rels for d in (prj / rel).parents if prj in d.parents}
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def _manifest(prj: Path) -> dict:
    data = source.read_manifest(prj)
    if data is None:
        raise ValueError(
            f"{MANIFEST} absent or unreadable: without it, nobody knows what the "
            "installation wrote or from which source"
        )
    return data


def _version(fw: Path) -> str:
    return (fw / "VERSION").read_text(encoding="utf-8").strip()


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"{path}: invalid JSON ({e})") from e
    if not isinstance(data, dict):
        raise ValueError(f"{path}: not a JSON object")
    return data


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _current_settings(prj: Path) -> dict:
    path = prj / SETTINGS
    return _read_json(path) if path.is_file() else {}


def _cited_guides(prj: Path) -> list[str]:
    refs: set[str] = set()
    for f in doctor._markdown_files(prj):
        refs |= set(doctor.SHARED_REF_RE.findall(f.read_text(encoding="utf-8")))
    return sorted(refs)


def _hook_name(entry: object) -> str | None:
    command = entry.get("command") if isinstance(entry, dict) else None
    if not isinstance(command, str):
        return None
    return next((n for n in HOOK_PATH_RE.findall(command) if n in settings.HOOKS), None)


def _referenced_hooks(data: object) -> set[str]:
    """The framework hooks a slice of settings names."""
    if not isinstance(data, dict):
        return set()
    text = json.dumps(data.get("hooks", {}))
    return {n for n in HOOK_PATH_RE.findall(text) if n in settings.HOOKS}


def _drop_framework_hooks(data: dict) -> tuple[dict, list[str]]:
    """`(rest, dropped)`: every hook entry that launches a framework script goes.

    Single entries are removed, not the group: a user hook placed under the
    same `matcher` stays. Only the containers emptied here are pruned.
    """
    rest = copy.deepcopy(data)
    events = rest.get("hooks")
    if not isinstance(events, dict):
        return rest, []
    dropped: list[str] = []
    for event in list(events):
        groups = events[event]
        if not isinstance(groups, list):
            continue
        survivors = []
        for group in groups:
            inner = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(inner, list) or not inner:
                survivors.append(group)
                continue
            keep = [h for h in inner if _hook_name(h) is None]
            dropped += [
                f"{event} «{group.get('matcher', '')}» → .claude/hooks/{_hook_name(h)}.py"
                for h in inner
                if _hook_name(h) is not None
            ]
            if keep:
                survivors.append({**group, "hooks": keep})
        if survivors:
            events[event] = survivors
        elif groups:
            del events[event]
    if not events and data.get("hooks"):
        del rest["hooks"]
    return rest, dropped


def _uninstalled_settings(current: dict, record: object) -> tuple[dict, list[str], list[str]]:
    """`(rest, kept, dropped)`: the record removed, then every hook entry left.

    A hook entry the user touched up is no longer equal to the record, and
    without a record none is removed: but the script it points to goes away,
    and a closed hook without its script blocks every Edit and every Bash.
    """
    if isinstance(record, dict):
        rest, kept = settings.unmerge(current, record)
    else:
        rest, kept = copy.deepcopy(current), []
    rest, dropped = _drop_framework_hooks(rest)
    return rest, kept, dropped


def _settings_uninstall_ops(prj: Path, manifest: dict) -> list[Operation]:
    if not (prj / SETTINGS).is_file():
        return []
    record = manifest.get("settings_added")
    _, kept, dropped = _uninstalled_settings(_read_json(prj / SETTINGS), record)
    ops = []
    if isinstance(record, dict):
        reason = "the entries recorded in settings_added go"
        if kept:
            reason += f"; changed by you, they stay: {', '.join(kept)}"
        ops.append(_op(prj, SETTINGS, MERGE, reason))
    elif not dropped:
        return [_op(prj, SETTINGS, KEEP, "no settings_added: nobody knows what is the framework's")]
    for entry in dropped:
        ops.append(
            _op(prj, SETTINGS, MERGE, f"the hook entry {entry} goes too: it is not the "
                "recorded one, but the script goes away and a closed hook without its "
                "script blocks every Edit and Bash")
        )
    return ops


def _hook_after(prj: Path, name: str, ops: Sequence[Operation]) -> bool:
    """Whether the hook's script will be there after the plan."""
    rel = f".claude/hooks/{name}.py"
    return (prj / rel).is_file() or any(
        op.path == rel and op.action in (CREATE, OVERWRITE) for op in ops
    )


def _framework_settings(
    prj: Path, fw: Path, manifest: dict, ops: Sequence[Operation], current: dict
) -> dict:
    """The entries the framework wants in `settings.json`: the profile, those of
    the installed orchestration, plus one entry for every hook whose script will
    be there and that no entry launches yet.

    The orchestration is not in the manifest: it is derived from the kernel
    region of the coordinator's guide. Without the guide nobody knows which one
    it is, and recomputing without its variables would leave switched off a
    model the project uses.

    A hook already named is not added again: if the command changed between one
    release and the next, the new entry would be appended to the old one and
    the hook would run twice.
    """
    name = manifest.get("profile")
    path = fw / "profiles" / f"{name}.toml"
    if not isinstance(name, str) or not path.is_file():
        raise ValueError(
            f"profile {name!r} missing from the source: the settings.json entries "
            "cannot be recomputed"
        )
    guide = prj / ORCHESTRATION
    region = kernel.parse(guide.read_text(encoding="utf-8")) if guide.is_file() else None
    if region is None:
        raise ValueError(
            f"{ORCHESTRATION} missing or without a kernel region: the installed "
            "orchestration cannot be derived and the settings.json entries cannot "
            "be recomputed — reassemble the guide with assemble.orchestration_file, then retry"
        )
    orchestration = assemble.installed_orchestration(region.body, fw).stem
    referenced = _referenced_hooks(current)
    names = [n for n in settings.HOOKS if n not in referenced and _hook_after(prj, n, ops)]
    merged, _, conflicts = settings.merge(profile.load(path).settings, settings.hooks(names))
    if conflicts:
        raise ValueError(f"profile and hooks conflict on: {', '.join(conflicts)}")
    merged, _, conflicts = settings.merge(
        merged, settings.ORCHESTRATION_SETTINGS.get(orchestration, {})
    )
    if conflicts:
        raise ValueError(f"orchestration conflicts on: {', '.join(conflicts)}")
    return merged


def _settings_update_ops(
    prj: Path, fw: Path, manifest: dict, ops: Sequence[Operation]
) -> list[Operation]:
    current = _current_settings(prj)
    _, added, conflicts = settings.merge(
        current, _framework_settings(prj, fw, manifest, ops, current)
    )
    if not added:
        return []
    reason = "missing: " + ", ".join(sorted(added))
    if conflicts:
        reason += f"; your value stays on: {', '.join(conflicts)}"
    action = MERGE if (prj / SETTINGS).is_file() else CREATE
    return [_op(prj, SETTINGS, action, reason)]
