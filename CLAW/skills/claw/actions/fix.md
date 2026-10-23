# `/claw fix` — diagnose, then put back what is missing

First the diagnosis; then, if files are missing, the regeneration (last section).

```bash
python "<FW>/claw.py" doctor --strict "<PRJ>"
```

- Complete installation → `OK — no findings`.
- **Always use `--strict`**, in CI and by hand: without it the exit code is 0 even with warnings.
- `--json` adds the measurement of `CLAUDE.md` and is **a format, not a posture**: the exit code does not change.
- **Notes** do not make `--strict` fail: they are warnings the project declares it accepts, and they stay printed (→ *Declared waivers*).

## How to read each finding

### `ROSTER_MISSING` — ERROR

An agent is in `agents` of `claw.json` (the roster table is generated from it) but its file is not in `.claude/agents/`: the coordinator will delegate to something that is not there.

**What to do:** `update --keep-version` regenerates the card; dropped on purpose → `/claw update --remove <name>`.

### `SHARED_MISSING` — ERROR

An installed file — `CLAUDE.md`, an agent, a guide — points at a guide that was not installed. A broken pointer is worse than an absent one: the agent tries and finds nothing. The finding says **which file** it starts from.

Special case: **`orchestration.md` absent** with installed agents. Without it, whoever delegates has neither the delegation rules nor the routing table, and the doctor cannot check the roster.

**What to do:** a guide of the roster or cited by one of its cards, and `orchestration.md`: `update --keep-version` regenerates them. A pointer to a guide outside the roster (written in the project part or a rule): `/claw update --add <core/x.md>`, or remove the pointer.

### `SHARED_ORPHAN` — WARNING

A guide installed in `.claude/shared/` that no file cites: context carried around and never opened, the exact inverse of `SHARED_MISSING`.

**What to do:** in the roster → `/claw update --remove <path>`. One the user wrote: cite it from a rule (`/claw rule`) or delete it.

### `COORDINATOR_LEAK` — WARNING

`CLAUDE.md` contains a section of the coordinator's guide: delegation rules, work cycle, prompt template, state levels, disambiguation between agents.

**Why it matters:** `CLAUDE.md` is loaded into **every** context, every subagent's included. An `explorer` on Haiku pays for the code cycle and the four levels of state without being able to use any of it — waste on the most expensive file in the system.

**What to do:** delete the section: `orchestration.md` is generated and already carries the coordinator's guide. If whoever executes really needs a piece of it, it becomes a one-line rule (`/claw rule`).

⚠️ The check compares **titles**, not meaning: the same section under a different title does not trigger it. The finding covers only the eight known titles; on content leakage, reading is what counts.

### `KERNEL_MISSING` — ERROR

The kernel region's markers have disappeared from `CLAUDE.md`. Without them nobody can tell the framework's text from the project's, and `update` refuses.

**What to do:** put the pair back around the framework's text — `<!-- FRAMEWORK:KERNEL v<any> — generated — edit .claude/user-rules.md instead -->` before it, `<!-- /FRAMEWORK:KERNEL -->` after it (an empty pair on top if the text is gone) — then `update --keep-version`: the region is rewritten, the project part stays. A line of the old region worth keeping goes into `user-rules.md` first.

### `VERSION_MISMATCH` — WARNING

The kernel regions do not all declare the same version, or the project is on a different version from the source. **No other finding sees it:** an old method is consistent with itself. It is the fork between projects, the defect the framework exists to avoid.

**What to do:** `/claw update`: it regenerates `CLAUDE.md`, `orchestration.md` and every card together. The plugin older than the project → update the plugin first (`actions/update.md` § 1).

### `SETTINGS_MISSING` — WARNING

`.claude/settings.json` is missing with installed agents. It is the file that carries the profile's permissions — among them the prohibition on reading `.env`, keys and certificates: without it, that prohibition is not in force and nobody notices.

⚠️ **That prohibition covers the `Read` tool, not the shell.** An agent with `Bash` reads a `.env` with `cat` and no configuration prevents it. Where the secret matters, the only mechanical guard is not giving that agent the shell: it is why the reviewers that execute nothing have `Read, Grep, Glob` only.

**What to do:** `update --keep-version` rebuilds the whole file (profile permissions, hooks, orchestration variables, spawn depth) and updates `settings_added`; across versions, `update` with plan and ok.

### `HOOKS_MISSING` — ERROR if a wired script is gone, WARNING if not wired

`config_protection` and `block_no_verify` belong to every installation with agents. **Not wired** in `settings.json`: the checks they make are off and nothing else says so — the typical case is an installation born before the hooks. **Wired without its script:** the closed hook blocks every command it has something to say about (`git` for `block_no_verify`, a linter configuration for `config_protection`). `gateguard` is optional: not wired, it is not flagged; wired without its script, it is flagged like the others.

**What to do:** not wired, or script gone → `update --keep-version` (see *Regeneration*), which wires them and puts the script back.

### `STATE_MISSING` — ERROR

One of `docs/TODO.md`, `docs/status.md`, `docs/roadmap.md` is missing.

**What to do:** copy the missing template from `<FW>/templates/`. Without level 1, every session restarts by guessing. `update` creates a missing one too.

### `MANIFEST_MISSING` — ERROR if the file is missing, WARNING if incomplete

`.claude/claw.json` absent, unreadable, or missing one of `version`, `profile`, `orchestration`, `agents`, `guides`, `hooks`. It holds the installation's choices: without it `/claw update` does not know what to generate, and `report` does not count the project.

**What to do:** rewrite it from what is installed — profile and orchestration as the user remembers them, else deduced from the agents and guides in `.claude/` — with `version` that of the files' kernel marker. Then `update --keep-version` regenerates from it; read the plan if it is refused.

### `ACCEPTED_UNUSED` — WARNING

A waiver declared in `claw.json` covers no finding: either the finding is gone, or it is an ERROR (which cannot be accepted), or it is written without a reason. A waiver that does not apply stays there and next time silences something else.

**What to do:** remove it if the finding is gone, write the reason if it is missing, fix the error if it is an error.

### `RULES_UNKNOWN` — WARNING

`.claude/user-rules.md` holds something nobody reads: a `## <name>` section that is neither `## All` nor an agent of `claw.json`, text before the first section, or a file that does not parse (a section twice, `model:`/`effort:` under `## All`). One finding each, naming what and where. The rule its author believes in is not in force.

**What to do:** fix the name (a typo, or an agent that was removed), put the loose text under a section, resolve the duplicate. Do not guess the intent: ask the user, then `update --keep-version` regenerates.

### `GENERATED_DIFF` — WARNING

At the version that wrote the installation, a generated file differs from what the source generates from the current `user-rules.md`. Two causes: the file was edited by hand, or `user-rules.md` changed and nobody regenerated. For `CLAUDE.md` only the two framework regions count.

**What to do:** ask which it is. A hand edit that must stay goes into `user-rules.md` first, because the regeneration overwrites the file. Then `update` with plan and ok: the plan names every overwrite.

### `FABLE` — WARNING

`model: fable`: on most plans Fable bills to usage credits, outside the plan's limits.

**What to do:** not intended → remove the `model:` line from the agent's section of `user-rules.md` (or the hand edit), then `update --keep-version`; intended → accept it in `claw.json`.

### `EXCLUSIVE` — ERROR

`deploy` and `infra` installed together. They cover the same space with opposite postures — simple publication versus infrastructure as code — and the overlap produces ambiguous routing.

**What to do:** choose which one really describes the project and deactivate the other.

### `TOKEN_BUDGET` — WARNING

The project sections of `CLAUDE.md` have exceeded the kernel region in words. The ceiling that breaks the build sits on the **source** and constrains only the method; every subagent pays the whole assembled `CLAUDE.md` at **every spawn**, and the part the installation writes has no other threshold and is the only one that grows with the project.

The threshold is the kernel itself, the only known quantity: *the project does not write more than the method*. It is a judgement call, not a measure of effectiveness. Below the ceiling the framework sets itself for the method alone the finding stays silent: on a small file the ratio is true and irrelevant.

**What to do:** do not cut at random. Move into `.claude/shared/` what only a few agents need, leaving the pointer; remove what the repository already says by itself (structure that can be derived, commands already in a `Makefile` or `package.json`); keep in `CLAUDE.md` only what an agent cannot deduce — hard constraints, contracts with their consumers, the critical surface. If after the cut the file stays over the threshold because the project is large, it is a warning to accept knowingly.

### `UNSAFE_UNICODE` — WARNING

An installed file contains an invisible character: bidirectional control (U+202A–202E, U+2066–2069), zero-width space or operator (U+200B–200D, U+2060–2064), tag character (U+E0000–E007F), filler (U+115F, U+1160, U+180E, U+3164), U+FEFF past the start of the file. The model reads it, whoever reviews the file does not: it is the way a hidden instruction gets into an agent or a skill. The project's files, the skills, the hooks and `settings.json` are scanned. Variation selectors (U+FE00–FE0F, U+E0100–E01EF), which compose emoji, do not count, nor does the BOM at the start of a file, which editors write.

WARNING and not error: the ZWJ (U+200D) also composes emoji and legitimate scripts.

**What to do:** open the file at the given line with an editor that shows invisible characters. In a skill or a hook, compare it with the source in `<FW>/`: a difference nobody can explain is treated as tampering. If the character is intended, accept it with `UNSAFE_UNICODE:<file>` and the reason.

### `PERSONAL_PATH` — WARNING

An installed file contains a path inside a user's folder — `C:\Users\<name>`, `/Users/<name>`, `/home/<name>`, doubled JSON backslashes included. The file travels with the repository: on another machine the path does not exist, and it carries the name of whoever wrote it. Template placeholder names (`user`, `username`, `yourname`, `you`, `me`, `example`) do not count. The message gives file and line, not the path.

⚠️ The check compares text: a URL with `/home/` or `/Users/` in its path triggers it.

**What to do:** replace it with a path relative to the project root or with a placeholder (`<PRJ>`, `<FW>`). If the absolute path is really needed, accept it with `PERSONAL_PATH:<file>` and the reason.

## Declared waivers

A warning can be wrong **for this project**: a large `CLAUDE.md` because the project is large. Without a valve `--strict` stays red forever and the team learns to ignore it — which is how a check dies.

In `.claude/claw.json`:

```json
"accepted": {
  "PERSONAL_PATH:.claude/settings.json": "deliberate: the path is the same on every machine of the team",
  "TOKEN_BUDGET": "monorepo, the contracts are in CLAUDE.md on purpose"
}
```

The key is the code, or `code:fragment` to limit it to one file. The value is the **reason, and it is mandatory**: without one the waiver does not apply and becomes `ACCEPTED_UNUSED`. The accepted finding stays printed as a `NOTE` — visible, not blocking.

**Errors cannot be accepted.** A warning is a judgement, and on a judgement a project may be right against the default; an error is an installation that does not work, and a missing file stays missing even if somebody writes that it is fine.

Before adding a row here, the question is: *a waiver for this project, or a default that is wrong for everyone?* In the second case the road is a change in the framework's repository, not `accepted`.

## Several projects at once

```bash
python "<FW>/claw.py" report <folder-of-repositories>
```

`doctor` answers "does this installation hold?". `report` answers **how many versions of the method are out there, and where**: it looks for `.claude/claw.json` under the given paths (two levels, `--depth` to change that), calls the doctor on each and lines up version, findings and the size of `CLAUDE.md`.

The reference is the version of the **source** you run from, not the most widespread one: the majority is not a reference. `--strict` exits 1 if a project diverges or has findings; `--json` gives the same report for CI.

## After the diagnosis

Report to the user: how many findings by severity, what you corrected, what requires a decision from them. Pure notes — waivers already decided — get one line.

---

## Regeneration — putting back what is missing

`python "<FW>/claw.py" update "<PRJ>" --keep-version` regenerates every framework file from `claw.json` and `user-rules.md`, in one call. It applies at once, and refuses when the plugin is at another version or a plan line overwrites a hand edit: then `update` with plan and ok (`actions/update.md`). Close with `doctor --strict`.
