"""Kernel region: normalisation and markers.

The marker delimits the generated method inside a hand-adapted file. It carries
the version and nothing else: the region is regenerated, never compared.
"""

import re
from dataclasses import dataclass

OPEN_RE = re.compile(
    r"<!-- FRAMEWORK:KERNEL v(?P<version>\S+)(?: sha256:[0-9a-f]{8})? "
    r"— generated(?:, do not edit by hand| — edit \.claude/user-rules\.md instead) -->"
)
CLOSE = "<!-- /FRAMEWORK:KERNEL -->"


@dataclass(frozen=True)
class KernelRegion:
    version: str
    body: str
    start: int
    end: int


def normalize(text: str) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    joined = "\n".join(line.rstrip() for line in lines).strip("\n")
    return joined + "\n" if joined else "\n"


def wrap(body: str, version: str) -> str:
    body_n = normalize(body)
    marker = f"<!-- FRAMEWORK:KERNEL v{version} — generated — edit .claude/user-rules.md instead -->"
    return f"{marker}\n{body_n}{CLOSE}\n"


def parse(text: str) -> KernelRegion | None:
    m = OPEN_RE.search(text)
    if not m:
        return None
    newline = text.find("\n", m.end())
    if newline == -1:
        return None
    body_start = newline + 1
    close_at = text.find(CLOSE, body_start)
    if close_at == -1:
        return None
    return KernelRegion(
        version=m.group("version"),
        body=normalize(text[body_start:close_at]),
        start=m.start(),
        end=close_at + len(CLOSE),
    )


USER_RULES_OPEN = "<!-- CLAW:USER-RULES -->"
USER_RULES_CLOSE = "<!-- /CLAW:USER-RULES -->"


def wrap_user_rules(body: str) -> str:
    """The user-rules region: the marker pair around `body`, nothing else."""
    return f"{USER_RULES_OPEN}\n{normalize(body)}{USER_RULES_CLOSE}\n"


def strip_user_rules(text: str) -> tuple[str, str | None]:
    """`text` without its user-rules region, and the region body (None if absent).

    What was around the region is left as it was, so a file regenerated from
    this keeps its project part byte for byte.
    """
    start = text.find(USER_RULES_OPEN)
    if start == -1:
        return text, None
    close = text.find(USER_RULES_CLOSE, start)
    if close == -1:
        raise ValueError("user-rules region opened and never closed")
    end = close + len(USER_RULES_CLOSE)
    body = text[start + len(USER_RULES_OPEN) : close]
    return text[:start] + text[end:].removeprefix("\n"), normalize(body)
