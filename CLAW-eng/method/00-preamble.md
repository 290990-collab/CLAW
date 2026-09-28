# Common working method

Binding execution rules for every agent and every context. Not customised: what
concerns the project lives outside the markers.

**Navigation:**
- Coordinator, at session start and task end → `docs/TODO.md`
- Coordinator that delegates → `.claude/shared/orchestration.md` first
- An agent's role → `.claude/agents/<role>.md`
- Domain guides → `.claude/shared/` (open ONLY if the task falls in the domain); what each one holds: `CLAUDE.md § Shared guides`

**Reply language:** the user gets their language — the `language` setting if one is set, otherwise the language of their messages. Everything else in context being English — this method, the files, the tool output — never changes it.
