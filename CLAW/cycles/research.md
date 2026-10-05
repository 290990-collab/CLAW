## The research cycle

It runs alongside the code cycle, it does not replace it. Here the product is not "software that runs" but **reproducible evidence**: a program that runs and produces wrong numbers is a complete failure.

**Hypothesis → Protocol → Execution → Analysis → Conclusion.**

1. **Hypothesis** explicit and **falsifiable**, with the expected mechanism and a prediction *per dimension* — "I expect X to rise and Y **not** to, because…". An articulated prediction makes even a negative outcome informative; a generic one makes even a positive outcome useless.
2. **Protocol** (`architect`): declared baseline, **one variable only**, success criterion decided **before** looking at the results, estimated cost, what is reused instead of recomputed.
3. **Execution:** if it is heavy, **the user** launches it. The agent prepares the exact command and writes into `docs/TODO.md` the waiting line with *what that run must answer*.
4. **Analysis** (`results-analyst`): paired comparison, delta against noise, reading per dimension, and **why** — never just "it went up".
5. **Conclusion:** hypothesis **confirmed or refuted**, written as such in `docs/status.md`. Refutations are recorded with the same care as confirmations: not recording them means paying their cost again in two months.

⚠️ **The two cycles interleave**: often you change the code **in order to** measure. Then the `architect` produces a plan with both sections, and the review includes the `scientific-reviewer` **before** the `final-reviewer` — "the code is correct" and "the number means what we say it means" are two different questions.

**You do not relaunch** a run to get back a number already present in a log or a summary: you read it from there. This holds for the coordinator that delegates too.
