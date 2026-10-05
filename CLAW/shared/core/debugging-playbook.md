# Diagnosis playbook

Symptom → suspects map: it serves to **narrow down**, not to jump to the hypothesis. Every suspect must be confirmed with evidence on the real flow before touching a line.

## Map

| Symptom | Suspects, in order |
|---|---|
| Works the first time, then not | residual state in memory or on disk · cache · connection or resource not released · index or counter not reset |
| Works locally, not in the real environment | difference in configuration or environment variables · different version of a dependency · relative paths · permissions · system time zone or locale |
| Fails only sometimes | race between threads or processes · order dependency · timeout too tight · non-deterministic test data · clock or random generator not seeded |
| Fails only with real data | volume beyond expectations · null or absent values not accounted for · encoding · out-of-domain values · duplicates · limits reached |
| The test passes but the program does not | the test verifies a fake, not the real thing · different test environment · the real path is not the tested one |
| The test fails but the program works | the assertion checks an internal detail that changed · state left by another test · dependency on execution order |
| No error, wrong result | error swallowed by a catch block · return value ignored · condition always true or always false · comparison between different types · logical shortcut skipping the computation |
| Nothing is broken and nothing happens | a later call resets the state written by the earlier one, each correct on its own · side effect on shared state · asynchronous calls resolved in reverse order |
| Error far from the cause | wrong value produced much earlier and propagated · no validation at the boundary · an absent value treated as a valid default |
| Suddenly slow | complexity exploding past a data threshold · a call inside a loop that used to be outside · missing index · serial I/O waiting where parallel was needed · a cache that stopped working |
| Consumes memory without stopping | structure that grows and is never emptied · references retained · unbounded cache · resources not closed |
| Fails only after a release | migration not applied or half applied · new configuration missing in the environment · old data incompatible with the new code |

## Techniques, in order of cost

1. **Read the code of the real path**, not the one that looks relevant by name.
2. **Bisection** — on the data (half the input), on history (which change introduced it), on the path (where the value is still right and where it is no longer).
3. **Make the state observable** at the suspected boundary, instead of deducing it.
4. **Reduce to the minimal case** that reproduces: every element removed that leaves the defect is excluded from the diagnosis.
5. **Compare two runs**, one that works and one that does not: what counts is the **first** difference, not the last.

## Traps

- **Hunting for confirmations of a single hypothesis:** formulate two and ask yourself which observation distinguishes them.
- **Confusing coincidence and cause:** if the explanation does not cover *all* the symptoms, it is not the cause yet.
- **Fixing the symptom:** a check that avoids the error while upstream the wrong value keeps being produced.
- **Trial-and-error fixes:** they cost more than the diagnosis and leave unmotivated changes in the code.

## In this project

[TO FILL IN — the faults already seen and their real cause, where the logs live
and how they are read, what is reproducible locally and what is not, which
states persist between runs, which components are already known to be fragile.]
