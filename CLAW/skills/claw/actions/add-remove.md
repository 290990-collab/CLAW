# `/claw add <agent|guide>` · `/claw remove <agent|guide>`

**Activating** copies the agent from the source at its **current version**, fills in its `## Project context` block and adds the row to the routing table in `.claude/shared/orchestration.md` — never in `CLAUDE.md`: routing is coordinator content.

Mandatory shape of the row, because the doctor reads it:

```
| Situation | `agent-name` | Model |
```

The name goes in backticks in the **second** column. Anywhere else, that agent shows up as `ROSTER_ORPHAN` and the table cites a `ROSTER_MISSING` that does not exist.

Activating later is *better* than a dormant file: you always take the latest version, not one frozen at installation day.

**Deactivating** removes the file from `.claude/agents/` and the row from the routing. **The source is not touched.** If the project block held information that cannot be reconstructed, save it first.

**A guide** is named by its path under `shared/` (`domain/llm-guide.md`). Activating it: copy it into `.claude/shared/`, fill in the project block, add its line in `CLAUDE.md § Shared guides` — without it, it is `SHARED_ORPHAN`. Deactivating it: file and line go. A guide that an installed file still cites is not deactivated: the pointer would stay dead (`SHARED_MISSING`).

Close an activation with `down "<PRJ>"` and its `--apply`: at the same version it changes no text and records the new card, which the next `/claw update` needs. Always close with `doctor`: `EXCLUSIVE` names agents that do not coexist.
