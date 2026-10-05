## The content cycle

It runs alongside the code cycle, it does not replace it. Here the product is not software that runs but **attention earned**: a correct piece nobody opens is not a partial success, it is cost.

**Positioning → Packaging → Copy → Polish → Publication → Analysis → Positioning.**

1. **Positioning** (`market-researcher`): for whom, against which alternative, which promise. It is decided once and reopened only when the analysis disproves it: changing it with every piece wipes out recognition.
2. **Packaging** (`campaign-planner` with `visual-designer`): idea, title, image. Decided **before** the copy — it is what the audience sees first, and good copy in mute packaging is not opened. The **prediction** is written here too: what is expected, on which metric.
3. **Copy** (`copywriter`): the voice lives in `.claude/shared/domain/marketing-voice.md`, a replaceable default and not a rule of the method.
4. **Polish** (`copywriter`): in passes, one dimension at a time — clarity, evidence, objections, cuts and rhythm, the length of the channel — rechecking the earlier ones. Every claim stays attached to its evidence.
5. **Publication: the user does it.** The agent prepares the piece **and the measurement to collect**; the line goes into *Waiting* in `docs/TODO.md`, with what to report and when.
6. **Analysis** (`content-analyst`): the metrics are read against the prediction from step 2, never against the last piece. A delta inside the noise means no result, and it is said.

Rules of the cycle:

- **Claim review comes before publication:** `claim-reviewer` guards the critical surface and step 5 is irreversible — what has been read stays read even after the correction.
- **The goal lives in `docs/roadmap.md`, not in the prompt:** "until I reach N" is not a completion criterion — the outcome is not verifiable within the session and a single piece is dominated by noise. What closes is **the iteration**, with its prediction.
- **Nothing is republished to get back a number** already present in a summary: it is read from there.
