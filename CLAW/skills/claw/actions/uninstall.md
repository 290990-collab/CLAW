# `/claw uninstall` — removing the framework from the project

Each framework file is compared with what the plugin generates from `claw.json` and `user-rules.md`: **equal → removed, different → archived** whole in `.claude/claw-archive/` at its relative path. The plugin must be reachable and `claw.json` present; an archive already there stops the plan.

| file | what happens |
|---|---|
| `CLAUDE.md` | the kernel and user-rules regions go, the rest stays |
| cards, guides, styles, hooks, `orchestration.md` | equal → removed; different → archived; not from the plugin → stays |
| `.claude/settings.json` | the `settings_added` entries still equal go; those the user changed stay, and the plan names them. Without a record, the rest is not touched |
| framework hook entries, even ones the user touched up | removed, **one plan line per entry**: the script goes, and a closed hook without its script blocks every `git` command or linter-configuration edit |
| `.claude/user-rules.md`, `docs/` | stay |
| `.claude/claw.json` | archived last |

`uninstall "<PRJ>"`, ok, `--apply`: a file changed after the plan stops everything, before the first byte is written.
