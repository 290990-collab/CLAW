"""The lifecycle of an installation: install, update, uninstall.

Every file the framework writes comes from `assemble.generate`, which builds
all of them from the source, the choices in `claw.json` and the user's rules.
So each mode that writes is the same thing: take the choices, generate, compare
with the tree, show the plan, and on approval write what the plan names. There
is one write path, `_write`; modes differ only in how they compute the plan.

A plan is computed without touching anything, one operation per file, which the
user reads before saying yes. Execution receives the approved plan and does not
trust it: it recomputes the plan from the tree as it is now and refuses, before
the first byte, if the two differ. A plan approved on a tree that has changed in
the meantime is an approval given to something else.

What is never touched: `.claude/user-rules.md`, the parts of `CLAUDE.md` outside
the kernel and user-rules regions, the state files in `docs/`, cards and guides
that `claw.json` does not name, and any value of the user in `settings.json`.
Uninstall removes a file only if it equals what `generate` produces; any other
framework file is archived whole. From `settings.json` only what
`settings_added` says the framework added goes, plus the hook entries that
would point to a script that is gone.
"""

import copy
import hashlib
import json
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

from . import assemble, doctor, kernel, profile, settings, source
from .rules import OVERRIDE_KEYS, Rules, parse as parse_rules

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
USER_RULES = ".claude/user-rules.md"

# Instructions of other tools: the installation does not touch them, but
# whoever approves the plan must know they are there and can contradict
# CLAUDE.md.
FOREIGN_INSTRUCTIONS = ("AGENTS.md", ".cursorrules", ".github/copilot-instructions.md")
# The `.claude/` folders where framework and project files live side by side.
SHARED_DIRS = ("agents", "output-styles", "hooks", "shared")

# A framework hook entry is recognised by the script it launches, not by the
# whole command text: that changes between releases, and the user touches it up.
HOOK_PATH_RE = settings.HOOK_PATH_RE

HAND_EDIT = "modified by hand: the edit is lost — move it into .claude/user-rules.md"


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


@dataclass
class _Result:
    """A plan and everything needed to carry it out: nothing else is computed
    at write time."""

    ops: list[Operation] = field(default_factory=list)
    files: dict[str, str] = field(default_factory=dict)
    remove: list[str] = field(default_factory=list)
    settings: dict | None = None
    manifest: dict | None = None
    conflicts: list[str] = field(default_factory=list)


# --- Choices ----------------------------------------------------------------


def installed_choices(manifest: dict) -> dict:
    """The choices `claw.json` records, in the form `assemble.generate` takes."""
    gaps = [
        k
        for k in ("profile", "orchestration")
        if not isinstance(manifest.get(k), str) or not manifest[k].strip()
    ] + [
        k
        for k in source.MANIFEST_LISTS
        if not isinstance(manifest.get(k), list) or not all(isinstance(n, str) for n in manifest[k])
    ]
    if gaps:
        raise ValueError(
            f"{MANIFEST} without {', '.join(gaps)}: written by a release that did not "
            "record the choices, so nothing can be regenerated from it"
        )
    return {
        "profile": manifest["profile"],
        "orchestration": manifest["orchestration"],
        "agents": list(manifest["agents"]),
        "guides": list(manifest["guides"]),
        "hooks": list(manifest["hooks"]),
    }


def _checked(fw: Path, choices: dict) -> dict:
    """The choices if the source can honour them, with the guides the roster's
    cards cite added. Anything else is a configuration error, not a field to
    ignore: passed over in silence, the project would not receive what it asked
    for and no finding would say so."""
    if not (fw / "profiles" / f"{choices['profile']}.toml").is_file():
        names = sorted(p.stem for p in (fw / "profiles").glob("*.toml"))
        raise ValueError(f"no such profile: {choices['profile']} (one of: {', '.join(names)})")
    assemble.orchestration_file(fw, choices["orchestration"])
    gone = [n for n in choices["agents"] if not (fw / source.CARDS_DIR / f"{n}.md").is_file()]
    if gone:
        raise ValueError(
            f"no such agent in the source: {', '.join(gone)} — "
            f"/claw update --remove {','.join(gone)} if it is no longer wanted"
        )
    clash = profile.check_exclusive(choices["agents"])
    if clash:
        raise ValueError(f"agents that do not coexist: {', '.join(clash)}")
    gone = [g for g in choices["guides"] if not (fw / "shared" / g).is_file()]
    if gone:
        raise ValueError(
            f"no such guide in the source: {', '.join(gone)} — "
            f"/claw update --remove {','.join(gone)} if it is no longer wanted"
        )
    unknown = [h for h in choices["hooks"] if h not in settings.HOOKS]
    if unknown:
        raise ValueError(f"unknown hooks: {', '.join(unknown)}")
    guides = list(
        dict.fromkeys([*choices["guides"], *profile.required_guides(fw, choices["agents"])])
    )
    return {**choices, "guides": guides}


def _is_guide(name: str) -> bool:
    return "/" in name or name.endswith(".md")


def _after_profile(fw: Path, old: dict, profile_name: str | None) -> tuple[list[str], list[str]]:
    """The agents and guides once the field changes: the new profile's arrive,
    the old profile's (and what its roster cited) leave, and what the user added
    beyond the old profile stays. Without a change of profile, as recorded."""
    if not profile_name or profile_name == old["profile"]:
        return list(old["agents"]), list(old["guides"])
    path = fw / "profiles" / f"{profile_name}.toml"
    if not path.is_file():
        names = sorted(p.stem for p in (fw / "profiles").glob("*.toml"))
        raise ValueError(f"no such profile: {profile_name} (one of: {', '.join(names)})")
    before = profile.load(fw / "profiles" / f"{old['profile']}.toml")
    after = profile.load(path)
    old_roster = profile.roster(before, [], [])
    new_roster = profile.roster(after, [], [])
    agents = [n for n in old["agents"] if n not in old_roster or n in new_roster]
    agents += [n for n in new_roster if n not in agents]
    left = {*before.shared, *profile.required_guides(fw, old_roster)}
    guides = [g for g in old["guides"] if g not in left or g in after.shared]
    guides += [g for g in after.shared if g not in guides]
    return agents, guides


def _next_choices(
    fw: Path,
    manifest: dict,
    add: Sequence[str],
    remove: Sequence[str],
    profile_name: str | None,
    orchestration: str | None,
    gateguard: str | None,
) -> dict:
    """The choices after the requested changes, validated before any plan.

    A name with a `/` or a `.md` is a guide under `shared/`, any other an agent.
    """
    old = installed_choices(manifest)
    add_agents = [n for n in add if not _is_guide(n)]
    add_guides = [n for n in add if _is_guide(n)]
    drop_agents = [n for n in remove if not _is_guide(n)]
    drop_guides = [n for n in remove if _is_guide(n)]
    if gateguard not in (None, "on", "off"):
        raise ValueError("--gateguard is on or off")
    have_agents, have_guides = _after_profile(fw, old, profile_name)

    problems = []
    for n in add_agents:
        if n in have_agents:
            problems.append(f"{n} is already installed")
        elif not (fw / source.CARDS_DIR / f"{n}.md").is_file():
            problems.append(f"no such agent: {n}")
    for g in add_guides:
        if g in have_guides:
            problems.append(f"{g} is already installed")
        elif not (fw / "shared" / g).is_file():
            problems.append(f"no such guide: shared/{g}")
    for n in drop_agents:
        if n in profile.ALWAYS:
            problems.append(f"{n} is in every installation and cannot be removed")
        elif n not in have_agents:
            problems.append(f"{n} is not installed")
    for g in drop_guides:
        if g not in have_guides:
            problems.append(f"{g} is not installed")
    if problems:
        raise ValueError("; ".join(problems))

    agents = [n for n in have_agents if n not in drop_agents] + add_agents
    clash = profile.check_exclusive(agents)
    if clash:
        raise ValueError(f"agents that do not coexist: {', '.join(clash)}")
    cited = set(profile.required_guides(fw, agents))
    held = sorted(g for g in drop_guides if g in cited)
    if held:
        raise ValueError(
            f"{', '.join(held)}: cited by a card of the roster, it would come back at the "
            "next update — remove the agent that cites it first"
        )
    guides = [g for g in have_guides if g not in drop_guides] + add_guides

    def wanted(hook: str) -> bool:
        if hook not in settings.OPTIONAL_HOOKS:
            return True
        return hook in old["hooks"] if gateguard is None else gateguard == "on"

    return _checked(
        fw,
        {
            "profile": profile_name or old["profile"],
            "orchestration": orchestration or old["orchestration"],
            "agents": agents,
            "guides": guides,
            "hooks": [h for h in settings.HOOKS if wanted(h)],
        },
    )


def _managed(fw: Path, choices: dict) -> set[str]:
    """The project files these choices make the framework's."""
    guides = dict.fromkeys([*choices["guides"], *profile.required_guides(fw, choices["agents"])])
    return (
        {f".claude/agents/{n}.md" for n in choices["agents"]}
        | {f".claude/shared/{g}" for g in guides}
        | {f".claude/hooks/{h}.py" for h in choices["hooks"]}
    )


# --- Reading the tree ------------------------------------------------------


def _read(path: Path) -> str | None:
    """The file's text exactly as stored (no newline translation), None if absent."""
    return path.read_bytes().decode("utf-8") if path.is_file() else None


def _rules(prj: Path) -> Rules:
    text = _read(prj / USER_RULES)
    return parse_rules(text) if text is not None else Rules()


def _rules_text(region: str | None) -> str:
    """The rules inside a user-rules region body: what follows its title."""
    if not region or "\n\n" not in region:
        return ""
    return region.split("\n\n", 1)[1].strip("\n")


def _installed_rules(prj: Path, fw: Path, choices: dict) -> Rules:
    """The rules the installed files carry now, read back from their regions and
    from the card values that differ from the source's row.

    Compared with a regeneration from these, a difference is not the rules: it
    is something done to the files by hand. A region too damaged to read counts
    as empty, so the damage shows up as a difference.
    """
    rows = assemble.agent_rows(fw)

    def region_of(text: str | None) -> str | None:
        try:
            return kernel.strip_user_rules(text)[1] if text else None
        except ValueError:
            return None

    agents: dict[str, str] = {}
    overrides: dict[str, dict[str, str]] = {}
    for name in choices["agents"]:
        text = _read(prj / ".claude" / "agents" / f"{name}.md")
        if text is None:
            continue
        body = _rules_text(region_of(text))
        if body:
            agents[name] = body
        try:
            have = assemble.fields(text)
        except ValueError:
            continue
        for key in OVERRIDE_KEYS:
            if key in have:
                value = have[key].split(":", 1)[1].strip()
                if str(rows[name].get(key)) != value:
                    overrides.setdefault(name, {})[key] = value
    return Rules(all=_rules_text(region_of(_read(prj / CLAUDE_MD))), agents=agents, overrides=overrides)


def _baseline(prj: Path, fw: Path, previous: dict | None, claude: str | None) -> dict[str, str] | None:
    """What the installed files should be if nobody touched them: a regeneration
    from the recorded choices and the rules they carry. Only meaningful at the
    version that wrote them; at another one every file differs by design."""
    if previous is None or previous.get("version") != _version(fw):
        return None
    old = installed_choices(previous)
    return assemble.generate(fw, old, _installed_rules(prj, fw, old), claude)


# --- Computing a plan --------------------------------------------------------


def _build(prj: Path, fw: Path, choices: dict, previous: dict | None) -> _Result:
    """The plan for these choices on this tree, and what carrying it out writes.

    `previous` is the manifest of an installation being updated; `None` is an
    installation. Same inputs, same plan: execution calls this again.
    """
    version = _version(fw)
    installing = previous is None
    claude = _read(prj / CLAUDE_MD)
    if not installing and (claude is None or kernel.parse(claude) is None):
        raise ValueError(
            f"{CLAUDE_MD} has no kernel marker: nobody can tell the framework's text from "
            "the project's, so update refuses — put the marker pair back around the "
            "framework's text (an empty pair on top if it is gone), then update again: "
            "see /claw fix, KERNEL_MISSING"
        )
    generated = assemble.generate(fw, choices, _rules(prj), claude)
    baseline = _baseline(prj, fw, previous, claude)
    out = _Result()

    def by_hand(rel: str) -> bool:
        return baseline is not None and rel in baseline and (prj / rel).read_bytes() != baseline[rel].encode("utf-8")

    for rel, text in generated.items():
        path = prj / rel
        if assemble.is_create_only(rel):
            if not path.exists():
                out.ops.append(_op(prj, rel, CREATE))
                out.files[rel] = text
            elif installing:
                out.ops.append(_op(prj, rel, KEEP, "already there: the project's state, untouched"))
            continue
        if not path.exists():
            out.ops.append(_op(prj, rel, CREATE))
        elif path.read_bytes() == text.encode("utf-8"):
            continue
        else:
            if installing:
                reason = (
                    "already there: the kernel region is written, the rest stays as the project part"
                    if rel == CLAUDE_MD
                    else "already there: replaced"
                )
            elif by_hand(rel):
                reason = HAND_EDIT
            elif previous.get("version") != version:
                reason = f"v{previous.get('version')} → v{version}"
            else:
                reason = "regenerated from the choices and the rules"
            out.ops.append(_op(prj, rel, MERGE if rel == CLAUDE_MD else OVERWRITE, reason))
        out.files[rel] = text

    if not installing:
        for rel in sorted(_managed(fw, installed_choices(previous)) - _managed(fw, choices)):
            if (prj / rel).is_file():
                reason = "no longer chosen" + ("; modified by hand, the edit is lost" if by_hand(rel) else "")
                out.ops.append(_op(prj, rel, REMOVE, reason))
                out.remove.append(rel)

    _settings_and_manifest(prj, fw, choices, previous, out)

    if installing:
        if (prj / USER_RULES).is_file():
            out.ops.append(_op(prj, USER_RULES, KEEP, "your rules: applied, never rewritten"))
        else:
            out.ops.append(_op(prj, USER_RULES, CREATE, "empty: your rules go here"))
            out.files[USER_RULES] = ""
        wanted = set(generated)
        for area in SHARED_DIRS:
            for p in _files(prj / ".claude" / area):
                rel = p.relative_to(prj).as_posix()
                if rel not in wanted:
                    out.ops.append(_op(prj, rel, KEEP, "not the framework's: stays as it is"))
        for rel in FOREIGN_INSTRUCTIONS:
            if (prj / rel).is_file():
                out.ops.append(
                    _op(prj, rel, KEEP, "instructions of another tool: they stay, "
                        "and they can contradict CLAUDE.md")
                )
    return out


def _settings_and_manifest(
    prj: Path, fw: Path, choices: dict, previous: dict | None, out: _Result
) -> None:
    """`settings.json`: what the record says the framework added goes, then the
    framework's slice for these choices is merged. A value of the user's that
    differs stays and is reported. Then the new `claw.json`."""
    prof = profile.load(fw / "profiles" / f"{choices['profile']}.toml")
    current = _current_settings(prj)
    record = previous.get("settings_added") if previous else None
    rest = settings.unmerge(current, record)[0] if isinstance(record, dict) else current
    rest, stale = _drop_framework_hooks(rest, only_stale=True)
    merged, added, conflicts = settings.merge(
        rest, settings.framework(prof.settings, choices["hooks"], choices["orchestration"])
    )
    exists = (prj / SETTINGS).is_file()
    if merged != current or not exists:
        why = []
        if exists and previous is None:
            why.append("merged: your entries stay")
        if previous is not None and previous.get("profile") != choices["profile"]:
            why.append(f"profile {previous.get('profile')} → {choices['profile']}")
        if stale:
            why.append(f"replaced, from an older release or touched up: {', '.join(stale)}")
        if conflicts:
            why.append(f"your value stays on: {', '.join(conflicts)}")
        if not why:
            why.append("the framework's entries follow the choices")
        out.ops.append(_op(prj, SETTINGS, MERGE if exists else CREATE, "; ".join(why)))
        out.settings = merged
    elif conflicts:
        out.ops.append(_op(prj, SETTINGS, KEEP, f"your value stays on: {', '.join(conflicts)}"))
    out.conflicts = conflicts

    accepted = previous.get("accepted") if previous else None
    data = source.manifest(
        _version(fw),
        choices["profile"],
        choices["orchestration"],
        choices["agents"],
        choices["guides"],
        choices["hooks"],
        settings_added=added,
        accepted=accepted if isinstance(accepted, dict) else None,
    )
    if previous is None:
        out.ops.append(_op(prj, MANIFEST, CREATE))
    elif data != previous:
        out.ops.append(
            _op(prj, MANIFEST, MERGE, f"v{previous.get('version')} → v{_version(fw)}"
                if previous.get("version") != _version(fw) else "the choices")
        )
    else:
        return
    out.manifest = data


def _same_plan(prj: Path, saved: Sequence[Operation], fresh: Sequence[Operation]) -> None:
    """Refuses, before anything is written, a plan the tree has outgrown.

    A file changed after the plan is named first; then the saved plan must be
    exactly the one computed now, so a hand-edited plan file cannot ask for a
    removal or a move the framework would never plan.
    """
    active = [op for op in saved if op.action != KEEP]
    _verify(prj, active)
    key = lambda ops: {(o.path, o.action, o.digest) for o in ops if o.action != KEEP}  # noqa: E731
    differ = key(saved) ^ key(fresh)
    if differ:
        raise ValueError(
            "the plan is not the one this tree and these choices give, nothing was written — "
            "plan again: " + ", ".join(sorted({path for path, _, _ in differ}))
        )


def _write(prj: Path, result: _Result) -> None:
    """The one place files are written."""
    for rel, text in result.files.items():
        path = prj / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    for rel in result.remove:
        (prj / rel).unlink()
    _prune(prj, result.remove)
    if result.settings is not None:
        (prj / SETTINGS).parent.mkdir(parents=True, exist_ok=True)
        _write_json(prj / SETTINGS, result.settings)
    if result.manifest is not None:
        (prj / MANIFEST).parent.mkdir(parents=True, exist_ok=True)
        _write_json(prj / MANIFEST, result.manifest)


# --- Install -----------------------------------------------------------------


def plan_install(project_root: Path, framework_root: Path, choices: dict) -> list[Operation]:
    """What the installation would do to this project, file by file.

    An existing `CLAUDE.md` becomes the project part, `settings.json` is merged,
    state files already there stay. Every other target already present is
    overwritten, and the plan says so by name. The project's files that sit in
    the framework's folders stay, and are listed: whoever approves must know
    they will live side by side. `.claude/user-rules.md` is created empty, or
    applied if it is there.
    """
    return _install(Path(project_root), Path(framework_root), choices).ops


def _install(prj: Path, fw: Path, choices: dict) -> _Result:
    if (prj / MANIFEST).exists():
        raise ValueError(
            f"{MANIFEST} already exists: the project is installed — "
            "/claw update or /claw fix, not a second installation"
        )
    return _build(prj, fw, _checked(fw, choices), None)


def apply_install(
    project_root: Path, framework_root: Path, ops: Sequence[Operation], choices: dict
) -> list[str]:
    """Runs a `plan_install` plan: returns the settings conflicts (your value stays).

    Everything is computed and every digest re-checked before the first byte.
    """
    prj, fw = Path(project_root), Path(framework_root)
    result = _install(prj, fw, choices)
    _same_plan(prj, ops, result.ops)
    _write(prj, result)
    return result.conflicts


# --- Update ------------------------------------------------------------------


def update_summary(
    project_root: Path,
    framework_root: Path,
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
    profile_name: str | None = None,
    orchestration: str | None = None,
    gateguard: str | None = None,
) -> str:
    """The plan's header: `update v2.7.0 → v3.0.0 · profile a → b · agents +x −y`."""
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    old = installed_choices(manifest)
    new = _next_choices(fw, manifest, add, remove, profile_name, orchestration, gateguard)
    parts = [f"update v{manifest.get('version')} → v{_version(fw)}"]
    for key in ("profile", "orchestration"):
        if old[key] != new[key]:
            parts.append(f"{key} {old[key]} → {new[key]}")
    for key in source.MANIFEST_LISTS:
        gained = [n for n in new[key] if n not in old[key]]
        lost = [n for n in old[key] if n not in new[key]]
        if gained or lost:
            parts.append(f"{key} " + " ".join([f"+{n}" for n in gained] + [f"−{n}" for n in lost]))
    return " · ".join(parts)


def plan_update(
    project_root: Path,
    framework_root: Path,
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
    profile_name: str | None = None,
    orchestration: str | None = None,
    gateguard: str | None = None,
) -> list[Operation]:
    """What bringing the installation to this source and these choices would do.

    The files are regenerated from the source, the choices in `claw.json` after
    `add`/`remove`/`profile_name`/`orchestration`/`gateguard`, and the user's
    rules. At the version that wrote them, a file that differs from what the
    recorded choices generate has been edited by hand: the plan names it, since
    the edit is lost. The validation of the requested changes comes first.
    """
    prj, fw = Path(project_root), Path(framework_root)
    return _update(prj, fw, add, remove, profile_name, orchestration, gateguard).ops


def _update(prj, fw, add, remove, profile_name, orchestration, gateguard) -> _Result:
    manifest = _manifest(prj)
    choices = _next_choices(fw, manifest, add, remove, profile_name, orchestration, gateguard)
    return _build(prj, fw, choices, manifest)


def apply_update(
    project_root: Path,
    framework_root: Path,
    ops: Sequence[Operation],
    add: Sequence[str] = (),
    remove: Sequence[str] = (),
    profile_name: str | None = None,
    orchestration: str | None = None,
    gateguard: str | None = None,
) -> list[str]:
    """Runs a `plan_update` plan with the same changes: returns the settings
    conflicts. Nothing is written if the tree is no longer the one planned."""
    prj, fw = Path(project_root), Path(framework_root)
    result = _update(prj, fw, add, remove, profile_name, orchestration, gateguard)
    _same_plan(prj, ops, result.ops)
    _write(prj, result)
    return result.conflicts


# --- Uninstall ---------------------------------------------------------------


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

    A framework file is removed only if it equals what the source generates for
    the installation's choices and rules, that is if it holds nobody's work;
    any other is archived whole. The source is needed to know that: without it
    a plan that archives everything is not the one the user believes they are
    approving. An archive already there is a previous uninstall: writing over
    it would mix it with this one.
    """
    return _uninstall(Path(project_root), Path(framework_root))


def _uninstall(prj: Path, fw: Path) -> list[Operation]:
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
    try:
        rules = _rules(prj)
    except ValueError:
        # Unreadable rules: every file that carried one differs, and a file that
        # differs is archived, never deleted.
        rules = Rules()
    claude = _read(prj / CLAUDE_MD)
    generated = assemble.generate(fw, installed_choices(manifest), rules, claude)

    ops = _settings_uninstall_ops(prj, manifest)
    if claude is not None:
        if kernel.parse(kernel.strip_user_rules(claude)[0]) is None:
            ops.append(_op(prj, CLAUDE_MD, KEEP, "no markers: no framework region"))
        else:
            ops.append(_op(prj, CLAUDE_MD, MERGE, "the kernel and user-rules regions go, the rest stays"))

    for area in SHARED_DIRS:
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            if rel not in generated:
                ops.append(_op(prj, rel, KEEP, "not from the source: stays"))
            elif p.read_bytes() == generated[rel].encode("utf-8"):
                ops.append(_op(prj, rel, REMOVE, "identical to what the source generates"))
            elif _archivable(rel):
                ops.append(_op(prj, rel, ARCHIVE, "differs from what the source generates: kept"))
            else:
                ops.append(_op(prj, rel, KEEP, "not the framework's: stays"))

    if (prj / USER_RULES).is_file():
        ops.append(_op(prj, USER_RULES, KEEP, "your rules"))
    for name in doctor.STATE_FILES:
        if (prj / "docs" / name).is_file():
            ops.append(_op(prj, f"docs/{name}", KEEP, "project state"))
    ops.append(
        _op(prj, MANIFEST, ARCHIVE, "last: while it is there, /claw knows the choices")
    )
    return ops


def apply_uninstall(
    project_root: Path, framework_root: Path, ops: Sequence[Operation]
) -> None:
    """Runs a `plan_uninstall` plan.

    All digests are re-checked **before** writing: a file changed after the
    plan stops everything, not only itself. The plan is also recomputed: it is a
    saved file, and a "remove" written by hand with the right digest would
    delete the project's work. Then, in this order: settings, `CLAUDE.md`, moves
    into the archive with the manifest last, removals, folders left empty.
    """
    prj, fw = Path(project_root), Path(framework_root)
    fresh = _uninstall(prj, fw)
    _same_plan(prj, ops, fresh)
    active = [op for op in fresh if op.action != KEEP]
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
    paths = {op.path for op in active}

    if SETTINGS in paths:
        record = (source.read_manifest(prj) or {}).get("settings_added")
        rest, _, _ = _uninstalled_settings(_read_json(prj / SETTINGS), record)
        _write_json(prj / SETTINGS, rest)

    if CLAUDE_MD in paths:
        claude = prj / CLAUDE_MD
        text, rules_region = kernel.strip_user_rules(_read(claude))
        if rules_region is not None and text.endswith("\n\n"):
            text = text[:-1]  # the blank line `generate` put before the region
        region = kernel.parse(text)
        claude.write_bytes((text[: region.start] + text[region.end :].lstrip("\n")).encode("utf-8"))

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


# --- Helpers -----------------------------------------------------------------


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _op(prj: Path, rel: str, action: str, reason: str = "") -> Operation:
    return Operation(rel, action, reason, _digest(prj / rel))


def _files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file()) if directory.is_dir() else []


def _verify(prj: Path, ops: Sequence[Operation]) -> None:
    changed = sorted({op.path for op in ops if _digest(prj / op.path) != op.digest})
    if changed:
        raise ValueError(
            "changed after the plan, nothing was written — plan again: "
            + ", ".join(changed)
        )


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
            "installation wrote or from which choices"
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


def _hook_name(entry: object) -> str | None:
    command = entry.get("command") if isinstance(entry, dict) else None
    if not isinstance(command, str):
        return None
    return next((n for n in HOOK_PATH_RE.findall(command) if n in settings.HOOKS), None)


def _drop_framework_hooks(data: dict, only_stale: bool = False) -> tuple[dict, list[str]]:
    """`(rest, dropped)`: every hook entry that launches a framework script goes
    — with `only_stale`, only those that differ from the source's entry, so the
    merge that follows writes the current one in their place.

    Single entries are removed, not the group: a user hook placed under the
    same `matcher` stays. Only the containers emptied here are pruned.
    """
    def drops(entry: object) -> bool:
        name = _hook_name(entry)
        if name is None:
            return False
        return not only_stale or entry != settings.hook_entry(name)

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
            keep = [h for h in inner if not drops(h)]
            dropped += [
                f"{event} «{group.get('matcher', '')}» → .claude/hooks/{_hook_name(h)}.py"
                for h in inner
                if drops(h)
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
    and a closed hook without its script blocks every `git` command and linter-configuration edit.
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
                "script blocks every git command and linter-configuration edit")
        )
    return ops
