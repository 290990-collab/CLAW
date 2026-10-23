# `/claw update` — bringing the source's version into the project

This action brings the source's version into the project. Every project moves only when someone opens it.

1. **Diagnosis first.** A `KERNEL_DRIFT` is resolved *before*: the plan says "edited by hand: the local change is lost". Let it go, by the user's word.
2. **Plan:** `down "<PRJ>" [--hooks a,b] [--adopt a,b|all]`.
   - **Hooks:** the ones in use are kept. On a project with none, **one question** — does it want them, `gateguard` included? — and a yes becomes `--hooks`.
   - **Card front matter** (`model`, `effort`, `description`, `maxTurns`, …): a value the project still has as recorded at the last sync follows the source; a different one is a local choice (a `/claw tune`, a hand) and stays — the plan names both. **Without a record** (installations older than the record) every difference stays and is named: ask the user card by card, yes → `--adopt <card>`.
   - **A guide a new card cites** arrives from the source: fill in its block and add its line in `CLAUDE.md § Shared guides`.
   - **Guides and style** take the source text and keep the project block; without a recognisable block they are `keep`: updated by hand, comparing with the source.
3. **After the ok, `--apply`:** regions, cards, roster cells that still say the old model, guides, style, skills, hooks, `settings.json`, manifest (version, source, record) — everything computed before the first write. It closes with the doctor, which must show no findings.

**Conflicts are presented, they do not resolve themselves:** on a region modified locally the user sees both versions and decides.
