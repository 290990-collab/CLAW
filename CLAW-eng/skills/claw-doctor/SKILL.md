---
name: claw-doctor
description: >
  Checks the integrity of a framework installation: unfilled placeholders, a
  roster inconsistent with the routing table, missing guides, drift of the
  kernel region, absent state files. Use when something does not add up, after
  hand edits to the framework, or before updating it.
---

# Diagnosing an installation

```bash
python "<FW>/claw.py" doctor --strict "<PRJ>"
```

`<PRJ>` is the project root. `<FW>` is the `source` field of `.claude/framework.json` (if the file is missing, `./framework/`), relative to the project root when not absolute.

The modes `--down`, `--up`, `--upgrade`, `--repair`, `--uninstall`, `--activate`, `--deactivate` belong to `claw-sync`, they are not flags of `claw.py`.

- Complete installation → `OK — no findings`.
- **Always use `--strict`**, in CI and by hand: without it the exit code is 0 even with warnings.
- `--json` adds the measurement of `CLAUDE.md` and is **a format, not a posture**: the exit code does not change.
- **Notes** do not make `--strict` fail: they are warnings the project declares it accepts, and they stay printed (→ *Declared waivers*).

## How to read each finding

### `PLACEHOLDER` — ERROR

A `[TO FILL IN — …]` block left unfilled: the agent reading it receives instructions instead of directives. It is the **only** placeholder marker — not `{{…}}`, which is the template syntax of half the world (Vue, Angular, Jinja, Handlebars): a project quoting it among its own constraints would get an error it could not get out of.

**What to do:** fill the placeholder with the project's real directives. If the information is not there, ask the user — do not invent it.

### `ROSTER_MISSING` — ERROR

An agent is in the routing table of `.claude/shared/orchestration.md` (or of `CLAUDE.md`, if that guide is absent) but the file does not exist in `.claude/agents/`: the coordinator will delegate to something that is not there.

**What to do:** install the agent (`claw-sync --activate <name>`, which takes the current version from the master) or remove the row from the table.

### `ROSTER_ORPHAN` — WARNING

The agent's file exists but is not in the table: it costs context in every session and will never be chosen.

**What to do:** add it to the table or deactivate it (`claw-sync --deactivate <name>`). No exceptions: either the agent is superfluous, or the table is incomplete.

### `SHARED_MISSING` — ERROR

An installed file — `CLAUDE.md`, an agent, a guide — points at a guide that was not installed. A broken pointer is worse than an absent one: the agent tries and finds nothing. The finding says **which file** it starts from.

Special case: **`orchestration.md` absent** with installed agents. Without it, whoever delegates has neither the delegation rules nor the routing table, and the doctor cannot check the roster.

**What to do:** copy the guide from `<FW>/shared/` and fill in its project block, or remove the pointer. For `orchestration.md`, regenerate it by assembling `<FW>/coordinator/` and adding the project's routing table.

### `SHARED_ORPHAN` — WARNING

A guide installed in `.claude/shared/` that no file cites: context carried around and never opened, the exact inverse of `SHARED_MISSING`.

**What to do:** cite it from where it is needed — generic guides in `CLAUDE.md § Shared guides`, role guides from the agent that uses them — or remove it.

### `COORDINATOR_LEAK` — WARNING

`CLAUDE.md` contains a section of the coordinator's guide: delegation rules, work cycle, prompt template, state levels, disambiguation between agents.

**Why it matters:** `CLAUDE.md` is loaded into **every** context, every subagent's included. An `explorer` on Haiku pays for the code cycle and the four levels of state without being able to use any of it — waste on the most expensive file in the system.

**What to do:** move the section into `.claude/shared/orchestration.md`, leaving at most a one-line pointer. If the content is really needed by whoever executes, rewrite it as an execution obligation in `<FW>/method/`: that is a different thing.

⚠️ The check compares **titles**, not meaning: the same section under a different title does not trigger it. The finding covers only the six known titles; on content leakage, reading is what counts.

### `KERNEL_MISSING` — ERROR

The kernel region's markers have disappeared from a file that has one by construction — `CLAUDE.md`, `orchestration.md`, an agent. **More serious than drift:** without markers the check disappears, and a method rewritten by hand becomes indistinguishable from the generated one. It does not trigger if **no** tracked file has markers: that is the installation without tracking, and it is a choice.

**What to do:** reassemble with `claw-sync --down`, after comparing the current content with the source — inside there may be a change worth promoting.

### `KERNEL_DRIFT` — WARNING, and it is not an error

The kernel region was modified by hand. **This is information, not a fault:** the framework does not forbid modifying the method, it makes it visible.

**Ask the user, one single question:**

> "You modified the method in `<file>`. Is it an improvement that holds for all projects — so I promote it into the source — or is it a derogation specific to this project?"

- **Improvement** → `claw-sync --up`: it goes up into the source, increments the version, the next project is born with it inside.
- **Local derogation** → it is noted in the project, so the next person to read the finding knows it is deliberate.

Never "correct" a drift by overwriting it before having asked that question: you would throw away a change someone had a reason to make.

### `VERSION_MISMATCH` — WARNING

The kernel regions do not all declare the same version, or the project is on a different version from the source. **No other finding sees it:** on an old method the hash matches, because it matches the old one. It is the fork between projects, the defect the framework exists to avoid.

**What to do:** `claw-sync --down` on **both** versioned documents and on every installed agent. A gap between a single agent and the rest is normal right after an `--activate`, which takes the current master: it is closed with the same `--down`.

### `SETTINGS_MISSING` — WARNING

`.claude/settings.json` is missing with installed agents. It is the file that carries the profile's permissions — among them the prohibition on reading `.env`, keys and certificates: without it, that prohibition is not in force and nobody notices.

⚠️ **That prohibition covers the `Read` tool, not the shell.** An agent with `Bash` reads a `.env` with `cat` and no configuration prevents it. Where the secret matters, the only mechanical guard is not giving that agent the shell: it is why the reviewers that execute nothing have `Read, Grep, Glob` only.

**What to do:** regenerate it by serialising the `Profile.settings` of the project's profile — its name is in `profile` inside `.claude/framework.json` — as in Step 5 of the installation.

### `SKILLS_MISSING` — WARNING

`claw-doctor`, `claw-sync`, `claw-memory` or `claw-fair` are not in `.claude/skills/`: they exist in the source but are not invocable here. Nobody notices until they are needed, that is, when something has already gone wrong.

**What to do:** copy them from `<FW>/skills/`. No adaptation: they are framework files, copied verbatim.

### `STATE_MISSING` — ERROR

One of `docs/TODO.md`, `docs/status.md`, `docs/roadmap.md` is missing.

**What to do:** copy the missing template from `<FW>/templates/`. Without level 1, every session restarts by guessing.

### `MANIFEST_MISSING` — ERROR if the file is missing, WARNING if incomplete

`.claude/framework.json` absent, unreadable, or missing one of `source`, `version`, `profile`. It is the file that ties an installation to its source: without it `claw-sync` does not know where to update from, and `fwbuild report` does not even count the project — it disappears from the fleet report instead of showing up in it as broken.

**What to do:** rewrite it with `source.manifest(<PRJ>, <FW>, version, profile)`. The profile is the one chosen at Step 3; if nobody remembers it, deduce it from the installed agents and guides, and write it down **before** needing it again.

### `ACCEPTED_UNUSED` — WARNING

A waiver declared in `framework.json` covers no finding: either the finding is gone, or it is an ERROR (which cannot be accepted), or it is written without a reason. A waiver that does not apply stays there and next time silences something else.

**What to do:** remove it if the finding is gone, write the reason if it is missing, fix the error if it is an error.

### `FABLE` — WARNING

`model: fable`: on most plans Fable bills to usage credits, outside the plan's limits.

**What to do:** not intended → the source card's `model:` and `effort:`; intended → accept it in `framework.json`.

### `EXCLUSIVE` — ERROR

`deploy` and `infra` installed together. They cover the same space with opposite postures — simple publication versus infrastructure as code — and the overlap produces ambiguous routing.

**What to do:** choose which one really describes the project and deactivate the other.

### `TOKEN_BUDGET` — WARNING

The project sections of `CLAUDE.md` have exceeded the kernel region in words. The ceiling that breaks the build sits on the **source** and constrains only the method; the assembled `CLAUDE.md` is what every subagent pays at **every spawn**, and the part the installation writes had no threshold at all — and it is the only one that grows, because it grows with the project.

The threshold is the kernel itself, the only known quantity: *the project does not write more than the method*. It is a judgement call, not a measure of effectiveness. Below the ceiling the framework sets itself for the method alone the finding stays silent: on a small file the ratio is true and irrelevant.

**What to do:** do not cut at random. Move into `.claude/shared/` what only a few agents need, leaving the pointer; remove what the repository already says by itself (structure that can be derived, commands already in a `Makefile` or `package.json`); keep in `CLAUDE.md` only what an agent cannot deduce — hard constraints, contracts with their consumers, the critical surface. If after the cut the file stays over the threshold because the project is large, it is a warning to accept knowingly.

### `REPORT_FORMAT` — WARNING

The installed report schema still carries confidence as a percentage: previous format, fake precision in the field the coordinator reads first, while a model's self-reported confidence is poorly calibrated. No other finding sees it: the hash matches that very text, and the declared version is the one the project was born with.

**What to do:** `claw-sync --down`. The current format is categorical and carries the falsifier (`REFUTE`) with it, which is what makes a judgement without numbers readable.

### `UNSAFE_UNICODE` — WARNING

An installed file contains an invisible character: bidirectional control (U+202A–202E, U+2066–2069), zero-width space or operator (U+200B–200D, U+2060–2064), tag character (U+E0000–E007F), filler (U+115F, U+1160, U+180E, U+3164), U+FEFF past the start of the file. The model reads it, whoever reviews the file does not: it is the way a hidden instruction gets into an agent or a skill. The project's files, the skills, the hooks and `settings.json` are scanned. Variation selectors (U+FE00–FE0F, U+E0100–E01EF), which compose emoji, do not count, nor does the BOM at the start of a file, which editors write.

WARNING and not error: the ZWJ (U+200D) also composes emoji and legitimate scripts.

**What to do:** open the file at the given line with an editor that shows invisible characters. In a skill or a hook, compare it with the source in `<FW>/`: a difference nobody can explain is treated as tampering. If the character is intended, accept it with `UNSAFE_UNICODE:<file>` and the reason.

### `PERSONAL_PATH` — WARNING

An installed file contains a path inside a user's folder — `C:\Users\<name>`, `/Users/<name>`, `/home/<name>`, doubled JSON backslashes included. The file travels with the repository: on another machine the path does not exist, and it carries the name of whoever wrote it. Template placeholder names (`user`, `username`, `yourname`, `you`, `me`, `example`) do not count. The message gives file and line, not the path.

**`.claude/framework.json` is not scanned:** its `source` is absolute by construction when the source sits outside the project, because a relative path does not hold there — the depth of the clone is not known. Flagging it would give a warning on every installation made that way.

⚠️ The check compares text: a URL with `/home/` or `/Users/` in its path triggers it.

**What to do:** replace it with a path relative to the project root or with a placeholder (`<PRJ>`, `<FW>`). If the absolute path is really needed, accept it with `PERSONAL_PATH:<file>` and the reason.

## Declared waivers

A warning can be wrong **for this project**: a deliberate `KERNEL_DRIFT`, a large `CLAUDE.md` because the project is large. Without a valve `--strict` stays red forever and the team learns to ignore it — which is how a check dies.

In `.claude/framework.json`:

```json
"accepted": {
  "KERNEL_DRIFT:CLAUDE.md": "deliberate waiver: constraint X applies only here",
  "TOKEN_BUDGET": "monorepo, the contracts are in CLAUDE.md on purpose"
}
```

The key is the code, or `code:fragment` to limit it to one file. The value is the **reason, and it is mandatory**: without one the waiver does not apply and becomes `ACCEPTED_UNUSED`. The accepted finding stays printed as a `NOTE` — visible, not blocking.

**Errors cannot be accepted.** A warning is a judgement, and on a judgement a project may be right against the default; an error is an installation that does not work, and an unfilled placeholder stays unfilled even if somebody writes that it is fine.

Before adding a row here, the question is the drift one: *a waiver for this project, or a default that is wrong for everyone?* In the second case the road is `claw-sync --up`, not `accepted`.

## Several projects at once

```bash
python "<FW>/claw.py" report <folder-of-repositories>
```

`doctor` answers "does this installation hold?". `report` answers **how many versions of the method are out there, and where**: it looks for `.claude/framework.json` under the given paths (two levels, `--depth` to change that), calls the doctor on each and lines up version, findings and the size of `CLAUDE.md`.

The reference is the version of the **source** you run from, not the most widespread one: the majority is not a reference. `--strict` exits 1 if a project diverges or has findings; `--json` gives the same report for CI.

## After the diagnosis

Report to the user: how many findings by severity, what you corrected, what requires a decision from them. `KERNEL_DRIFT` findings are always listed, even when everything else is clean: they are the useful part of the report. Pure notes — waivers already decided — get one line.
