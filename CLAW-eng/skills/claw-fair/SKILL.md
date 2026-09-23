---
name: claw-fair
description: >
  Tunes the model and effort of the subagents of a project with the framework
  installed to the project's real scope — profile (web, software, research,
  data, llm, marketing, library) and described idea — instead of the source's
  one-size-fits-all values: raises where a mistake costs, lowers where you pay
  for a model the work does not ask for. Absolute ceiling opus/xhigh. Touches
  only the `model:` and `effort:` lines of the cards and the Model column of the
  roster; if the scope is neither described nor deducible it stops without
  changing anything. Use when the user wants to adjust, tune or review the
  agents' models and effort, cut the cost of subagents, or asks whether the
  agents have the right model for this project: `/claw-fair`.
---

# Claw-fair — the model the work asks for, in this project

The source gives every agent a model and effort meant for any project. A `security-reviewer` on Opus makes sense for a service with authentication, not for a static site; a `copywriter` on Sonnet is fine for a changelog, less so for the page that presents a person. Here each card is tuned to the scope of **this** project.

**What the written value becomes.** The card's value is the coordinator's default and its ceiling: the delegation rule «agent and model to the task» can only lower it at spawn, never raise it. Claw-fair moves that ceiling, up or down, within the absolute ceiling.

**The coordinator invokes it, at the user's request.** It writes nothing without the user's ok on the plan.

## Constraints — not negotiable

- **Only these change:** the `model:` line and the `effort:` line in the frontmatter of `.claude/agents/<agent>.md`, and the *Model* cell of that agent's row in the roster table. No other line of any file: not the method, not `## Project context`, not `framework.json`, not `CLAUDE.md` outside the table. A problem noticed elsewhere goes in the report, not in the diff.
- **Absolute ceiling: `opus` / `xhigh`.** Never `max`, even if the idea seems to ask for it: the cost of `max` has never been measured on these roles.
- **Allowed models:** `haiku` < `sonnet` < `opus`. **Never `fable`**: it is not available, the agent does not start and the doctor treats it as ERROR.
- **Allowed effort:** `low` < `medium` < `high` < `xhigh`. `xhigh` **only with `opus`**, and avoided: at most `architect`, with a concrete reason.
- **Agents without a card in the source** (created in the project): not touched, listed in the report.

## Step 0 — Is it a framework project?

`<PRJ>` is the project root. It needs `<PRJ>/.claude/framework.json`: if missing, the framework is not installed → say so and stop.

`<FW>` is its `source` field, which may be relative to the project root: resolve it with `source.dereference(<PRJ>, source)` from `<FW>/tools`, as the other lifecycle skills do. `<FW>/agents/` does not exist → stop: without the source value there is nowhere to start from.

The roster is the list of files in `<PRJ>/.claude/agents/`. The roster table is in `<PRJ>/.claude/shared/orchestration.md` (section `## This project's roster`, columns `| Situation | Agent | Model |`), or in `CLAUDE.md` if that guide is not there.

## Step 1 — Read the scope, or stop

Sources, in this order:

1. `profile` in `.claude/framework.json` — the domain.
2. `CLAUDE.md`, sections `## The project` and `## Critical surface` — the idea and where a mistake costs most.
3. `README.md`, `docs/` (roadmap, TODO) and, if there is any, the code: what the product does, who uses it, what it exposes on the network.

**Stop condition.** The profile alone is not enough: it is always there, and it says «web», not «static portfolio» or «e-commerce with payments». If `## The project` is empty or still contains `TO FILL IN`, **and** neither README, nor `docs/`, nor the code say what the product is → **stop without changing anything**. Tell the user what is missing and where it goes: `## The project` in `CLAUDE.md`, or the answer to the `claw-install` questionnaire. Tuning on the profile alone would give values different from the source with no reason to hold them up.

From the scope derive, one line each:
- **what is produced** (site, service, pipeline, evidence, text);
- **the critical surface**, as the project declares it;
- **what the project does not have**: no backend, no personal data, no automated tests, no external audience. It is often this that justifies a lowering.

## Step 2 — Starting values

For each installed agent, one row:

| agent | source | current |
|---|---|---|
| `frontend` | opus / medium | opus / medium |

- **source**: `model:` and `effort:` of `<FW>/agents/<agent>.md`.
- **current**: the same lines in the project's card.

**Always reason from the source, never from the current value.** A second run must give the same result as the first, not move the values again at every round. If current ≠ source, the difference comes from a previous claw-fair or from a hand: it is flagged in the plan, not added up.

## Step 3 — Tuning

Each agent starts from the source value and moves only if **the scope gives a concrete reason**, written in one line that names a fact from Step 1. «To be safe» or «to save» are not reasons: «the site has no backend and no forms» or «the bio is the first text a recruiter reads» are. Without such a reason the value stays the source's: it is the expected result for most agents.

### Four questions per agent

1. **How close is it to the critical surface?** An agent that produces or judges what the project declared critical is kept high, or raised. One that works on a part that in the project does not exist, or barely does, is lowered.
2. **What kind of work does it do?** «Find and list» holds on `haiku`. «Classify, judge, compare» does not: it asks at least `sonnet`. «Decide a structure», «find an unknown cause», «be the last check before saying done»: `opus`.
3. **How much does its mistake cost, and who catches it?** A mistake that a reviewer downstream stops costs one more round; one that reaches the user or the network costs more. Lower where there is a safety net, not where you are the last one.
4. **How often does it work?** An agent used constantly on routine tasks weighs on cost, and lowering it pays. One called rarely for critical cases costs little even on `opus`: lowering it saves little and risks a lot.

**Model and effort are two different levers.** The model decides *whether* a task is within reach. Effort decides *how deeply* it reasons on a task that is within reach: it serves those who follow long causal chains (diagnosis, plan, review), much less those who do repetitive work. If an agent fails for lack of capability, raise the model, not the effort.

### Invariants

- **A reviewer is not weaker than what it reviews.** If `frontend` is `opus`, `final-reviewer` does not drop to `sonnet`. If `implementer` goes up to `opus`, the same holds for the reviewer of its work.
- **`explorer` stays `haiku`.** Its work is the use case of the light model; raising it multiplies the cost of reconnaissance.
- **Never below the declared work.** If an agent's card gives it decisions or judgements, `haiku` is not enough, whatever the profile.

### Where to look by profile

A starting point for question 1, not a table to apply: the described idea always wins. It holds only for installed agents: a profile does not bring them all.

| profile | usually at the centre | usually at the margins |
|---|---|---|
| `web` | `frontend`, `final-reviewer` | `security-reviewer` if the site is static, `silent-failure-hunter` without I/O |
| `software` | `architect`, `debugger`, `security-reviewer` | `copywriter`, `visual-designer` |
| `library` | `architect` (the public contract is the product), `tester` | `deploy`, `frontend` |
| `data` | `data-ingestion`, `data-quality-reviewer` | `frontend`, `copywriter` |
| `research` | `scientific-reviewer`, `results-analyst` | `deploy`, `frontend` |
| `llm` | `results-analyst`, `scientific-reviewer` | `visual-designer` |
| `marketing` | `copywriter`, `claim-reviewer`, `market-researcher` | `debugger`, `refactorer` |

### Example

Static portfolio, design-award ambition, no backend, published on static hosting:

| agent | source | proposed | why |
|---|---|---|---|
| `security-reviewer` | opus / high | sonnet / high | no backend and no forms: the surface is headers and dependencies |
| `copywriter` | sonnet / high | opus / medium | bio and project descriptions are few lines carrying the whole first impression |
| `architect` | opus / high | opus / medium | the structural decisions of a static site are few and shallow |
| `frontend` | opus / medium | opus / medium | — (at the centre: stays) |

## Step 4 — Plan, then ok

Show the user **a single table**, with every installed agent, including those that do not change:

| agent | source | current | proposed | why |
|---|---|---|---|---|

Below the table, three lines:
- how many agents change, and how many go up and how many go down;
- the agents not touched because they do not exist in the source;
- **what happens next:** at every `claw-sync`, each card different from the source is named and sync asks whether to bring it back to the source value. To keep the tuning, answer no.

Ask with the multiple-choice tool: apply all / apply only some (which) / cancel. **No writing without an answer.** Cancel → stop: it is not a failure.

A partial selection can break an invariant — raising `frontend` without `final-reviewer`. In that case say so before writing, with the pair involved, and ask again.

All proposed values equal the current ones → say so and stop, without asking anything.

## Step 5 — Apply

For each approved agent whose value changes:

1. In the card, replace **the whole line** `model: <old>` with `model: <new>`, and the same for `effort:`. Format unchanged — key, colon, one space, value — because sync reads them with `^(model|effort):[ \t]*(\S+)[ \t]*$`. If `effort:` is missing, add it right after `model:`.
2. In the roster table, replace the value **in the third column** of the row that has the agent in backticks in the second. The second column is a contract (the doctor reads the agent's name there): not touched.

Before writing, read the file: if the expected line is not there, or differs from the one in the plan, stop on that file and report it. Do not guess where to put it.

## Step 6 — Verify, then report

**Verify that the diff is only the promised one.** Before the changes copy every file you will touch into a temporary folder outside the project; afterwards, compare line by line (the stdlib's `difflib` is enough). Every changed line must be a `model:`/`effort:` line of a card, or a roster row in which only the third cell changed. Any other difference → restore the file from the kept text and report it as an error.

Then `doctor`, as at the close of `claw-sync`: from `<FW>/tools`, `python -m fwbuild doctor <PRJ>`, run before writing too: only a finding that was not there before counts. It is reported, not fixed outside the allowed lines.

Then the report to the user, short:
- the final table `agent | before | after`;
- the files touched;
- the result of the diff check;
- what stays unmeasured: nobody has verified that quality holds where it was lowered. The first signal is wasted rounds — an agent coming back with wrong or incomplete decisions. In that case raise that card, not all of them.
