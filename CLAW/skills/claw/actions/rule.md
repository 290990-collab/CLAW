# `/claw rule` — a rule of the project's own

`.claude/user-rules.md` is the only file the user's rules live in: `update` never writes it, every regeneration applies it. On conflict a rule wins over the rest of `CLAUDE.md`.

**Only on the user's explicit request to make something a rule, never from a passing remark.** A remark that sounds like a rule → ask once whether it should become one; no answer, nothing written. The user's yes to an offer of this action (`install`, `fix`, `tidy`) counts as the request.

## Format

```
## All
- Commit messages in English, no signature.

## tester
model: sonnet
effort: high
- Run `pytest -q -x`, never the whole matrix.
```

| Section | Lands in |
|---|---|
| `## All` | the user-rules region at the bottom of `CLAUDE.md`: **every agent pays it at every spawn** — one line, the most compressed form |
| `## <agent>` (a name in `claw.json`) | the end of that card only |

- `model:` / `effort:` lines: only in an agent section, at most one of each, they override the card's frontmatter (limits: `actions/tune.md`). Under `## All`, or repeated, the file is an error. Coordinator rules go in `## All`.
- A section with another name, or text before the first one: ignored, `RULES_UNKNOWN`. A section named twice: error.
- A rule the kernel already says is not written: cite where (`file:line`) and ask.

## Steps

1. Choose the section: one agent's job → its section, anything else → `All`.
2. **Show the exact line and the section; wait for the yes.**
3. Read the file; with Edit add the line at the end of its section, or the section at the end of the file. No other line changes.
4. `python "<FW>/claw.py" update "<PRJ>" --keep-version` regenerates `CLAUDE.md` or the card in one call. Refused (another plugin version, or a hand edit it would overwrite) → `update` with plan and ok, as in `actions/update.md`.
5. `python "<FW>/claw.py" doctor --strict "<PRJ>"`.
