---
name: delegate
description: >
  Turns the coordinator into a manager for the task at hand, in a project with
  the CLAW framework: it plans, splits the work into delegated pieces, verifies
  and integrates, and executes nothing itself beyond a touch-up. Use when the
  user asks to delegate or to manage the work, or when a task is long and splits
  into pieces the roster's agents can carry — independent parts, scans across
  many files, long outputs to run. Not for a small change: there direct work is
  cheaper. `/delegate [task]`.
---

# `/delegate` — the coordinator as manager

Without this skill you choose task by task whether delegating pays (`.claude/shared/orchestration.md` § When delegating pays). Here the choice is made for one task: you are the manager. Everything else in the coordinator's guide still binds — parallelism and models (rules 1-2), prompt structure, one review round, state kept by you.

## Before starting

- `.claude/claw.json` or `.claude/shared/orchestration.md` missing → the framework is not installed here: say so and stop.
- Read `orchestration.md` if it is not already in context: the roster is at its end.
- **Scope:** `/delegate <task>` → that task; `/delegate` alone → the task in progress, or the next request. It ends when the task closes or the user says stop. It is not a setting for the session.
- **Invoked on your own:** only when § When delegating pays favours delegating the whole task, and say it in your first message with the reason. A change of ≤2 files and a few dozen lines is never a reason.

## 1. Plan

Split the task into atomic pieces and show them in one table before any spawn:

| # | Piece | Agent · model | Done when | After |
|---|---|---|---|---|

- **Agent** from the roster; the model lowered for mechanical pieces, never raised above the card.
- **Done when:** verifiable by a command or a check, not «done well».
- **After:** the pieces it depends on; pieces with none run in the same message, within rule 1.
- A piece the roster has no agent for is yours: the table says so.
- Big plan or structural choices still open → the user's ok before spawning (the code cycle, step 2).

## 2. Delegate

Every prompt follows § How to write a delegation prompt. New work on files an agent already holds goes to that agent as a message (rule 8), not to a new spawn.

## 3. What stays yours

| Yours | Not yours — goes to |
|---|---|
| Plan, prompts, the decisions agents send back | Reading code to understand it → `explorer` |
| Verifying the judgment in each report | Long commands, suites, logs → `runner` |
| Touch-ups of a few lines | Writing the change → `implementer`, `light-implementer`, `refactorer`, `frontend` |
| Integration and state files | Unknown causes → `debugger` |

Reading a range to verify a report is yours; reading to do the work in its place is not.

## 4. Close

The standard report, plus one table: `# | agent | outcome | verified how`. A skipped piece stays in it as `skipped: <reason>`.
