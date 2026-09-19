"""Merging and removing entries of `.claude/settings.json`, and declaring the hooks.

The file is the user's before it is the framework's: what the installation adds
has to be recorded so it can be removed later, and nothing else is touched. It
imports nothing from the package: the installation, `claw-sync` and the
end-to-end trial use it, and none of them should drag the rest along to merge
two dicts.
"""

import copy
from collections.abc import Sequence

HOOKS = ("config_protection", "block_no_verify", "gateguard")

# The one installed only if the project asks for it: it denies the first touch
# of every file, and costs one extra turn per session.
OPTIONAL_HOOKS = ("gateguard",)

# Closed hooks block even when they cannot run: a check that disappears because
# the interpreter is missing is a check nobody knows is off.
_CLOSED = ("config_protection", "block_no_verify")

_MATCHER = {
    "config_protection": "Edit|Write|MultiEdit",
    "block_no_verify": "Bash|PowerShell",
    "gateguard": "Edit|Write|MultiEdit",
}

_TIMEOUT_SECONDS = 10

# What an orchestration requires from `settings.json` in order to work. It is
# merged like the profile and ends up in the same record: changing it or
# uninstalling has to be able to remove it.
# The Task tools — the teams' shared list — are given by Claude Code by default
# only up to Opus 4.7 and Sonnet 4.6: on later models, without the second
# variable, the list stays empty and the team coordinates by messages alone.
ORCHESTRATION_SETTINGS = {
    "agent-teams": {
        "env": {
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
            "CLAUDE_CODE_ENABLE_TODO_TOOLS": "1",
        }
    },
}


def merge(existing: dict, framework: dict) -> tuple[dict, dict, list[str]]:
    """`(merged, added, conflicts)`: the framework's entries on top of the user's.

    A missing key is added whole; two dicts merge recursively; two lists are
    joined by appending only the missing items; on a differing scalar the
    existing one wins and the key goes into the conflicts. `added` carries only
    what actually got in, in the same nested shape: it is the record `unmerge`
    consumes. Conflicts are dotted paths.
    """
    merged = copy.deepcopy(existing)
    added: dict = {}
    conflicts: list[str] = []
    for key, value in framework.items():
        if key not in merged:
            merged[key] = copy.deepcopy(value)
            added[key] = copy.deepcopy(value)
            continue
        current = merged[key]
        if isinstance(current, dict) and isinstance(value, dict):
            sub, sub_added, sub_conflicts = merge(current, value)
            merged[key] = sub
            if sub_added:
                added[key] = sub_added
            conflicts += [f"{key}.{c}" for c in sub_conflicts]
        elif isinstance(current, list) and isinstance(value, list):
            new = [copy.deepcopy(v) for v in value if v not in current]
            if new:
                merged[key] = current + new
                added[key] = new
        elif current != value:
            conflicts.append(str(key))
    return merged, added, conflicts


def unmerge(current: dict, added: dict) -> tuple[dict, list[str]]:
    """`(rest, kept)`: removes `merge`'s record from what is there today.

    Only what is still equal to the record is removed: a scalar the user
    changed stays, and its path goes into `kept`. A list item that is no longer
    there is not reported: removed or changed, the two cannot be told apart.
    Containers emptied by the removal are pruned — those the user already had
    empty before `merge` go with them, which is the same thing for
    `settings.json`.
    """
    rest = copy.deepcopy(current)
    kept: list[str] = []
    for key, value in added.items():
        if key not in rest:
            continue
        have = rest[key]
        if isinstance(have, dict) and isinstance(value, dict):
            sub, sub_kept = unmerge(have, value)
            kept += [f"{key}.{k}" for k in sub_kept]
            if sub:
                rest[key] = sub
            else:
                del rest[key]
        elif isinstance(have, list) and isinstance(value, list):
            remaining = list(have)
            for item in value:
                if item in remaining:
                    remaining.remove(item)
            if remaining:
                rest[key] = remaining
            else:
                del rest[key]
        elif have == value:
            del rest[key]
        else:
            kept.append(str(key))
    return rest, kept


def _command(name: str) -> str:
    """A hook's shell command: it finds script and interpreter, or it stops.

    Claude Code runs it with `sh -c` (Git Bash on Windows). The script is found
    from `$CLAUDE_PROJECT_DIR` and not from an absolute path, because
    `settings.json` travels with the repository. `python3` comes after
    `python` because on Windows it is the Store stub. ASCII only: the command
    goes through the shell's encoding.

    A closed hook is not run with `exec`: a script that does not compile
    (Python 2, or below 3.10) exits 1, and for Claude Code 1 means "no
    objection". Every exit other than 0 becomes 2; stdin passes to the script
    because `sh -c` does not read it.
    """
    if name not in HOOKS:
        raise ValueError(f"unknown hook: {name}")
    if name in _CLOSED:
        fallback = f'echo "{name}: script or python missing, blocking" >&2; exit 2;'
        run = (
            '"$P" "$F"; c=$?; [ $c -eq 0 ] && exit 0; '
            f'[ $c -eq 2 ] || echo "{name}: script exited with code $c, blocking" >&2; exit 2'
        )
    else:
        fallback = f'echo "{name}: script or python missing, letting it through" >&2; exit 0;'
        run = 'exec "$P" "$F"'
    return (
        f'F="$CLAUDE_PROJECT_DIR/.claude/hooks/{name}.py"; '
        "P=$(command -v python || command -v python3); "
        f'[ -f "$F" ] && [ -n "$P" ] || {{ {fallback} }}; '
        + run
    )


def hooks(names: Sequence[str]) -> dict:
    """The part of `settings.json` that declares the chosen hooks, to be merged.

    No hooks → empty dict: a `hooks` key with no entries would be a container
    `unmerge` would prune, and the merge-remove round trip would not come back.
    """
    unknown = [n for n in names if n not in HOOKS]
    if unknown:
        raise ValueError(f"unknown hooks: {', '.join(unknown)}")
    if not names:
        return {}
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": _MATCHER[name],
                    "hooks": [
                        {
                            "type": "command",
                            "command": _command(name),
                            "timeout": _TIMEOUT_SECONDS,
                        }
                    ],
                }
                for name in names
            ]
        }
    }
