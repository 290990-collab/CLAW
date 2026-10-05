# Performance guide

How to measure and optimise code with a declared performance threshold. Without a threshold only the first point of the optimisation order applies.

## Measurement

- **No claim of speed without a measurement:** a number estimated from memory or read off a label is not data.
- **Percentiles, not averages:** p50, p95 and p99 over several runs, with the spread. The best value and the single run are not measurements.
- **Separate metrics:** latency, throughput, data freshness, queue depth, cache hits, correctness under load. "Fast" is not a metric.
- **Representative input:** volume and shape of the real data, not the ideal case.

## Hot path

- **Write down the path from the event to the visible state, in segments:** source, ingress, queue, cache, transport, rendering.
- **Each segment is measured on its own:** the total says that time is lost, not where.

## Optimisation order

1. **Complexity before the constant:** an `O(N²)` where `O(N log N)` was needed counts more than any micro-optimisation.
2. **Remove unnecessary round trips.**
3. **Cache stable reads, with their age.**
4. **Batch small calls and writes.**
5. **Compute close to the data or to whoever uses it.**
6. **Separate the hot path from the cold one.**
7. **Backpressure before a queue grows without limit.**

## Guardrails

- **Correctness comes first:** no optimisation removes a mandatory validation or puts data integrity at risk.
- **No stale data hidden behind a fast cache:** the read carries its age, and past the threshold it says so.
- **Every optimisation has a declared price:** readability, memory, complexity.
- **Logs and measurement artefacts without secrets or private data.**

## In this project

[TO FILL IN — the operations with a threshold and its value, the hot path
written in segments, the command that measures reproducibly, the optimisations
already discarded with the reason.]
