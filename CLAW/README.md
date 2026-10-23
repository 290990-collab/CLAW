# CLAW — source

A **self-sufficient** folder: the plugin root. Everything needed is in here,
tooling included.

```
VERSION              kernel version (semantics: patch · minor · major)
method/              COMMON kernel → CLAUDE.md, read by everyone at every spawn
coordinator/         COORDINATOR kernel → shared/orchestration.md, on demand
orchestrations/      orchestration models: one is appended to the guide, orchestrator-worker by default
cycles/              domain cycles, appended to the guide if the profile asks
cards/               31 agents: method; agents.toml holds their model, effort, tools
shared/core/         generic guides, loaded on demand
shared/domain/       domain guides (design, research, data, llm, marketing)
profiles/            7 profiles: domain → roster, guides, cycles, permissions
templates/           the state files, generated empty but structured
styles/              reporting.md: how to answer the user, aliases and rule names — main conversation only
hooks/               config_protection · block_no_verify (closed) · gateguard (open) → .claude/hooks/
skills/claw/         the /claw skill: SKILL.md routes, actions/ holds one file per action
tools/fwbuild/       generation, checks — pure Python stdlib
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

Python 3.11+; nothing else to install.

The folder is a Claude Code plugin (`/plugin marketplace add 290990-collab/CLAW`,
`/plugin install claw@claw`): `/claw install`, in Claude Code in a project, installs
the framework.
The installation asks two languages per project: the chat's, written as
Claude Code's `language` setting in the project's `.claude/settings.local.json`,
and the codebase's (comments and identifiers), written in `conventions.md`.
Without `language`, the method's kernel answers in the language of the user's
messages.

## Commands

**Claude Code's `/claw <action>`** works on a project — install, update (also
add, remove, profile, orchestration), rule, fix, tune, tidy, comply, uninstall —
and runs the commands below itself, as `python "<FW>/claw.py" <command>`; there
is no `claw` launcher on the terminal.

Whatever writes prints a plan and asks; `--yes` skips the question, and
without a terminal (a skill) the plan is saved and `--apply` runs it,
re-checking every file.

| command | does |
|---|---|
| `doctor [project] [--strict] [--json]` | integrity check |
| `install <project> --profile P` | the mechanical part of `/claw install`: every file generated from the choices, settings, manifest |
| `update <project> [--add --remove --profile --orchestration --gateguard]` | regenerates the project from the plugin and `claw.json` |
| `uninstall <project>` | remove the framework, archiving what was adapted |
| `report <folders>` | versions and findings across many repositories |

## How it is built

**Everything is generated, the adaptation is one file.** `.claude/claw.json`
records the choices (`version`, `profile`, `orchestration`, `agents`, `guides`,
`hooks`, `settings_added`, optional `accepted`); `install` and `update` regenerate
every framework file from it, from the plugin and from `.claude/user-rules.md`. In
`CLAUDE.md` and in every agent, the method lives inside a marked region:

```html
<!-- FRAMEWORK:KERNEL v2.7.0 — generated — edit .claude/user-rules.md instead -->
…
<!-- /FRAMEWORK:KERNEL -->
```

A change to the method belongs in the framework's repository, not in the region.

`.claude/user-rules.md` is the only file the user writes: `## All` lands at the
bottom of `CLAUDE.md`, `## <agent>` at the end of that card, and `model:` /
`effort:` lines there override the card's front matter. On conflict the user's
rules win. A generated file edited by hand is named by the `update` plan before it
is overwritten.

## Maintenance rules

- **The method is not customised per project.** You add rules
  (`.claude/user-rules.md`), you do not rewrite the method. If a change to the
  method is right, it is right for everyone: it is made in the framework's
  repository.
- **Only the active is installed.** An agent not chosen is not deleted, it is
  not yet installed: it stays in the source and `/claw update --add` brings it
  in.
- **Non-universal content → `shared/`**, behind a pointer. `CLAUDE.md` is paid
  at every agent spawn: it is the most expensive file in the system.

## Tests

```bash
cd tools && python -m unittest discover -s tests -t . -v
```
