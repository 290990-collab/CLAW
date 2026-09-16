# Research principles

For projects whose product is not "software that runs" but **reproducible evidence**.

> **Guiding principle.** Every decision is motivated by data, experiments or literature; every result is explainable, reproducible and verifiable by others.

## Evidence and honesty

1. **Evidence first** — every technical statement rests on a measurement, a source or an experiment, never on a plausible supposition.
2. **Facts, interpretations and ideas stay separate**, typographically too: confusing them is the most common way of writing something false without lying.
3. **Explicit assumptions** about problem, data and model: the unspoken ones are the ones that turn out to be wrong.
4. **Negative results are reported:** a refuted hypothesis is acquired information, hiding it means paying its cost again later.
5. **Scepticism towards your own improvements:** a gain is a hypothesis to verify, not an acquired result.
6. **Strengths and weaknesses are both reported:** work that exposes only its strong points cannot be assessed.

## Experimental method

7. **Baseline before complexity** — first the simple reference, even trivial or random. Without the right denominator a gain can be overestimated by an order of magnitude.
8. **One variable at a time:** changing two, the effect is not attributable and the experiment is wasted.
9. **Every added component must be justified by an ablation:** if removing it changes nothing, it was not needed.
10. **The success criterion is decided before** looking at the results. Deciding it afterwards is choosing the conclusion.
11. **Measurement against intuition:** the metrics decide, not the feeling that something "should" work better.
12. **Fair comparisons:** same data, same protocol, same exclusions, model capacity declared when it differs.
13. **Respect significance:** differences of the order of the noise are not results until the contrary is shown.
14. **Error analysis before improvement:** understanding *how* it fails precedes the attempt to make it fail less.
15. **Understand before optimising.**

## Data integrity

16. **The test set selects nothing:** hyperparameters, variants and checkpoints are chosen on validation; the test set is touched once, for the final number.
17. **Normalisation statistics from the training set alone.**
18. **Beware circularity:** if the model receives as input what the ground truth measures as output, on that dimension the result is an upper bound, not a performance. It must be declared every time.
19. **Do not optimise for a single benchmark:** what comes out of it measures the benchmark, not the problem.

## Reproducibility

20. **Seeds and sources of randomness fixed and declared.**
21. **Configuration outside the code**, versioned together with the result it produced.
22. **Every reported number must be traceable:** which configuration, which run, which file. A number without provenance is not citable.
23. **Do not relaunch an experiment** to get back a number that already exists in a log or a summary.

## In this project

[TO FILL IN — the current research hypothesis, which sets exist and which
selects what, the metrics adopted and what they can hide, the baselines
available, the known circularities, who launches the heavy runs and how, where
the results are written.]
