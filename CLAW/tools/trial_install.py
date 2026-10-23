"""Trial installation: simulates /claw install on the `software` profile.

Fake project: `logtail`, a command-line tool that follows and filters log
files, with the CLAUDE.md its owner wrote and a `.claude/user-rules.md`. It
serves to demonstrate that a complete installation passes the doctor.
"""

import shutil
import sys
from pathlib import Path

from fwbuild import assemble, lifecycle, profile, settings

FRAMEWORK = Path(__file__).resolve().parents[1]
# Outside the source: the package ships the code that runs the trial, not the trial.
DEFAULT_OUT = FRAMEWORK.parent / "_build" / "trial"
VERSION = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
# The answer to question 5: `software` recommends none, the default holds.
ORCHESTRATION = assemble.DEFAULT_ORCHESTRATION

PROJECT_SECTIONS = """## The project

`logtail` — a command-line tool that follows and filters log files in real
time.

| Path | Role |
|---|---|
| `src/logtail/core/` | pure logic: incremental reading, parsing, filters |
| `src/logtail/cli/` | argument parsing, terminal rendering |
| `tests/` | tests for every module of `core/` |
| `fixtures/` | real, dirty logs for the tests |

**HARD constraints:**

- `core/` does not import from `cli/`: the dependency goes one way only.
- Constant memory during follow, whatever the size of the file.
- Malformed lines do not stop processing and end up in a count.

**Contracts:** the format of `~/.logtail.toml` · the names of the subcommands
and options · the exit codes. Changing them breaks users' scripts.

## Commands

```bash
python -m pytest -q          # tests — the quick check the agent runs
ruff check && ruff format    # analysis and formatting
python -m build              # full build
```

The performance measurements on `fixtures/big.log` (2 GB) are launched by the
user.

## Critical surface

Security: the user's filter patterns become regular expressions, the paths come
from the command line and from configuration, and the logs can contain
credentials. `security-reviewer` reviews before the final check.

## Current state

Project just initialised. No consolidated conclusions.
"""

USER_RULES = """## All
- Commit messages in English, no signature.

## tester
model: sonnet
effort: high
- Run `pytest -q -x`, never the whole matrix.
"""


def choices(orchestration: str = ORCHESTRATION) -> dict:
    """The questionnaire's answers, as `claw.json` records them.

    A function and not variables inside `install()`: the tests plan from the
    same choices, and two copies would diverge in silence.
    """
    prof = profile.load(FRAMEWORK / "profiles" / "software.toml")
    roster = profile.roster(prof, extras=[], drop=[])
    return {
        "profile": prof.name,
        "orchestration": orchestration,
        "agents": roster,
        "guides": profile.guides(FRAMEWORK, prof, roster),
        "hooks": list(settings.HOOKS),
    }


def install(out: Path, orchestration: str = ORCHESTRATION) -> int:
    """Installs the fake project and returns the number of agents.

    The owner's `CLAUDE.md` and `user-rules.md` are in place first, as on a real
    project; the installation is the one `claw.py install` runs.
    """
    if out.exists():
        shutil.rmtree(out)
    (out / ".claude").mkdir(parents=True)
    (out / "CLAUDE.md").write_bytes(PROJECT_SECTIONS.encode("utf-8"))
    (out / ".claude" / "user-rules.md").write_bytes(USER_RULES.encode("utf-8"))

    chosen = choices(orchestration)
    ops = lifecycle.plan_install(out, FRAMEWORK, chosen)
    lifecycle.apply_install(out, FRAMEWORK, ops, chosen)

    print(f"installed: {len(chosen['agents'])} agents, {len(chosen['guides'])} guides -> {out}")
    return len(chosen["agents"])


if __name__ == "__main__":
    install(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
