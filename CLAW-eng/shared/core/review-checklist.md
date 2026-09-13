# Review checklist

Reference material for whoever reviews. Two blocks, **separate and not merged** — generic and project-specific: keeping them distinct is what makes it possible to update the framework without losing the specific entries, and vice versa.

**Severity:** blocks (security, data loss) · warns (defect, serious quality issue) · informs (maintainability) · note (style). Outcome: **approved** with no finding that blocks or warns · **approved with reservations** with warnings only, and it closes only if the user accepts them · **rejected** with a blocking finding. In the reviewer cards HIGH = blocks, MEDIUM = warns, LOW = informs.

---

## Generic block — correctness (valid everywhere)

### Scope

- Do the changes do **everything** the task asked?
- Do they do **only** that? Unrequested extra work is a finding even if it is good code: it widens the risk surface without a mandate.
- One problem at a time, or several things interleaved in the same change?

### Values and boundaries

- Null or absent values: handled where they can arrive, or assumed present?
- Empty collections, empty string, zero, negative value: what happens?
- Indexes and ranges: first and last element, single-element range, empty range.
- Numeric conversions: truncation, exceeding limits, floating point used where exact precision is needed.
- Text: declared encoding, characters outside the Latin alphabet, maximum lengths, normalisation before comparison.
- Dates and times: explicit time zone, daylight saving, comparisons between instants with different representations.

### Errors

- Is every error handled or propagated **deliberately**? No empty catch block and none that hides the original exception.
- Does an error midway leave partial state? If so, is it recoverable?
- Do error messages say enough to diagnose, without revealing internal details or sensitive data?

### Resources and concurrency

- Files, connections, locks: released on the error path too?
- Subscriptions, timers, listeners: closed when their owner ends?
- Structures shared between threads or processes: access protected, or race possible?
- Long work run where it does not block what must stay responsive.
- Loops over external resources: is there a limit, a timeout, a maximum number of attempts?

### Regressions and contracts

- For every symbol or behaviour changed: who uses it? Searched also where the compiler does not look — markup, configuration, scripts in other languages, string references, documentation.
- Do formats already written to disk still read back?
- Do external consumers stay compatible? If not, is the migration planned?
- Do changed public signatures have every side updated?
- Text shortened, merged or moved: did the enforcement survive — obligations, checks, defaults? Compression removes it first, because it reads as repetition.

### Tests

- Do they exist, do they run, and have they been **seen failing** on the code without the change? One that would pass with the defect present does not count.
- Do they assert behaviour or only that the code does not blow up?
- Do they cover the level at which the defect can arise, not only the most convenient unit?

### Verifications run

- Build run, not deduced. Tests run, not deduced. Real output in hand.
- What was not verified is declared as such, with the steps to do it.

---

## Project block

[TO FILL IN — the entries specific to this project: classes of regression
already seen, delicate surfaces requiring extra attention, mandatory manual
checks before saying "done", platform or runtime constraints to re-check at
every change.]
