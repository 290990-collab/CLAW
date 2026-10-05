---
name: claw
description: >
  The CLAW framework in a project: install it, bring it to the source's
  version, check and repair it, add or remove an agent or a guide, change
  profile or orchestration, promote a local change to every project, tune the
  agents' model and effort, review persistent memory, measure whether a rule
  is followed, uninstall. `/claw <action>`; `/claw` alone lists the actions.
---

# `/claw` — the framework in this project

`<FW>` is the source, written here by `claw setup`. `<PRJ>` is the project root: the current folder, unless the user names another.

| Action | What it does | Read |
|---|---|---|
| `install` | Sets up the framework in this project | `actions/install.md` |
| `update` | Brings the source's version into the project | `actions/update.md` |
| `fix` | Checks the installation; puts back what is missing | `actions/fix.md` |
| `add <agent\|guide>` · `remove <agent\|guide>` | Activates or deactivates an agent or a guide | `actions/add-remove.md` |
| `change` | Changes the profile or the orchestration | `actions/change.md` |
| `share [what]` | Promotes a local change into the source, for every project | `actions/share.md` |
| `tune` | Tunes each agent's model and effort to this project | `actions/tune.md` |
| `memory` | Finds stale facts in persistent memory | `actions/memory.md` |
| `comply <rule>` | Measures how often a rule is followed; spends tokens | `actions/comply.md` |
| `uninstall` | Removes the framework, archiving what was adapted | `actions/uninstall.md` |

Open only the file of the action asked, from this skill's folder. No action, or one not in the table → show the table and ask which.

**For every action:**

- **Only at the user's request:** `install`, `share`, `comply`, `uninstall`. The others you may run when the situation calls for them — `fix` after a hand edit, `memory` at the start of a long session.
- **Commands:** `python "<FW>/claw.py" <command>` — the terminal's `claw` is the same program.
- **Plan, ok, then write.** `install`, `down`, `repair`, `uninstall` print their plan and save it; after the user's ok the same command with `--apply` runs that plan, never a recomputed one: a file changed in between stops everything before the first byte.
- **Close** every action that writes with `python "<FW>/claw.py" doctor --strict "<PRJ>"`.
