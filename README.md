<p align="center">
  <img src="assets/claw.png" alt="CLAW, an orange block with two claws, sitting cross-legged in calm focus" width="440">
</p>

<h1 align="center">CLAW</h1>

<table align="center"><tr><td>

```
+-- CLAW-eng ----------------------------------------------+
|       method             coordinator        cycles       |
|       agents             shared             hooks        |
|       orchestrations                                     |
+-----------------------------------+----------------------+
                                    |               ^
                            +-------+-------+       |
                            |    profile    |       |
                            +-------+-------+       |
                                    |               |
  /framework-install -+     +-------+-------+       |
  /framework-doctor  -+---->|    fwbuild    |       |
  /framework-sync    -+     +-------+-------+       |
  /framework-comply  -+             |               |
+-- project ------------------------+---------------+------+
|      CLAUDE.md            .claude/agents       docs      |
|      .claude/shared       .claude/hooks                  |
+----------------------------------------------------------+
```

</td></tr></table>

**A working method for Claude Code. Installed in one command, checked by a doctor.**

Claude Code ships subagents, hooks and skills, but no method. Every project
writes its own `CLAUDE.md` by hand, and every one drifts. CLAW is the method:
versioned, tested, generated into your project.

**Contents:** [What it does](#what-it-does) · [Talking to it](#talking-to-it) ·
[Hooks](#hooks) · [Agents](#agents) · [Profiles](#profiles) ·
[Orchestration](#orchestration) · [Install](#install) · [How do I…](#how-do-i) ·
[Command reference](#command-reference)

---

## What it does

### Evidence before action

- Nothing is cited unless it was read or run in the current session.
- Every fact says how far it is proven: said so · pointed at the line · showed
  the bad case cannot happen · **ran it** · reproduced for real. High
  confidence without a run is a contradiction.
- Anything not executed is marked `UNVERIFIED`. A check that ran and decided
  nothing is `INCONCLUSIVE`, never green.
- A fact a command can settle is run, not asked of you.
- No fix until the root cause explains every symptom, and a refuted hypothesis
  takes back what it motivated.
- Every agent closes with the same report: confidence, what would disprove it,
  what it did **not** check.

### Principles, applied

| Principle | In practice |
|---|---|
| **KISS, YAGNI** | The simplest code for today's requirement. Nothing for hypothetical needs. |
| **Minimal safe change** | One problem per diff. No unrequested refactoring. |
| **Single source of truth** | Two copies that can diverge will diverge. |
| **Fail loudly** | No swallowed exceptions, no invented defaults. Security checks fail closed. |
| **Hyrum's law** | Every observable behaviour is a contract. Find its consumers before changing it. |
| **Least privilege** | Read-only reviewers get no shell. |
| **No shortcut to green** | A check never passes by being weakened. If the check is wrong, it is fixed on its own. |

### Context as a budget

- `CLAUDE.md` holds only what every agent needs, under a word budget the test
  suite enforces.
- Delegation rules load for the coordinator only.
- The response style loads in the main conversation only. Subagents never pay
  for it.
- Domain guides load when the task needs them.
- `fwbuild cost` converts all of it into tokens and dollars.

### Drift detection

The generated method sits in a hashed region of `CLAUDE.md`, of the
coordinator's guide and of every agent. Edit it and the doctor reports it.
Changes worth keeping go back to the source with `framework-sync --up`, and the
next project inherits them. Guides and the response style carry no hash: their
text comes from the source, their last section is yours.

### Work state across sessions

The coordinator keeps three files in `docs/`, and every new session starts from
them:

| File | Holds |
|---|---|
| `TODO.md` | Where the work is now: in progress, next, waiting on you, blocked |
| `status.md` | Closed decisions and measured results |
| `roadmap.md` | Goals, in dependency order, each with its done criterion |

---

## Talking to it

Three shortcuts work in the main conversation. They come with the `Reporting`
response style, which the install selects for you.

### Rule names

Write a rule's name anywhere in a message. Claude opens that rule, applies it to
the current work and tells you which decision it changed. An unknown name is
not guessed: it says so.

```
minimal change here, please
proof level?
not a finding — skip it
```

The names are the same in both editions:

| Name | What it makes Claude do |
|---|---|
| `strict scope` | Do only the assigned task; anything else goes in the report |
| `outside the mandate` | A choice that is not its to make is reported with options, not made |
| `open request` | Several readings possible: ask before picking one |
| `don't ask, run it` | Something a command can show is run, not asked of you |
| `stop criterion` | No verifiable "done" condition: stop and ask for one |
| `zero redundancy` | Tests green and nothing changed: do not re-run |
| `verified sources` | Cite nothing not read or run in this session |
| `proof level` | Say how far a claim is proven (1-5); inconclusive is not green |
| `hypotheses vs facts` | Keep what is deduced apart from what is verified |
| `blame the instrument` | An empty or too-easy result: doubt the check first |
| `rigorous debugging` | The cause must explain every symptom; undo what a wrong guess added |
| `honesty` | "I don't know" and "this is wrong" are fine; no agreeing against evidence |
| `which decision` | Whoever cites a rule says what it changed |
| `minimal change` | The smallest change, one problem at a time |
| `existing pattern` | Reuse what the repo already has |
| `contract first` | Find every consumer before changing an interface or a written rule |
| `kiss` | The simplest solution for today's requirement |
| `real green` | Never weaken a check; if the check is wrong, fix the check |
| `fail loudly` | No swallowed errors, no invented defaults |
| `useful test` | Write a test only if you can name the defect that makes it fail |
| `do it yourself` | Small change: the coordinator does it instead of delegating |
| `model to the task` | Agent and model chosen by the task, never raised |
| `declared selection` | Running an agent twice? Say first how the results will be chosen |
| `proportionate review` | No, one or two reviewers depending on how big the task is |
| `skipped step` | A skipped step stays written, with its reason |
| `tick with evidence` | A TODO box is ticked only with the command and outcome next to it |
| `safe pause` | Stop at a clean point and leave a note for whoever resumes |
| `pickup` | On resuming, read the trail left behind; do not redo it |
| `promote when it repeats` | One case is not a rule; two independent ones are a pattern |
| `two shapes` | The architect proposes two structurally different options |
| `plan that does not hold` | Recurring friction is reported; the plan is not reopened alone |
| `reader load` | A refactoring that does not make the code easier to read is undone |
| `not a finding` | Preferences, unreachable "what ifs" and unrequested abstractions are dropped |
| `impractical test-first` | If a test cannot come first, say why and run the closest check |
| `repro before the fix` | The failing reproduction is committed before the fix |

### Reference codes

When a reply lists three or more findings, decisions, options, risks, questions
or actions, each gets a numbered code: `F1` finding, `D1` decision, `O1` option,
`R1` risk, `Q1` question, `A1` action. You answer with the codes, and they stay
valid for the whole conversation:

```
keep D1, drop O2, go ahead with A3
```

### Aliases

Send one of these as the whole message. Inside a longer sentence they are
ordinary words.

| Alias | What you get |
|---|---|
| `scr` | The last reply again, simplified and compressed |
| `foc` | Only the real signal of the last reply |
| `ref` | The last reply rewritten with reference codes |
| `eli` | The last reply explained simply, and shorter |

---

## Hooks

A hook is a script Claude Code runs **before** a tool call; it can block the
call. A rule written in a prompt is followed most of the time; a hook holds
every time. CLAW installs three, in `.claude/hooks/`, registered in
`.claude/settings.json`:

| Hook | What it stops | Why |
|---|---|---|
| `block_no_verify` | `git commit --no-verify`, `git commit -n` and any change to `core.hooksPath` | Your git hooks cannot be skipped to get a commit through |
| `config_protection` | Edits to an **existing** linter or formatter config (`.eslintrc*`, `eslint.config.*`, `.prettierrc*`, `biome.json`, `ruff.toml`, `.flake8`, `.pylintrc`, `mypy.ini`, …). Creating a new one is allowed | A failing check gets fixed in the code, not by loosening the rule |
| `gateguard` | The **first** edit of each file in a session. It answers with what to check — who imports the file, what public surface changes — and the second attempt goes through | The edit starts from facts, not from a guess |

`block_no_verify` and `config_protection` are **closed**: if they cannot read
the call, they block. `gateguard` is **open**: an internal error lets the edit
through. It costs one extra turn per file, so the install asks whether you want
it; turn it off any time with `FRAMEWORK_GATEGUARD=off`.

Not sure a rule needs a hook? `/framework-comply <rule>` measures how often
Claude follows it. It runs the rule in real `claude -p` sessions on a throwaway
copy of the project, with a prompt that reminds the rule, a neutral one and one
that pushes to skip it, and counts each step. A step that is missed and visible
in the tool call becomes a hook candidate. It asks before spending: 17 sessions
by default, on your tokens.

---

## Agents

29 agents. Each project installs only the ones its profile and your answers
call for.

**Always installed** — the code cycle:

| Agent | What it does |
|---|---|
| `explorer` | Finds where things live, cheaply, before anything changes |
| `architect` | Plans changes that cross files or contracts. Writes no production code |
| `implementer` | Writes the planned change |
| `tester` | Tests invariants and contracts, not just examples |
| `refactorer` | Cleans up the structure, behaviour unchanged |
| `final-reviewer` | Rereads the diff from scratch and re-runs the tests before anything is called done |

**Added by profile or on request:**

| Agent | What it does |
|---|---|
| `api-scout` | Checks third-party APIs and version differences before code relies on them |
| `debugger` | Finds the cause of the defect nobody can explain |
| `silent-failure-hunter` | Hunts swallowed errors and faults hidden behind defaults |
| `comment-analyzer` | Finds comments that no longer tell the truth |
| `conversation-analyzer` | Reads past sessions for corrections that keep repeating |
| `frontend` | Views, components, style, motion, accessibility |
| `deploy` | Simple hosting: build, domain, secrets, redirects. Never with `infra` |
| `infra` | Infrastructure as code, environments, migrations. Never with `deploy` |
| `data-ingestion` | Pipelines that bring external data in |
| `results-analyst` | Reads measured results: is the change real, and why |
| `literature` | Finds and reads publications, places the project against them |
| `skill-runner` | Runs an external skill for the coordinator (see [skills](#use-other-peoples-skills)) |
| `market-researcher` | Audience, alternatives, the promise the product keeps |
| `campaign-planner` | Channel, cadence, headline, what to measure |
| `copywriter` | Writes the copy, every claim with its proof |
| `visual-designer` | Specifies images and layouts for published material |
| `content-analyst` | Reads the numbers after publishing, against the prediction |

**Reviewers of the critical surface** — the install asks what would make the
work wrong even with perfect code, and adds the matching reviewer:

| Agent | Critical surface |
|---|---|
| `security-reviewer` | Someone could abuse it |
| `scientific-reviewer` | The conclusions might not hold |
| `data-quality-reviewer` | The data might be wrong upstream |
| `compliance-reviewer` | Personal data, licences, terms of use |
| `perf-analyst` | A declared, measurable performance requirement |
| `claim-reviewer` | Public claims about the product (marketing) |

---

## Profiles

The first install question picks one. The profile sets the extra agents, the
guides, the work cycle and the file permissions. You can change it later
([how](#change-what-a-project-has)).

| Profile | For | Adds to the code cycle |
|---|---|---|
| `software` | Applications, services, CLI and desktop tools | `debugger`, `security-reviewer`, `api-scout`, `silent-failure-hunter`, `conversation-analyzer`, `comment-analyzer` |
| `library` | Libraries and packages: the public API is the product | `debugger`, `api-scout`, `silent-failure-hunter`, `conversation-analyzer`, `comment-analyzer` |
| `web` | Sites and web apps where the look is part of the product | `frontend`, `deploy`, `security-reviewer`, `api-scout`, `debugger`, `silent-failure-hunter`, `conversation-analyzer` · design cycle |
| `data` | Acquisition, transformation, storage, indexing | `debugger`, `data-ingestion`, `data-quality-reviewer`, `infra`, `api-scout`, `silent-failure-hunter`, `conversation-analyzer` |
| `research` | The product is reproducible evidence | `debugger`, `api-scout`, `results-analyst`, `literature`, `scientific-reviewer`, `silent-failure-hunter`, `conversation-analyzer` · research cycle |
| `llm` | A language model produces text, decisions or actions the code uses | `debugger`, `api-scout`, `scientific-reviewer`, `results-analyst`, `silent-failure-hunter`, `conversation-analyzer`, `comment-analyzer` · research cycle |
| `marketing` | Making a product known: positioning, copy, images, campaigns | `market-researcher`, `copywriter`, `visual-designer`, `campaign-planner`, `content-analyst`, `claim-reviewer` · content cycle |

A software project that also publishes content stays `software`, with the
marketing agents added on request.

---

## Orchestration

How the coordinator and the agents work together. One per project, chosen at
install, changeable later ([how](#change-what-a-project-has)).

| Model | How it runs |
|---|---|
| `orchestrator-worker` | The default. The coordinator spawns agents and collects their reports; agents never talk to each other |
| `agent-teams` | Experimental, on Claude Code's Agent teams. Agents share a task list, message each other and keep notes in `docs/team/`. Needs an interactive session, a trusted folder and Claude Code 2.1.233 or later; the install writes the two environment variables it needs. Suggested for `web`, `research` and `marketing` |

---

## Install

Once per machine. Needs Claude Code, git and Python 3.11+ — nothing else to
install.

### macOS · Linux

```bash
git clone https://github.com/290990-collab/CLAW.git ~/.claude/CLAW
cp -r ~/.claude/CLAW/CLAW-eng ~/.claude/framework        # or CLAW-it, in Italian
mkdir -p ~/.claude/skills
cp -r ~/.claude/framework/skills/framework-install ~/.claude/skills/
cp -r ~/.claude/framework/skills/framework-comply ~/.claude/skills/
```

### Windows · PowerShell

```powershell
git clone https://github.com/290990-collab/CLAW.git $HOME\.claude\CLAW
Copy-Item -Recurse $HOME\.claude\CLAW\CLAW-eng $HOME\.claude\framework   # or CLAW-it, in Italian
New-Item -ItemType Directory -Force $HOME\.claude\skills | Out-Null
Copy-Item -Recurse $HOME\.claude\framework\skills\framework-install $HOME\.claude\skills\framework-install
Copy-Item -Recurse $HOME\.claude\framework\skills\framework-comply $HOME\.claude\skills\framework-comply
```

`~/.claude/framework` is the **source**: the master copy every project is
generated from. The other skills — `framework-doctor`, `framework-sync`,
`framework-memory` — are copied into each project by the install.

---

## How do I…

### Set up

| I want to… | Do this | What happens |
|---|---|---|
| Set up a project | Open Claude Code in the project folder and run `/framework-install` | It reads the code (or asks for your idea), asks five questions one at a time — profile, critical surface, what you already know, what it may do without asking, orchestration — shows every file it will write and waits for your ok. It ends with the doctor |
| Keep the source inside one project | Copy the edition folder into the project as `framework/`, copy `framework/skills/framework-*` into `.claude/skills/`, run `/framework-install` | The install finds `./framework/` first. Search order: `./framework/`, `$CLAUDE_FRAMEWORK`, `~/.claude/framework/` |
| Check an installation | `/framework-doctor` | Every finding with its remedy; it fixes what it can. `OK — no findings` means healthy |
| Accept a warning on purpose | Add it to `accepted` in `.claude/framework.json`, with a reason (example below) | It prints as a note and no longer fails the check. Errors cannot be accepted |

The install writes only `CLAUDE.md`, `.claude/` and `docs/`. Existing files
there are merged or asked about, never silently overwritten; your code, build
and dependencies stay untouched.

```json
"accepted": {
  "TOKEN_BUDGET": "monorepo, the contracts live in CLAUDE.md on purpose",
  "KERNEL_DRIFT:CLAUDE.md": "deliberate: constraint X applies only here"
}
```

The key is the finding code, or `CODE:file` to limit it to one file.

### Change what a project has

| I want to… | Do this | What happens |
|---|---|---|
| Add an agent | `/framework-sync --activate frontend` | The agent arrives at the source's current version, with its project block filled in |
| Remove an agent | `/framework-sync --deactivate comment-analyzer` | Gone from the project; the source keeps it. The six code-cycle agents always stay |
| Add or remove a guide | `/framework-sync --activate domain/llm-guide.md` (or `--deactivate`) | The guide is copied and listed in `CLAUDE.md`, or removed |
| Change the orchestration | `/framework-sync`, then say `change the orchestration to agent-teams` | The coordinator's guide and the settings are rebuilt for the new model |
| Change the profile | `/framework-sync`, then say `change the profile to web` | Agents, guides, work cycles and permissions follow the new field; permissions you added stay |
| Put back missing files | `/framework-sync --repair` | Skills, hooks, state files, guides and settings that went missing come back. Nothing is overwritten |
| Remove the framework | `/framework-sync --uninstall` | Files identical to the source are deleted, adapted ones go to `.claude/framework-archive/`. `docs/` and your sections of `CLAUDE.md` stay |

`deploy` and `infra` cannot be installed together. If the doctor reports
`VERSION_MISMATCH` or `KERNEL_DRIFT`, run `/framework-sync --down` before
changing the orchestration or the profile.

### Update the framework

| I want to… | Do this | What happens |
|---|---|---|
| Get a new release | The steps below | Source and projects move to the new version, your changes kept |
| Make a change in one project count for all | Edit the method in the project, then `/framework-sync --up` | It asks whether the change is for everyone, writes it into the source and raises its version. Other projects get it with `--down`. The other edition is a separate source: carry it there by hand |

**New release, step by step:**

| Step | Do this |
|---|---|
| 1. Check the source | `cd ~/.claude/framework/tools && python -m fwbuild source ..` |
| 2a. If it says `intact` | `git -C ~/.claude/CLAW pull`, then replace `~/.claude/framework` with a fresh copy of the edition folder. Connected skill packages live inside it: reconnect them, or copy their folders and `skills/pool.toml` back |
| 2b. If it says `modified with --up` | `/framework-sync --upgrade`: the release is merged into your source, your changes are kept and each conflict is asked |
| 3. Update every project | `/framework-sync --down` in each: method, agents, guides, hooks and response style are refreshed; what you filled in is kept |

### Use other people's skills

Skills written by other people are connected to the source, never published
with CLAW. Read a skill before connecting it: it is instructions, sometimes
scripts, that an agent will run. Shell commands run in `~/.claude/framework/tools`.

| I want to… | Do this | What happens |
|---|---|---|
| Connect a repository of skills | `python -m fwbuild skills add <repo-url>` (add `--commit <sha>` to pin a version) | Every folder with a `SKILL.md` is connected, pinned to a commit |
| Get them into a project | `/framework-sync --down` (or `--repair`) in the project | You run them as `/<skill-name>`; the coordinator cannot see them |
| See what is connected | `python -m fwbuild skills list` | Packages, their skills, and which are in the pool |
| Let the coordinator use one | The steps below | The coordinator may call it — rarely, and through `skill-runner` |
| Disconnect a package | `python -m fwbuild skills remove <package>`, then `/framework-sync --down` in each project | The skills leave the source, the pool and the projects |

**Pool, step by step:**

| Step | Do this |
|---|---|
| 1. Add it to the pool | Write the name in `~/.claude/framework/skills/pool.toml` (create it if missing): `skills = ["skill-name"]` |
| 2. Update the project | `/framework-sync --down`. If the skill was already in the project, also delete its line under `skillOverrides` in `.claude/settings.json` |
| 3. Enable the runner | Once per project: `/framework-sync --activate skill-runner` |

### Everyday use

| I want to… | Do this | What happens |
|---|---|---|
| Stop and resume later | Say `safe pause` | Claude stops at a clean point and writes in `docs/TODO.md` where things are and the next step. A new session starts from there |
| Clean up stale memory | `/framework-memory` | Each stale memory is paired with the repo line that contradicts it; nothing changes without your ok |
| Check whether a rule is really followed | `/framework-comply <rule>` | See [Hooks](#hooks) |
| Turn off `gateguard` | Set `FRAMEWORK_GATEGUARD=off` in the environment Claude Code starts from | Edits are no longer stopped on first touch |
| Know what the method costs | `python -m fwbuild cost <project>` in `~/.claude/framework/tools` | Tokens of `CLAUDE.md` paid at every spawn, and the daily and monthly cost. Tune with `--spawns`, `--devs`, `--price` |
| See which projects run old versions | `python -m fwbuild report <folder-with-your-repos>` in `~/.claude/framework/tools` | One line per project: version, findings, `CLAUDE.md` size. `--depth N` looks deeper, `--json` is for CI |

---

## Command reference

### In Claude Code

| Command | What it does |
|---|---|
| `/framework-install` | Sets up the framework in a project |
| `/framework-doctor` | Checks an installation; every finding comes with its remedy |
| `/framework-memory` | Finds and fixes stale project memory |
| `/framework-comply <rule>` | Measures how often a rule is followed |
| `/framework-sync --down` | Brings the source's version into the project |
| `/framework-sync --up [what]` | Promotes a local change into the source |
| `/framework-sync --upgrade` | Merges a new release into a source changed with `--up` |
| `/framework-sync --activate <agent\|guide>` | Adds an agent or a guide |
| `/framework-sync --deactivate <agent\|guide>` | Removes it from the project; the source keeps it |
| `/framework-sync --repair` | Puts back missing files; overwrites nothing |
| `/framework-sync --uninstall` | Removes the framework, archiving what you adapted |
| `/framework-sync` + a request | Changes the profile or the orchestration |

Every command that writes shows its plan first and waits for your ok.

### From the shell — in `<source>/tools`

| Command | What it does |
|---|---|
| `python -m fwbuild doctor --strict <project>` | The doctor's check; exit 1 on warnings too |
| `python -m fwbuild doctor --json <project>` | Findings plus the `CLAUDE.md` measure, for CI |
| `python -m fwbuild cost <project> [--spawns N] [--devs N] [--price USD]` | Cost of `CLAUDE.md`. Defaults: 100 spawns a day, 1 person, $5 per million input tokens |
| `python -m fwbuild report <folder> [--depth N] [--strict] [--json]` | Method versions and findings across repos |
| `python -m fwbuild source [path]` | Validates a source and says whether it was changed with `--up` |
| `python -m fwbuild skills list` | Connected packages, their skills, which are in the pool |
| `python -m fwbuild skills add <repo> [--commit <sha>]` | Connects a repository of skills |
| `python -m fwbuild skills remove <package>` | Disconnects it and takes its skills out of the pool |

### Settings

| Setting | Effect |
|---|---|
| `CLAUDE_FRAMEWORK` | Where the source is, checked after `./framework/` and before `~/.claude/framework/` |
| `FRAMEWORK_GATEGUARD=off` | Turns the `gateguard` hook off (`0` and `false` work too) |
| `accepted` in `.claude/framework.json` | Warnings you accept, with a reason |
| `skills/pool.toml` in the source | Connected skills the coordinator may use on its own |

---

## Version 1.5.5

MIT — see [LICENSE](LICENSE).
