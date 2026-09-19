## State that keeps itself up to date

The state is written **exclusively by the coordinator**: whoever writes it must have seen the whole picture, and an agent that has seen only one task does not have it. Subagents just report.

| Lvl | File | Content | Update | Ceiling |
|---|---|---|---|---|
| 1 | `docs/TODO.md` | immediate operational state: in progress, waiting, next step, blocked | at every step | ~120 lines, indicative |
| 2 | `docs/status.md` | closed decisions, measured results, hypotheses confirmed or refuted, intentional removals | when a task closes | telegraphic entry |
| 3 | `CLAUDE.md § Current state` | the project's picture (it sits **outside the kernel region**: updating it must not produce drift) | only if the picture changes | ~25 lines |
| 4 | persistent memory | facts between sessions: user directives, preferences, structural decisions, mistakes that would repeat | at every discovery or structural change | 1 fact per file |

*Note on `docs/roadmap.md`:* not a level. The levels say where we are, the roadmap where we are going — goals, dependencies, criteria. It is touched when a goal closes or another is added.

## Update rules

- **You add or tick off, you do not rewrite.** A box is ticked with the evidence next to it — the command run, `file:line`, the real outcome. Without it, it stays open.
- **Safe pause:** close the step in progress or go back, never halfway through a change; no irreversible action in order to stop; what is only on disk becomes a `wip:` commit that says in one line whether the tree is broken. Level 1 receives where we are, what is verified and the first action on resuming — written for whoever restarts cold, not for whoever was here.
- **Pickup:** the trail left behind is authoritative input: it is read, not redone. Re-verifying from scratch what level 2 records as closed is work paid twice; you verify what you are about to act on.
- **Compression at the ceiling:** past the ceiling you compress at task end, not before adding; the long trace goes down a level, it does not inflate the current one.
- **Session start:** level 1 first, always. **Task end:** level 1 always; level 2 if something closed; level 3 if the picture changes.
- **Long or asynchronous operations:** as soon as something starts that the user has to launch or wait for, the line goes into *Waiting* on level 1, with what they must report back.
- **Zero duplication:** TODO = operational | `status.md` = results | `CLAUDE.md` = picture | memory = what survives the session.

## Maintaining persistent memory (level 4)

To look at it: the `claw-memory` skill lists it and pairs every conflict with the line in the repo that contradicts it.

- **To be revisited, not just filled:** at every change of paths, contracts or modules and at every refuted hypothesis, ask *"does this supersede a memory?"* and correct it or mark it superseded immediately.
- **Compact memory:** one fact per file, no number duplicated from the repo, no path that no longer exists.
- **Mistakes:** register the mistake that would repeat — telegraphic, technical, with the references (`file:line`, command, message) — not the episode. Once the cause is gone, delete the memory: the problem no longer exists. To find them: `conversation-analyzer` extracts the recurring candidates from the transcripts with the evidence — rule, memory or hook — and the coordinator decides.
- **A rule is promoted when it repeats:** one episode is a case, two independent ones are a pattern, and only a narrow pattern verified several times becomes a general rule. The entry says when it holds, when it does **not**, and where it comes from (`file:line`, command, PR). Security, data and permissions never become a pattern “to skip”, however many times they have repeated.
- **In a conflict the repo wins:** an old unannotated memory is an active bias, it restarts the next session with a month-old view.
