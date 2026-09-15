"""Trovare e validare la root del sorgente.

Un prodotto scaricabile non può cablare il percorso di una macchina: si cerca in
ordine e si valida prima di scrivere. La ricerca è **pura** — i candidati li
assembla il chiamante — perché è l'unico modo di provarla senza dipendere da
dove sta il framework che esegue i test.
"""

import json
from collections.abc import Sequence
from pathlib import Path

# Ciò senza cui l'installazione non può nemmeno cominciare.
REQUIRED = (
    "VERSION",
    "method",
    "coordinator",
    "orchestrations",
    "agents",
    "profiles",
    "templates",
    "skills",
    "hooks",
    "tools/fwbuild",
)


def missing(root: Path) -> list[str]:
    """Le voci obbligatorie assenti. Vuoto = è una root di framework."""
    return [r for r in REQUIRED if not (Path(root) / r).exists()]


def resolve(bases: Sequence[Path]) -> Path:
    """La prima root valida, provando `<base>` e poi `<base>/framework`.

    Le due forme — sorgente copiato nel progetto e master unico — sono coperte
    dalla stessa prova, senza una regola in più.

    «Percorso indicato ma invalido: errore, nessun fallback» non è un caso
    speciale qui dentro: è il chiamante che, avendone uno, passa un candidato
    solo. Un fallback silenzioso maschera un percorso sbagliato.
    """
    tried = []
    for base in bases:
        for cand in (Path(base), Path(base) / "framework"):
            gaps = missing(cand)
            if not gaps:
                return cand
            tried.append(
                f"{cand}: "
                + ("assente" if not cand.is_dir() else f"manca {', '.join(gaps)}")
            )
    raise LookupError("nessun sorgente valido fra:\n  " + "\n  ".join(tried))


def reference(project_root: Path, framework_root: Path) -> str:
    """Come `.claude/framework.json` deve citare il sorgente.

    Il primo dei tre modi previsti è il sorgente **dentro** il progetto: lì un
    percorso assoluto è la macchina di chi ha installato, e il primo clone
    trova un `source` che non esiste. Relativo alla root del progetto, invece,
    viaggia col repository. Fuori dal progetto il relativo non regge — la
    profondità del clone non è nota — e l'assoluto resta l'unica forma
    scrivibile.

    È qui e non nella skill: una regola scritta solo in prosa si disattende.
    """
    project_root = Path(project_root).resolve()
    framework_root = Path(framework_root).resolve()
    if framework_root == project_root or project_root in framework_root.parents:
        return framework_root.relative_to(project_root).as_posix() or "."
    return str(framework_root)


def dereference(project_root: Path, recorded: str) -> Path:
    """L'inverso: il `source` letto da `framework.json` come percorso reale.

    Un relativo si scioglie contro la root del progetto, non contro la
    directory di lavoro: `framework-doctor` e `framework-sync` girano da
    `<FW>/tools`, non da `<PRJ>`.
    """
    p = Path(recorded)
    return p if p.is_absolute() else (Path(project_root) / p).resolve()


MANIFEST = Path(".claude") / "framework.json"


def manifest(
    project_root: Path,
    framework_root: Path,
    version: str,
    profile_name: str,
    settings_added: dict | None = None,
) -> dict:
    """Il contenuto di `.claude/framework.json`.

    `source` e `version` dicono da dove il progetto è nato. `profile` dice **di
    cosa** è fatto: senza, `SETTINGS_MISSING` prescrive di rigenerare i
    permessi «del profilo del progetto» che nessuno può più nominare, e un
    cambio di campo non ha un punto di partenza.

    `settings_added` è ciò che l'installazione ha davvero aggiunto a
    `settings.json`: il solo pezzo di quel file che la disinstallazione può
    togliere. Si scrive solo se c'è — un record vuoto e un record assente
    dicono cose diverse, e la seconda vuol dire «non toccare».
    """
    data = {
        "source": reference(project_root, framework_root),
        "version": version,
        "profile": profile_name,
    }
    if settings_added is not None:
        data["settings_added"] = settings_added
    return data


def read_manifest(project_root: Path) -> dict | None:
    """Il manifesto letto, o `None` se assente o illeggibile.

    Le due cose non si distinguono qui apposta: per chi legge il progetto sono
    lo stesso guasto — `framework-sync` non trova il sorgente — e il doctor le
    riporta con lo stesso codice.
    """
    try:
        data = json.loads((Path(project_root) / MANIFEST).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def accepted(project_root: Path) -> dict[str, str]:
    """Le deroghe dichiarate nel manifesto: `codice` o `codice:frammento` → ragione.

    Si restituiscono **tutte**, ragione vuota compresa: scartarle qui le farebbe
    sparire in silenzio, e una deroga che non si applica è la cosa che il doctor
    deve dire, non nascondere. A deciderne la sorte è chi le confronta coi
    rilievi.
    """
    data = read_manifest(project_root) or {}
    raw = data.get("accepted")
    if not isinstance(raw, dict):
        return {}
    return {str(k): (v.strip() if isinstance(v, str) else "") for k, v in raw.items()}
