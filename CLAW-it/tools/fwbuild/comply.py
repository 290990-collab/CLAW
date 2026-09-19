"""Leggere le trascrizioni di `claude -p --output-format stream-json --verbose`.

Una riga JSON per evento. `claw-comply` ne prende le chiamate agli
strumenti, in ordine, per etichettare quali passi di una regola sono stati
eseguiti. Il formato è dell'harness e cambia con lui: la fixture dei test è una
trascrizione vera, e un evento che non ha la forma attesa è un errore, non un
salto — un passo saltato in silenzio si leggerebbe come regola non seguita.
"""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Call:
    name: str
    input: dict
    # `tool_use` del subagent che l'ha fatta; None se dalla sessione principale.
    parent: str | None


@dataclass(frozen=True)
class Transcript:
    calls: tuple[Call, ...]
    # Testo dell'evento `result`; None se la sessione non è arrivata in fondo.
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
            raise ValueError(f"{path}:{n}: riga non JSON — {e.msg}") from None
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
                raise ValueError(f"{path}:{n}: evento assistant senza la forma attesa ({e})") from None
        elif kind == "result":
            result, is_error = event.get("result", ""), bool(event.get("is_error"))
    return Transcript(tuple(calls), result, is_error)
