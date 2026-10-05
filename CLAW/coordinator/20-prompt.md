## How to write a delegation prompt

The edge rule, non-negotiable: **operative instructions at the margins, data and reference material in the middle.**

### Mandatory structure

```
1. TASK:        [one sentence: what to do]
2. DONE WHEN:   [verifiable completion criterion]
3. NOT DONE:    [the near misses this task invites]
4. CONSTRAINTS: [hard prohibitions, few and specific]
5. MATERIAL:    [excerpts and a list of exact file:line]
6. DONE WHEN:   [repeated identically to point 2]
```

The criterion opens and closes on purpose: if an agent misses the target, almost always it was implicit or sat in the middle.

### Non-negotiable rules

- **Zero `file:line` in prose:** they go only in a list, in the MATERIAL block.
- **Essential constraints:** few and hard. Ten constraints amount to no constraint.
- **Zero echo:** do not repeat what is already in `CLAUDE.md`. Pass only the task's delta.
- **Objective criterion:** verifiable by whoever receives it ("the tests in `tests/x.py` pass and the build is clean"), not "do a good job".
- **Light model, narrow question:** whatever goes to a light model is answered by a list or a table it fills by searching. "Whether", "is it safe", "why" stay with you or go to a mid-tier agent: a verdict from an executor that cannot give it is paid twice, once by it and once by your check.
- **Near misses named:** what a pressed agent returns in place of the result — narrower scope, a plan instead of the change, a check that never ran, a fix that holds only on the example. Each one named is an exit closed; none fits → the line is left out.
- **Reviewer prompts:** MATERIAL lists how *this* change can look right and be wrong — the boundary it crosses, the consumer it may break. A generic "check it" finds less.
- **Second round (rule 8):** for corrections or iterations continue the existing session sending ONLY the findings. Never rebuild the prompt from scratch.
