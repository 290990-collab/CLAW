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

from . import assemble, doctor, kernel, profile, settings, skills, source

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

# Guides and styles have no kernel region: the text belongs to the framework,
# the last section to the project. The source marks it with the placeholder,
# which sits there and only there, and the heading is read from the file: no
# per-language constant.
SECTION_RE = re.compile(r"^## .*$", re.MULTILINE)


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
            "claw-sync --down or --repair, not a second installation"
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


PROJECT_SKELETON = """## The project

[TO FILL IN — one line on what it is · "path → role" map · HARD constraints (breaking them invalidates the work, not just the code) · contracts, with who consumes them]

## Commands

[TO FILL IN — build, test, start · the agent's quick check · heavy operations the user launches, with what they must report]

## Critical surface

[TO FILL IN — what makes the work wrong even with perfect code, and who reviews it. The field's: {surface}]

## Current state

## Shared guides

- `.claude/shared/orchestration.md` — coordinator only, first if the session delegates: when to delegate and to whom, the work cycle, delegation prompts, state.
{guides}
"""

PREEXISTING = """
## Pre-existing instructions

[TO FILL IN — move what follows into the sections above, in the most compressed form that keeps its meaning, then delete this section]

"""

ROSTER_SKELETON = """## This project's roster

| Situation | Agent | Model |
|---|---|---|
{rows}

## Delegation notes for this project

[TO FILL IN — operations the user launches, not the agent · project-specific parallelism limits · when to skip a cycle step]
"""


def apply_install(
    project_root: Path,
    framework_root: Path,
    ops: Sequence[Operation],
    profile_name: str,
    roster: Sequence[str],
    guides: Sequence[str],
    hooks: Sequence[str],
    orchestration: str,
) -> tuple[list[str], list[str]]:
    """Runs a `plan_install` plan: `(settings conflicts, files to fill in)`.

    Everything is computed and every digest re-checked before the first byte.
    Cards, guides and styles arrive with their placeholders; `CLAUDE.md` and the
    coordinator's guide with the project skeleton, a pre-existing `CLAUDE.md`
    appended to be redistributed. State files already there are left for the
    model to fold into the template. The placeholders are filled next, then
    `doctor --strict`.
    """
    prj, fw = Path(project_root), Path(framework_root)
    prof = profile.load(fw / "profiles" / f"{profile_name}.toml")
    clash = profile.check_exclusive(list(roster))
    if clash:
        raise ValueError(f"agents that do not coexist: {', '.join(clash)}")
    if {op.path for op in ops if op.action != KEEP} != set(targets(fw, roster, guides, hooks)):
        raise ValueError("the plan was made for other choices, nothing was written: plan again")
    _verify(prj, [op for op in ops if op.action != KEEP])
    version = _version(fw)

    cards = {n: (fw / "agents" / f"{n}.md").read_text(encoding="utf-8") for n in roster}
    listed = "\n".join(
        f"- `.claude/shared/{rel}` — {_guide_line((fw / 'shared' / rel).read_text(encoding='utf-8'))}"
        for rel in guides
    )
    sections = PROJECT_SKELETON.format(surface=prof.critical_surface or "-", guides=listed)
    if (prj / CLAUDE_MD).is_file():
        sections += PREEXISTING + (prj / CLAUDE_MD).read_text(encoding="utf-8")
    rows = "\n".join(f"| {_situation(c)} | `{n}` | {_model_cell(c)} |" for n, c in cards.items())
    texts = {
        CLAUDE_MD: assemble.build_document(fw / "method", version, sections),
        ORCHESTRATION: assemble.build_document(
            fw / "coordinator",
            version,
            ROSTER_SKELETON.format(rows=rows),
            extra=[
                assemble.orchestration_file(fw, orchestration),
                *assemble.cycle_files(fw, prof.cycles),
            ],
        ),
    }
    for name, card in cards.items():
        texts[f".claude/agents/{name}.md"] = assemble.build_agent(
            *assemble.split_source(card), version
        )
    copies = {f".claude/shared/{rel}": fw / "shared" / rel for rel in guides}
    copies |= {f".claude/output-styles/{p.name}": p for p in _files(fw / "output-styles")}
    copies |= {f".claude/hooks/{n}.py": _hook_source(fw, n) for n in hooks}
    copies |= dict(_skill_files(fw))
    copies |= {
        f"docs/{n}": fw / "templates" / n
        for n in doctor.STATE_FILES
        if not (prj / "docs" / n).exists()
    }
    merged, added, conflicts = settings.merge(
        _current_settings(prj),
        settings.framework(prof.settings, hooks, orchestration, skills.overrides(fw)),
    )
    data = source.manifest(
        prj, fw, version, prof.name, settings_added=added, skills=skills.installed(fw)
    )
    data["frontmatter"] = {n: field_record(c) for n, c in cards.items()}

    for rel, original in copies.items():
        (prj / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, prj / rel)
    for rel, text in texts.items():
        (prj / rel).parent.mkdir(parents=True, exist_ok=True)
        (prj / rel).write_text(text, encoding="utf-8")
    _write_json(prj / SETTINGS, merged)
    _write_json(prj / MANIFEST, data)
    to_fill = sorted(
        rel
        for rel in [*texts, *copies]
        if not rel.startswith(".claude/skills/")
        and rel.endswith(".md")
        and doctor.PLACEHOLDER_RE.search((prj / rel).read_text(encoding="utf-8"))
    )
    return conflicts, to_fill


def _situation(card: str) -> str:
    """The roster's Situation for a card: its description up to the first colon or full stop."""
    block = _fields(card).get("description", "description:")
    text = " ".join(
        line.strip() for line in block.split(":", 1)[1].splitlines() if line.strip() not in ("", ">")
    )
    return re.split(r"(?<=[.:])\s", text)[0].rstrip(".:")


def _guide_line(text: str) -> str:
    """A guide's line in `CLAUDE.md § Shared guides`: the first sentence under its title."""
    line = next(
        (s.strip() for s in text.splitlines()[1:] if s.strip() and not s.startswith("#")), ""
    )
    return re.split(r"(?<=\.)\s", line)[0]


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
            inside = p.relative_to(prj / ".claude" / area)
            original = (
                _skill_source(fw, inside.as_posix()) if area == "skills" else fw / area / inside
            )
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
        _op(prj, MANIFEST, ARCHIVE, "last: while it is there, claw-sync finds the source")
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
            "claw-sync --down first, then --repair"
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
    project_root: Path,
    framework_root: Path,
    hooks: Sequence[str] | None = None,
    adopt: Sequence[str] = (),
) -> list[Operation]:
    """What a new version brings: kernel regions, guides and styles, skills,
    hooks, settings.

    The kernel regions are reassembled by `apply_down`: here they are listed,
    and a touched-up region says the change will be lost. A card's front
    matter follows `_frontmatter_merge`; `adopt` names the cards (or `all`)
    that take the source's values whatever the record says. Guides and styles
    take the source text and keep their project block; without a recognisable
    block they stay as they are, and the plan says so. `hooks` are the hooks to
    have afterwards; `None` means those the project already uses — a project
    born without hooks does not get any in silence.
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
        note = _card_note(manifest, rel, text, original, adopt) if is_agent else ""
        if region is None:
            ops.append(_op(prj, rel, KEEP, "no markers: no region to reassemble"))
        elif kernel.verify(text) == "DRIFT":
            ops.append(_op(prj, rel, MERGE, f"v{region.version} → v{version}, region "
                           f"edited by hand: the local change is lost{note}"))
        else:
            ops.append(_op(prj, rel, MERGE, f"v{region.version} → v{version}, rest unchanged{note}"))

    for rel, original in _adapted_files(prj, fw):
        installed = (prj / rel).read_text(encoding="utf-8")
        text = original.read_text(encoding="utf-8")
        merged = with_project_block(text, installed)
        if merged is None and installed != text:
            why = "project block not found" if project_heading(text) else "no project block"
            ops.append(_op(prj, rel, KEEP, f"{why}: differs from the source, update it by hand"))
        elif merged is not None and merged != installed:
            ops.append(_op(prj, rel, MERGE, "text from the source, project block unchanged"))

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
    moved = manifest.get("source") != source.reference(prj, fw)
    ops.append(_op(prj, MANIFEST, MERGE, f"version {manifest.get('version')} → {version}"
                   + (f"; source → {source.reference(prj, fw)}" if moved else "")))
    return ops


def _card_note(manifest: dict, rel: str, text: str, original: Path, adopt: Sequence[str]) -> str:
    name = Path(rel).stem
    record = _record(manifest, name)
    _, taken, kept = _frontmatter_merge(
        text, original.read_text(encoding="utf-8"), record, "all" in adopt or name in adopt
    )
    note = f"; from the source: {', '.join(taken)}" if taken else ""
    if kept:
        note += f"; kept (local): {', '.join(kept)}" if record is not None else (
            f"; kept (no record): {', '.join(kept)} — --adopt {name} takes the source"
        )
    return note


def apply_down(
    project_root: Path, framework_root: Path, ops: Sequence[Operation], adopt: Sequence[str] = ()
) -> None:
    """Runs a `plan_down` plan, kernel regions included.

    Every new text is computed and every digest re-checked before the first
    byte is written: a failure leaves the project as it was. The regions take
    the source's method and keep what surrounds them; cards take their front
    matter from `_frontmatter_merge`, and a roster row whose Model cell still
    says the old value is rewritten. The manifest records the source cards'
    front matter — the reference of the next `--down` — and the source.
    """
    prj, fw = Path(project_root), Path(framework_root)
    _verify(prj, [op for op in ops if op.action != KEEP])
    manifest = _manifest(prj)
    version = _version(fw)
    table = manifest.get("frontmatter")
    record = dict(table) if isinstance(table, dict) else {}
    regions = [op.path for op in ops if op.action == MERGE and _is_kernel_file(op.path)]
    writes: dict[Path, str] = {}
    cells: dict[str, tuple[str, str]] = {}
    for rel in regions:
        if not rel.startswith(".claude/agents/"):
            continue
        name = Path(rel).stem
        text = (prj / rel).read_text(encoding="utf-8")
        original = (fw / "agents" / f"{name}.md").read_text(encoding="utf-8")
        fm, _, _ = _frontmatter_merge(
            text, original, _record(manifest, name), "all" in adopt or name in adopt
        )
        _, method, _ = assemble.split_source(original)
        domain = text[kernel.parse(text).end :].lstrip("\n")
        writes[prj / rel] = assemble.build_agent(fm, method, domain, version)
        record[name] = field_record(original)
        if _model_cell(text) != _model_cell(fm):
            cells[name] = (_model_cell(text), _model_cell(fm))
    for rel, method_dir in ((CLAUDE_MD, "method"), (ORCHESTRATION, "coordinator")):
        if rel not in regions:
            continue
        text = (prj / rel).read_text(encoding="utf-8")
        region = kernel.parse(text)
        sections = text[region.end :].lstrip("\n")
        extra: list[Path] = []
        if rel == ORCHESTRATION:
            sections = _roster_cells(sections, cells)
            extra = [
                assemble.installed_orchestration(region.body, fw),
                *assemble.installed_cycles(region.body, fw),
            ]
        writes[prj / rel] = text[: region.start] + assemble.build_document(
            fw / method_dir, version, sections, extra=extra
        )

    apply_update(prj, fw, ops)
    for path, text in writes.items():
        path.write_text(text, encoding="utf-8")
    data = _manifest(prj)
    data["frontmatter"] = {
        n: r for n, r in record.items() if (prj / ".claude" / "agents" / f"{n}.md").is_file()
    }
    data["source"] = source.reference(prj, fw)
    _write_json(prj / MANIFEST, data)


def apply_update(project_root: Path, framework_root: Path, ops: Sequence[Operation]) -> None:
    """Runs a `plan_repair` or `plan_down` plan.

    Files with a kernel region are skipped: the skill's steps rewrite them,
    keeping the project sections, and by the time this function runs they have
    already changed. For everything else the digests are re-checked before
    writing. Then: copies from the source, guides and styles re-merged with
    their project block, missing entries in `settings.json`, manifest — the
    source's version and the new delta appended to the record.
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
    rewrites = []
    for op in active:
        if op.action != MERGE or op.path in (SETTINGS, MANIFEST):
            continue
        merged = with_project_block(
            _source_of(fw, op.path).read_text(encoding="utf-8"),
            (prj / op.path).read_text(encoding="utf-8"),
        )
        if merged is None:
            raise ValueError(
                f"{op.path}: the project block is no longer recognisable, "
                "nothing was written — redo the plan"
            )
        rewrites.append((prj / op.path, merged))

    for rel, original in copies:
        dest = prj / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, dest)
    for dest, merged in rewrites:
        dest.write_text(merged, encoding="utf-8")

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
        # What the project received from the packages: the only place where the
        # doctor reads it without having to reach the source.
        connected = skills.installed(fw)
        if connected:
            data["skills"] = connected
        else:
            data.pop("skills", None)
        if added:
            record = data.get("settings_added")
            data["settings_added"] = settings.merge(
                record if isinstance(record, dict) else {}, added
            )[0]
        _write_json(prj / MANIFEST, data)


def project_heading(text: str) -> str | None:
    """The heading of the project block of a guide or style in the source: the
    last `## ` section, if it holds every placeholder of the file. `None`
    without placeholders, or with one outside the last section: there `--down`
    could not tell what belongs to the project."""
    heads = list(SECTION_RE.finditer(text))
    total = len(doctor.PLACEHOLDER_RE.findall(text))
    if not heads or not total:
        return None
    if len(doctor.PLACEHOLDER_RE.findall(text[heads[-1].start() :])) != total:
        return None
    return heads[-1].group(0).rstrip()


def with_project_block(original: str, installed: str) -> str | None:
    """The source text up to the project block, then the block as it is in the
    installation. `None` if the source has no block or the installation no
    longer has that heading."""
    heading = project_heading(original)
    if heading is None:
        return None

    def start(text: str) -> int | None:
        found = [m.start() for m in SECTION_RE.finditer(text) if m.group(0).rstrip() == heading]
        return found[-1] if found else None

    at = start(installed)
    return None if at is None else original[: start(original)] + installed[at:]


def _adapted_files(prj: Path, fw: Path) -> list[tuple[str, Path]]:
    """Installed guides and styles that come from the source. `orchestration.md`
    lives in `shared/` but has a kernel region: it belongs to the skill's steps."""
    out = []
    for area in ("shared", "output-styles"):
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            original = fw / area / p.relative_to(prj / ".claude" / area)
            if rel != ORCHESTRATION and p.suffix == ".md" and original.is_file():
                out.append((rel, original))
    return out


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _op(prj: Path, rel: str, action: str, reason: str = "") -> Operation:
    return Operation(rel, action, reason, _digest(prj / rel))


def _files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file()) if directory.is_dir() else []


def _skill_files(fw: Path) -> list[tuple[str, Path]]:
    """The skill files to install: path in the project, original.

    The lifecycle ones already sit at one level; those of the connected
    packages lose the package level, because Claude Code only discovers
    `.claude/skills/<skill>/`.
    """
    base = fw / "skills"
    out = [
        (f".claude/skills/{p.relative_to(base).as_posix()}", p)
        for skill in doctor.LIFECYCLE_SKILLS
        for p in _files(base / skill)
    ]
    for skill, package in skills.installed(fw).items():
        out += [
            (f".claude/skills/{p.relative_to(base / package).as_posix()}", p)
            for p in _files(base / package / skill)
        ]
    return out


def _skill_source(fw: Path, rest: str) -> Path:
    """The source file of an installed skill, given `<skill>/...`.

    It is the inverse of the flattening: without it the uninstall does not
    recognise a package skill as its own and leaves it in the project, and
    `--repair` does not know where to copy it back from.
    """
    base = fw / "skills"
    package = skills.installed(fw).get(rest.split("/", 1)[0])
    return base / package / rest if package else base / rest


def _hook_source(fw: Path, name: str) -> Path:
    return fw / "hooks" / f"{name}.py"


def _kernel_files(prj: Path) -> list[str]:
    out = [rel for rel in (CLAUDE_MD, ORCHESTRATION) if (prj / rel).is_file()]
    agents = _files(prj / ".claude" / "agents")
    return out + [p.relative_to(prj).as_posix() for p in agents if p.suffix == ".md"]


FIELD_RE = re.compile(r"[A-Za-z][\w-]*(?=:)")
ROSTER_ROW_RE = re.compile(r"^(\|[^|\n]*\|\s*)`([a-z-]+)`\s*\|([^|\n]*)\|", re.MULTILINE)


def _fields(text: str) -> dict[str, str]:
    """A card's front matter: top-level key → its normalised lines, continuation
    lines included."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("card without front matter")
    out: dict[str, str] = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            return {k: kernel.normalize(v) for k, v in out.items()}
        m = FIELD_RE.match(line)
        if m:
            key = m.group(0)
            out[key] = line + "\n"
        elif key is not None:
            out[key] += line + "\n"
        elif line.strip():
            raise ValueError(f"front matter line outside any key: {line!r}")
    raise ValueError("front matter not closed")


def field_record(card: str) -> dict[str, str]:
    """What `framework.json` records of a source card at every sync: key → digest."""
    return {k: kernel.digest(v) for k, v in _fields(card).items()}


def _record(manifest: dict, name: str) -> dict | None:
    table = manifest.get("frontmatter")
    entry = table.get(name) if isinstance(table, dict) else None
    return entry if isinstance(entry, dict) else None


def _frontmatter_merge(
    installed: str, original: str, record: dict | None, adopt: bool
) -> tuple[str, list[str], list[str]]:
    """`(front matter, taken, kept)` after `--down`.

    A key the project still has at the value recorded at the last sync is taken
    from the source: nobody chose it. A different value is a local choice and
    stays. Without a record the two cannot be told apart: every difference
    stays, unless `adopt`.
    """
    here, there = _fields(installed), _fields(original)
    blocks, taken, kept = [], [], []
    for key in [*there, *(k for k in here if k not in there)]:
        h, t = here.get(key), there.get(key)
        if h == t:
            chosen = h
        elif adopt or (
            record is not None and (kernel.digest(h) if h else "-") == record.get(key, "-")
        ):
            chosen = t
            taken.append(key)
        else:
            chosen = h
            kept.append(key)
        if chosen:
            blocks.append(chosen)
    return "---\n" + "".join(blocks) + "---\n", taken, kept


def _model_cell(card: str) -> str:
    """The roster's Model cell for a card: `model effort`."""
    f = _fields(card)
    return " ".join(
        f[k].split(":", 1)[1].strip() for k in ("model", "effort") if k in f
    )


def _roster_cells(sections: str, changes: dict[str, tuple[str, str]]) -> str:
    """Rewrites a roster row's Model cell only where it still says the old value."""

    def fix(m: re.Match) -> str:
        name, cell = m.group(2), m.group(3).strip()
        if name in changes and cell == changes[name][0]:
            return f"{m.group(1)}`{name}` | {changes[name][1]} |"
        return m.group(0)

    return ROSTER_ROW_RE.sub(fix, sections)


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
            if area == "skills":
                return _skill_source(fw, rel[len(prefix) :])
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
            original = (
                _skill_source(fw, rel[len(prefix) :])
                if area == "skills"
                else fw / area / rel[len(prefix) :]
            )
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
    # `skills.overrides`: the skills connected and outside the pool, invocable
    # by the user, invisible to the coordinator. Without it the pool does not
    # exist — the model sees them all.
    return settings.framework(
        profile.load(path).settings, names, orchestration, skills.overrides(fw)
    )


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
