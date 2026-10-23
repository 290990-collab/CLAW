# `/claw update` — the plugin's version, and changes to the choices

One command regenerates every framework file from the plugin, the choices in `.claude/claw.json` and `.claude/user-rules.md`. Never touched: `user-rules.md`, `CLAUDE.md` outside the kernel and user-rules regions, `docs/`, cards and guides `claw.json` does not name, the user's values in `settings.json`.

| Request | Flag |
|---|---|
| add / remove agents or guides | `--add a,core/x.md` · `--remove a,core/x.md` (guides by path under `shared/`) |
| change field | `--profile <P>` |
| change orchestration | `--orchestration <O>` (`agent-teams` is experimental, interactive sessions only) |
| gateguard | `--gateguard on\|off` |
| new plugin version | none |

## 1. Version

Compare `version` in `claw.json` with `<FW>/VERSION`. Plugin **older** than the project (or the user wants the newest): the user updates the plugin with `/plugin` (auto-update recommended), restarts Claude Code, then `/claw update`; never update from the older one. Equal or newer → go on.

## 2. Plan

```bash
python "<FW>/claw.py" update "<PRJ>" [flags]
```

Validation comes first and fails before any plan: unknown or already installed name, one of the six always-installed agents (`explorer`, `architect`, `implementer`, `tester`, `refactorer`, `final-reviewer`), `deploy` with `infra`, a guide still cited by a roster card (remove that agent first). `CLAUDE.md` without the kernel marker is refused: restore the marker, or move the project's text aside and `install` again.

Show the header (`v2.x → v3.0.0 · profile a → b · agents +x −y`) and every `overwrite`, `remove`, `merge` with its reason. A reason "modified by hand" means a generated file differs from what the recorded choices generate: the edit is lost. Ask whether it must survive; if so it goes into `user-rules.md` first (`/claw rule`), then back here.

## 3. Apply

After the ok: `python "<FW>/claw.py" update "<PRJ>" --apply` (the flags are saved with the plan). A tree changed since the plan stops it before the first byte. It prints the settings values of the user that stayed, and runs the doctor. Close with `doctor --strict`; findings → `/claw fix`.

Removing an agent keeps its section in `user-rules.md`, which then raises `RULES_UNKNOWN`: ask whether to delete the section.
