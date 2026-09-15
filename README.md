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

---

## Why CLAW

### Evidence before action

- Nothing is cited unless it was read or run in the current session.
- Anything not executed is marked `UNVERIFIED`.
- No fix until the root cause explains every symptom.
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
| **No shortcut to green** | A check never passes by being weakened. |

### Hooks where prompts fall short

A rule in a prompt is followed most of the time, not every time.
`/framework-comply` measures how often: it runs the rule through real `claude -p`
sessions and counts each step. The steps a tool call can prove become hooks:

| Hook | Blocks |
|---|---|
| `block_no_verify` | `--no-verify`, `commit -n` and any change to `core.hooksPath` |
| `config_protection` | Edits to an existing linter configuration |
| `gateguard` | The first edit of a file, until its importers and public surface are checked |

### Context as a budget

Progressive disclosure by design:

- `CLAUDE.md` holds only what every agent needs, under a word budget the test
  suite enforces.
- Delegation rules load for the coordinator only.
- Domain guides load when the task needs them.
- `fwbuild cost` converts all of it into tokens and dollars.

### Drift detection

The generated method sits in a hashed region. Edit it and the doctor reports it.
Changes worth keeping go back to the source with `framework-sync --up`, and the
next project inherits them.

---

## The team

28 agents across 7 profiles. Each project installs only the ones it needs. The
core roster:

| Agent | What it does |
|---|---|
| `explorer` | Finds where things live, cheaply, before anything changes |
| `api-scout` | Checks third-party APIs and version differences before code relies on them |
| `architect` | Plans changes that cross files or contracts. Writes no production code |
| `implementer` | Writes the planned change |
| `debugger` | Finds the cause of the defect nobody can explain |
| `tester` | Tests invariants and contracts, not just examples |
| `refactorer` | Cleans up the structure, behaviour unchanged |
| `silent-failure-hunter` | Hunts swallowed errors and faults hidden behind defaults |
| `security-reviewer` | Reviews untrusted input, secrets, auth and data exposure |
| `final-reviewer` | Rereads the diff from scratch and re-runs the tests before anything is called done |

---

## Install

Once per machine. Needs Claude Code and Python 3.11+ — nothing else to install.

### macOS · Linux

1. Clone the repository

   ```bash
   git clone https://github.com/290990-collab/CLAW.git ~/.claude/CLAW
   ```

2. Copy one edition as your source — `CLAW-eng`, or `CLAW-it` for Italian

   ```bash
   cp -r ~/.claude/CLAW/CLAW-eng ~/.claude/framework
   ```

3. Create the personal skills folder

   ```bash
   mkdir -p ~/.claude/skills
   ```

4. Add `/framework-install` — generates the method into a project

   ```bash
   cp -r ~/.claude/framework/skills/framework-install ~/.claude/skills/
   ```

5. Add `/framework-comply` — measures whether a rule is followed

   ```bash
   cp -r ~/.claude/framework/skills/framework-comply ~/.claude/skills/
   ```

### Windows · PowerShell

1. Clone the repository

   ```powershell
   git clone https://github.com/290990-collab/CLAW.git $HOME\.claude\CLAW
   ```

2. Copy one edition as your source — `CLAW-eng`, or `CLAW-it` for Italian

   ```powershell
   Copy-Item -Recurse $HOME\.claude\CLAW\CLAW-eng $HOME\.claude\framework
   ```

3. Create the personal skills folder

   ```powershell
   New-Item -ItemType Directory -Force $HOME\.claude\skills | Out-Null
   ```

4. Add `/framework-install` — generates the method into a project

   ```powershell
   Copy-Item -Recurse $HOME\.claude\framework\skills\framework-install $HOME\.claude\skills\framework-install
   ```

5. Add `/framework-comply` — measures whether a rule is followed

   ```powershell
   Copy-Item -Recurse $HOME\.claude\framework\skills\framework-comply $HOME\.claude\skills\framework-comply
   ```

### Then, in any project

```
/framework-install
```

---

## Use

### In Claude Code

| Command | When | What it does |
|---|---|---|
| `/framework-install` | once per project | Reads the repo, asks a short questionnaire, picks the roster, generates everything, verifies it |
| `/framework-doctor` | something looks off, before an update | Checks the installation; every finding comes with its remedy |
| `/framework-memory` | long session, after a restructure | Pairs every stale memory with the repo line that contradicts it |
| `/framework-comply <rule>` | a rule seems ignored | Counts how often each step of the rule is followed across `claude -p` runs — 17 by default, on your tokens |

### Keeping in sync — `/framework-sync <mode>`

| Mode | What it does |
|---|---|
| `--down` | New source version into the project, your adaptation kept |
| `--up [what]` | A local change up into the source, so the next project inherits it |
| `--upgrade` | A new release over a source you changed with `--up` |
| `--activate <agent\|guide>` | Adds an agent or a guide at the source's current version |
| `--deactivate <agent\|guide>` | Removes it from the project; the source keeps it |
| `--repair` | Puts back missing skills, hooks, guides and state files; overwrites nothing |
| `--uninstall` | Deletes what matches the source, archives what you adapted |

Every mode that writes shows the plan first and waits for your ok.

### From the shell — in `<source>/tools`

| Command | What it does |
|---|---|
| `python -m fwbuild doctor --strict <project>` | The doctor's check; exit 1 on warnings too |
| `python -m fwbuild doctor --json <project>` | Findings plus the `CLAUDE.md` measure, for CI |
| `python -m fwbuild cost <project> [--spawns N] [--devs N] [--price USD]` | Estimated cost of `CLAUDE.md`: its tokens × spawns a day × people × price per million input tokens. Defaults: 100 spawns, 1 person, $5 |
| `python -m fwbuild report <folder>` | Which method versions run where, across repos; `--depth`, `--strict`, `--json` |
| `python -m fwbuild source [path]` | Validates a source and says whether it was promoted with `--up` |

### Settings

| Setting | Effect |
|---|---|
| `$CLAUDE_FRAMEWORK` | Source location, checked after `./framework/` and before `~/.claude/framework/` |
| `FRAMEWORK_GATEGUARD=off` | Turns the `gateguard` hook off |
| `accepted` in `.claude/framework.json` | Warnings you accept: printed as notes, `--strict` still passes |

**Profiles:** `software` · `library` · `web` · `data` · `research` · `llm` ·
`marketing` — each sets the roster, the guides and the permissions for its
field.

The framework writes `CLAUDE.md`, `.claude/` and `docs/`, and nothing else. Your
code, build and dependencies stay untouched.

---

## Version 1.5.1

MIT — see [LICENSE](LICENSE).
