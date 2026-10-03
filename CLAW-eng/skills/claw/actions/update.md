# `/claw update` — bringing the source's version into the project

The source is updated from the terminal, `claw update`; this action brings its version into the project. Two steps on purpose: every project moves only when someone opens it.

1. **What arrives:** `python "<FW>/claw.py" status "<PRJ>"` — the two versions and the commits between them. The source behind its release (`N behind`) → tell the user to run `claw update` in a terminal first, then continue.
2. **Diagnosis first.** A `KERNEL_DRIFT` is resolved *before*: the plan says "edited by hand: the local change is lost". Promote it (`/claw share`) or let it go, by the user's word.
3. **Plan:** `down "<PRJ>" [--hooks a,b] [--adopt a,b|all]`.
   - **Hooks:** the ones in use are kept. On a project with none, **one question** — does it want them, `gateguard` included? — and a yes becomes `--hooks`.
   - **Card front matter** (`model`, `effort`, `description`, `maxTurns`, …): a value the project still has as recorded at the last sync follows the source; a different one is a local choice (a `/claw tune`, a hand) and stays — the plan names both. **Without a record** (installations older than the record) every difference stays and is named: ask the user card by card, yes → `--adopt <card>`.
   - **A guide a new card cites** arrives from the source: fill in its block and add its line in `CLAUDE.md § Shared guides`.
   - **Guides and style** take the source text and keep the project block; without a recognisable block they are `keep`: updated by hand, comparing with the source.
4. **After the ok, `--apply`:** regions, cards, roster cells that still say the old model, guides, style, skills, hooks, `settings.json`, manifest (version, source, record) — everything computed before the first write. It closes with the doctor, which must show no findings.

**Conflicts are presented, they do not resolve themselves:** on a region modified locally the user sees both versions and decides.

---

## When `claw update` stops on a conflict

The master is a git clone: a release is its tracked branch, a promotion (`/claw share`) a local commit. `claw update` merges it; uncommitted changes in the master stop it first — commit them (they are promotions) or discard them, by the user's word.

**On conflict the merge stays open, one file at a time:** read the three versions — base, yours, new (`git show :1:<file>`, `:2:`, `:3:`) — and propose a merge that keeps your addition *inside* the new text, not beside it. If the new text already covers it, take that and say so. No conflict is resolved without showing the user what they lose. `VERSION` is not a conflict: the release's wins. Then `git commit`.

Then the projects: `/claw update` in each one that is behind.

**A source that is not a clone** (copied into a project): get the release into `<NEW>` and the base — the release your copy came from, `upgrade.base_version(<FW>)` — into `<BASE>`, then `upgrade.classify(<BASE>, <FW>, <NEW>)`: `same` and `theirs` come from the release, `yours` stays, `conflict` is handled as above; after it, `upgrade.write_record` with the release just taken. No commit declares the base → stop and ask. It works in place with no undo: copy the source aside first.
