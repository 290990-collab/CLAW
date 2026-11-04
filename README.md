<div align="center">

<img src="assets/claw.png" alt="CLAW, an orange block with two claws, sitting cross-legged in calm focus" width="396">

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

| Requirement | Purpose |
|---|---|
| [Claude Code](https://code.claude.com) | CLAW runs as a Claude Code plugin |
| Python 3.11 or later | Used by the installer and hooks. Standard library only; no extra packages or services |

### Install the plugin

Install CLAW once per machine. In Claude Code, run:

```text
/plugin marketplace add 290990-collab/CLAW
/plugin install claw@claw
```

> [!TIP]
> In `/plugin` → Marketplaces, enable auto-update for this marketplace to receive new releases automatically.

### Install CLAW in a project

Open Claude Code in the project's folder and run:

```text
/claw install
```

The installer asks five questions, previews every file it plans to write and waits for your approval.

> [!NOTE]
> CLAW does not run as a separate application. It installs project files (`CLAUDE.md`,
> `.claude/agents/`, `.claude/shared/`, hooks and state files) that Claude Code reads
> during its sessions.

<br>

## Proof

These results come from two evaluation tasks:

| Task | Result | Cost |
|---|---|---|
| **Build** a B2B billing service from one request that asked for the crew | 22,000 lines, half of them tests. 948 tests green in 2 hours. Seven `implementer` agents on Sonnet 5.5 spent 91% of the tokens; Opus, 9% | 85% of one Pro session |
| **Fix** 16 seeded bugs in that service, sent as 16 tickets in one prompt | 16 of 16 fixed, in both runs, checked by hidden tests | $3.89 and $5.95 |

In everyday work on real projects it runs the same way: Opus plans and checks, while
Sonnet and Haiku write the code, make the edits and run the commands.

Measured with `claude -p` on Claude Code 2.1.294 to 2.1.301, Opus 5.5 as coordinator, on
a 22,000-line service built for the eval.

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
| Set up a project | Run `/claw install` in Claude Code from the project folder |
| Get a new CLAW release | Update the plugin (automatically or in `/plugin`), then restart Claude Code |
| Update a project to the new release | Run `/claw update` in that project's Claude Code session. Your own rules are preserved |
| Check a project's installation | Run `/claw fix`. It explains each finding and repairs what is missing |
| Pause and resume later | Say `safe pause`. Claude records the current state in `docs/TODO.md` |

> [!IMPORTANT]
> Updating the plugin does not change projects automatically. Run `/claw update` inside
> each project when you are ready to apply the new version.

<br>

## Commands

### `/claw` in Claude Code

Run `/claw` without an action to see the available commands.

| Command | What it does |
|---|---|
| `/claw install` | Installs CLAW in the current project |
| `/claw update` | Updates the project to the installed CLAW version. Adds or removes agents and guides, and updates the profile or orchestration when needed |
| `/claw rule` | Creates a project-wide rule or a rule for one agent |
| `/claw fix` | Checks the installation, explains each finding and regenerates missing files |
| `/claw tune` | Adjusts each agent's model and effort for the project |
| `/claw tidy` | Finds stale entries in the to-do list and project memory, plus shortcuts left in the code |
| `/claw comply <rule>` | Measures how consistently Claude follows a rule. Uses your tokens, so it asks for approval first |
| `/claw uninstall` | Removes CLAW. Your customizations are moved to `.claude/claw-archive/` |

Every command that writes files previews its plan and waits for your approval.

### `/delegate` in Claude Code

Use `/delegate <task>` to have Claude coordinate a task. It breaks the work into
parts, shows who will handle each part, delegates to the agents and checks their reports.

Claude may also start delegation automatically for a long task, and will tell you when it does.

### Checks in CI

Run this command from the plugin's folder:

```text
python claw.py doctor --strict --json <project>
```

It treats warnings as failures and outputs JSON.

<br>

## Agents

CLAW provides 31 agents. Each project installs only the agents required by its profile
and your answers during setup.

<details>
<summary><strong>The full roster</strong>: always installed, profile-specific and critical-surface reviewers</summary>

**Always installed**

| Agent | Role |
|---|---|
| `explorer` | Finds relevant files and code paths |
| `architect` | Plans changes across files or interfaces |
| `implementer` | Implements the agreed change |
| `tester` | Tests invariants and contracts |
| `refactorer` | Restructures code without changing behavior |
| `final-reviewer` | Independently reviews important changes and reruns relevant tests |

**Added by profile or on request**

| Agent | Role |
|---|---|
| `api-scout` | Checks third-party APIs before code depends on them |
| `debugger` | Investigates defects whose cause is unclear |
| `silent-failure-hunter` | Finds swallowed errors and faults hidden by defaults |
| `comment-analyzer` | Finds comments that no longer match the code |
| `conversation-analyzer` | Finds recurring corrections in past sessions |
| `visual-director` | Defines the visual direction and checks the rendered result |
| `frontend` | Handles views, components, styling, motion and accessibility |
| `deploy` | Handles straightforward hosting, builds, domains and secrets. Never runs alongside `infra` |
| `infra` | Handles infrastructure as code, environments and migrations. Never runs alongside `deploy` |
| `data-ingestion` | Builds pipelines that bring in external data |
| `results-analyst` | Evaluates measured results and explains what changed |
| `literature` | Finds and reads publications |
| `runner` | Runs tests, builds and logs, then reports the outcome |
| `light-implementer` | Implements a closed specification and acceptance test at lower cost |
| `market-researcher` | Researches audiences, alternatives and product positioning |
| `campaign-planner` | Plans channels, cadence, headlines and measurements |
| `copywriter` | Writes copy and supports each claim with evidence |
| `visual-designer` | Specifies images and layouts |
| `content-analyst` | Analyzes performance data after publication |

**Reviewers for critical surfaces**

During `/claw install`, CLAW asks what could make the work fail even if the code is
correct, then adds the relevant reviewer.

| Agent | What it reviews |
|---|---|
| `security-reviewer` | Security and abuse risks |
| `scientific-reviewer` | Whether conclusions are supported |
| `data-quality-reviewer` | Whether source data may be incorrect |
| `compliance-reviewer` | Personal data, licenses and terms of use |
| `perf-analyst` | Declared performance requirements |
| `claim-reviewer` | Public claims about the product |

</details>

<br>

## Profiles

The first `/claw install` question selects a profile. It determines the additional agents,
guides and work cycle. You can change it later with `/claw update`.

| Profile | Intended for |
|---|---|
| `software` | Applications, services, CLI and desktop tools |
| `library` | Libraries and packages where the public API is the product |
| `web` | Websites and web apps where visual quality matters |
| `data` | Data acquisition, transformation and storage |
| `research` | Work where reproducible evidence is the product |
| `llm` | Systems where a language model produces output used by the code |
| `marketing` | Positioning, copy, images and campaigns |

### Orchestration modes

| Mode | How agents work |
|---|---|
| `orchestrator-worker` (default) | The coordinator assigns tasks and collects reports |
| `agent-teams` | Agents communicate with one another. Experimental; requires an interactive session |

<br>

## Talking to it

| Feature | How it works | Example |
|---|---|---|
| **Rule names** | Mention a rule to apply it to the current task. All 35 names are in [`reporting.md`](CLAW/styles/reporting.md) | `minimal change here`, `proof level?` |
| **Reference codes** | Replies with three or more findings, decisions or options are numbered | `keep D1, drop O2` |
| **Aliases** | Send an alias as your entire message to transform the previous reply | See below |

| Alias | Result |
|---|---|
| `scr` | Simplifies and shortens the previous reply |
| `foc` | Keeps only the essential information |
| `ref` | Adds reference codes to the previous reply |
| `eli` | Explains the previous reply in simpler terms |

<br>

## Your own rules

Use `.claude/user-rules.md` to store project-specific instructions. It starts empty.

Use `## All` for rules that apply to every agent and `## <agent>` for rules that apply
to one agent. Inside an agent's section, `model:` and `effort:` override that agent's
defaults.

```text
## All
- Commit messages in English, no signature.

## tester
model: sonnet
- Run `pytest -q -x`, never the whole matrix.
```

Claude writes to this file only when you ask it to create a rule with `/claw rule`,
and shows you the proposed line first. CLAW regenerates the framework files from this
source. If a project rule conflicts with a framework default, your rule takes precedence.

<br>

## Settings

| Setting | Effect |
|---|---|
| `language` in Claude Code settings | Sets Claude's response language. If unset, Claude uses the language of your messages |
| `CLAW_GATEGUARD=off` | Disables the optional hook that checks a file's importers before its first edit |
| `accepted` in `.claude/claw.json` | Stores doctor warnings you have chosen to keep, together with the reason |

`.claude/claw.json` records your setup choices. CLAW regenerates framework files from
this configuration.

To keep a warning, copy its code from the doctor's output into `accepted`:

```text
WARN  TOKEN_BUDGET      CLAUDE.md: 2400 project words against 1900 of kernel — 4300 in all, ≈5700 tokens paid at every spawn
```

Example configuration:

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
> Errors cannot be accepted; they must be fixed.

<br>

## FAQ

**Does CLAW work with Codex, Cursor or Gemini?**

No. CLAW is built specifically for Claude Code's agents, hooks and skills.

**Does CLAW slow Claude down?**

On a small task, yes: the method is overhead there, and plain Claude Code does it for
less. CLAW is built for the long task, where one unchecked assumption can cost hours.

**Can CLAW commit, push or install things on its own?**

Under CLAW's rules, no. Commits, pushes, installs and other irreversible actions require
your approval after a preview. You can add a project rule to allow specific actions, such
as local commits.

**Has CLAW been measured against Claude Code alone?**

CLAW is built for long builds, the kind that fill one context and run for hours. There
the crew takes the reading, running and writing off Opus: in the build in [Proof](#proof),
Sonnet carried 91% of the tokens. On a short task the method is a fixed cost, and Opus
alone finishes it for less.

**Will a project update overwrite my rules?**

No. Rules in `.claude/user-rules.md` are preserved. Framework files edited manually
are regenerated; `/claw update` identifies those files first so you can move your
changes into a project rule.

<br>

## License

[MIT](LICENSE).
