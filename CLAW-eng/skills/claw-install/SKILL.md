---
name: claw-install
disable-model-invocation: true
description: >
  Installs and adapts the framework in a project: detects whether the project
  is empty or already has code, runs the questionnaire, chooses the agent
  roster, generates CLAUDE.md, the active agents, the guides and the state
  files, and verifies the result. To be used once per project:
  `/claw-install`.
---

# Installing and adapting the framework

You are the coordinator: you read a project, ask questions, decide a roster, fill in content. The tooling does only the mechanical part — assembly, hashing, checks.

**You install nothing** (packages, dependencies, extensions) at any step. If something seems to be missing, you flag it and ask.

---

## Step 0 — Validate the source

`<FW>` is the source: `claw.py setup` writes its path into this skill. Where it is still literal (a skill copied by hand), take the first that **exists** of `./framework/`, `$CLAUDE_FRAMEWORK`, `~/.claude/framework/`.

```bash
python "<FW>/claw.py" source "<FW>"
```

**Exit 1 → stop:** no folders, no files — a wrong source discovered halfway leaves a project worse than a virgin one. Ask the user where the framework is. **Found but incomplete is an error, not a reason to try the next one.**

`<PRJ>` is the project root. Replace both with real paths.

## Step 1 — Detect the kind of installation

```bash
ls -A | head -50
```

- **Empty project** (or only configuration): the adaptation starts from an **idea**, which the user describes in words → Step 3.
- **Existing codebase:** the adaptation starts from the **code** → Step 2.
- **Instructions already written** — `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, `.claude/skills/`, `docs/TODO.md`, `docs/status.md`, `docs/roadmap.md` — in **both** cases → Step 2, block *Instructions already there*. They are the only files the installation can destroy: here you look whether they exist, at Step 5 you decide what to do with them.

## Step 2 — Low-cost reconnaissance

### The code — only if there is any

**Do not read the repository yourself:** delegate to `explorer`. Prompt in the mandatory structure:

```
TASK: map this repository in order to adapt a working framework.

DONE WHEN: you have delivered, in compact form:
  1. languages and stack, with versions where declared
  2. "folder → responsibility" map of the real modules (not generated ones)
  3. build, test and startup commands — taken from the configuration files, not deduced
  4. entry points
  5. presence or absence of: user interface, data pipelines,
     publication configuration, tests, documentation,
     language models, notebooks
  6. visible contracts: public APIs, persisted formats, schemas
  7. what looks relevant but is generated or third-party
  8. field signals — dependencies, files, folders that tell what kind of
     project this is — each with file:line, without classifying them

CONSTRAINTS:
  - read only, no changes
  - do not open heavy artefacts or dependency folders
  - if a command is not declared anywhere, say so instead of inventing it

DONE WHEN: the 8 points above, in compact form, with file:line where needed.
```

Large repository → several `explorer`s in parallel on disjoint subtrees: it is the only agent with free parallelism.

### Instructions already there — only if there are any

These you **read yourself**: they are few files, and judging what the framework already covers is not delegated. Read the ones listed at Step 1 and nothing else — one `.md` per folder on a large repo costs more than the whole installation.

Then show the user **one single table**:

| directive found | where | does the framework cover it? |
|---|---|---|
| one change at a time, no unrequested refactoring | `CLAUDE.md:12` | yes — `method/30-code-principles.md`, *Minimal Safe Change* |
| commit messages in English | `CLAUDE.md:40` | no |

**A "yes" is cited, not asserted:** the column carries the framework file that covers that directive. Without it, it is a statement from memory — exactly what the evidence rules forbid, and the installation cannot be the first to break them. When in doubt: "no", and it gets integrated.

On the "no" rows ask **one single question** — which ones to keep — and for those:

| the directive is about… | it goes in |
|---|---|
| anyone executing a task | project sections of `CLAUDE.md` |
| delegation, work cycle, state | project sections of `.claude/shared/orchestration.md` |
| a whole domain (data, security, style, application domain) | a guide in `.claude/shared/`, a new one if needed |
| one role only | the `## Project context` block of that agent |

They are rewritten in the **most compressed form that keeps the meaning**: these are words paid at every spawn, and a verbose imported directive costs more than it is worth. Never inside the kernel region — there the text comes from the source and the assembly at Step 5 rewrites it. A new guide must be cited by at least one agent and listed in `CLAUDE.md § Shared guides`, or it is born orphaned (`SHARED_ORPHAN`).

## Step 3 — Questionnaire

**One question at a time**, not a single block: every answer can change the following ones. Offer concrete options and a recommendation motivated by the code or by the idea.

**Proposal** — once per installation, before question 1: profile, extra agents and guides, hooks, orchestration, each with its evidence — the signals of `explorer`'s point 8 with `file:line`, or the sentence of the idea that motivates it. It sits **next to** the questions, never in their place: they are all asked, and each one confirms or corrects its part.

### Always — five questions

**1. Field of the project** → profile in `<FW>/profiles/`:

| profile | when |
|---|---|
| `software` | applications, services, command-line tools, desktop |
| `library` | libraries and packages: the public contract is the product |
| `web` | sites and applications where visual rendering is part of the product |
| `research` | the product is reproducible evidence, not software that runs |
| `data` | acquisition, transformation and indexing pipelines |
| `llm` | a language model produces text, decisions or actions that the code uses |
| `marketing` | the product has to become known: positioning, copy, images, campaigns |

A software project that also publishes content stays `software`: the marketing agents and guides are added as extras.

If none fits, ask the user to describe the field and build the roster by hand from the closest profile.

**2. Critical surface** — *"what is the critical surface of this work?"* It determines the reviewer, and **one** is activated.

The profile already declares one in `critical_surface`: it is the **field's**, known before the project. Read it to the user as a starting point, not as an answer given, and have it confirmed, narrowed or replaced — a project can have one that its field does not imply.

| answer | reviewer |
|---|---|
| **Security** — someone could abuse it | `security-reviewer` |
| **Scientific validity** — the conclusions might not hold | `scientific-reviewer` |
| **Data quality** — it might be wrong upstream | `data-quality-reviewer` |
| **Regulation and licences** — personal data, dependency licences, legal obligations | `compliance-reviewer` |
| **Performance** — only if the requirement is declared and measurable | `perf-analyst` |

Two reviewers only if the project really has two distinct critical surfaces.

**If the answer is not in the table** — public contract, accessibility, operational cost — **you do not invent an agent**: it would be a role paid by everyone for a single case. The surface is written in two places: the *Critical surface* section of `CLAUDE.md`, and `final-reviewer`'s project context, as one line of "here verified also means". Point 4 of its checklist already covers external consumers and contracts; what it does not know without that line is **which** surface, here, comes before the others.

**3. Language and assumed knowledge base.** *Language of the replies:* already fixed by `language` in `~/.claude/settings.json` or by `~/.claude/CLAUDE.md` → nothing to write. Otherwise ask, proposing the language of the user's messages or of the project's docs; with the user's ok it goes in `language` of `~/.claude/settings.json` (Claude Code's native setting: every project and session; the file is outside the project).

*Knowledge base:* what to take as known and what to introduce at first mention. Ask it like this: *"what should I take for granted that you already know, and what would you rather I explained every time?"* The answer goes in the `## This project` block of the `Reporting` style, not in `CLAUDE.md`: the form of the replies is already fixed by the style, and it only concerns the coordinator.

**4. Autonomy** — what can be done without asking. Conservative default: **none of this**. Commits · publication · installing dependencies · long or expensive runs · irreversible changes.

In the same question, **`gateguard` yes or no**: it denies the first touch of every file in a session until the facts are presented — who imports it, what public surface changes — and it costs one extra turn per file; `FRAMEWORK_GATEGUARD=off` turns it off. The other hooks in `settings.HOOKS` are always installed.

**5. Orchestration** → a file from `<FW>/orchestrations/`, **one** per project. Propose `assemble.DEFAULT_ORCHESTRATION`; name as useful for the field those in the profile's `recommended_orchestrations`, with the **When** point of their module, and the others as available. `agent-teams` is experimental and needs an interactive session: say so before the choice. It is changed later with `claw-sync` (§ Change of orchestration).

### Conditional — only for what the profile does not already install

**Ask only about agents the roster does not have.** Compute it first (Step 4) and skip the questions already settled: a question that cannot change anything teaches the user that the questionnaire is a formality.

Is there an interface? → `frontend` · Does external data come in? →
`data-ingestion` · Are there measurements to interpret? → `results-analyst` ·
Is literature or academic writing needed? → `literature` · Does the project get
published, and with simple hosting or infrastructure defined as code? →
`deploy` **or** `infra`, never both · Comments and docstrings to keep true? →
`comment-analyzer` · A guide from `<FW>/shared/` that the profile does not
bring? → extra guide · Are there heavy operations launched by the user and not
by the agent? → they go into the commands.

Regulatory constraints and performance requirements belong to **question 2**: they are critical surfaces, not contours of the profile.

## Step 4 — Plan

**Only the active is installed.** An agent not chosen stays in `<FW>/agents/`, *not yet installed*, and arrives later already up to date with `claw-sync --activate`: every file in `.claude/agents/` puts its name and `description` in the coordinator's context at every session.

**Six cannot be removed** — `explorer`, `architect`, `implementer`, `tester`, `refactorer`, `final-reviewer`: the code cycle; `--drop` ignores them.

```bash
python "<FW>/claw.py" install "<PRJ>" --profile <PROFILE> [--agents a,b] [--drop a,b] [--guides domain/x.md] [--no-gateguard] [--orchestration <name>]
```

`--agents`: the extras from the conditional questions, `skill-runner` when a skill package is connected. `--guides`: guides the profile does not bring (the ones the chosen cards cite are added by themselves). `--no-gateguard`: question 4 said no. Nothing is written: it prints roster, guides and the plan — `overwrite` and `merge` by name, `keep` for project material that stays next to the framework — and saves it. Conflicting agents, an unknown agent, guide or orchestration: an error before any plan. A `framework.json` already there: the project is installed → `claw-sync`.

**Show the plan and wait for the ok.**

## Step 5 — Generation

```bash
python "<FW>/claw.py" install "<PRJ>" --apply
```

It runs the approved plan, and only that one: `CLAUDE.md` and `.claude/shared/orchestration.md` with their kernel regions and the project skeleton, the cards, guides, reply style and state templates with their placeholders, hooks, skills (lifecycle and connected packages), `settings.json` merged over the user's (on a differing value theirs stays, and it prints it), `framework.json` with the record of every card. It ends with the list of files still carrying `[TO FILL IN`: **fill in every one now.** The `accepted` field is not written at installation: it is added by whoever decides to live with a warning (→ `claw-doctor`).

| document | kernel | who reads it | cost |
|---|---|---|---|
| `CLAUDE.md` | `<FW>/method/` | **everyone**, at every spawn | always paid |
| `.claude/shared/orchestration.md` | `<FW>/coordinator/` + orchestration + profile cycles | only whoever delegates | on demand |

**Never in `CLAUDE.md`:** routing table, work cycle, delegation rules, state levels — a `tester` or an `explorer` would pay for them at every spawn (`COORDINATOR_LEAK`). **Nor the reply style:** it is an output style, applied to the main conversation only.

### Pre-existing material — read before writing

**Nothing that was there is lost:**

- **`CLAUDE.md`:** its old content ends up in `## Pre-existing instructions`. The directives kept at Step 2 go into the project sections, the rest (commands, architecture, state, constraints) into the section it belongs to, then the section goes. What finds no place is asked about, not thrown away.
- **`docs/TODO.md`, `status.md`, `roadmap.md`:** not overwritten. Fold them into the template's structure **with their content**: a TODO deleted at installation is the first file the framework promises every session will read.
- **Skills in `.claude/skills/`:** untouched. List them in `CLAUDE.md`, one line each: a skill nobody knows they have never gets invoked.
- **`.claude/settings.json`:** merged, the user's permissions stay; the printed conflicts are shown to the user.
- **`.claude/hooks/`:** the user's scripts stay; one with a framework hook's name was named in the plan as `overwrite`. The entries are merged, never replaced.
- **`.claude/output-styles/`, or an `outputStyle` already set:** printed as a conflict. Ask which one holds; the loser stays on disk.

### `CLAUDE.md` — project sections

- `## The project` — one-line description · "path → role" map · HARD constraints (breaking them invalidates the work, not just the code) · contracts, with their consumers.
- `## Commands` — build, test, start · the agent's quick check · heavy operations the user launches, with what they report back.
- `## Critical surface` — what makes the work wrong even with perfect code, and who reviews it: from the profile's `critical_surface` and question 2; if they coincide one line, if they diverge both hold.
- `## Current state` — empty at birth: level 3 of the state.
- `## Shared guides` — generated, one line per guide from the line under its title: check it still says what the guide holds and when to open it.

### `.claude/shared/orchestration.md` — project sections

- `## This project's roster` — generated from the real roster: `| Situation | Agent | Model |`, the situation taken from each card's description; sharpen it for this project. **The columns are a contract:** the doctor reads the agent in backticks in the **second** one.
- `## Delegation notes for this project` — operations the user launches, not the agent · specific parallelism limits · when to skip a cycle step.

**Cards, guides, style** — every `## Project context`, every guide's project block, the `## This project` block of `Reporting` (question 3): each placeholder says what goes there.

**State files** — first entry and first step in `TODO.md` with today's date, first goal with its criterion in `roadmap.md`; `status.md` is born empty. Sections that may stay empty carry no placeholder.

## Step 6 — Verification

```bash
python "<FW>/claw.py" doctor --strict "<PRJ>"
```

It must print `OK — no findings` and exit 0: **as long as one finding remains, of any severity, the installation is not complete.** What each code means: skill `claw-doctor`.
