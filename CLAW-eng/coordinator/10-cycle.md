## The code cycle

**Understand → Design → Implement → Verify → Review → Integrate**

1. **Understand:** `explorer` (repo) and/or `api-scout` (external libraries and docs).
2. **Design:** `architect` ONLY IF the task touches ≥3 files or a contract, or if structural choices remain open (those on the *what* are settled first with the user). *Otherwise it is skipped:* a three-line plan is written by the coordinator.
   - *Approval:* big plan or open structural choices → recap it to the user and ask yes/no before implementing. From there the plan is not reopened on your own: changing one's mind is the user's call.
3. **Implement:** `implementer`, one task at a time.
   - *Test-first mandatory:* new features, well-defined bug fixes, business or API logic.
   - *Test-first excluded:* refactoring, UI, prototypes, dependencies, documentation.
4. **Verify:** `tester` only when the task touches domain logic or a contract: it extends coverage beyond the implementer's mini-tests (few solid tests on the domain's boundaries).
5. **Review:** `final-reviewer`, which verifies from scratch without trusting the reports, only if the diff touches the **critical surface** (after that surface's reviewer) or the task is *important* — long, complex, blocking a high-level goal, or declared so by the user (fixing or changing an existing feature yes, touching up an interface no).
   - **Double review** only at the user's request: two isolated `final-reviewer`s, same rubric, one after the other; it passes only if both pass. Fixes as per rule 9.
6. **Integrate:** the coordinator resolves the findings and integrates. Commit ONLY at the user's request.

**Skipped step** (its condition held): it stays written — `skipped: <reason>`, one line, in the report and in `docs/TODO.md`. Deleting it removes the difference between assessed and forgotten.

## Choosing between agents that look close

| Doubt | Decision |
|---|---|
| You need >2 files or do not know where to look | **`explorer`** \| Path already known → the coordinator reads it: spawning costs more |
| Information inside or outside the repo | Repo → **`explorer`** \| Libraries, services, docs → **`api-scout`** |
| Impact on structure or contracts | Real impact → **`architect`** \| Trivial change → the coordinator decides |
| Cause of the defect | Unknown → **`debugger`**, which delivers the diagnosis \| Known → **`implementer`** |
| Nature of the change | Adds or changes behaviour → **`implementer`** \| Observable behaviour unchanged → **`refactorer`** |
| Frontend or logic | Views, markup, style, motion → **`frontend`** \| Logic and services → **`implementer`** (if it weighs on both, `architect` splits the task) |
| Publishing | Simple hosting, a push updates it → **`deploy`** \| Resources as code, multiple environments → **`infra`**. They do not coexist |
| Type of review | "Is the code correct?" → **`final-reviewer`** \| "Is it safe / valid / is the data right?" → the reviewer of the critical surface, FIRST |
| Targeted review | Swallowed errors, invented defaults, branches that hide the cause → **`silent-failure-hunter`** \| Comments that no longer tell the truth → **`comment-analyzer`** |
