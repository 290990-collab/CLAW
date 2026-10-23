# `/claw install` — setting up the framework in a project

You read the project, ask, decide the roster. The tooling generates every file from the choices; you write only the project part of `CLAUDE.md`. **Install nothing else** (packages, dependencies, extensions): flag what seems missing and ask.

## Step 0 — Python

`python --version` must print ≥ 3.11. On Windows `python` may be the Microsoft Store stub (no version, or "Python was not found"): try `py -3 --version`. None ≥ 3.11 → stop and tell the user; use the working interpreter for every command.

## Step 1 — Reconnaissance, only to make the proposal

`ls -A | head -50`. Empty project → the idea, in the user's words. Code → delegate the reading to `explorer` (a few files: read them yourself):

```
TASK: map this repository to adapt a working framework.
DONE WHEN, compact, with file:line:
  1. languages and stack, versions where declared
  2. folder → responsibility map of the real modules
  3. build, test and startup commands, from the configuration files; undeclared → say so
  4. entry points
  5. presence or absence of: user interface, data pipelines, publication configuration, tests, documentation, language models, notebooks
  6. visible contracts: public APIs, persisted formats, schemas
  7. what is generated or third-party
  8. field signals (dependencies, files, folders), unclassified
CONSTRAINTS: read only; no heavy artefacts or dependency folders.
```

Large repository → several `explorer`s on disjoint subtrees. Existing instructions (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, …) stay where they are; an existing `CLAUDE.md` becomes the project part as it is.

## Step 2 — Questions

One at a time: each answer can change the next. Offer options and a recommendation motivated by evidence. Before question 1, once, a **proposal** — profile, extras, hooks, orchestration — each with its evidence (point 8 with `file:line`, or the sentence of the idea); questions are all still asked.

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

A software project that also publishes content stays `software`, with the marketing agents and guides as extras. None fits → ask for a description and build from the closest.

**2. Critical surface** — *"what is the critical surface of this work?"* Read the profile's `critical_surface` as a starting point; the user confirms, narrows or replaces it. **One** reviewer, two only for two distinct surfaces:

| answer | reviewer |
|---|---|
| **Security** — someone could abuse it | `security-reviewer` |
| **Scientific validity** — the conclusions might not hold | `scientific-reviewer` |
| **Data quality** — it might be wrong upstream | `data-quality-reviewer` |
| **Regulation and licences** — personal data, dependency licences, legal obligations | `compliance-reviewer` |
| **Performance** — only if the requirement is declared and measurable | `perf-analyst` |

Not in the table (public contract, accessibility, operational cost): **invent no agent**. The surface goes in `## Critical surface` of the project part, and you offer a `## final-reviewer` rule of one line, "here verified also means …", through `/claw rule` — the user's yes to the offer is the explicit request.

**3. Language of the chat.** Propose the language of the user's messages; with their ok it goes in `language` of `<PRJ>/.claude/settings.local.json` (the user's file, not committed: check `.gitignore` covers it). A value in `~/.claude/settings.json` does not settle it, the project's overrides; a `~/.claude/CLAUDE.md` rule naming another language contradicts it: point it out, the user decides.

**4. Autonomy and gateguard.** What can be done without asking — commits · publication · installing dependencies · long or expensive runs · irreversible changes. Default **none**; each yes becomes a line of the project part. `gateguard` yes/no, default no: it denies the first touch of every file in a session until the facts are presented, two extra turns per file; `CLAW_GATEGUARD=off` turns it off.

**5. Orchestration** → one file of `<FW>/orchestrations/`. Propose `assemble.DEFAULT_ORCHESTRATION`; name as useful the profile's `recommended_orchestrations` with their **When** point, the others as available. `agent-teams` is experimental and needs an interactive session: say so before the choice.

**Conditional** — only for agents the roster lacks (compute it at Step 3 first; skip settled questions). Interface → `frontend`, plus `visual-director` if its look matters · external data in → `data-ingestion` · measurements to interpret → `results-analyst` · literature or academic writing → `literature` · published, with simple hosting or infrastructure as code → `deploy` **or** `infra`, never both · comments and docstrings to keep true → `comment-analyzer` · a guide of `<FW>/shared/` the profile lacks → extra guide. Regulation and performance belong to question 2. Heavy operations the user launches go in the project part's commands.

## Step 3 — Plan

Six agents cannot be removed (`explorer`, `architect`, `implementer`, `tester`, `refactorer`, `final-reviewer`): `--drop` ignores them. An agent not chosen stays in the plugin and arrives later with `/claw update --add`.

```bash
python "<FW>/claw.py" install "<PRJ>" --profile <PROFILE> [--agents a,b] [--drop a,b] [--guides domain/x.md] [--gateguard] [--orchestration <name>]
```

`--agents`: conditional extras. `--guides`: guides the profile lacks (those the chosen cards cite come by themselves). Nothing is written: it prints roster, guides and the plan — `overwrite` and `merge` by name, `keep` for what stays — and saves it. A bad name or conflicting agents: an error before any plan. A `claw.json` already there → `/claw update`. **Show the plan, wait for the ok**, then:

```bash
python "<FW>/claw.py" install "<PRJ>" --apply
```

It writes `CLAUDE.md` (kernel region on top; the existing text stays below as the project part), `.claude/shared/orchestration.md`, cards, guides, style, hooks, `settings.json` merged over the user's (a differing value of theirs stays, and it prints it), `claw.json`, an empty `.claude/user-rules.md` (an existing one is applied), and the missing `docs/` state templates. Nothing already in `docs/` is touched.

## Step 4 — The project part

Write, **outside the markers** and below any text the project already had, from the reconnaissance, in the most compressed form (every spawn pays these words):

- `## The project` — one line · path → role · HARD constraints (breaking them invalidates the work, not only the code) · contracts, with their consumers.
- `## Commands` — build, test, start, the agent's quick check, heavy operations the user launches; from the configuration files, undeclared ones left out.
- `## Critical surface` — what makes the work wrong with perfect code, and who reviews it; profile and question 2 coincide → one line.
- `## Current state` — the project's picture in a few lines (level 3 of the state); nothing built yet → one line.
- Question 4's yes's, as standing approvals.

Show the text, write it after the user's ok (Edit, between the kernel region and the user-rules region). Never ask for or invent what the repo and the user did not say.

## Step 5 — Close

`python "<FW>/claw.py" doctor --strict "<PRJ>"` must print `OK — no findings`: with any finding the installation is not complete (`/claw fix`). Mention `/claw rule` to the user in one line.
