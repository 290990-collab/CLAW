"""Assemblaggio degli artefatti installabili.

Il metodo generato vive dentro la regione kernel; frontmatter e blocchi di
progetto restano fuori, perché sono la superficie che l'utente adatta.
"""

from collections.abc import Sequence
from pathlib import Path

from . import kernel

METHOD_HEADING = "## Metodo"
DOMAIN_HEADING = "## Contesto di progetto"

# I due tetti del sorgente, in parole. Sono test veri — la build cade sopra
# soglia — e stanno qui perché li legge anche il doctor: il rilievo
# `TOKEN_BUDGET` tace finché il file assemblato non arriva almeno al tetto
# che il framework si dà per il solo metodo.
METHOD_WORD_BUDGET = 2000
COORDINATOR_WORD_BUDGET = 2900

# L'orchestrazione di chi non ne sceglie una.
DEFAULT_ORCHESTRATION = "orchestrator-worker"


def read_method(method_dir: Path, extra: Sequence[Path] = ()) -> str:
    """Concatena i moduli di una cartella di metodo, in ordine di nome file.

    `extra` accoda file scelti dal profilo — i cicli di dominio — dopo i moduli
    fissi: sono contenuto di metodo a tutti gli effetti, ma non tutti i progetti
    li vogliono.
    """
    parts = [
        p.read_text(encoding="utf-8")
        for p in sorted(method_dir.glob("*.md"), key=lambda p: p.name)
    ]
    parts += [p.read_text(encoding="utf-8") for p in extra]
    return kernel.normalize("\n".join(parts))


def build_document_from_text(
    method: str,
    version: str,
    project_sections: str,
    *,
    markers: bool = True,
) -> str:
    head = kernel.wrap(method, version) if markers else kernel.normalize(method)
    return f"{head}\n{kernel.normalize(project_sections)}"


def build_document(
    method_dir: Path,
    version: str,
    project_sections: str,
    *,
    markers: bool = True,
    extra: Sequence[Path] = (),
) -> str:
    return build_document_from_text(
        read_method(method_dir, extra), version, project_sections, markers=markers
    )


def cycle_files(framework_root: Path, names: Sequence[str]) -> list[Path]:
    """Risolve i cicli dichiarati da un profilo in file di `cycles/`.

    Un ciclo dichiarato ma inesistente è un errore di configurazione, non un
    campo da ignorare: se passasse in silenzio, il profilo prometterebbe un
    metodo che il progetto non riceve.
    """
    out = []
    for name in names:
        p = framework_root / "cycles" / f"{name}.md"
        if not p.is_file():
            raise FileNotFoundError(f"ciclo dichiarato ma assente: cycles/{name}.md")
        out.append(p)
    return out


def installed_cycles(region_body: str, framework_root: Path) -> list[Path]:
    """I cicli di dominio già presenti in una regione kernel installata.

    Un progetto non registra da quale profilo è nato: riassemblare da
    `coordinator/` senza questo li cancellerebbe in silenzio a ogni `--down`, e
    nessun rilievo del doctor lo vedrebbe. Si riconoscono dal primo titolo.
    """
    out = []
    for p in sorted((framework_root / "cycles").glob("*.md")):
        heading = p.read_text(encoding="utf-8").lstrip().splitlines()[0]
        if heading and heading in region_body:
            out.append(p)
    return out


def orchestration_file(framework_root: Path, name: str) -> Path:
    """Risolve l'orchestrazione scelta in un file di `orchestrations/`.

    Come per i cicli: un nome che non esiste passato in silenzio lascerebbe la
    guida del coordinatore senza modello di delega, e nessun rilievo lo vedrebbe.
    """
    p = framework_root / "orchestrations" / f"{name}.md"
    if not p.is_file():
        raise FileNotFoundError(
            f"orchestrazione dichiarata ma assente: orchestrations/{name}.md"
        )
    return p


def installed_orchestration(region_body: str, framework_root: Path) -> Path:
    """L'orchestrazione già presente in una regione kernel installata.

    Stessa ragione di `installed_cycles`, stesso riconoscimento dal primo
    titolo. Il progetto ne ha esattamente una: nessuna riconosciuta vuol dire
    di solito un titolo rinominato nel sorgente, e ripiegare sul default
    riscriverebbe in silenzio il modello sbagliato; due non sono una scelta da
    indovinare.
    """
    found = []
    for p in sorted((framework_root / "orchestrations").glob("*.md")):
        heading = p.read_text(encoding="utf-8").lstrip().splitlines()[0]
        if heading and heading in region_body:
            found.append(p)
    if not found:
        raise ValueError(
            "nessuna orchestrazione riconosciuta nella regione: sceglila e "
            "passala con assemble.orchestration_file"
        )
    if len(found) > 1:
        names = ", ".join(p.stem for p in found)
        raise ValueError(f"più di un'orchestrazione nella regione: {names}")
    return found[0]


def build_agent(
    frontmatter: str,
    method_body: str,
    domain_block: str,
    version: str,
    *,
    markers: bool = True,
) -> str:
    body = kernel.wrap(method_body, version) if markers else kernel.normalize(method_body)
    return f"{kernel.normalize(frontmatter)}\n{body}\n{kernel.normalize(domain_block)}"


def split_source(text: str) -> tuple[str, str, str]:
    """Spezza un sorgente di agente in (frontmatter, metodo, blocco dominio).

    Il frontmatter si delimita sui primi due '---' a inizio riga, non su una
    split globale: un '---' usato come riga orizzontale nel corpo non deve
    rompere il parsing.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("sorgente senza frontmatter")
    close = next(
        (i for i in range(1, len(lines)) if lines[i].strip() == "---"), None
    )
    if close is None:
        raise ValueError("frontmatter non chiuso")
    frontmatter = "\n".join(lines[: close + 1]) + "\n"
    rest = "\n".join(lines[close + 1 :])

    if METHOD_HEADING not in rest:
        raise ValueError(f"manca la sezione {METHOD_HEADING!r}")
    if DOMAIN_HEADING not in rest:
        raise ValueError(f"manca la sezione {DOMAIN_HEADING!r}")
    m_at = rest.index(METHOD_HEADING)
    d_at = rest.index(DOMAIN_HEADING)
    if d_at < m_at:
        raise ValueError(f"{DOMAIN_HEADING} precede {METHOD_HEADING}")
    return frontmatter, rest[m_at:d_at], rest[d_at:]
