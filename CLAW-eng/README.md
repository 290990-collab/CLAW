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
shared/domain/       domain guides (design, research, data, llm, marketing)
profiles/            7 profiles: domain → roster, guides, cycles, permissions
templates/           the state files, generated empty but structured
output-styles/       reporting.md: how to answer the user, aliases and rule names — main conversation only
hooks/               config_protection · block_no_verify (closed) · gateguard (open) → .claude/hooks/
skills/claw/         the /claw skill: SKILL.md routes, actions/ holds one file per action
skills/              plus the packages connected with `claw skills add` and pool.toml: local, never published
tools/fwbuild/       assembly, hashing, checks — pure Python stdlib
tools/trial_install.py  the proof: installs a fake project, which the doctor checks
tools/tests/         the tests
claw.py              the command line
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

Python 3.11+ and git; nothing else to install.

```bash
git clone <repo> ~/.claude/CLAW
python ~/.claude/CLAW/CLAW-eng/claw.py setup    # the /claw skill into ~/.claude/skills/, `claw` into ~/.local/bin/
```

The clone is the master. From then on every new project is `/claw install`.
The reply language is Claude Code's `language` setting: the installation asks
for it once if neither `~/.claude/settings.json` nor `~/.claude/CLAUDE.md`
fixes one. Without it, the method's kernel answers in the language of the
user's messages.

## Commands

Two surfaces, split by who acts. **The terminal** works on the source:
`claw update` takes a release, `claw status` and `claw doctor` look.
**Claude Code's `/claw <action>`** works on a project — install, update, fix,
add, remove, change, share, tune, memory, comply, uninstall — and runs the
commands below itself.

Whatever writes prints a plan and asks; `--yes` skips the question, and
without a terminal (a skill) the plan is saved and `--apply` runs it,
re-checking every file.

| command | does |
|---|---|
| `update` | fetches, lists incoming commits, merges them into the master (a promotion is a local commit, kept), refreshes `/claw` |
| `status [project]` | source against its branch; the project in this folder, or the one named: version, doctor, commits in between |
| `doctor [project] [--strict] [--json]` | integrity check |
| `setup` | the `/claw` skill with this source's path written in, and the `claw` launcher |
| `install <project> --profile P` | the mechanical part of `/claw install`: files with placeholders, skeleton, settings, manifest |
| `down <project>` | a new version into a project, kernel regions included; card front matter follows the record |
| `repair` · `uninstall <project>` | put back what is missing · remove the framework, archiving what was adapted |
| `report <folders>` | versions and findings across many repositories |
| `source [path]` · `skills list\|add\|remove` | validate a source · connected skill packages |

## How it is built

**The method is generated, the adaptation is by hand.** In `CLAUDE.md` and in
every agent, the method lives inside a delimited region:

```html
<!-- FRAMEWORK:KERNEL v1.1.1 sha256:a3f9c1e4 — generated, do not edit by hand -->
…
<!-- /FRAMEWORK:KERNEL -->
```

It is not locked: you can modify it. The hash stops matching and
`claw doctor` tells you, so a change to the method becomes **visible**
instead of buried. From there `/claw share` carries it up into the source —
and that is the direction whose absence makes the method diverge between
projects.

Agents' front matter stays **outside** the region: changing `model:` is
configuration, not drift.

**Guides and the response style have no region.** The text belongs to the
framework, the last section — the `[TO FILL IN]` block — to the project.
`/claw update` takes the new text from the source and keeps that block
as it is; if the block's heading is gone, the file is left untouched and the
plan names it, to be updated by hand. That is why in a guide the placeholder
sits **only** in the last section: a test checks it.

## Maintenance rules

- **The method is not customised per project.** You fill in the context (the
  `[TO FILL IN]` blocks), you do not rewrite the method. If a change to the
  method is right, it is right for everyone: it goes up into the source with
  `/claw share`.
- **Only the active is installed.** An agent not chosen is not deleted, it is
  not yet installed: the master stays here and `/claw add` takes it up to
  date.
- **Non-universal content → `shared/`**, behind a pointer. `CLAUDE.md` is paid
  at every agent spawn: it is the most expensive file in the system.

## Tests

```bash
cd tools && python -m unittest discover -s tests -t . -v
```
