"""Reading the transcripts of `claude -p --output-format stream-json --verbose`.

One JSON line per event. `claw-comply` takes the tool calls from them, in
order, to label which steps of a rule were executed. The format belongs to the
harness and changes with it: the test fixture is a real transcript, and an
event without the expected shape is an error, not a skip — a step skipped in
silence would read as a rule not followed.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Call:
    name: str
    input: dict
    # `tool_use` of the subagent that made it; None if from the main session.
    parent: str | None


@dataclass(frozen=True)
class Transcript:
    calls: tuple[Call, ...]
    # Text of the `result` event; None if the session did not reach the end.
    result: str | None
    is_error: bool


def read(path: Path) -> Transcript:
    calls: list[Call] = []
    result, is_error = None, False
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"{path}:{n}: not a JSON line — {e.msg}") from None
        kind = event.get("type")
        if kind == "assistant":
            try:
                blocks = event["message"]["content"]
                calls += [
                    Call(b["name"], b["input"], event.get("parent_tool_use_id"))
                    for b in blocks
                    if b.get("type") == "tool_use"
                ]
            except (KeyError, TypeError) as e:
                raise ValueError(f"{path}:{n}: assistant event without the expected shape ({e})") from None
        elif kind == "result":
            result, is_error = event.get("result", ""), bool(event.get("is_error"))
    return Transcript(tuple(calls), result, is_error)
