# `/claw uninstall` — removing the framework from the project

Only what is byte-for-byte identical to the source is deleted; what the project adapted goes into `.claude/framework-archive/`, at its relative path. The source must be reachable and the manifest present; an archive already there stops the plan.

| file | what happens |
|---|---|
| `CLAUDE.md` | only the kernel region goes, the project sections stay |
| skills and hooks | identical to the source → removed; different → archived |
| cards, guides and styles that come from the source, `orchestration.md` | archived |
| `.claude/settings.json` | the `settings_added` entries still equal go; those the user changed stay, and the plan names them. Without a record, the rest is not touched |
| framework hook entries, even ones the user touched up | removed, **one plan line per entry**: the script goes, and a closed hook without its script blocks every `git` command or linter-configuration edit |
| `docs/` | stay |
| `.claude/framework.json` | archived last |

`uninstall "<PRJ>"`, ok, `--apply`: a file changed after the plan stops everything, before the first byte is written.
