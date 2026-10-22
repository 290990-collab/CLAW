# `/claw tidy` — what the state says, and what contradicts it

Two places drift from the repository without any finding of the doctor seeing them: the operational state (`docs/TODO.md`, level 1) and persistent memory (level 4), the only one that lives **outside the repository**. The rules of the state fire on an event — a decision falls with its premise —; this action compares them with the repo as it is. In a conflict the repo wins.

**The coordinator runs it, at the user's request.** Whoever executes a task does not read the TODO or the memory: they receive in the delegation prompt what they need, as with everything else.

## Step 0 — Find what to check

- **TODO:** `<PRJ>/docs/TODO.md`. Missing → say so and go on with the memory.
- **Memory:** do not assume the path, **look at it**. First directory that exists, in this order:
  1. the harness's one for this project — in Claude Code `~/.claude/projects/<project>/memory/`, with the project's path turned into a directory name; if it is not there, do not invent it
  2. `<PRJ>/.claude/memory/`

  Neither exists → say so. A project without memory is young, not broken, and the directory is not created here: memory is born when there is a fact to write in it. If there is an index (`MEMORY.md`) and it does not match the files, that is already the first conflict to report.

Neither TODO nor memory → stop.

## Step 1 — List

One line per open TODO entry — unticked boxes, *Waiting*, *Blocked*, *Open decisions* — and one per memory, **never** the full content: the list is there to decide what to open.

| where | entry | says |
|---|---|---|
| TODO | *Waiting* · trial of the runner | wait for 1.4 to measure it |
| memory | `two-editions.md` | the two editions differ only by language |

## Step 2 — Mechanical check

This one first: it costs little and does not get it wrong. From every entry extract the **concrete** references and verify them one by one:

- paths, file and function names: do they still exist?
- commits: `git cat-file -e <sha>`; versions: is the one named already behind `VERSION`?
- an entry of `docs/status.md` it cites: does it exist, and does it say what the line claims?
- commands and numbers: declared where the line says, matching the source in the repo?

Every failed check is a **proven** conflict.

## Step 3 — Judgement check

Then the contradictions with `CLAUDE.md`, `docs/status.md` and the kernel rules: a TODO entry already done, or resting on a premise a closed decision overturned; a memory superseded by a new directive.

**A judgement conflict is declared only if you can cite the line that contradicts it.** Without that line it is not a conflict, it is an impression — and it stays unsaid.

## Step 4 — The report

One table, paired:

| where | entry | says | the repo says | proposal |
|---|---|---|---|---|
| TODO | *Waiting* · trial of the runner | "wait for 1.4" | `VERSION` — 2.7.0 | ask the direction |
| memory | `test-count.md` | "160 tests per edition" | `README.md:19` — 161 | correct the number |

**A row without the "the repo says" column does not get written.** A conflict without the two sources side by side is an invented alarm, and the state is exactly the place where an invented alarm survives across sessions.

Allowed proposals:

- **TODO:** **tick off**, with the evidence next to the box · **move to `docs/status.md`**, a closed result still sitting in level 1 · **mark superseded**, with the date and what superseded it · **ask the direction**, when the premise fell and the entry could go either way.
- **Memory:** **correct** · **mark superseded**, with the date and what superseded it · **delete** · **leave**, for a fact still true that *looks* old. Delete is right in one precise case: the memory records a mistake and **the cause is gone**.

Then the **declared debt**: search the project's code — not `docs/` — for `TODO`, `FIXME`, `HACK`. One row per hit:

| file:line | the shortcut | when to revisit |
|---|---|---|
| `src/export.py:42` | no time zones, dates are local | when a customer is outside Italy |

A hit that does not state its limit or when to revisit gets `—` in that column: the user decides whether it becomes an entry in the TODO, a fix or nothing.

## Step 5 — Apply, one row at a time

Nothing is written and nothing is deleted without the user's approval, row by row: the TODO and the memory are theirs and survive this session.

- Once a memory changes, update the index too.
- If an entry or a memory fell because of a **decision**, the decision goes into `docs/status.md`: the state says what holds now, `status.md` why it changed.
- Past the TODO's ceiling at the end, compress as the update rules say: the long trace goes down a level.

## When to propose it

The user launches it. The coordinator proposes it — one line, never runs it unasked —:

- when `docs/TODO.md` is past its ceiling;
- at the end of a release;
- after a change of paths, contracts or modules: levels 1 and 4 already ask for it, this is the how.

Not at every task: rereading the whole state every round is a cost paid for a change that did not happen.
