"""`.claude/user-rules.md`: the project's own rules, parsed.

The file is plain Markdown with one `## <name>` section per recipient: `## All`
for `CLAUDE.md`, `## <agent>` for that agent's card. In an agent section the
lines `model: x` and `effort: x` are not prose: they override the card's
frontmatter. This module imports nothing from the package, so the doctor can
read the file without pulling in the assembly.
"""

import re
from dataclasses import dataclass, field

ALL = "All"
OVERRIDE_KEYS = ("model", "effort")

_HEADING_RE = re.compile(r"^## (?P<name>.*?)\s*$")
_OVERRIDE_RE = re.compile(r"^(?P<key>model|effort):[ \t]*(?P<value>\S+)[ \t]*$")


@dataclass(frozen=True)
class Rules:
    all: str = ""
    agents: dict[str, str] = field(default_factory=dict)
    overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    stray: str = ""


def parse(text: str) -> Rules:
    """The rules in `text`.

    Text before the first heading is `stray`: reported, never applied. An empty
    section contributes nothing. A section named twice, or a `model:`/`effort:`
    line under `## All` (it has no frontmatter), is an error: applying one of
    two readings silently would hide the other.
    """
    stray: list[str] = []
    bodies: dict[str, list[str]] = {}
    overrides: dict[str, dict[str, str]] = {}
    current: str | None = None
    for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        heading = _HEADING_RE.match(line)
        if heading:
            current = heading.group("name")
            if current in bodies:
                raise ValueError(f"user-rules: section '## {current}' appears twice")
            bodies[current] = []
            continue
        if current is None:
            stray.append(line)
            continue
        override = _OVERRIDE_RE.match(line)
        if override:
            if current == ALL:
                raise ValueError(
                    f"user-rules: '{line.strip()}' under '## {ALL}': "
                    "model and effort belong in an agent's section"
                )
            key = override.group("key")
            mine = overrides.setdefault(current, {})
            if key in mine:
                raise ValueError(f"user-rules: '{key}:' twice in '## {current}'")
            mine[key] = override.group("value")
            continue
        bodies[current].append(line)

    prose = {name: "\n".join(lines).strip("\n") for name, lines in bodies.items()}
    prose = {name: body for name, body in prose.items() if body.strip()}
    return Rules(
        all=prose.pop(ALL, ""),
        agents=prose,
        overrides=overrides,
        stray="\n".join(stray).strip("\n") if "".join(stray).strip() else "",
    )
