---
name: claw-sync
description: >
  Aligns an installation with the source framework: brings a new version of the
  method down while preserving the adaptation, promotes a local change up so
  the next project inherits it, activates or deactivates an agent or a guide,
  changes the orchestration, puts back what is missing, uninstalls. Use when a new version comes out, when
  a local change deserves to become general, when an installation has lost
  files or must be removed.
---

# Synchronisation with the source

Connects the **source** (the master) to the **installations** (the projects). The source must be reachable from the machine; if it is not, only `doctor` works.

`<PRJ>` is the project root; `<FW>` is the `source` field of `.claude/framework.json`, relative to `<PRJ>` when not absolute. `--down`, `--up`, `--upgrade`, `--activate`, `--deactivate`, `--repair`, `--uninstall` are **modes of this skill**; the commands they run:

```bash
python "<FW>/claw.py" status "<PRJ>"              # versions, doctor, commits between them
python "<FW>/claw.py" <down|repair|uninstall> "<PRJ>" [options]   # plan: printed and saved, nothing written
python "<FW>/claw.py" <down|repair|uninstall> "<PRJ>" --apply     # after the ok: runs that plan
python "<FW>/claw.py" report <folder>             # divergence across many repositories, modifies none
```

**Every mode that writes shows the plan first and waits for the ok.** `--apply` runs the saved plan of that project, mode and source, never a recomputed one; every file is re-checked and a tree changed after the ok stops everything before the first byte. A plan runs once.

---

## `--down` — bringing a new version into the project

1. **What arrives:** `status` — the two versions and the commits between them.
2. **Diagnosis first.** A `KERNEL_DRIFT` is resolved *before*: the plan says "edited by hand: the local change is lost". Promote it (`--up`) or let it go, by the user's word.
3. **Plan:** `down "<PRJ>" [--hooks a,b] [--adopt a,b|all]`.
   - **Hooks:** the ones in use are kept. On a project with none, **one question** — does it want them, `gateguard` included? — and a yes becomes `--hooks`.
   - **Card front matter** (`model`, `effort`, `description`, `maxTurns`, …): a value the project still has as recorded at the last sync follows the source; a different one is a local choice (a `claw-fair`, a hand) and stays — the plan names both. **Without a record** (installations older than the record) every difference stays and is named: ask the user card by card, yes → `--adopt <card>`.
   - **Guides and style** take the source text and keep the project block; without a recognisable block they are `keep`: updated by hand, comparing with the source.
4. **After the ok, `--apply`:** regions, cards, roster cells that still say the old model, guides, style, skills, hooks, `settings.json`, manifest (version, source, record) — everything computed before the first write. It closes with the doctor, which must show no findings.

**Conflicts are presented, they do not resolve themselves:** on a region modified locally the user sees both versions and decides.

---

## `--up [what]` — promoting a local change into the source

**Precondition: the project must be aligned with the source.** If `version` in `.claude/framework.json` is not the one in `<FW>/VERSION`, run `--down` first, then promote. From a project left behind, the local region differs from the source for **two** reasons — your change, and the one another project has already promoted — and step 1 does not tell them apart: promoting wholesale deletes the second one silently. Aligned means base and source coincide, and it is the only condition in which a two-tree comparison is correct.

`[what]` names **one** change. With no argument, list what can be promoted and go **one thing at a time**: step 2 has to be asked case by case, and a wholesale promotion cannot ask it.

1. **Locate the change:** `doctor` flags it as `KERNEL_DRIFT`; the content is obtained by comparing the project's kernel region with the corresponding source. **Drift does not see new files:** only `CLAUDE.md`, `orchestration.md` and the agent cards have a kernel region, so also list the files that sit in the project's `.claude/shared/` or `.claude/agents/` and are missing from the source, and the hooks in `.claude/hooks/` that differ from their original. A guide added by hand can be promoted and no finding names it.
2. **Ask whether it holds for everyone.** An improvement to the method goes up, a derogation specific to that project does not: the question is put to the user, not decided.
3. **Apply it to the source**, and the choice of destination is **by
   recipient**:

   | the change concerns… | it goes in |
   |---|---|
   | what holds for anyone executing a task | `<FW>/method/` |
   | when to delegate, to whom, with what prompt, the project's state | `<FW>/coordinator/` |
   | the mandate of a specific role | `<FW>/agents/<name>.md` |
   | reference material of a domain | `<FW>/shared/` |
   | a check the agent must not be able to skip | `<FW>/hooks/`, and its entry in `<FW>/tools/fwbuild/settings.py` |

   Getting this wrong costs: a delegation rule in `method/` is paid by every subagent at every spawn without being usable; an execution rule in `coordinator/` will never be seen by whoever executes.
4. **Increment `<FW>/VERSION`:** correction → patch; new or reworded rule → minor; structural change → major. A source that is not a git clone records its base first, once: `upgrade.write_record(<FW>, <its VERSION>, <edition folder>, <repository URL>)`.
5. **Commit it in the master**, the message saying what changed: it is what `status` shows whoever updates, and what `--upgrade` carries through the next release.
6. **Realign the originating project** with `--down`, so the hash matches again.

---

## `--upgrade` — bringing a new release into the master

The master is a git clone: a release is its tracked branch, a promotion (`--up`) a local commit.

1. `python "<FW>/claw.py" upgrade` — fetches, lists the incoming commits and the uncommitted changes. Uncommitted changes are promotions not yet committed: commit them first, or discard them by the user's word.
2. After the ok, `upgrade --apply` — merges: fast-forward, or a merge commit that keeps your commits. Then it refreshes the user-level skills (`claw-install`, `claw-comply`).
3. **On conflict the merge stays open, one file at a time:** read the three versions — base, yours, new (`git show :1:<file>`, `:2:`, `:3:`) — and propose a merge that keeps your addition *inside* the new text, not beside it. If the new text already covers it, take that and say so. No conflict is resolved without showing the user what they lose. `VERSION` is not a conflict: the release's wins. Then `git commit`.
4. **Then the projects:** `status` on each, `--down` where it is behind.

**A source that is not a clone** (copied into a project): get the release into `<NEW>` and the base — the release your copy came from, `upgrade.base_version(<FW>)` — into `<BASE>`, then `upgrade.classify(<BASE>, <FW>, <NEW>)`: `same` and `theirs` come from the release, `yours` stays, `conflict` is handled as in step 3; after it, `upgrade.write_record` with the release just taken. No commit declares the base → stop and ask. It works in place with no undo: copy the source aside first.

---

## `--activate <agent|guide>` / `--deactivate <agent|guide>`

**Activating** copies the agent from the master at its **current version**, fills in its `## Project context` block and adds the row to the routing table in `.claude/shared/orchestration.md` — never in `CLAUDE.md`: routing is coordinator content.

Mandatory shape of the row, because the doctor reads it:

```
| Situation | `agent-name` | Model |
```

The name goes in backticks in the **second** column. Anywhere else, that agent shows up as `ROSTER_ORPHAN` and the table cites a `ROSTER_MISSING` that does not exist.

Activating later is *better* than a dormant file: you always take the latest version, not one frozen at installation day.

**Deactivating** removes the file from `.claude/agents/` and the row from the routing. **The master is not touched.** If the project block held information that cannot be reconstructed, save it first.

**A guide** is named by its path under `shared/` (`domain/llm-guide.md`). Activating it: copy it into `.claude/shared/`, fill in the project block, add its line in `CLAUDE.md § Shared guides` — without it, it is `SHARED_ORPHAN`. Deactivating it: file and line go. A guide that an installed file still cites is not deactivated: the pointer would stay dead (`SHARED_MISSING`).

Close an activation with `down "<PRJ>"` and `--apply`: at the same version it changes no text and records the new card, which the next `--down` needs. Always close with `doctor`: `EXCLUSIVE` names agents that do not coexist.

---

## `--repair` — putting back what is missing

At the installed version, which must be the source's: otherwise the plan refuses, and `--down` comes first. It puts back the lifecycle skills, the hooks in use, the state files and the cited guides that are missing, and the missing entries in `settings.json`. **It overwrites nothing:** a file that differs from the source is a local change and stays.

1. `repair "<PRJ>"`, ok, `--apply`.
2. Guides and state files that are recreated come from the template: fill in the `[TO FILL IN]` blocks as at installation.
3. Close with `doctor`.

---

## `--uninstall` — removing the framework from the project

Only what is byte-for-byte identical to the source is deleted; what the project adapted goes into `.claude/framework-archive/`, at its relative path. The source must be reachable and the manifest present; an archive already there stops the plan.

| file | what happens |
|---|---|
| `CLAUDE.md` | only the kernel region goes, the project sections stay |
| skills and hooks | identical to the source → removed; different → archived |
| cards, guides and styles that come from the source, `orchestration.md` | archived |
| `.claude/settings.json` | the `settings_added` entries still equal go; those the user changed stay, and the plan names them. Without a record, the rest is not touched |
| framework hook entries, even ones the user touched up | removed, **one plan line per entry**: the script goes, and a closed hook without its script blocks every edit or every command |
| `docs/` | stay |
| `.claude/framework.json` | archived last |

`uninstall "<PRJ>"`, ok, `--apply`: a file changed after the plan stops everything, before the first byte is written.

---

## External skills — connecting and disconnecting a package

Skills by other authors are not published with the framework: they stay on the machine, under `<FW>/skills/<package>/`, and the commands are **from the shell**, because they write into the source and not into a project.

```bash
python "<FW>/claw.py" skills list
python "<FW>/claw.py" skills add <repo> [--commit <sha>]
python "<FW>/claw.py" skills remove <package>
```

`add` fetches the repository, pins it to a commit, copies every folder with a `SKILL.md` and refuses a skill name already connected: in the project they all sit at one level and the second would cover the first. **Connecting is an installation of other people's material: you ask the user first**, and the content is read — these are instructions, and sometimes scripts, that an agent will run.

The **pool** is `<FW>/skills/pool.toml`: the skills the coordinator may invoke on its own. Everything connected and outside the pool stays invocable by the user and invisible to the model (`skillOverrides` in `settings.json`). A wrong name in the pool stops the commands instead of hiding a skill in silence.

In the projects the skills arrive with `--down` or `--repair`, and they leave with `--uninstall` or after a `remove`. With the first package, `skill-runner` is to be activated (`--activate`): it is the only agent that may invoke them, and the coordinator does not run them itself.

---

## Change of field

A project does not stay where it was born: a library grows a demo, a tool becomes a service. The field lives in `profile` inside `.claude/framework.json`, the only place that knows it. No dedicated mode: these are the same four operations of an installation, on the new profile.

1. **Roster** — `--activate` what the new field implies, `--deactivate` the rest. Check for conflicts afterwards.
2. **Guides** — copy those of `profile.guides` on the new profile and the roster after the change, and add the line in `CLAUDE.md § Shared guides`: what the guide holds, taken from the line under its title. The doctor demands that the path be cited (`SHARED_ORPHAN`), not that the line be written well: that is on whoever installs.
3. **Cycles** — reassemble the coordinator's guide appending, after the installed orchestration (`assemble.installed_orchestration`), the new field's (`assemble.cycle_files`), or none if it drops them. They live **inside** the kernel region: no finding sees them vanish. Same precondition as § Change of orchestration.
4. **Permissions** — `settings.unmerge(current, settings_added)` removes what the old field had added and is still equal; then `settings.merge(rest, new)`, with `new` = `settings.framework(<new Profile.settings>, <hooks in .claude/hooks/>, <installed_orchestration>, skills.overrides(<FW>))`: the record contains base, hooks and orchestration, and without merging them again the change of field switches them off. Show `kept` and the conflicts before writing. Without a record, `merge` only: the old `deny` stays until the user removes it. A flat regeneration deletes permissions no profile ever wrote.

Then update `profile` in `framework.json`; `settings_added` becomes what the `merge` added. Skipping it leaves the project declaring a field it no longer has: the next maintenance regenerates the wrong permissions and no finding notices — the file declares, it does not verify.

---

## Change of orchestration

One per project, inside the kernel region of the coordinator's guide. No dedicated mode.

**Precondition:** `version` in `framework.json` equal to `<FW>/VERSION` and no `KERNEL_DRIFT` on `orchestration.md`; otherwise `--down` first. Reassembling the guide alone would bring it to the source's version while `CLAUDE.md` stays behind (`VERSION_MISMATCH`), and a local change in the region would vanish silently.

`old` and `new` are the `settings.ORCHESTRATION_SETTINGS` entries of the two orchestrations, `{}` if they have none.

1. **Guide** — reassemble `.claude/shared/orchestration.md`: `assemble.build_document(<FW>/coordinator, <VERSION>, <its project sections, unchanged>, extra=[assemble.orchestration_file(<FW>, '<new>'), *assemble.installed_cycles(region.body, <FW>)])`.
2. **Settings** — remove only what the installation really added: `rec = settings.unmerge(old, settings.unmerge(old, settings_added)[0])[0]` is the part of `old` still in the record. `settings.unmerge(current, rec)` removes it — a variable the user already had stays —, then `settings.merge(rest, new)` adds the new one's. Conflicts and `kept` are shown before writing.
3. **Manifest** — `settings_added` becomes `settings.merge(settings.unmerge(settings_added, rec)[0], added)[0]`, with `added` the second value of the `merge` in step 2: without it, `--uninstall` leaves on a variable no orchestration asks for any more.
4. **Verify** with `doctor`.
