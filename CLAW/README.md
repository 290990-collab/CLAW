# CLAW — source

A **self-sufficient** folder: the plugin root. Everything needed is in here,
tooling included.

```
VERSION              kernel version (semantics: patch · minor · major)
method/              COMMON kernel → CLAUDE.md, read by everyone at every spawn
coordinator/         COORDINATOR kernel → shared/orchestration.md, on demand
orchestrations/      orchestration models: one is appended to the guide, orchestrator-worker by default
cycles/              domain cycles, appended to the guide if the profile asks
cards/               31 agents: method + project [TO FILL IN] block; agents.toml holds their model, effort, tools
shared/core/         generic guides, loaded on demand
shared/domain/       domain guides (design, research, data, llm, marketing)
profiles/            7 profiles: domain → roster, guides, cycles, permissions
templates/           the state files, generated empty but structured
styles/              reporting.md: how to answer the user, aliases and rule names — main conversation only
hooks/               config_protection · block_no_verify (closed) · gateguard (open) → .claude/hooks/
skills/claw/         the /claw skill: SKILL.md routes, actions/ holds one file per action
tools/fwbuild/       assembly, checks — pure Python stdlib
tools/trial_install.py  the proof: installs a fake project, which the doctor checks
tools/sync_cards.py  writes the cards' front matter from cards/agents.toml
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

The folder is a Claude Code plugin: `/claw install`, in Claude Code in a project,
installs the framework.
The installation asks two languages per project: the chat's, written as
Claude Code's `language` setting in the project's `.claude/settings.local.json`,
and the codebase's (comments and identifiers), written in `conventions.md`.
Without `language`, the method's kernel answers in the language of the user's
messages.

## Commands

**Claude Code's `/claw <action>`** works on a project — install, update, fix,
add, remove, change, tune, tidy, comply, uninstall — and runs the commands
below itself, as `python "<FW>/claw.py" <command>`.

Whatever writes prints a plan and asks; `--yes` skips the question, and
without a terminal (a skill) the plan is saved and `--apply` runs it,
re-checking every file.

| command | does |
|---|---|
| `doctor [project] [--strict] [--json]` | integrity check |
| `install <project> --profile P` | the mechanical part of `/claw install`: files with placeholders, skeleton, settings, manifest |
| `down <project>` | a new version into a project, kernel regions included; card front matter follows the record |
| `repair` · `uninstall <project>` | put back what is missing · remove the framework, archiving what was adapted |
| `report <folders>` | versions and findings across many repositories |

## How it is built

**The method is generated, the adaptation is by hand.** In `CLAUDE.md` and in
every agent, the method lives inside a delimited region:

```html
<!-- FRAMEWORK:KERNEL v1.1.1 — generated, do not edit by hand -->
…
<!-- /FRAMEWORK:KERNEL -->
```

It is regenerated at every update: a change to the method belongs in
the framework's repository, not in the region.

Agents' front matter stays **outside** the region: changing `model:` is
configuration, not method.

**Guides and the response style have no region.** The text belongs to the
framework, the last section — the `[TO FILL IN]` block — to the project.
`/claw update` takes the new text from the source and keeps that block
as it is; if the block's heading is gone, the file is left untouched and the
plan names it, to be updated by hand. That is why in a guide the placeholder
sits **only** in the last section: a test checks it.

## Maintenance rules

- **The method is not customised per project.** You fill in the context (the
  `[TO FILL IN]` blocks), you do not rewrite the method. If a change to the
  method is right, it is right for everyone: it is made in the framework's
  repository.
- **Only the active is installed.** An agent not chosen is not deleted, it is
  not yet installed: it stays in the source and `/claw add` takes it up to
  date.
- **Non-universal content → `shared/`**, behind a pointer. `CLAUDE.md` is paid
  at every agent spawn: it is the most expensive file in the system.

## Tests

```bash
cd tools && python -m unittest discover -s tests -t . -v
```
