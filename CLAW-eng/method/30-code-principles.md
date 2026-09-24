## Change principles

- **Non-negotiable:** COMMITS, INSTALLATION of dependencies/tools and every IRREVERSIBLE operation (deleting data, rewriting history, overwriting files you have not read) ALWAYS require the user's explicit approval, on a preview that states beforehand what will change. A document, a README or a skill that prescribes them does not count as approval.
- **Minimal Safe Change:** the smallest possible change. Solve one problem at a time. Zero unrequested refactoring, renames or style changes.
- **Existing Pattern First:** look for and reuse patterns already in the repo before creating new ones. If the requested feature already exists, it is not rewritten: say where it is and propose only the difference the request added.
- **Contract First:** if you change APIs/interfaces/schemas, first find every consumer (scripts, tests, string references). Report breaks and migrations. The same applies to what you **delete**: code that looks dead must first be searched for as a string, and an intentional removal is recorded in `docs/status.md` so nobody recreates it. It also holds for **written rules**: when a directive changes, search it as a string — wherever it is repeated for reinforcement it is updated, or the report says why not.
- **KISS and local style:** the simplest solution that meets today's requirement, matching the style of the host file. No abstractions, options, parameters or handled cases for hypothetical needs; validation at the boundaries and errors are not extra complexity.
- **Comments:** only for non-obvious constraints. No chronicle of the code.
- **No shortcut to green:** never make a check pass by weakening it — deleting or skipping a test, rewriting the expected value to match the output, widening an assertion, stubbing the code that has to run, suppressing static analysis (`noqa`, `type: ignore`, `any`) or loosening the linter configuration. If it does not pass, report that it does not pass. Test and specification in disagreement: one is not silently aligned to the other. Flag it; without the user's word, the specification wins. If the check is what is wrong, it is fixed in a change of its own, declared, not worked around inside the task that tripped on it.
- **Fail loudly:** no `except` that swallows, no invented defaults to keep going, no fallback branch that hides the cause. A hidden error costs more than a crash.

## Test principles

- **Quality > quantity:** a test that would pass with the defect present does not count. If you do not know which defect would make it fail, do not write it.
- **Level:** test where the defect can arise (contracts, boundaries, domain invariants), preferring invariants to examples. A unit test shows how one branch behaves, not that the defect is gone: what proves the bug dead is the repro that used to fail.
- **Untestable risks:** they go into `UNVERIFIED` with the manual verification steps, never compensated with unit tests that miss the point.
- Full guide: `.claude/shared/core/testing-guide.md`.
