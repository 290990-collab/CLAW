# Orchestration — coordinator's guide

## When delegating pays

Nothing obliges a spawn; convenience decides, and it has two parts:
- **Cost:** what you read stays in your context and is paid again on every later turn. A subagent on a cheaper model reaches the same result on cheaper tokens; one on your own model saves only the context, and copies of it in parallel multiply your price. The expensive model goes where judgment is needed; reading, running and executing a clear change go to the cheaper agents.
- **Effectiveness:** a long task held in one context degrades — early detail fades, the noise of scans and outputs crowds the reasoning. Delegating cuts it into clean pieces, each returning a narrow report you verify.

Delegate when the two together favour it, in any case, not only the ones the agents' descriptions name; work yourself when they do not — a small change, a prompt longer than the work, a context you already hold. Rules 1-2 below bind how many run at a time and on which model. Once the code is in context, delegating no longer pays: decide first.

## Who does what

- **Coordinator:** plans, delegates, verifies and integrates. It verifies the **judgment** — causes, assessments, “it works” — and whatever it acts on irreversibly; data that carries its own address (`file:line`, signatures) is checked when it is used, not re-read on delivery.
- **Direct execution:** a small change (≤2 files, a few dozen lines, no contract touched) is usually cheaper done directly; § When delegating pays decides.
- **Roster:** use only the agents in § This project's roster; a step whose agent is missing is yours.
- **Subagents:** execute the task and report to the coordinator, and spawn no subagents. Who communicates with whom is set by the orchestration model, in the section of this guide that names it.

## External skills

The connected skills live in `.claude/skills/`. The ones you may invoke on your own are the ones you are listed: the others stay with the user, and the settings hide them from you.

- **Rarely, and only if needed:** a skill is long and good for one task. Invoking one out of habit is context the whole session pays for.
- **You do not run it:** you delegate to `skill-runner`, which invokes it and reports. Its instructions stay in that agent's context and leave with it; you verify the report like any other.
- **If the user launches it, you run it:** they chose it, and going through a subagent would lose what they had in mind.
- **Personal and plugin skills are not invoked on your own initiative:** this project did not choose them.
- **What holds only for that skill dies there:** it is not saved to memory, not written into the state files, not quoted as a general rule.

## Token economy — the ten rules of delegation

1. **Parallelism by role and by cost**
   - `architect`, and any agent that decides for the whole job: one only, never duplicated nor relaunched on the same task: two controllers collide.
   - Top-tier model: in sequence by default. In parallel only if the task requires it, on work that neither touches nor influences each other: up to 2 copies of the same agent, or different agents on different fields (`architect` on the backend, `frontend` on the interface, `debugger` on a fault).
   - Mid-tier model: up to 3 copies in parallel, under the same conditions. Light: no limit.
   - No repeated work: the same task given to several top-tier agents, or over several rounds, costs more than it adds. Two exceptions: the double review (rule 9) and an unknown-cause failure on an important task — two isolated `debugger`s on the same symptom, then you compare the diagnoses. Isolated on purpose: the gain comes from independence, not from debate. Whoever duplicates states **before** the spawn how they will choose among the results — the first that passes, the ranking, the synthesis — and if an agent drops out goes on with the ones left, saying so: deciding afterwards is picking the result you like.
   - Parallelism does not lower the cost, it concentrates it, even across different agents: the user's usage window runs out sooner and the work stops halfway.
2. **Agent and model to the task, not to the role:** no `architect` for obvious decisions nor `debugger` for evident causes. The card's model is the default: the spawn lowers it for mechanical, judgement-free or low-risk tasks (the card's effort stays), and never raises it. A decision an executor sends back is answered to the same stopped agent, in one line (rule 8). Several decisions coming back → the plan was missing, not the model. A model that is too weak gets it wrong, and the wasted round costs more than the premium.
3. **Pre-digest the context:** a question a command answers — a text search, the tests, the doctor — is settled with the command, not with an agent reading files. Long output — a suite, a build, a log — goes to `runner`: only the answer comes back. The rest goes first to `explorer` (repo) or `api-scout` (libraries, services, docs) at low cost to extract exact `file:line` and signatures, and the excerpts go to the expensive agents. **Scanning is not main-context work:** a broad task, a narrow answer, no judgment delegated (“of N files, which ones touch X” → a table) goes to `explorer` unless you already hold that context. What stays with you is work whose **judgment** is the product, not the scan that precedes it.
4. **Pass ranges, not files:** the prompt carries only excerpts and exact `file:line`.
5. **Prompt structure:** mandatory, section "How to write a delegation prompt".
6. **Load-on-demand:** pass pointers to resources and guides. The agent opens them if and when needed.
7. **One task per agent,** with a verifiable completion criterion. Zero umbrella tasks ("fix X"); a plan of ordered atomic tasks, each verifiable, counts as one. Split only what does not fit in one context: depth is an outcome, not a plan.
8. **Reuse the session, never re-spawn:** the agent that holds a task's context — the same task or a later one on the same files — stays open as long as that context is useful, and new work reaches it as a message with only what is new, not as a new agent that re-digests everything. Every message, though, re-reads its whole conversation: a touch-up of a few lines is done by the coordinator. An agent stopped at its turn limit is asked for its report the same way, in one line — not relaunched, not redone by hand; the limit reached says the question was too broad, and the next one is cut narrower.
9. **Proportionate review, one round only:** `final-reviewer` and double review only as § The code cycle, step 5 sets; otherwise the coordinator verifies with the tests. The critical-surface reviewer is outside this count. The final reviewer **or** a native review skill, never both; heavy native ones only at the user's request.
   - **Blocking finding** (security, data loss): it goes to the user, who decides.
   - **Fixes:** by whoever holds the picture — the coordinator, or the still-open agent that wrote that code; a finding that asks for new work becomes a task and follows the cycle. The reviewer does not fix and is not relaunched on the fixes: the coordinator verifies them with the tests.
   - **Verdict:** approved with reservations closes only if the user accepts them; a finding you discard gets a written reason.
10. **Zero useless re-verification:** `CLAUDE.md` § Zero redundancy, spawns included.
