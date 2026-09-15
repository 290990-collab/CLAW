# CLAW — source

A **self-sufficient** folder: a single master on the machine, or copied into
the project. Everything needed is in here, tooling included.

```
VERSION              kernel version (semantics: patch · minor · major)
method/              COMMON kernel → CLAUDE.md, read by everyone at every spawn
coordinator/         COORDINATOR kernel → shared/orchestration.md, on demand
orchestrations/      orchestration models: one is appended to the guide, orchestrator-worker by default
cycles/              domain cycles, appended to the guide if the profile asks
agents/              29 agents: method + project [TO FILL IN] block
shared/core/         generic guides, loaded on demand
shared/domain/       domain guides (design, research, data, llm)
profiles/            7 profiles: domain → roster, guides, cycles, permissions
templates/           the state files, generated empty but structured
hooks/               config_protection · block_no_verify (closed) · gateguard (open) → .claude/hooks/
skills/              framework-install · framework-doctor · framework-sync · framework-memory · framework-comply
                     plus the packages connected with `fwbuild skills add` and pool.toml: local, never published
tools/fwbuild/       assembly, hashing, checks — pure Python stdlib
tools/trial_install.py  the proof: installs a fake project, which the doctor checks
tools/tests/         218 tests
```

## The separation that matters: by recipient, not by subject

`CLAUDE.md` is loaded into **every** context, including every subagent's.
Putting the delegation rules there means making an `explorer` that does not
delegate pay for them, at every single spawn.

So the method is split in two, by who reads it:

| source | artefact | recipient | cost |
|---|---|---|---|
| `method/` | `CLAUDE.md` | everyone | paid at **every spawn** |
| `coordinator/` | `.claude/shared/orchestration.md` | only whoever delegates | on demand |

In `method/` live the **obligations of whoever executes**, evidence, the
standard report, the change principles. In `coordinator/`, the ten rules of
delegation, the work cycle, how to write a prompt, the four levels of state.

The ten rules stay **complete and numbered in a single place**: the execution
obligations are a distinct list, not a renumbered subset of them. The doctor
flags `COORDINATOR_LEAK` if the boundary gets lost again.

## Installation

Claude Code looks for skills in `.claude/skills/` or in `~/.claude/skills/`,
not in here: until `framework-install` is in one of the two, it does not exist.
It is the only friction, and it is paid **once**, not per project.

**Single master** — recommended: one source on the machine, personal skill.

The repository carries **two sources**, one per language:
`CLAW-it/` and `CLAW-eng/`. You install **one**.

```bash
git clone <repo> ~/.claude/CLAW
cp -r ~/.claude/CLAW/CLAW-eng ~/.claude/framework
cp -r ~/.claude/framework/skills/framework-install ~/.claude/skills/
cp -r ~/.claude/framework/skills/framework-comply ~/.claude/skills/
```

```powershell
git clone <repo> $HOME\.claude\CLAW
Copy-Item -Recurse $HOME\.claude\CLAW\CLAW-eng $HOME\.claude\framework
Copy-Item -Recurse $HOME\.claude\framework\skills\framework-install $HOME\.claude\skills\
Copy-Item -Recurse $HOME\.claude\framework\skills\framework-comply $HOME\.claude\skills\
```

The destination is named `framework/` because that is one of the three places
Step 0 looks in; to leave it where it is, point at it with `$CLAUDE_FRAMEWORK`.

**Copied into the project** — this folder, renamed `framework/`, in the
project root, plus `cp -r framework/skills/framework-* .claude/skills/`. Step 0
finds it first.

From then on, every new project is **only** `/framework-install`: Step 0
validates the source before writing anything, Step 6 checks the result with
`doctor --strict`. To check a candidate source by hand:

```bash
cd <source>/tools && python -m fwbuild source ..
```

No dependency to install: only Python 3.11+ is needed (for `tomllib`).

What the common context of an installed project costs — the `CLAUDE.md` every
subagent pays at every spawn — is told by:

```bash
cd <source>/tools && python -m fwbuild cost <project> [--spawns N] [--devs N] [--price USD]
# defaults: 100 spawns a day, 1 person, $5 per million input tokens
```

`doctor --json` prints the same findings plus that measurement, for CI.

Across several repositories at once — how many versions of the method are out
there, and where:

```bash
cd <source>/tools && python -m fwbuild report <folder-of-repositories>
```

## How it is built

**The method is generated, the adaptation is by hand.** In `CLAUDE.md` and in
every agent, the method lives inside a delimited region:

```html
<!-- FRAMEWORK:KERNEL v1.1.1 sha256:a3f9c1e4 — generated, do not edit by hand -->
…
<!-- /FRAMEWORK:KERNEL -->
```

It is not locked: you can modify it. The hash stops matching and
`framework-doctor` tells you, so a change to the method becomes **visible**
instead of buried. From there `framework-sync` carries it up into the source —
and that is the direction whose absence makes the method diverge between
projects.

Agents' front matter stays **outside** the region: changing `model:` is
configuration, not drift.

## Maintenance rules

- **The method is not customised per project.** You fill in the context (the
  `[TO FILL IN]` blocks), you do not rewrite the method. If a change to the
  method is right, it is right for everyone: it goes up into the source with
  `framework-sync`.
- **Only the active is installed.** An agent not chosen is not deleted, it is
  not yet installed: the master stays here and `--activate` takes it up to
  date.
- **Non-universal content → `shared/`**, behind a pointer. `CLAUDE.md` is paid
  at every agent spawn: it is the most expensive file in the system.

## Tests

```bash
cd tools && python -m unittest discover -s tests -t . -v
```
