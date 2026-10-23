# `/claw tune` — the model the work asks for, in this project

The source gives every agent a model and effort meant for any project; here each is tuned to **this** one. The card's value is the coordinator's default and ceiling: the delegation rule «agent and model to the task» can only lower it at spawn. Tuning moves that ceiling, within the absolute one.

**The coordinator runs it, at the user's request. Approving the table of Step 4 is the explicit request for the `user-rules.md` lines it contains** (`actions/rule.md`); nothing is written without it.

## Constraints

- **Only these are written:** `model:` and `effort:` lines in the agent's section of `<PRJ>/.claude/user-rules.md`. The cards and the roster cell are regenerated from them. Nothing else in any file; a problem noticed elsewhere goes in the report.
- **Absolute ceiling `opus` / `xhigh`.** Never `max`: its cost on these roles is unmeasured.
- **Models:** `haiku` < `sonnet` < `opus`. **Never `fable`**: it bills outside the plan; only the user sets it.
- **Effort:** `low` < `medium` < `high` < `xhigh`; `xhigh` only with `opus`, and avoided: at most `architect`, with a concrete reason.
- Agents with no row in `<FW>/cards/agents.toml` (created in the project): untouched, listed in the report.

## Step 0 — Installed?

`<PRJ>/.claude/claw.json` missing → not installed, stop. The roster is its `agents`.

## Step 1 — Scope, or stop

Read in order: `profile` in `claw.json`; `CLAUDE.md` (`## The project`, `## Critical surface`); `README.md`, `docs/` and the code (what it does, for whom, what it exposes on the network).

**Stop** if the profile is all there is — it says «web», not «static portfolio» or «e-commerce with payments»: `## The project` empty or absent **and** README, `docs/`, code silent. Change nothing; say where the scope goes (`## The project` in `CLAUDE.md`, or the `/claw install` answers). Tuning on the profile alone gives different values with nothing to hold them.

Derive, one line each: what is produced · the critical surface as the project declares it · what the project does not have (no backend, personal data, automated tests, external audience) — often what justifies a lowering.

## Step 2 — Starting values

One row per installed agent:

| agent | source | current |
|---|---|---|
| `frontend` | sonnet / medium | sonnet / medium |

- **source**: the agent's row in `<FW>/cards/agents.toml`.
- **current**: the source row with the `model:`/`effort:` lines of its `user-rules.md` section applied.

**Reason from the source, never from the current value:** a second run gives the same result. current ≠ source comes from an earlier tune or a hand-written override: flagged in the plan, not added up.

## Step 3 — Tuning

An agent moves only if **the scope gives a concrete reason**, one line naming a fact from Step 1. «To be safe» and «to save» are not reasons; «no backend and no forms» and «the bio is the first text a recruiter reads» are. Otherwise it keeps the source value, the expected result for most.

Four questions per agent:

1. **Distance from the critical surface:** what produces or judges it stays high or goes up; what works on a part the project lacks goes down.
2. **Kind of work:** «find and list» holds on `haiku` at `medium`, never `low` (it skips searches on a long prompt); «classify or extract into fixed categories, with evidence» on `haiku` at `high`; «judge, compare» without fixed categories at least `sonnet`; «decide a structure», «find an unknown cause», «last check before done» `opus`.
3. **Cost of its mistake, and who catches it:** lower where a reviewer downstream stops it, not where it is the last one.
4. **How often it works:** constant routine work weighs on cost, lowering pays; a rarely-called critical agent costs little even on `opus`.

Model decides *whether* a task is within reach; effort *how deeply* it reasons on one that is — it serves long causal chains (diagnosis, plan, review), little repetitive work. Failing for lack of capability → raise the model.

**Invariants:** a reviewer is not weaker than what it reviews (`frontend` on `opus` → `final-reviewer` not `sonnet`; same for `implementer`) · `explorer` stays `haiku` / `medium` · never below the declared work: a card with decisions or open judgements is not `haiku`.

Where to look by profile (starting point for question 1; the described idea wins; installed agents only):

| profile | usually at the centre | usually at the margins |
|---|---|---|
| `web` | `visual-director`, `frontend`, `final-reviewer` | `security-reviewer` if static, `silent-failure-hunter` without I/O |
| `software` | `architect`, `debugger`, `security-reviewer` | `copywriter`, `visual-designer` |
| `library` | `architect` (the public contract is the product), `tester` | `deploy`, `frontend` |
| `data` | `data-ingestion`, `data-quality-reviewer` | `frontend`, `copywriter` |
| `research` | `scientific-reviewer`, `results-analyst` | `deploy`, `frontend` |
| `llm` | `results-analyst`, `scientific-reviewer` | `visual-designer` |
| `marketing` | `copywriter`, `claim-reviewer`, `market-researcher` | `debugger`, `refactorer` |

Example, static portfolio with design-award ambition, no backend:

| agent | source | proposed | why |
|---|---|---|---|
| `security-reviewer` | opus / high | sonnet / high | no backend, no forms: headers and dependencies |
| `copywriter` | sonnet / low | opus / medium | bio and descriptions carry the whole first impression |
| `visual-director` | opus / medium | opus / medium | — (at the centre: stays) |

## Step 4 — Plan, then ok

One table, every installed agent, unchanged ones included:

| agent | source | current | proposed | why |
|---|---|---|---|---|

Below it: how many change, up and down · agents untouched (no source row) · **what happens next**: tuned values live in `user-rules.md`, survive every `/claw update`, and a value equal to the source's is removed from the file.

Ask with the multiple-choice tool: apply all / apply some (which) / cancel. No writing without an answer; cancel is not a failure. A partial selection breaking an invariant (`frontend` up without `final-reviewer`) → say so with the pair, ask again. Nothing changes → say so, stop.

## Step 5 — Apply

Read `user-rules.md`; for each approved agent, in its `## <agent>` section (created at the end if missing):

- proposed ≠ source → set `model: <v>` and `effort: <v>` (one line each, key, colon, one space);
- proposed = source → remove the line; the heading too if nothing else is left.

No other line of the file changes. Then `python "<FW>/claw.py" update "<PRJ>" --keep-version`; refused → plan and ok, as `actions/rule.md` step 4.

## Step 6 — Verify, report

The plan printed by `--keep-version` may `overwrite` only the tuned agents' cards and `.claude/shared/orchestration.md` (their roster cells); any other path → report it as an error. Run `doctor` before writing too: only a finding that was not there before counts, reported and not fixed here.

Report: final table `agent | before | after`; files touched; what stays unmeasured — nobody has verified that quality holds where it was lowered; the first signal is wasted rounds (wrong or incomplete decisions from an agent): raise that card, not all.
