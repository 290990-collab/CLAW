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

Connects the **source** (the master) to the **installations** (the projects). Requirement: the source must be reachable from the machine; if it is not, only `doctor` is usable.

`--down`, `--up`, `--upgrade`, `--activate`, `--deactivate`, `--repair`, `--uninstall` are **modes of this skill**, not shell flags: `fwbuild` has `doctor`, `source`, `cost`, `report` and `skills`. The divergence report across several repositories — `python -m fwbuild report <folder>` — is from the shell instead: it reads many projects and modifies none.

The snippets start from `<FW>/tools`. `<PRJ>` is the project root; `<FW>` is the `source` field of `.claude/framework.json` (if missing, `./framework/`), which may be **relative to the project root**, not to the directory you run from: resolve it with `source.dereference(<PRJ>, source)`.

**Every mode that writes shows the plan first, file by file, and waits for the ok.** Where a `plan_*` of `lifecycle` exists, the plan is saved bound to the project and the mode, and **that** plan is executed, not a recomputed one: execution refuses the plan of another project or another mode, re-checks every file and stops if the tree changed after the ok.

```bash
# plan: printed and saved with the project path and the mode, nothing is written
cd <FW>/tools && python -c "
import dataclasses, hashlib, json, sys, tempfile
from pathlib import Path
from fwbuild import lifecycle
sys.stdout.reconfigure(encoding='utf-8')   # the reasons contain '→': cp1252 cannot print it
P = str(Path('<PRJ>').resolve())
M = '<down | repair | uninstall>'
H = None   # down only: None keeps the hooks in use; on a project without any, the names chosen at step 0
ops = getattr(lifecycle, 'plan_' + M)(Path(P), Path('..'), **({'hooks': H} if M == 'down' else {}))
print(lifecycle.render(ops))
f = Path(tempfile.gettempdir(), 'fw-plan-' + hashlib.sha256(P.encode()).hexdigest()[:16] + '.json')
f.write_text(json.dumps({'project': P, 'mode': M, 'ops': [dataclasses.asdict(o) for o in ops]}), encoding='utf-8')
"
# after the ok: only the plan of this project and this mode
cd <FW>/tools && python -c "
import hashlib, json, sys, tempfile
from pathlib import Path
from fwbuild import lifecycle
sys.stderr.reconfigure(encoding='utf-8')
P = str(Path('<PRJ>').resolve())
M = '<down | repair | uninstall>'   # the mode you are running, not the one read from the file
f = Path(tempfile.gettempdir(), 'fw-plan-' + hashlib.sha256(P.encode()).hexdigest()[:16] + '.json')
plan = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}
if plan.get('project') != P or plan.get('mode') != M: sys.exit(f'no {M} plan saved for {P}: plan again')
ops = [lifecycle.Operation(**d) for d in plan['ops']]
if M == 'uninstall': lifecycle.apply_uninstall(Path(P), Path('..'), ops)
else: lifecycle.apply_update(Path(P), Path('..'), ops)
"
```

In the other modes the plan is the list of files and of what happens to them, written before touching them.

---

## `--down` — bringing a new version into the project

Updates the method while preserving the adaptation.

0. **Plan** with `plan_down`: kernel regions to reassemble, guides and the response style to re-merge, skills and hooks to update, missing entries in `settings.json`, the manifest's version. `hooks=None` keeps the hooks the project uses; if it uses none, **one single question** — does it want them, `gateguard` included? — and a yes becomes `hooks=[…]` with the chosen names from `settings.HOOKS`.
1. **Compare the versions:** the project's is in the kernel region's marker, the source's in `<FW>/VERSION`.
2. **Diagnosis first.** `KERNEL_DRIFT` findings must be resolved *first*: updating over a local change erases it silently.
3. **Reassemble** with the new method and the existing project sections, extracted from the current installation and rewritten unchanged.

```bash
cd <FW>/tools && python -c "
from pathlib import Path
from fwbuild import assemble, kernel
p = Path('<PRJ>/CLAUDE.md')
text = p.read_text(encoding='utf-8')
region = kernel.parse(text)
sections = text[region.end:].lstrip('\n')          # the adaptation, unchanged
version = Path('../VERSION').read_text(encoding='utf-8').strip()
p.write_text(assemble.build_document(Path('../method'), version, sections), encoding='utf-8')
"
```

4. **Same operation on `.claude/shared/orchestration.md`**, with the kernel from `<FW>/coordinator/`: the versioned documents are **two**, updating only one leaves them misaligned. There orchestration and domain cycles are **inside** the region and the project does not record what it was born from: they must be passed again, in this order, with `extra=[assemble.installed_orchestration(region.body, Path('..')), *assemble.installed_cycles(region.body, Path('..'))]`, or they disappear without any finding seeing it. A region without a recognisable orchestration is a `ValueError`: the orchestration is chosen explicitly with `assemble.orchestration_file`, not guessed.
5. **Same operation on every installed agent**, with `split_source` and `build_agent`: front matter and the `## Project context` block stay the project's, the method comes from the master. If the plan names a `model` or `effort` different from the source, ask: yes → that front-matter line takes the source's value.
6. **Run the plan** from step 0 with `apply_update`: it copies skills and hooks, re-merges guides and the style — text from the source, the last section (the project block, the one holding the placeholder in the source) stays the project's —, merges `settings.json`, writes `version` into `.claude/framework.json` and appends the new delta to `settings_added`. It skips the kernel regions: steps 3-5 have already rewritten them. A guide or style without a recognisable block appears in the plan as `keep`, with the reason: it is updated by hand, comparing it with the source — replacing it whole would erase the adaptation.
7. **Verify** with `doctor`: it must exit 0.

**Conflicts are presented, they do not resolve themselves:** on a region modified locally the user must see both versions and decide.

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
4. **Record the base, if it is not there already**, **before** touching `VERSION`:

   ```bash
   cd <FW>/tools && python -c "
   from pathlib import Path
   from fwbuild import upgrade
   F = Path('..')
   if upgrade.read_record(F) is None:
       print(upgrade.write_record(F, (F/'VERSION').read_text(encoding='utf-8').strip(),
                                  '<EDITION>', '<repository URL>'))
   "
   ```

   From here on `VERSION` is no longer a published number, and without this line nobody knows which release the source came from any more: it is the only thing that makes your work recoverable at the next upgrade (→ `--upgrade`). **If the record is already there it is not touched:** the base stays what it is, however many promotions you make.
5. **Increment `<FW>/VERSION`:** correction → patch; new or reworded rule → minor; structural change → major.
6. **State what changed**, so whoever updates knows what they receive.
7. **Realign the originating project** with `--down`, so the hash matches again.

⚠️ **A translation of this source is a source of its own**, with its own `VERSION`: `--up` does not reach it. A rule that holds in every language has to be carried across by hand — until it is, the two editions say different things.

---

## `--upgrade` — bringing a new release over a modified source

Only for those who have used `--up`: an untouched source is updated by replacing it. The absence of `upstream.json` **is** that answer, not a fault.

1. **Get the new release** where it disturbs nothing, and from there `<NEW>` is the edition folder inside the clone:

   ```bash
   git clone <repo> <NEW>   # or: git -C <existing clone> pull
   ```

2. **Rebuild the base**, that is the edition as it was at the release your source came from. `upgrade.base_version(<FW>)` gives the number; in the clone, the base is the commit where that edition's `VERSION` held that number, extracted where it touches nothing:

   ```bash
   git -C <NEW> log --format=%H -- <EDITION>/VERSION   # newest first
   git -C <NEW> show <commit>:<EDITION>/VERSION        # until it matches
   git -C <NEW> worktree add --detach <BASE> <commit>
   ```

   **Wrong base, useless comparison:** if no commit matches — wrong repository, truncated history, a number never published — stop and ask. Do not fall back on `VERSION`: that is the right answer only when `upstream.json` is missing.

3. **Classify**, writing nothing:

   ```bash
   cd <FW>/tools && python -c "
   from pathlib import Path
   from fwbuild import upgrade
   plan = upgrade.classify(Path('<BASE>/<EDITION>'), Path('<FW>'), Path('<NEW>/<EDITION>'))
   for name in ('theirs', 'yours', 'conflict'):
       print(name, len(getattr(plan, name)), getattr(plan, name)[:20])
   "
   ```

   | outcome | what it means | what you do |
   |---|---|---|
   | `same` | you and the release say the same thing — including when your addition landed upstream identical | nothing |
   | `theirs` | you left it as it was and upstream changed it | copy from the release |
   | `yours` | you changed it and upstream did not | **keep yours** |
   | `conflict` | changed by both, differently | the user decides |

4. **Show the plan before applying it**, with the counts and the conflicting paths. `same`, `theirs` and `yours` are mechanical: the second are applied by copying from the release, the third by not touching them.
5. **One conflict at a time:** read the three versions — base, yours, new — and propose a merge that keeps your addition *inside* the new text, not beside it. If your change is already covered by the new text, take that and say so. No conflict is resolved without showing the user what they lose.
6. **`VERSION` is not a conflict:** you take the release's. A source declaring a number that was never published is what created the problem.
7. **Rewrite the record** with the release just taken: it is the base of the next upgrade.

   ```bash
   cd <FW>/tools && python -c "
   from pathlib import Path
   from fwbuild import upgrade
   F = Path('..')
   print(upgrade.write_record(F, (F/'VERSION').read_text(encoding='utf-8').strip(),
                              '<EDITION>', '<repository URL>'))
   "
   ```

8. **Close with `--down` on the projects**, which are now one version behind, and with `doctor` on each.

⚠️ The source is upgraded **in place**: copy it aside before applying. It is the only operation of this skill that touches the master, and it has no undo.

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

Always check for conflicts after an activation:

```bash
cd <FW>/tools && python -c "
from fwbuild import profile
import pathlib
present = sorted(p.stem for p in pathlib.Path('<PRJ>/.claude/agents').glob('*.md'))
print('conflicts:', profile.check_exclusive(present) or 'none')
"
```

Always close with `doctor`.

---

## `--repair` — putting back what is missing

At the installed version, which must be the source's: otherwise `plan_repair` refuses, and `--down` comes first. It puts back the lifecycle skills, the hooks in use, the state files and the cited guides that are missing, and the missing entries in `settings.json`. **It overwrites nothing:** a file that differs from the source is a local change and stays.

1. Plan with `plan_repair`, ok, `apply_update`.
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

Plan with `plan_uninstall`, ok, `apply_uninstall`: a file changed after the plan stops everything, before the first byte is written.

---

## External skills — connecting and disconnecting a package

Skills by other authors are not published with the framework: they stay on the machine, under `<FW>/skills/<package>/`, and the commands are **from the shell**, because they write into the source and not into a project.

```bash
cd <FW>/tools && python -m fwbuild skills list
cd <FW>/tools && python -m fwbuild skills add <repo> [--commit <sha>]
cd <FW>/tools && python -m fwbuild skills remove <package>
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
4. **Permissions** — `settings.unmerge(current, settings_added)` removes what the old field had added and is still equal; then `settings.merge(rest, new)`, with `new` = the new profile's `Profile.settings` merged with `settings.hooks` of the hooks in `.claude/hooks/` and with `settings.ORCHESTRATION_SETTINGS` of the installed orchestration (`installed_orchestration`): the record contains them, and without merging them again the change of field switches the team off. Show `kept` and the conflicts before writing. Without a record, `merge` only: the old `deny` stays until the user removes it. A flat regeneration deletes permissions no profile ever wrote.

Then update `profile` in `framework.json`; `settings_added` becomes what the `merge` added. Skipping it leaves the project declaring a field it no longer has: the next maintenance regenerates the wrong permissions and no finding notices — the file declares, it does not verify.

---

## Change of orchestration

One per project, inside the kernel region of the coordinator's guide. No dedicated mode.

**Precondition:** `version` in `framework.json` equal to `<FW>/VERSION` and no `KERNEL_DRIFT` on `orchestration.md`; otherwise `--down` first. Reassembling the guide alone would bring it to the source's version while `CLAUDE.md` stays behind (`VERSION_MISMATCH`), and a local change in the region would vanish silently.

`old` and `new` are the `settings.ORCHESTRATION_SETTINGS` entries of the two orchestrations, `{}` if they have none.

1. **Guide** — reassemble `.claude/shared/orchestration.md` as in step 4 of `--down`, with `assemble.orchestration_file(Path('..'), '<new>')` instead of `installed_orchestration`; the cycles are passed again unchanged.
2. **Settings** — remove only what the installation really added: `rec = settings.unmerge(old, settings.unmerge(old, settings_added)[0])[0]` is the part of `old` still in the record. `settings.unmerge(current, rec)` removes it — a variable the user already had stays —, then `settings.merge(rest, new)` adds the new one's. Conflicts and `kept` are shown before writing.
3. **Manifest** — `settings_added` becomes `settings.merge(settings.unmerge(settings_added, rec)[0], added)[0]`, with `added` the second value of the `merge` in step 2: without it, `--uninstall` leaves on a variable no orchestration asks for any more.
4. **Verify** with `doctor`.
