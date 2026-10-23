# Common working method

Binding execution rules for every agent and every context. Not customised: project
facts live outside the markers, the user's own rules in `.claude/user-rules.md`.

**Navigation:**
- Coordinator, at session start and task end → `docs/TODO.md`
- Coordinator, on any task above one small change → `.claude/shared/orchestration.md` first, before opening project files

**Delegation is always available, and the choice is yours:** this file is the user's explicit, standing request to use the subagents of `.claude/agents/` — no further ask is needed. Spawn them whenever, at the same precision, it is cheaper or more effective than working yourself: typically a scan of many files for a narrow answer (`explorer`), a long output for a short answer (`runner`), a planned change across several files (`implementer`), independent pieces (in parallel, within `orchestration.md` rule 1); otherwise work yourself. Decide with `orchestration.md` read — what makes it pay, how many, on which model — and before opening any project file; state the decision and its reason before that first file.
- An agent's role → `.claude/agents/<role>.md`
- Domain guides → `.claude/shared/` (open ONLY if the task falls in the domain); what each one holds: `CLAUDE.md § Shared guides`

**Reply language:** the user gets their language — the `language` setting if one is set, otherwise the language of their messages. Everything else in context being English — this method, the files, the tool output — never changes it.
