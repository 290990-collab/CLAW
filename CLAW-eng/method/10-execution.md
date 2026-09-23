## Execution obligations

They hold for every agent that receives a task, coordinator included when it works directly.

- **Strict scope:** execute *only* the assigned task. Any extra problem noticed goes into the report, NEVER into the diff.
- **Decisions outside the mandate:** a choice the task does not assign you — structure, contract, alternatives not indicated — is not yours to make: stop and report it at the top of the report with the options, and resume on the answer.
- **Range reads:** read the `file:line` ranges you receive, not whole files. Widen only if the excerpt is not enough, and say so.
- **Zero redundancy:** build/tests passed and no file changed → do not re-run.
- **Open request:** several plausible readings lead to different work and neither the repo nor the documents choose → do not pick one: ask before acting. Questions grouped, only on what changes the work — goal, what it does and does not do, requirements and constraints, priorities —, never on what the repo, the documents or an obvious default already settle. Proceed when the answers are enough to fix the completion criterion. **An observable fact is not asked:** if the answer comes from running something — behaviour, timing, output, whether a check really tells cases apart — you observe it. The user keeps the product or preference calls that no run can settle.
- **Stop criterion:** no verifiable completion criterion → ask for it before proceeding. It becomes unsatisfiable along the way → it is neither abandoned nor worked around: stop and report it at the top of the report, with the constraint that prevents it.
