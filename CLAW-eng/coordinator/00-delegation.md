# Orchestration — coordinator's guide

Content actionable **only by the coordinator**. Subagents do NOT read this file.

> To be read at the start of a session **if the session delegates**.

## Who does what

- **Coordinator:** plans, delegates, verifies and integrates.
- **Direct execution:** small changes (≤2-3 files, a few dozen lines, no contract touched) are executed directly: delegating costs more.
- **Subagents:** execute the task and report to the coordinator, and spawn no subagents. Who communicates with whom is set by the orchestration model, in the section of this guide that names it.

## External skills

The connected skills live in `.claude/skills/`. The ones you may invoke on your own are the ones you are listed: the others stay with the user, and the settings hide them from you.

- **Rarely, and only if needed:** a skill is long and good for one task. Invoking one out of habit is context the whole session pays for.
- **You do not run it:** you delegate to `skill-runner`, which invokes it and reports. Its instructions stay in that agent's context and leave with it; you verify the report like any other.
- **If the user launches it, you run it:** they chose it, and going through a subagent would lose what they had in mind.
- **Personal and plugin skills are not invoked on your own initiative:** this project did not choose them.
- **What holds only for that skill dies there:** it is not saved to memory, not written into the state files, not quoted as a general rule.

## Token economy — the ten rules of delegation

Canonical and complete list, it lives **only here**. The obligations of whoever executes are in `CLAUDE.md` and are a different thing, not a renumbered subset of these.

1. **Parallelism by role and by cost** — the constraint names roles and cost tiers, never a model: a constraint that names a model dies with the model.
   - `architect`, and any agent that decides for the whole job: one only, never duplicated nor relaunched on the same task: two controllers collide.
   - Top-tier model: in sequence by default. In parallel only if the task requires it, on work that neither touches nor influences each other: up to 2 copies of the same agent, or different agents on different fields (`architect` on the backend, `frontend` on the interface, `debugger` on a fault).
   - Mid-tier model: up to 3 copies in parallel, under the same conditions. Light: no limit.
   - No repeated work: the same task given to several top-tier agents, or over several rounds, costs more than it adds. Two exceptions: the double review (rule 9) and an unknown-cause failure on an important task — two isolated `debugger`s on the same symptom, then you compare the diagnoses. Isolated on purpose: the gain comes from independence, not from debate. Whoever duplicates states **before** the spawn how they will choose among the results — the first that passes, the ranking, the synthesis — and if an agent drops out goes on with the ones left, saying so: deciding afterwards is picking the result you like.
   - Parallelism does not lower the cost, it concentrates it, even across different agents: the user's usage window runs out sooner and the work stops halfway.
2. **Agent and model to the task, not to the role:** no `architect` for obvious decisions nor `debugger` for evident causes. The card's model is the default: the spawn lowers it for mechanical, judgement-free or low-risk tasks (the card's effort stays), and never raises it. A decision the mandate does not give the executor goes back to whoever delegated, and the answer goes to the same stopped agent, in one line (rule 8). Several decisions coming back → the plan was missing, not the model. A model that is too weak gets it wrong, and the wasted round costs more than the premium: a light model handles “find and list”, not “classify”.
3. **Pre-digest the context:** a question a command answers — a text search, the tests, the doctor — is settled with the command, not with an agent reading files. The rest goes first to `explorer` (repo) or `api-scout` (libraries, services, docs) at low cost to extract exact `file:line` and signatures, and the excerpts go to the expensive agents. **Scanning is not main-context work:** a broad task, a narrow answer, no judgment delegated (“of N files, which ones touch X” → a table) goes to `explorer` even when doing it yourself looks faster, because the coordinator costs more per token and keeps the noise for the whole session. What stays with you is work whose **judgment** is the product, not the scan that precedes it.
4. **Pass ranges, not files:** the prompt carries only excerpts and exact `file:line`; whoever receives them does not widen the read.
5. **Prompt structure:** mandatory, section "How to write a delegation prompt". Instructions at the edges, data and excerpts in the middle.
6. **Load-on-demand:** pass pointers to resources and guides. The agent opens them if and when needed.
7. **One task per agent,** with a verifiable completion criterion. Zero umbrella tasks ("fix X"); a plan of ordered atomic tasks, each verifiable, counts as one. Split only what does not fit in one context: depth is an outcome, not a plan.
8. **Reuse the session, never re-spawn:** the agent that holds a task's context — the same task or a later one on the same files — stays open as long as that context is useful, and new work reaches it as a message with only what is new, not as a new agent that re-digests everything. Every message, though, re-reads its whole conversation: a touch-up of a few lines is done by the coordinator.
9. **Proportionate review, one round only:** no reviewer for small changes, one for a normal task, two isolated ones for an important task (§ The code cycle, step 5); the critical-surface reviewer is outside this count. The final reviewer **or** a native review skill, never both; heavy native ones only at the user's request. Findings are fixed by whoever holds the picture — the coordinator, or the still-open agent that wrote that code; a finding that asks for new work becomes a task and follows the cycle. The reviewer does not fix and is not relaunched on the fixes: the coordinator verifies them with the tests. A blocking finding (security, data loss) goes to the user, who decides.
10. **Zero useless re-verification:** do not spawn agents to re-run builds/tests that just passed if nothing has changed.
