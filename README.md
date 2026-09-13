<p align="center">
  <img src="assets/claw.png" alt="CLAW, an orange block with two claws, sitting cross-legged in calm focus" width="440">
</p>

<h1 align="center">CLAW</h1>

<table align="center"><tr><td>

```
+-- CLAW-eng ----------------------------------------------+
|       method             coordinator        cycles       |
|       agents             shared             hooks        |
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

**A working method for Claude Code. One command to install. A doctor to keep it honest.**

Claude Code gives you subagents, hooks and skills. It doesn't give you a
**method** — so every project writes its own `CLAUDE.md` by hand, and every one
of them drifts. CLAW is that method: written once, tested, versioned, and
generated into your project in minutes.

---

## Why CLAW

### Evidence, not vibes

No API, number or file gets cited unless it was read in this session. Whatever
wasn't run is marked `UNVERIFIED`. No fix until the cause explains every symptom.
And every agent closes with the same report: how confident it is, what would
prove it wrong, and what it did **not** check.

### The rules you already know — actually applied

- **KISS and YAGNI** — the simplest thing that meets today's requirement, nothing
  built for hypothetical needs.
- **Minimal safe change** — one problem per diff, no drive-by refactors.
- **Single source of truth** — two copies that can diverge will.
- **Fail loudly** — no swallowed exceptions, no invented defaults; security
  checks fail closed.
- **Hyrum's law** — every observable behaviour is a contract: find who relies on
  it before you change it.
- **Least privilege** — reviewers read the code; they don't get a shell.
- **No shortcut to green** — a test never passes because it was weakened.

### Guardrails that don't trust the model

A rule in a prompt is a suggestion. CLAW measures it: `/framework-comply` puts the
rule through real sessions and counts how often each step actually happens. What
the model skips, and a tool call can prove, becomes a hook — `--no-verify` blocked,
linter configs that loosen blocked, and the first edit of a file answered with
"who imports this?".

### Context is a budget

Progressive disclosure, by construction. The method every agent needs lives in
`CLAUDE.md`, under a word budget the tests enforce. Delegation rules live where
only the coordinator reads them. Domain guides load only when the task needs
them. `fwbuild cost` turns it all into tokens and dollars.

### One method, every project

The method sits in a hashed region: touch it and the doctor notices. The edits
worth keeping go back to the source with `framework-sync --up`, so the next
project starts smarter.

---

## The team

28 specialised agents across 7 profiles. Your project gets only the ones it
needs. The core of the roster:

| Agent | What it does |
|---|---|
| `explorer` | Finds where things live, cheaply, before anything changes |
| `api-scout` | Checks third-party APIs and version differences before code relies on them |
| `architect` | Plans changes that cross files or contracts — and writes no production code |
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

## Version 1.5.0

MIT — see [LICENSE](LICENSE).
