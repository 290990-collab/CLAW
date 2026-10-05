# Guide to systems with LLMs

For projects in which a language model produces text, decisions or actions that the code uses. The model does not fail like code: it fails plausibly, and sometimes because someone asked it to.

## Trust

- **The model's output is untrusted input:** it is validated like external data — schema, types, ranges, allowed values — before being used, executed or stored.
- **Hard limits live in the code, never in the prompt:** amounts, quantities, recipients, permissions are enforced downstream of the output, whatever the model wrote.
- **External data in a prompt that can act is an injection:** documents, pages, names, tool responses carry instructions. Where the model acts, they enter delimited and filtered, or they do not enter.
- **Independent layers of defence:** prompt hygiene, limits in code, simulation before the effect, isolation of credentials. No layer is enough, and none assumes another one held.

## Agents

- **An agent's limits are set by the caller:** budget, permissions and tools are decided before delegating; the agent does not raise them and has no tool to do so.
- **Narrow tools:** schema-bound input, fixed-shape output, errors that say how to retry and when to stop. High-risk operations have a tool of their own.

## Deterministic first

- **The model works on the residue:** what a rule, a parser or a query resolves does not go through the model; the model takes only the cases the deterministic part does not cover.
- **Confidence routes:** deterministic extraction declares how sure it is; above the threshold it goes out directly, below it goes to the model or to a person. The threshold is measured on real cases.

## Evaluation

- **Repeatable evaluation before touching the prompt:** a fixed set of cases with the expected outcome, run before and after every change. Without it, a better prompt is an impression.
- **Several attempts, not one:** the output varies across runs. Measure how many succeed out of k attempts; on critical paths they must all succeed.
- **Judge in code where it is enough:** if a deterministic check decides the outcome, it is not asked of a model.
- **What used to pass stays in the set:** a regression only shows on the cases that worked.

## In this project

[TO FILL IN — where the model enters the flow and what it can do, which
external data reaches the prompts, the limits enforced in code and where they
live, who sets the agents' permissions and budgets, the evaluation set and how
it is run, the injections and errors already seen.]
