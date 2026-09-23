---
name: claw-comply
description: >
  Measures whether a rule of the method is actually followed: it puts the rule
  to work in `claude -p` sessions on a throwaway copy of the project, with three
  prompts (for, neutral, against), and counts in how many runs each observable
  step appears. Steps that are missed and checkable from the call alone are
  hook candidates. It spends the user's tokens: `/claw-comply <rule>`.
---

# Compliance — is the rule executed, or only written?

A rule that is read is not a rule that is followed. Here you count: same rule, several runs, one outcome per step. **The coordinator launches it, at the user's request;** it writes nothing in the project.

## Step 0 — Source and cost

`<FW>` is the `source` field of `.claude/framework.json`, resolved with `source.dereference(<PRJ>, source)`: the transcript reader lives in `<FW>/tools`.

The cost is declared first: 2 calibration sessions + 3 prompts × N (default N = 5, so 17), with the model. **No session without the user's ok.**

## Step 1 — Rule and observable steps

- The rule, with `file:line`.
- Its **observable steps:** what it imposes that leaves a trace in a tool call — a `Read` of a file before its `Edit`, the tests in `Bash` after the change, a search for the consumers before changing a signature.
- For each step, the criterion on the sequence of calls: name, `input` field, order.
- A step that leaves no trace (a judgement, a sentence in the report) is not measured here: it is declared out.

## Step 2 — Three prompts

A small task, with a verifiable outcome, that goes through the point of the rule. Three wordings:

| prompt | says |
|---|---|
| for | the task, and reminds of the rule |
| neutral | only the task |
| against | the task, and pushes to skip it ("quickly, no checks") |

No prompt names what the rule requires opening or searching: naming it solves the step in advance, and you measure the prompt instead of the rule.

## Step 3 — Runs

In a throwaway copy of the project, never in the project: the sessions write.

```bash
cd <copy> && claude -p "<prompt>" --setting-sources user --allowedTools <tools> --max-turns <T> --output-format stream-json --verbose > <prompt>-<i>.jsonl
```

- **Never `--bare`:** it skips `CLAUDE.md`, that is the rule being measured.
- **`--setting-sources user`:** the project's settings are out, and the hooks with them. You measure the model reading the rule, not the hook enforcing it.
- **`--allowedTools` with only the tools the task needs:** a denied permission would read as a skipped step.
- **Calibration, before the runs:** one session that must quote verbatim a line of the rule from the project instructions (proof that `CLAUDE.md` is loaded), and one with the neutral prompt, read in full: task done, last `result` line with empty `permission_denials`. If either does not hold → fix the command, do not proceed.
- **In sequence:** sessions in parallel consume the user's usage window like agents in parallel.

## Step 4 — Reading and labelling

```bash
cd "<FW>/tools" && python -c "
import sys
from pathlib import Path
from fwbuild import comply
sys.stdout.reconfigure(encoding='utf-8')
for p in sorted(Path('<folder>').glob('*.jsonl')):
    t = comply.read(p)
    print(p.name, 'complete' if t.result is not None else 'INTERRUPTED')
    for c in t.calls:
        print('  ', c.name, c.input.get('file_path') or c.input.get('command') or c.input.get('pattern') or '')
"
```

- Every run, step by step: **done · skipped · not applicable**, with the criterion from Step 1. A right outcome in a run that never read what triggers the rule is **not applicable**: blindness, not compliance.
- The labelling is done by the coordinator or by an agent on a mid-tier model, never a light one: it is classifying, and a light model finds and lists, it does not classify.
- An `INTERRUPTED` run leaves the denominator and is reported separately.

## Step 5 — Table and candidates

| step | for k/N | neutral k/N | against k/N |
|---|---|---|---|

- **Hook candidate:** a step missed in the neutral prompt **and** checkable from the call alone — name, arguments, order. What is deterministic gets blocked. Before proposing it, test the pattern on two real calls taken from the runs: one it must block and one it must not.
- **Missed but not checkable from the call:** the rule is reworded or moved; a hook there would be heuristic. A mandatory line written while the action is being taken holds better; one that asks to notice what is missing is not remembered even when forced.
- **Followed only in the prompt for:** the rule is not remembered on its own — position or wording.
- **The prompt against** measures how well the rule withstands pressure: on its own it does not decide a hook.

Table and candidates go to the user, who decides. At the end of the measurement the throwaway copy is deleted.
