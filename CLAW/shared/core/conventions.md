# Conventions

Cross-cutting rules of form.

## Commits

- Messages in English, imperative, first line ≤ 72 characters (`Fix …`, `Add …`, `Remove …`).
- One commit = one logical change.
- When a defect is fixed, the repro that failed goes into the history **before** the fix: whoever reads the log sees the proof, not just the outcome.
- The body explains the **why**, not the what (the what is in the diff).
- Never rewrite shared history, never force a push, never skip the automated checks.

## Scope of a change

- Refactoring, dependency updates and mass reformatting are separate tasks.
- Do not touch generated artefacts: they are regenerated, not edited by hand.

## Names

- A name expresses **what something is or does**, not how it is implemented (avoid types/structures in names).
- Consistency before elegance: use the terminology already present in the project.
- No abbreviations that are not standard in the domain.
- New files follow the naming convention of their neighbours.

## Comments

- **Non-obvious constraint** = a non-obvious choice, an edge case, a format imposed from outside. Never what the code already says.
- **No chronicle:** no history of the change ("used to be", "fix for") and no IDs of internal documents. The constraint is stated in the present tense; the history lives in the commit.
- They are updated or removed together with the code they describe.
- Unused commented-out code is deleted.

## Documentation

- User-visible changes are recorded in the registers the project has established.
- Any change to a versioned contract forces a version bump and an explicit note.
- Behavioural documentation must be verified against the real code before being written.

## Non-negotiable minimum quality

- The build must pass after every task.
- No new warning introduced without flagging it.

## In this project

[TO FILL IN — language of code and comments, "kind of code → folder" map,
specific naming conventions, where user-visible changes are recorded, which
folders contain generated artefacts not to be touched.]
