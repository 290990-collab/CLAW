---
name: framework-install
description: >
  Installs and adapts the framework in a project: detects whether the project
  is empty or already has code, runs the questionnaire, chooses the agent
  roster, generates CLAUDE.md, the active agents, the guides and the state
  files, and verifies the result. To be used once per project:
  `/framework-install`.
---

# Installing and adapting the framework

You are the coordinator: you read a project, ask questions, decide a roster, fill in content. The tooling does only the mechanical part — assembly, hashing, checks.

**You install nothing** (packages, dependencies, extensions) at any step. If something seems to be missing, you flag it and ask.

---

## Step 0 — Find and validate the source

The source lives in one of these places, **in this order**: `./framework/` (copied into the project), `$CLAUDE_FRAMEWORK`, `~/.claude/framework/`. Take the **first that exists** — not the first that works — and validate it:

```bash
cd <FW>/tools && python -m fwbuild source ..
```

It prints root, version and the state of the upstream record, or what is missing and exits 1.

**If it exits 1, stop here:** no folders, no files — a wrong source discovered halfway leaves a project worse than a virgin one. Ask the user where the framework is and retry with that path. **Found but incomplete is an error, not a reason to try the next one.**

From here `<FW>` is the validated root and `<PRJ>` the project root: replace them with the real paths, do not leave them literal.

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

**3. Assumed knowledge base** — what to take as known and what to introduce at first mention. Ask it like this: *"what should I take for granted that you already know, and what would you rather I explained every time?"* The answer goes in the `## This project` block of the `Reporting` style, not in `CLAUDE.md`: the form of the replies is already fixed by the style, and it only concerns the coordinator.

**4. Autonomy** — what can be done without asking. Conservative default: **none of this**. Commits · publication · installing dependencies · long or expensive runs · irreversible changes.

In the same question, **`gateguard` yes or no**: it denies the first touch of every file in a session until the facts are presented — who imports it, what public surface changes — and it costs one extra turn per file; `FRAMEWORK_GATEGUARD=off` turns it off. The other hooks in `settings.HOOKS` are always installed.

**5. Orchestration** → a file from `<FW>/orchestrations/`, **one** per project. Propose `assemble.DEFAULT_ORCHESTRATION`; name as useful for the field those in the profile's `recommended_orchestrations`, with the **When** point of their module, and the others as available. `agent-teams` is experimental and needs an interactive session: say so before the choice. It is changed later with `framework-sync` (§ Change of orchestration).

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

## Step 4 — Roster and selective installation

**Only the active is installed.** The master stays in `<FW>/agents/`: an agent not chosen is not deleted, it is *not yet installed*, and it is added later already up to date with `framework-sync --activate`. Reason: the name and `description` of every file in `.claude/agents/` enter the coordinator's context in every session.

**Six cannot be removed** — `explorer`, `architect`, `implementer`, `tester`, `refactorer`, `final-reviewer`: they are the code cycle, and `drop` ignores them on purpose. Everything else is optional and comes back with `--activate`.

The commands start from `<FW>/tools`: there the framework root is `..`, the project's is `<PRJ>`.

```bash
cd <FW>/tools && python -c "
from pathlib import Path
from fwbuild import profile
prof = profile.load(Path('../profiles/<PROFILE>.toml'))
r = profile.roster(prof, extras=[], drop=[])
print(r)
print('conflicts:', profile.check_exclusive(r))
print('guides:', profile.guides(Path('..'), prof, r, extras=[]))
"
```

`guides` joins the profile's guides, those the chosen cards cite and the extras from the conditional questions; an extra that does not exist is a `FileNotFoundError`, not one guide fewer.

## Step 5 — Generation

**Two** documents with a kernel region are generated, not one. The difference is the recipient:

| document | kernel source | who reads it | cost |
|---|---|---|---|
| `CLAUDE.md` | `<FW>/method/` | **everyone**, at every spawn | always paid |
| `.claude/shared/orchestration.md` | `<FW>/coordinator/` | only whoever delegates | on demand |

**Never in `CLAUDE.md`:** the routing table, the work cycle, the delegation rules, the state levels. They are instructions a `tester` or an `explorer` pays for at every spawn without being able to use them, and the doctor detects them (`COORDINATOR_LEAK`).

### Pre-existing material — read before writing

It holds everywhere, but this is where things get lost: **none of these files is overwritten before being read.**

**Before the first file is written, the plan and the user's ok:**

```bash
cd <FW>/tools && python -c "
import sys
from pathlib import Path
from fwbuild import lifecycle
sys.stdout.reconfigure(encoding='utf-8')
ops = lifecycle.plan_install(Path('<PRJ>'), lifecycle.targets(Path('..'), <ROSTER>, <GUIDES>, <HOOKS>))
print(lifecycle.render(ops))
print(*(f'keep        {o.path} — {o.reason}' for o in ops if o.action == 'keep'), sep='\n')
"
```

`<HOOKS>` is `settings.HOOKS`, without `gateguard` if question 4 said no. `overwrite` and `merge` are read by name; `keep` is project material that will stay next to the framework. A `ValueError` on an existing `framework.json`: the project is already installed → `framework-sync`.

- **A `CLAUDE.md` that was already there:** its content is project material. The directives kept at Step 2 go into the project sections, the rest (commands, architecture, state, constraints) into the section it belongs to. Only then do you write the new file, which now contains the old one too. Whatever finds no place is asked about, not thrown away.
- **`docs/TODO.md`, `status.md`, `roadmap.md` that were already there:** you fill in the template **with their content**, instead of copying the empty one over them. A TODO deleted at installation is the first file the framework promises every session will read.
- **Skills already in `.claude/skills/`:** they are not touched and not moved. List them in `CLAUDE.md` next to the lifecycle ones, one line each: a skill nobody knows they have never gets invoked.
- **A `.claude/settings.json` that was already there:** the permissions inside it are the user's, and serialising `Profile.settings` over them deletes them. It is merged with `settings.merge`: lists are joined, on a differing scalar theirs stays and the key goes into the conflicts, which are shown before writing.
- **Hooks already in `.claude/hooks/`, or `hooks` entries in the settings:** they are the user's. The scripts stay; one with the name of a framework hook shows up as `overwrite` and is asked about. The entries are merged with the framework's, never replaced.
- **Output styles already in `.claude/output-styles/`, or an `outputStyle` already written in the settings:** the user has already chosen how they want to be spoken to. Show it next to `Reporting` and ask which one holds; the loser stays on disk, it is not deleted.

### `CLAUDE.md` — project sections

```
[KERNEL REGION from <FW>/method/]

## The project
one-line description · "path → role" map · HARD constraints (violating them
invalidates the work, not just the code) · contracts, with their consumers

## Commands
build, test, startup · quick check the agent runs · heavy operations the user
launches, with what they must report back

## Critical surface
what the critical surface is — what makes the work wrong even with perfect
code — and who reviews it. It starts from `prof.critical_surface` and from the
answer to question 2: if they coincide you write one line, if they diverge both
hold

## Current state
empty at birth — it is level 3 of the self-updating state

## Shared guides
first line: `orchestration.md`, only for the coordinator and first if the
session delegates. Then **one line per installed guide**: what it holds — copied
from the line under the guide's title, not invented — and when to open it. A
list of bare paths is not usable: to decide whether to open a guide you would
already have to know what is inside
```

**The reply style does not live here.** It is an output style — `.claude/output-styles/` — and Claude Code applies it **to the main conversation only**: a subagent runs on its own system prompt. Writing it into `CLAUDE.md` would have it paid at every spawn by those who never talk to the user.

### `.claude/shared/orchestration.md` — project sections

```
[KERNEL REGION from <FW>/coordinator/]

## This project's roster
table GENERATED from the real roster, never copied: | Situation | Agent | Model |
one row per installed agent, none excluded.
**The columns are a contract**, not a matter of style: the doctor reads the
agent name in backticks in the **second** one. Swapping them produces an
all-orphan roster and names that do not exist

## Delegation notes for this project
operations the user launches and not the agent · specific parallelism
constraints · when to skip a step of the cycle
```

### Assembly

```bash
cd <FW>/tools && python -c "
from pathlib import Path
from fwbuild import assemble
F = Path('..'); V = (F/'VERSION').read_text(encoding='utf-8').strip()
P = Path('<PRJ>')
for d in ('.claude/shared', '.claude/agents', '.claude/skills', '.claude/output-styles', '.claude/hooks', 'docs'):
    P.joinpath(d).mkdir(parents=True, exist_ok=True)
P.joinpath('CLAUDE.md').write_text(
    assemble.build_document(F/'method', V, PROJECT_SECTIONS), encoding='utf-8')
ORCH = '<ORCHESTRATION>'; CYCLES = [<profile cycles>]
P.joinpath('.claude/shared/orchestration.md').write_text(
    assemble.build_document(F/'coordinator', V, ROSTER_SECTIONS,
        extra=[assemble.orchestration_file(F, ORCH), *assemble.cycle_files(F, CYCLES)]),
    encoding='utf-8')
"
```

**Active agents** — for each one: read the source with `assemble.split_source`, **fill in the `## Project context` block** with the specific directives (every placeholder declares what to put there), reassemble with `assemble.build_agent`, write into `.claude/agents/`.

**Orchestration and domain cycles** — the module from question 5, then the cycles if the profile declares `cycles`, are appended **in this order** to the kernel region of the coordinator's guide: `--down` passes them again the same way. They are orchestration, not execution, so never in `CLAUDE.md`.

**Guides** — copy from `<FW>/shared/` the list from `profile.guides` at Step 4, filling in the project block there too. An extra agent brings its own: without them the card goes out with a dead pointer that the doctor sees only once the installation is already written (`SHARED_MISSING`).

**Lifecycle skills** — copy `<FW>/skills/framework-doctor`, `framework-sync` and `framework-memory` into `.claude/skills/`. Without them they are not invocable and the doctor flags it (`SKILLS_MISSING`).

**Skills of the connected packages** — `skills.installed(F)` says which ones there are (empty is the normal case). They are copied **flattened**, from `<FW>/skills/<package>/<skill>/` to `.claude/skills/<skill>/`: Claude Code does not discover a skill nested any deeper. With a package connected, `skill-runner` is to be activated as well — the only agent that may invoke them.

**Reply style** — copy `<FW>/output-styles/reporting.md` into `.claude/output-styles/` and **fill in the `## This project` block** with the answer to question 3. Left unfilled it is a `PLACEHOLDER`: the doctor reads every `.md` under `.claude/` except the skills.

**Hooks** — copy `<FW>/hooks/<name>.py` into `.claude/hooks/` for every name in `<HOOKS>`. An entry in the settings without its script, for a closed hook, blocks every edit or every command.

**`.claude/settings.json`** — profile and hooks together first, then on top of whatever was there (→ *Pre-existing material*):

```python
fw_settings, _, c = settings.merge(prof.settings, settings.hooks(<HOOKS>))   # c not empty: a defect in the source, stop
fw_settings, _, c = settings.merge(fw_settings, settings.ORCHESTRATION_SETTINGS.get('<ORCHESTRATION>', {}))   # same
fw_settings, _, c = settings.merge(fw_settings, skills.overrides(F))   # the pool: outside it, they stay with the user
merged, added, conflicts = settings.merge(<existing settings.json, or {}>, fw_settings)
```

`conflicts` are shown before writing `merged`. It carries `outputStyle`, the name of the style just copied: without it the file is installed and nobody selects it.

**`.claude/framework.json`** — `source`, `version`, `profile`: it is how the two skills find the source again, and the only place that records **what** the installation is made of. Without the profile, "regenerate the permissions of the project's profile" cannot be carried out. `settings_added` is `added`: the only piece of `settings.json` that `framework-sync --uninstall` will be able to remove. The shape **is not written by you**: `source.manifest` makes the path relative when the source sits inside the project and absolute only when it sits outside — an absolute path to an internal source is the machine of whoever installed it, and it dies at the first clone.

```python
source.manifest(PRJ, FW, version, prof.name, settings_added=added, skills=skills.installed(FW))
```

`skills` is `skill name → package`: in the project the package skills all sit at one level, and without this line the doctor cannot say which package is missing.

The `accepted` field **is not written at installation**: it is born empty and is added by whoever decides to live with a warning (→ `framework-doctor` skill).

**State files** — copy the three templates into `docs/` and fill in every `[TO FILL IN — …]` block **immediately**: first entry and first step in `TODO.md` with today's date, first goal with its criterion in `roadmap.md`. `status.md` is born empty by construction — you write in it when something closes. The sections that may legitimately stay empty (waiting, blocked, open decisions) carry no placeholder: they already hold the right text, and it is replaced when there is something. It must be done here: at Step 6 a residual placeholder is a `PLACEHOLDER`, and `TODO.md` is the file every future session reads first.

**No `@import`:** the kernel is concatenated physically.

## Step 6 — Verification

```bash
cd <FW>/tools && python -m fwbuild doctor --strict <PRJ>
```

It must print `OK — no findings` and exit 0. `--strict` makes the rule mechanical: **as long as one finding remains, of any severity, the installation is not complete.** What each code means: skill `framework-doctor`.
