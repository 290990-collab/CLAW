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
<td align="center" width="33%"><h3>91%</h3>of a long build's tokens spent by the crew, not Opus<br><sub><a href="#proof">7 agents on Sonnet 5.5</a></sub></td>
<td align="center" width="33%"><h3>31 agents</h3>a project installs only the ones it needs<br><sub><a href="#agents">the full roster</a></sub></td>
<td align="center" width="33%"><h3>35 rules</h3>each with a name you can call in a message<br><sub><a href="#the-rules">real green, proof level, fail loudly…</a></sub></td>
</tr>
</table>

[Why](#why) · [Before / after](#before--after) · [Install](#getting-started) · [Proof](#proof) · [What's inside](#whats-inside) · [The rules](#the-rules) · [Principles](#principles-you-know-enforced) · [Everyday use](#everyday-use) · [Commands](#commands) · [Agents](#agents) · [FAQ](#faq)

</div>

<br>

## Why

Claude Code is a strong engineer that starts every session without a brief. When to ask
and when to pick a default, how sure to be before calling something done, what to leave
alone, which model should read the logs: it decides each time, and on a small task it
decides well. On a long task in a large repo those calls pile up, and each one made
differently from the last is one you check by hand.

Claude Code ships agents, hooks and skills, and leaves the method to you. CLAW writes
it down: the same rules and the same crew in every project, kept current from one source.
Built for long tasks and large repos, where consistency pays the most.

<br>

## Before / after

| You say | Claude Code decides case by case | With CLAW, it is a rule |
|---|---|---|
| "Add an export" | Picks a sensible format and builds it | Takes the format the repo points to and says which before building. Asks first only when a wrong guess would waste the work |
| "Fix this bug" | Fixes it, and may tidy the code around it | Fixes the bug only. Anything else it noticed goes in the report, not in the diff |
| "Fix the failing test" | Fixes it, and settles a test-versus-code disagreement on its own | Fixes the cause. If the test itself is wrong, says so and fixes it in a change of its own |
| "Is it done?" | Reports what it did | Reports what it did and how far each part is proven: "Done. Not verified: the migration never ran on a real database" |
| A long task | Works mostly in one context, on the model you picked | Ask for the crew, or run `/delegate`: Opus plans and checks, the crew reads, runs and writes on cheaper models |
| Tomorrow's session | Starts from what you tell it | Starts from `docs/TODO.md` and `docs/status.md`, where the last session left off |

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
| **Build** a B2B billing service from one request that asked for the crew | 22,000 lines, half of them tests. 948 tests green in 2 hours. Seven `implementer` agents on Sonnet 5.5 spent 91% of the tokens; Opus, 9% | 85% of one Pro session |
| **Fix** 16 seeded bugs in that service, sent as 16 tickets in one prompt | 16 of 16 fixed, in both runs, checked by hidden tests | $3.89 and $5.95 |

Measured with `claude -p` on Claude Code 2.1.294 to 2.1.301, Opus 5.5 as coordinator, on
a codebase built for the eval and smaller than most production code.

<br>

## What's inside

| | What it means for you |
|---|---|
| **Evidence first** | Claude cites what it read or ran, says what it did not check, finds the cause before fixing, and asks only when a wrong guess would cost you |
| **Small, safe changes** | No unrequested refactoring; a failing test gets its cause fixed, not its assertion loosened. Commits, installs and anything irreversible wait for your ok |
| **A team sized to the task** | The coordinator knows it can delegate and decides each time on cost and effectiveness: cheaper agents read, run and execute, the top model judges. Small changes it does itself |
| **Handoffs that close the exits** | Every delegation names the shortcuts a pressed agent would take: a plan instead of the change, a check that never ran, a fix that holds only on the example. Named, they are off the table |
| **Reviews without false alarms** | A reviewer tries to disprove a suspicion before reporting it. "What if a null arrives here?" counts only if something can pass one |
| **Guides that load on demand** | Security, architecture, testing, debugging, performance: each guide opens when the task enters its domain, and stays closed otherwise |
| **State across sessions** | `docs/TODO.md`, `docs/status.md` and `docs/roadmap.md` say where the work is; every session starts from them. A box is ticked only with the command and its outcome next to it |
| **A memory that corrects itself** | One episode is a case, two independent ones a pattern. When an old memory and the repo disagree, the repo wins |
| **Safety hooks** | Claude cannot skip your git hooks or relax a linter configuration. An optional hook makes it look up who imports a file before its first edit: "are you sure?" always gets a yes, a search does not |
| **One plugin, many projects** | Update CLAW once, then bring each project up to date. Your own rules stay |

<br>

## The rules

Each rule has a name. Write it in a message, `real green here`, and Claude applies it
to the work at hand. A selection of the 35, all in [`reporting.md`](CLAW/styles/reporting.md):

| Rule | What Claude does |
|---|---|
| `proof level` | Says how far each claim is proven, from 1, "I said so", to 5, "reproduced on the real system". A check that decided nothing is called inconclusive, never green |
| `verified sources` | Cites no API, version, number or file it has not read or run in this session |
| `real green` | Never makes a check pass by weakening it: no deleted test, no loosened assertion, no `noqa`. A wrong check is fixed in a change of its own |
| `useful test` | Writes a test only if it knows which defect would make it fail |
| `rigorous debugging` | Fixes nothing until one cause explains every symptom, and undoes whatever a refuted hypothesis motivated |
| `minimal change` | Makes the smallest complete change, fixing the cause once, where it lives |
| `existing pattern` | Before new code, climbs a ladder: the repo, the standard library and the platform, the installed dependencies. New code comes last |
| `contract first` | Finds every consumer before changing an interface, and every copy before changing a written rule |
| `fail loudly` | Swallows no error and invents no default to keep going |
| `strict scope` | Does the task and only the task. What else it noticed goes in the report |
| `open request` | Asks only when a wrong guess would waste the work; otherwise takes the safest reading and says which |
| `don't ask, run it` | Never asks you what a command can answer. Behaviour, timing, output: it runs and looks |
| `blame the instrument` | An empty search, or a check that passes too easily, makes it doubt the search before the code |
| No self-approval | No agent judges its own work. Each closes with the same report, confidence, what would refute it, what it assumed, what it did not verify, and the coordinator decides. `final-reviewer` rereads important changes from scratch |

<details>
<summary><strong>The other 22</strong></summary>

| Rule | What Claude does |
|---|---|
| `outside the mandate` | Makes a choice that is cheap to undo and says so; brings you an expensive one, with the options |
| `stop criterion` | Starts no task without a verifiable finish line. It derives one and states it, and asks only when that would mean guessing the goal |
| `zero redundancy` | Green and nothing changed: it does not run the suite again |
| `hypotheses vs facts` | Keeps what it deduced apart from what it verified, on the page too |
| `honesty` | Says "I don't know" and "this is wrong". Never agrees with you against the evidence |
| `which decision` | Citing a rule means naming what it changed. A rule quoted for decoration does not count |
| `kiss` | The simplest solution for today's requirement, never by cutting validation, error handling, security or accessibility |
| `do it yourself` | A small change is usually cheaper done directly than delegated |
| `model to the task` | Picks agent and model for the task in front of it, not for the job title |
| `declared selection` | Runs the same work twice only after saying how it will pick the winner |
| `proportionate review` | `final-reviewer` on the critical surface and important tasks; a double review only when you ask |
| `skipped step` | A step left out stays written, with its reason. Assessed and forgotten stay different |
| `tick with evidence` | A box closes with the command and the outcome next to it |
| `safe pause` | Stops at a clean boundary and leaves a note for whoever picks up |
| `pickup` | Reads the trail the last session left instead of redoing it |
| `promote when it repeats` | One case is not a rule; two independent ones are a pattern |
| `two shapes` | The `architect` puts two structurally different options on the table before choosing |
| `plan that does not hold` | An `implementer` that keeps hitting friction reports it instead of quietly redesigning |
| `reader load` | A refactoring that does not make the code easier to read is undone |
| `not a finding` | A review drops preferences, hypotheses with no caller and abstractions nobody asked for |
| `impractical test-first` | When a test cannot come first, says so and names the nearest check that can run |
| `repro before the fix` | In the history, the failing repro lands before the fix |

</details>

<br>

## Principles you know, enforced

The names you learned on the job. CLAW does not recite them: it makes Claude work by
them, from the method it reads every session and the guides it opens when a task needs them.

| Principle | What Claude does |
|---|---|
| **YAGNI** | No abstraction, option or parameter for a need that does not exist yet. In review, an abstraction without a second use case is the defect |
| **KISS** | The simplest solution for today's requirement, in the style of the file it lands in |
| **The Boy Scout rule** | Overruled on purpose. The campsite stays as it was: what Claude would tidy goes in the report, and your diff holds only the task |
| **Chesterton's fence** | Code that looks dead is searched for before it goes, and a deliberate removal is recorded so nobody brings it back |
| **Single source of truth** | One copy of each fact is authoritative. Caches, indexes and aggregates are derived and can be rebuilt |
| **Fail fast** | Missing configuration stops the program at startup. No swallowed exception, no invented default |
| **Fail closed** | A security check that errors out denies the action. Authorisation is checked server-side, per object, on every path |
| **Least privilege** | On files, roles and tokens. Input is validated at the boundary against an allowlist, and rejected, not cleaned up |
| **Make illegal states unrepresentable** | States are a closed set the compiler checks, never flags that combine into impossible ones |
| **Clean functions** | One level of abstraction per function, early returns, no boolean argument that switches behaviour, queries kept apart from commands |
| **Dependency inversion** | Domain logic knows nothing of the UI, the database or the transport. A rule that needs a server to be tested is coupled to a detail |
| **Property-based thinking** | Invariants before examples: idempotence, round-trip, conservation, monotonicity |
| **Regression test first** | The repro that failed comes before the fix, and proves the bug is gone |
| **Bisection** | Halves the input, the history or the path. Holds two hypotheses and looks for the observation that separates them |
| **Measure, don't guess** | No speed claim without a measurement: p50, p95 and p99 over several runs, never one average |

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
Not under CLAW's rules: commits, pushes, installs and anything irreversible wait for your
ok, on a preview. A rule of your own can allow some of them, such as local commits.

**Is it measured against Claude Code alone?**
Not yet. The runs in [Proof](#proof) show what a CLAW session delivers and what it
costs. The same tasks without CLAW are the next runs, and their results will go here.

**I changed a rule for my project. Will an update overwrite it?**
No. Your rules in `.claude/user-rules.md` stay. A framework file edited by hand is regenerated, and `/claw update` names it first so you can move the edit into a rule.

<br>

## License

[MIT](LICENSE).
