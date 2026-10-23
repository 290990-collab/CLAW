<div align="center">

<img src="assets/claw.png" alt="CLAW, an orange block with two claws, sitting cross-legged in calm focus" width="360">

# CLAW

### Let's send Claude to meditate.

*Clear mind, sharper code.*

One command gives Claude Code a method to think by and a crew of agents to build with.

[![Tests](https://github.com/290990-collab/CLAW/actions/workflows/tests.yml/badge.svg)](https://github.com/290990-collab/CLAW/actions/workflows/tests.yml)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python&logoColor=white)
![No dependencies](https://img.shields.io/badge/dependencies-none-brightgreen?style=flat-square)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)

<table>
<tr>
<td align="center" width="33%"><h3>22,000 lines</h3>a billing service and its tests, from one request<br><sub><a href="#proof">948 tests green in 2 hours</a></sub></td>
<td align="center" width="33%"><h3>16 of 16</h3>bug tickets fixed from a single prompt<br><sub><a href="#proof">checked by hidden tests</a></sub></td>
<td align="center" width="33%"><h3>91%</h3>of the build's tokens spent by the crew, not Opus<br><sub><a href="#proof">7 agents on Sonnet 5.5</a></sub></td>
</tr>
</table>

[Why](#why) · [Before / after](#before--after) · [Install](#getting-started) · [Proof](#proof) · [What's inside](#whats-inside) · [Everyday use](#everyday-use) · [Commands](#commands) · [Agents](#agents) · [FAQ](#faq)

</div>

<br>

## Why

Claude Code is the brilliant junior every team has had: quick on a small task, adrift on
a big one. It guesses what an unclear request meant. It says "done" about code it never
ran. It edits a failing test until it goes green, and it spends Opus tokens reading files
a cheaper model could read.

Claude Code ships agents, hooks and skills, and no method for using them. CLAW is the
method: the same rules and the same crew in every project, kept current from one source.
Built for long tasks and large repos, where those habits cost the most.

<br>

## Before / after

| You say | Claude Code alone, often | With CLAW |
|---|---|---|
| "Add an export" | Picks a format and builds it | Asks first: CSV or JSON, and for whom? |
| "Fix the failing test" | Edits the expected value until it is green | Fixes the cause. If the test itself is wrong, says so and fixes it in a change of its own |
| "Add a date field" | Writes a date picker by hand | Checks the repo, then the platform, and reuses your input with `type="date"` |
| "Is it done?" | "Done!" | "Done. Not verified: the migration never ran on a real database" |
| A long task | One expensive model does everything | Ask for the crew, or run `/delegate`: Opus plans and checks, the crew reads, runs and writes on cheaper models |
| "Commit and push it" | Commits and pushes | Shows what will change, then waits for your ok |

<sub>Each answer on the right is a rule in the <code>CLAUDE.md</code> that CLAW installs.</sub>

<br>

## Getting started

### Prerequisites

| You need | Why |
|---|---|
| [Claude Code](https://code.claude.com) | CLAW is a method for it |
| Python 3.11 or later | The installer and the hooks. Standard library only: no packages, no service, no account |

### Install

CLAW is a Claude Code plugin. Once per machine, in Claude Code:

```text
/plugin marketplace add 290990-collab/CLAW
/plugin install claw@claw
```

> [!TIP]
> In `/plugin` → Marketplaces, turn on auto-update for this marketplace: new releases
> arrive by themselves.

Then, in each project, open Claude Code in the project folder and run:

```text
/claw install
```

It asks five questions, shows every file it will write and waits for your ok.

> [!NOTE]
> CLAW does not run on its own. It installs files into your project (`CLAUDE.md`,
> `.claude/agents/`, `.claude/shared/`, hooks, state files) that Claude Code reads
> in every session.

<br>

## Proof

| Task | Result | Cost |
|---|---|---|
| **Build** `tally`, a B2B billing service, from one request that asked for the crew | 22,000 lines, half of them tests. 948 tests green in 2 hours. Seven `implementer` agents on Sonnet 5.5 spent 91% of the tokens; Opus, 9% | 85% of one Pro session |
| **Fix** 16 seeded bugs in `tally`, sent as 16 tickets in one prompt | 16 of 16 fixed, in both runs, checked by hidden tests | $3.89 and $5.95 |

Measured with `claude -p` on Claude Code 2.1.294 to 2.1.301, Opus 5.5 as coordinator, on
a codebase built for the eval and smaller than most production code.

<br>

## What's inside

| | What it means for you |
|---|---|
| **Evidence first** | Claude cites only what it read or ran, says what it did not check, finds the cause before fixing, and asks when a request is unclear |
| **Small, safe changes** | No unrequested refactoring, tests never weakened to go green. Commits, installs and anything irreversible wait for your ok |
| **A team sized to the task** | The coordinator knows it can delegate and decides each time on cost and effectiveness: cheaper agents read, run and execute, the top model judges. Small changes it does itself |
| **State across sessions** | `docs/TODO.md`, `docs/status.md` and `docs/roadmap.md` say where the work is; every session starts from them |
| **Safety hooks** | Claude cannot skip your git hooks or relax a linter configuration. An optional hook makes it check who uses a file before its first edit |
| **One plugin, many projects** | Update CLAW once, then bring each project up to date. Your own rules stay |

<br>

## Everyday use

| I want to… | Do this |
|---|---|
| Set up a project | In Claude Code, in the project: `/claw install` |
| Get a new CLAW release | The plugin updates (automatically, or in `/plugin`). Restart Claude Code |
| Bring a project to the new release | In Claude Code, in that project: `/claw update`. Your rules stay |
| Check that a project is healthy | `/claw fix` explains every finding and repairs it |
| Stop and resume later | Say `safe pause`. Claude writes where things are in `docs/TODO.md` |

> [!IMPORTANT]
> A project changes only when you run `/claw update` inside it, so nothing moves in a
> project you are not looking at.

<br>

## Commands

### `/claw` in Claude Code

One skill, one action at a time. `/claw` alone lists the actions.

| Action | What it does |
|---|---|
| `/claw install` | Sets up CLAW in this project |
| `/claw update` | Brings this project to the CLAW version you have. Also adds or removes an agent or guide, and changes the profile or the orchestration |
| `/claw rule` | Writes a rule of your own for this project, or for one agent |
| `/claw fix` | Checks the installation, explains every finding, regenerates what is missing |
| `/claw tune` | Adjusts each agent's model and effort to this project |
| `/claw tidy` | Finds what is stale in the to-do list and in Claude's memory of this project, and the shortcuts left in the code |
| `/claw comply <rule>` | Measures how often Claude follows a rule. Uses your tokens, so it asks first |
| `/claw uninstall` | Removes CLAW. What you adapted goes to `.claude/claw-archive/` |

Every action that writes shows its plan first and waits for your ok.

### `/delegate` in Claude Code

`/delegate <task>` makes Claude the manager of that task: it splits the work
into pieces, shows you who does each one, hands them to the agents, then checks
the results. Claude may also start it on its own for a long task, and says so.

### Checks in CI

`python claw.py doctor --strict --json <project>`, from the plugin's folder, fails on
warnings too and prints JSON.

<br>

## Agents

31 agents. A project installs only the ones its profile and your answers need.

<details>
<summary><strong>The full roster</strong>: always installed, by profile, reviewers of the critical surface</summary>

**Always installed**

| Agent | What it does |
|---|---|
| `explorer` | Finds where things live, cheaply |
| `architect` | Plans changes that cross files or contracts |
| `implementer` | Writes the planned change |
| `tester` | Tests invariants and contracts |
| `refactorer` | Cleans up the structure, behaviour unchanged |
| `final-reviewer` | Rereads the diff and reruns the tests before an important change is called done |

**Added by profile or on request**

| Agent | What it does |
|---|---|
| `api-scout` | Checks third-party APIs before code relies on them |
| `debugger` | Finds the cause of a defect nobody can explain |
| `silent-failure-hunter` | Finds swallowed errors and faults hidden behind defaults |
| `comment-analyzer` | Finds comments that no longer tell the truth |
| `conversation-analyzer` | Finds corrections that keep repeating in past sessions |
| `visual-director` | Decides how the interface looks, then checks the rendering against it |
| `frontend` | Views, components, style, motion, accessibility |
| `deploy` | Simple hosting: build, domain, secrets. Never with `infra` |
| `infra` | Infrastructure as code, environments, migrations. Never with `deploy` |
| `data-ingestion` | Pipelines that bring external data in |
| `results-analyst` | Reads measured results: is the change real, and why |
| `literature` | Finds and reads publications |
| `runner` | Runs tests, builds and logs, reports only the outcome |
| `light-implementer` | Writes code from a closed specification and its acceptance test, cheaply |
| `market-researcher` | Audience, alternatives, the promise the product keeps |
| `campaign-planner` | Channel, cadence, headline, what to measure |
| `copywriter` | Writes the copy, every claim with its proof |
| `visual-designer` | Specifies images and layouts |
| `content-analyst` | Reads the numbers after publishing |

**Reviewers of the critical surface.** `/claw install` asks what could make the
work wrong even with perfect code, and adds the matching reviewer.

| Agent | Watches for |
|---|---|
| `security-reviewer` | Someone could abuse it |
| `scientific-reviewer` | The conclusions might not hold |
| `data-quality-reviewer` | The data might be wrong upstream |
| `compliance-reviewer` | Personal data, licences, terms of use |
| `perf-analyst` | A declared performance requirement |
| `claim-reviewer` | Public claims about the product |

</details>

<br>

## Profiles

The first question of `/claw install`. It picks the extra agents, the guides and
the work cycle; `/claw update` switches it later.

| Profile | For |
|---|---|
| `software` | Applications, services, CLI and desktop tools |
| `library` | Libraries and packages: the public API is the product |
| `web` | Sites and web apps where the look matters |
| `data` | Acquisition, transformation, storage |
| `research` | The product is reproducible evidence |
| `llm` | A language model produces what the code uses |
| `marketing` | Positioning, copy, images, campaigns |

| Orchestration | How agents work together |
|---|---|
| `orchestrator-worker` (default) | The coordinator hands out work and collects reports |
| `agent-teams` | Agents message each other. Experimental, needs an interactive session |

<br>

## Talking to it

| Feature | How it works | Example |
|---|---|---|
| **Rule names** | Write a rule's name and Claude applies it to the current work. The 35 names are in [`reporting.md`](CLAW/styles/reporting.md) | `minimal change here`, `proof level?` |
| **Reference codes** | A reply with three or more findings, decisions or options numbers them | `keep D1, drop O2` |
| **Aliases** | Sent as the whole message, they rework the last reply | see below |

| Alias | You get |
|---|---|
| `scr` | The last reply, simplified and shorter |
| `foc` | Only the real signal of the last reply |
| `ref` | The last reply with reference codes |
| `eli` | The last reply explained simply |

<br>

## Your own rules

`.claude/user-rules.md` is the one file that holds them. It starts empty. Sections:
`## All` for every agent, `## <agent>` for one; in an agent's section, `model:` and
`effort:` lines override its defaults.

```text
## All
- Commit messages in English, no signature.

## tester
model: sonnet
- Run `pytest -q -x`, never the whole matrix.
```

Claude writes there only when you ask to make something a rule (`/claw rule`), and
after showing you the line. The framework files are regenerated from it; on conflict,
your rules win.

<br>

## Settings

| Setting | Effect |
|---|---|
| `language` in Claude Code's settings | The language Claude answers in. Without it, the language of your messages |
| `CLAW_GATEGUARD=off` | Turns off the optional hook that checks a file's users before its first edit |
| `accepted` in `.claude/claw.json` | Warnings of the doctor you keep on purpose, each with a reason |

`.claude/claw.json` records your choices; every framework file is regenerated from it.
To keep a warning, copy its code from the doctor's output into `accepted`:

```text
WARN  TOKEN_BUDGET      CLAUDE.md: 2400 project words against 1900 of kernel — 4300 in all, ≈5700 tokens paid at every spawn
```

```json
{
  "version": "3.0.0",
  "profile": "software",
  "orchestration": "orchestrator-worker",
  "agents": ["explorer", "architect", "implementer", "tester", "refactorer", "final-reviewer"],
  "guides": ["core/conventions.md"],
  "hooks": ["config_protection", "block_no_verify"],
  "settings_added": { "outputStyle": "Reporting" },
  "accepted": {
    "TOKEN_BUDGET": "large monorepo: CLAUDE.md is long on purpose"
  }
}
```

> [!WARNING]
> Errors cannot be accepted: they must be fixed.

<br>

## FAQ

**Does it work with Codex, Cursor or Gemini?**
No. CLAW is built on Claude Code's agents, hooks and skills.

**Does it slow Claude down?**
On a small task, yes: the method is overhead there, and plain Claude Code does it for
less. CLAW is built for the long task, where one unchecked guess costs hours.

**Will it commit, push or install anything on its own?**
Never. Commits, pushes, installs and anything irreversible wait for your ok, on a preview.

**I changed a rule for my project. Will an update overwrite it?**
No. Your rules in `.claude/user-rules.md` stay. A framework file edited by hand is regenerated, and `/claw update` names it first so you can move the edit into a rule.

<br>

## License

[MIT](LICENSE).
