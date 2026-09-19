---
name: claw-memory
description: >
  Shows what is in the project's persistent memory and what no longer holds:
  lists the facts, pairs them with the state of the repository and with the
  framework's rules, and proposes what to correct, mark as superseded or
  delete. To be used at the start of a long session, after a structural change,
  or when a memory looks old: `/claw-memory`.
---

# Persistent memory — what it says, and what contradicts it

Level 4 of the state is the only one that lives **outside the repository**: no finding of the doctor sees it, and in a conflict the repo wins.

**The coordinator invokes it.** Whoever executes a task does not read the memory: they receive in the delegation prompt what they need, as with everything else.

## Step 0 — Find the memory

Do not assume the path: **look at it**. First directory that exists, in this order:

1. the harness's one for this project — in Claude Code `~/.claude/projects/<project>/memory/`, with the project's path turned into a directory name; if it is not there, do not invent it
2. `<PRJ>/.claude/memory/`

Neither exists → say so and stop. A project without memory is young, not broken, and the directory is not created here: memory is born when there is a fact to write in it.

If there is an index (`MEMORY.md`) and it does not match the files, that is already the first conflict to report.

## Step 1 — List

One line per memory, **never** the full content: the list is there to decide what to open.

| memory | type | says |
|---|---|---|
| `two-editions.md` | structure | the two editions differ only by language |

## Step 2 — Mechanical check

This one first: it costs little and does not get it wrong. From every memory extract the **concrete** references — paths, file and function names, commands, numbers, versions — and verify them one by one: does the file still exist? is the command declared where the memory says? does the number match the source in the repo?

Every failed check is a **proven** conflict.

## Step 3 — Judgement check

Then the contradictions with `CLAUDE.md`, `docs/status.md` and the kernel rules: a closed decision that overturns a memory, a preference superseded by a new directive.

**A judgement conflict is declared only if you can cite the line that contradicts it.** Without that line it is not a conflict, it is an impression — and it stays unsaid.

## Step 4 — The report

One table, paired:

| memory | says | the repo says | proposal |
|---|---|---|---|
| `test-count.md` | "160 tests per edition" | `README.md:19` — 161 | correct the number |
| `script-path.md` | "the script is in `bin/run.sh`" | it is not there; `tools/run.sh` is | correct the path |

**A row without the "the repo says" column does not get written.** A conflict without the two sources side by side is an invented alarm, and memory is exactly the place where an invented alarm survives across sessions.

Allowed proposals: **correct** · **mark superseded**, with the date and what superseded it · **delete** · **leave**, for a fact still true that *looks* old.

Delete is the right proposal in one precise case: the memory records a mistake and **the cause is gone**. There the problem does not exist, so the memory must not either.

## Step 5 — Apply, one row at a time

Nothing is written and nothing is deleted without the user's approval, row by row: that memory is theirs and survives this session. Once a change is applied, update the index too.

If a memory fell because of a **decision**, the decision goes into `docs/status.md`: the memory says what holds now, `status.md` why it changed.

## When to invoke it

- at the start of a long session, before trusting what you "remember";
- after a change of paths, contracts or modules: level 4 already asks for it, this skill is the how;
- when **one** memory looks old — and then you look at that one, not all of them.

Not at every task: rereading the whole memory every round is a cost paid for a change that did not happen.
