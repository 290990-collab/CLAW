# Testing guide

The principle — **few meaningful tests, never many weak ones** — lives in the method. Here, how to apply it.

## How a test is chosen

**Which plausible defect would make it fail?** With no answer the test is of no use; if the answer is "none, it checks that the code exists", it is a test not to write.

A useful test fails when the behaviour is wrong, passes when it is right, and does not change when only the implementation changes. If a behaviour-preserving refactoring breaks it, it was verifying internal details.

## The right level

| The risk is… | The test goes… |
|---|---|
| a computation or transformation rule | on the unit, with real edge cases |
| the interaction between two modules | on the junction, with both real |
| a contract towards the outside | on the contract: shape, fields, compatibility |
| behaviour with real dirty data | on a real sample, not an ideal one |
| an end-to-end flow | one or two critical paths, not all of them |
| an access control | with another authenticated user's id, not only without credentials |
| hashes, encodings, arithmetic | against a known answer computed outside the code, never against its output |

Most common error: testing everything at the most convenient level — the unit — leaving uncovered the level at which defects really arise.

## Invariants before examples

An invariant covers infinite cases and does not age:

- **idempotence:** applying twice gives the same result as once;
- **round-trip:** serialise and read back, you get the original;
- **stability:** equivalent inputs give identical outputs, across runs too;
- **conservation:** no element lost or duplicated in a transformation;
- **monotonicity:** adding cannot decrease the result;
- **error handling:** a failure leaves no partial state.

## What not to do

- Tests that replicate the implementation line by line: they break at every change and find nothing.
- Assertions on log messages or on non-contractual formatting.
- Dependencies on execution order or on state left by another test.
- Fakes so permissive that anything passes: they verify the fake, not the real thing.
- Fixed time waits instead of a condition: slow and flaky.
- Weakening an assertion to make a red test pass.

## When a risk is not testable

Visual rendering, performance on real hardware, integration with an external service, behaviour under load: you do not compensate with unit tests that miss the point. The risk goes into `UNVERIFIED` with the **manual verification steps**, repeatable by anyone.

The same holds for an impractical test-first — heavy harness, state that exists only in production, vague reproduction: it is not skipped silently. You say why and name the nearest executable check — a targeted script, a command that reproduces, an output comparison — which is worth more than a test written to respect the form.

## In this project

[TO FILL IN — test run command, framework in use, where the tests live and how
they are named, what is excluded by nature and how it is verified instead, run
times, test data available, defects already seen that have a dedicated
regression.]
