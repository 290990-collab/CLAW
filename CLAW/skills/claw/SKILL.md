---
name: claw
description: >
  The CLAW framework in a project: install it, bring it to the plugin's version,
  add or remove agents and guides, change profile or orchestration, write the
  project's own rules, check and repair it, tune the agents' model and effort,
  tidy the TODO and persistent memory, measure whether a rule is followed,
  uninstall. `/claw <action>`; `/claw` alone lists the actions.
allowed-tools: Read(${CLAUDE_PLUGIN_ROOT}/**)
---

# `/claw` — the framework in this project

`<FW>` is `${CLAUDE_PLUGIN_ROOT}`, the plugin's folder and the source. `<PRJ>` is the project root: the current folder, unless the user names another.

| Action | What it does | Read |
|---|---|---|
| `install` | Sets up the framework in this project | `actions/install.md` |
| `update` | Brings the plugin's version in; adds or removes agents and guides; changes profile, orchestration, gateguard | `actions/update.md` |
| `rule` | Writes a rule of the project's own into `.claude/user-rules.md` | `actions/rule.md` |
| `fix` | Checks the installation; regenerates what is missing | `actions/fix.md` |
| `tune` | Tunes each agent's model and effort to this project | `actions/tune.md` |
| `tidy` | Finds what is stale in the TODO, persistent memory and user rules, and the shortcuts left in the code | `actions/tidy.md` |
| `comply <rule>` | Measures how often a rule is followed; spends tokens | `actions/comply.md` |
| `uninstall` | Removes the framework, archiving what was adapted | `actions/uninstall.md` |

Open only the file of the action asked, from this skill's folder. No action, or one not in the table → show the table and ask which.

**For every action:**

- **Only at the user's request:** `install`, `rule`, `comply`, `tune`, `tidy`, `uninstall`. The others you may run when the situation calls for them — `fix` after a hand edit.
- **Commands:** `python "<FW>/claw.py" <command>`, from this skill only: no `claw` launcher on the terminal.
- **Plan, ok, then write.** `install`, `update`, `uninstall` print their plan and save it; after the user's ok the same command with `--apply` runs that plan, never a recomputed one: a file changed in between stops everything before the first byte.
- **Close** every action that writes with `python "<FW>/claw.py" doctor --strict "<PRJ>"`.
