# `/claw share [what]` — promoting a local change into the source

**Precondition: the project must be aligned with the source.** If `version` in `.claude/framework.json` is not the one in `<FW>/VERSION`, run `/claw update` first, then promote. From a project left behind, the local region differs from the source for **two** reasons — your change, and the one another project has already promoted — and step 1 does not tell them apart: promoting wholesale deletes the second one silently. Aligned means base and source coincide, and it is the only condition in which a two-tree comparison is correct.

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
5. **Commit it in the master**, the message saying what changed: it is what `status` shows whoever updates, and what `claw update` carries through the next release.
6. **Realign the originating project** with `/claw update`, so the hash matches again.
