# Common working method

Binding execution rules for every agent and every context. Not customised: what
concerns the project lives outside the markers.

**Navigation:**
- Coordinator, at session start and task end → `docs/TODO.md`
- Coordinator that delegates → `.claude/shared/orchestration.md` first

**Delegation is a standing request of the user's:** the subagents of `.claude/agents/` are spawned without waiting to be asked each time. Delegate when a search spans more than two files or you do not know where to look (`explorer`), a defect has an unknown cause (`debugger`), or a task touches three files or more, a contract, or an open structural choice (`architect`). Below that — a small change, a path already known — you do it yourself.
- An agent's role → `.claude/agents/<role>.md`
- Domain guides → `.claude/shared/` (open ONLY if the task falls in the domain); what each one holds: `CLAUDE.md § Shared guides`

**Reply language:** the user gets their language — the `language` setting if one is set, otherwise the language of their messages. Everything else in context being English — this method, the files, the tool output — never changes it.
