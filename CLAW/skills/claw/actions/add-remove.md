# `/claw add <agent|guide>` · `/claw remove <agent|guide>`

**Activating** copies the agent from the master at its **current version**, fills in its `## Project context` block and adds the row to the routing table in `.claude/shared/orchestration.md` — never in `CLAUDE.md`: routing is coordinator content.

Mandatory shape of the row, because the doctor reads it:

```
| Situation | `agent-name` | Model |
```

The name goes in backticks in the **second** column. Anywhere else, that agent shows up as `ROSTER_ORPHAN` and the table cites a `ROSTER_MISSING` that does not exist.

Activating later is *better* than a dormant file: you always take the latest version, not one frozen at installation day.

**Deactivating** removes the file from `.claude/agents/` and the row from the routing. **The master is not touched.** If the project block held information that cannot be reconstructed, save it first.

**A guide** is named by its path under `shared/` (`domain/llm-guide.md`). Activating it: copy it into `.claude/shared/`, fill in the project block, add its line in `CLAUDE.md § Shared guides` — without it, it is `SHARED_ORPHAN`. Deactivating it: file and line go. A guide that an installed file still cites is not deactivated: the pointer would stay dead (`SHARED_MISSING`).

Close an activation with `down "<PRJ>"` and its `--apply`: at the same version it changes no text and records the new card, which the next `/claw update` needs. Always close with `doctor`: `EXCLUSIVE` names agents that do not coexist.

---

## Other people's skills — connecting and disconnecting a package

Skills by other authors are not published with the framework: they stay on the machine, under `<FW>/skills/<package>/`, and the commands are **from the shell**, because they write into the source and not into a project.

```bash
python "<FW>/claw.py" skills list
python "<FW>/claw.py" skills add <repo> [--commit <sha>]
python "<FW>/claw.py" skills remove <package>
```

`add` fetches the repository, pins it to a commit, copies every folder with a `SKILL.md` and refuses a skill name already connected: in the project they all sit at one level and the second would cover the first. **Connecting is an installation of other people's material: you ask the user first**, and the content is read — these are instructions, and sometimes scripts, that an agent will run.

The **pool** is `<FW>/skills/pool.toml`: the skills the coordinator may invoke on its own. Everything connected and outside the pool stays invocable by the user and invisible to the model (`skillOverrides` in `settings.json`). A wrong name in the pool stops the commands instead of hiding a skill in silence.

In the projects the skills arrive with `/claw update` or `/claw fix`, and they leave with `/claw uninstall` or after a `remove`. With the first package, `skill-runner` is to be activated (`/claw add`): it is the only agent that may invoke them, and the coordinator does not run them itself.
