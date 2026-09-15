"""Profili di dominio: quali agenti e quali guide installare."""

import re
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path

ALWAYS = [
    "explorer",
    "architect",
    "implementer",
    "tester",
    "refactorer",
    "final-reviewer",
]

EXCLUSIVE = [("deploy", "infra")]

# Lo stesso pattern del doctor: quello che lì è un rilievo, qui è la domanda
# "cosa serve installare perché quel rilievo non ci sia".
GUIDE_REF = re.compile(r"\.claude/shared/([A-Za-z0-9_./-]+\.md)")


@dataclass(frozen=True)
class Profile:
    """Un campo di lavoro: chi si installa, cosa si legge, cosa si rischia.

    `critical_surface` è la sola risposta che il profilo può dare da solo alla
    domanda del Passo 3.2 — «cosa rende il lavoro sbagliato anche a codice
    perfetto». Non installa nessun agente: la superficie di un campo è nota
    prima di conoscere il progetto, il revisore no.

    Non esiste un campo per gli agenti «da installare più tardi»: un agente
    che il campo implica sta in `agents` e si vede; uno che non implica lo
    porta il questionario come extra, o `--activate` a valle.
    """

    name: str
    agents: list[str]
    shared: list[str]
    cycles: list[str]
    settings: dict
    critical_surface: str = ""
    # Solo un suggerimento al questionario: l'orchestrazione la sceglie chi
    # installa, una per progetto, e il default vale per ogni campo.
    recommended_orchestrations: list[str] = field(default_factory=list)


def load(path: Path) -> Profile:
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return Profile(
        name=data["name"],
        agents=list(data.get("agents", [])),
        shared=list(data.get("shared", [])),
        cycles=list(data.get("cycles", [])),
        settings=dict(data.get("settings", {})),
        critical_surface=data.get("critical_surface", ""),
        recommended_orchestrations=list(data.get("recommended_orchestrations", [])),
    )


def roster(profile: Profile, extras: list[str], drop: list[str]) -> list[str]:
    droppable = set(drop) - set(ALWAYS)
    out: list[str] = []
    for name in ALWAYS + profile.agents + list(extras):
        if name not in out and name not in droppable:
            out.append(name)
    return out


def check_exclusive(agents: list[str]) -> list[str]:
    present = set(agents)
    return [f"{a} + {b}" for a, b in EXCLUSIVE if a in present and b in present]


def required_guides(framework_root: Path, agents: Sequence[str]) -> list[str]:
    """Le guide che le schede di questi agenti citano.

    Il profilo elenca le guide del **campo**; un agente attivato come extra
    porta le sue. Senza risolverle, la scheda si installa con un pointer morto
    che il doctor vede solo a installazione già scritta (`SHARED_MISSING`). Un
    pointer che l'agente non può seguire è peggio
    di assente — sta in un file che lui paga a ogni spawn.
    """
    out: list[str] = []
    for name in agents:
        src = framework_root / "agents" / f"{name}.md"
        if not src.is_file():
            continue
        for ref in GUIDE_REF.findall(src.read_text(encoding="utf-8")):
            if ref not in out:
                out.append(ref)
    return sorted(out)


def guides(
    framework_root: Path,
    prof: Profile,
    roster: Sequence[str],
    extras: Sequence[str] = (),
) -> list[str]:
    """Le guide da installare: quelle del campo, quelle citate dagli agenti
    scelti, quelle chieste in più.

    Un extra che non esiste è un errore di configurazione, come un ciclo
    dichiarato e assente: passato in silenzio, il progetto non riceverebbe la
    guida che ha chiesto e nessun rilievo lo direbbe — non la cita nessuno.
    """
    for rel in extras:
        if not (framework_root / "shared" / rel).is_file():
            raise FileNotFoundError(f"guida chiesta ma assente: shared/{rel}")
    out: list[str] = []
    for rel in [*prof.shared, *required_guides(framework_root, roster), *extras]:
        if rel not in out:
            out.append(rel)
    return out
