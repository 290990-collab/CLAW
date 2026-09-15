"""Il ciclo di vita di un'installazione: cosa si scrive, cosa si toglie, cosa si ripara.

Ogni modalità che scrive passa da un piano: un'operazione per file, calcolata
senza toccare niente, che l'utente legge prima di dire sì. L'esecuzione riceve
il piano approvato e non ne calcola un altro: ricontrolla che l'albero sia
ancora quello su cui il piano è stato fatto, e se non lo è si rifiuta prima di
scrivere il primo byte. Un piano approvato su un albero che nel frattempo è
cambiato è un'approvazione data a un'altra cosa.

Le regole di proprietà sono tre. Un file si cancella solo se è identico byte
per byte al sorgente, cioè se non contiene lavoro di nessuno. Ciò che il
progetto ha adattato — schede, guide, stili — si archivia intero, mai si
cancella. Di `settings.json` si toglie solo ciò che `settings_added` dice
aggiunto dal framework, più le voci hook che punterebbero a uno script andato.
"""

import copy
import hashlib
import json
import re
import shutil
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from . import assemble, doctor, kernel, profile, settings, source

CREATE = "crea"
OVERWRITE = "sovrascrive"
MERGE = "fonde"
KEEP = "lascia"
REMOVE = "rimuove"
ARCHIVE = "archivia"

# L'ordine in cui `render` conta. Le prime quattro cambiano o tolgono
# contenuto che c'era: si leggono per nome, file per file.
ACTIONS = (OVERWRITE, MERGE, ARCHIVE, REMOVE, CREATE, KEEP)
DESTRUCTIVE = (OVERWRITE, MERGE, ARCHIVE, REMOVE)

CLAUDE_MD = "CLAUDE.md"
SETTINGS = ".claude/settings.json"
MANIFEST = source.MANIFEST.as_posix()
ORCHESTRATION = f".claude/{doctor.ORCHESTRATION}"

# Istruzioni di altri strumenti: l'installazione non le tocca, ma chi approva
# il piano deve sapere che ci sono e che possono contraddire CLAUDE.md.
FOREIGN_INSTRUCTIONS = ("AGENTS.md", ".cursorrules", ".github/copilot-instructions.md")
# Le cartelle di `.claude/` dove file del framework e del progetto convivono.
SHARED_DIRS = ("agents", "skills", "output-styles", "hooks", "shared")

# Una voce hook del framework si riconosce dallo script che lancia, non dal
# testo intero del comando: quello cambia fra release, e l'utente lo ritocca.
HOOK_PATH_RE = re.compile(r"\.claude[\\/]+hooks[\\/]+([A-Za-z0-9_-]+)\.py")


@dataclass(frozen=True)
class Operation:
    """Un file del progetto e cosa gli succede.

    `digest` è l'impronta del file quando il piano è stato calcolato, vuota se
    il file non c'era: è ciò che l'esecuzione ricontrolla prima di scrivere.
    """

    path: str
    action: str
    reason: str = ""
    digest: str = ""


def targets(
    framework_root: Path,
    roster: Sequence[str],
    guides: Sequence[str],
    hooks: Sequence[str],
) -> list[str]:
    """Ogni file che l'installazione scrive, relativo alla root del progetto."""
    fw = Path(framework_root)
    out = {CLAUDE_MD, ORCHESTRATION, SETTINGS, MANIFEST}
    out |= {f".claude/agents/{name}.md" for name in roster}
    out |= {f".claude/shared/{rel}" for rel in guides}
    out |= {f".claude/hooks/{name}.py" for name in hooks}
    out |= {f"docs/{name}" for name in doctor.STATE_FILES}
    out |= {rel for rel, _ in _skill_files(fw)}
    out |= {f".claude/output-styles/{p.name}" for p in _files(fw / "output-styles")}
    return sorted(out)


def plan_install(project_root: Path, targets: Sequence[str]) -> list[Operation]:
    """Cosa l'installazione farebbe a questo progetto, file per file.

    `CLAUDE.md`, `settings.json` e i file di stato che ci sono già si fondono:
    sono del progetto prima che del framework. Ogni altro bersaglio presente
    si sovrascrive, e il piano lo dice per nome. I file del progetto che stanno
    nelle cartelle del framework restano, e si elencano: chi approva deve
    sapere che convivranno.
    """
    prj = Path(project_root)
    if (prj / MANIFEST).exists():
        raise ValueError(
            f"{MANIFEST} esiste già: il progetto è installato — "
            "framework-sync --down o --repair, non una seconda installazione"
        )
    mergeable = {CLAUDE_MD, SETTINGS} | {f"docs/{n}" for n in doctor.STATE_FILES}
    ops = []
    for rel in targets:
        if not (prj / rel).exists():
            ops.append(_op(prj, rel, CREATE))
        elif rel in mergeable:
            ops.append(_op(prj, rel, MERGE, "c'è già: si fonde, il contenuto resta"))
        else:
            ops.append(_op(prj, rel, OVERWRITE, "c'è già: si sostituisce"))
    wanted = set(targets)
    for area in SHARED_DIRS:
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            if rel not in wanted:
                ops.append(_op(prj, rel, KEEP, "non è del framework: resta com'è"))
    for rel in FOREIGN_INSTRUCTIONS:
        if (prj / rel).is_file():
            ops.append(
                _op(prj, rel, KEEP, "istruzioni di un altro strumento: restano, "
                    "e possono contraddire CLAUDE.md")
            )
    return ops


def render(ops: Sequence[Operation]) -> str:
    """Il piano da mostrare: prima ciò che cambia o toglie qualcosa, per nome,
    poi i conteggi. Cento righe «crea» sopra una «sovrascrive» la nascondono."""
    lines = [
        f"{op.action:<11} {op.path}" + (f" — {op.reason}" if op.reason else "")
        for op in ops
        if op.action in DESTRUCTIVE
    ]
    counts = Counter(op.action for op in ops)
    lines.append(
        " · ".join(f"{a}: {counts[a]}" for a in ACTIONS if counts[a]) or "nessuna operazione"
    )
    return "\n".join(lines)


def plan_uninstall(project_root: Path, framework_root: Path) -> list[Operation]:
    """Cosa la disinstallazione farebbe, file per file, senza toccare niente.

    Il sorgente serve per sapere cosa è identico all'originale: senza, niente
    si potrebbe cancellare con certezza, e un piano che archivia tutto non è
    quello che l'utente crede di approvare. Un archivio già presente è una
    disinstallazione precedente: scriverci sopra la mescolerebbe con questa.
    """
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    gaps = source.missing(fw)
    if gaps:
        raise ValueError(
            f"sorgente irraggiungibile in {fw} (manca {', '.join(gaps)}): senza, "
            "non si sa quali file sono identici all'originale"
        )
    if (prj / doctor.ARCHIVE_DIR).exists():
        raise ValueError(
            f"{doctor.ARCHIVE_DIR.as_posix()} esiste già: è un'altra disinstallazione, "
            "spostala prima"
        )

    ops = _settings_uninstall_ops(prj, manifest)
    claude = prj / CLAUDE_MD
    if claude.is_file():
        if kernel.parse(claude.read_text(encoding="utf-8")) is None:
            ops.append(_op(prj, CLAUDE_MD, KEEP, "senza marker: nessuna regione del framework"))
        else:
            ops.append(_op(prj, CLAUDE_MD, MERGE, "via la regione kernel, il resto rimane"))

    for area in ("skills", "hooks"):
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            original = fw / area / p.relative_to(prj / ".claude" / area)
            if not original.is_file():
                ops.append(_op(prj, rel, KEEP, "non viene dal sorgente: resta"))
            elif original.read_bytes() == p.read_bytes():
                ops.append(_op(prj, rel, REMOVE, "identico al sorgente"))
            else:
                ops.append(_op(prj, rel, ARCHIVE, "diverso dal sorgente: si conserva"))

    for area in ("agents", "shared", "output-styles"):
        for p in _files(prj / ".claude" / area):
            rel = p.relative_to(prj).as_posix()
            original = fw / area / p.relative_to(prj / ".claude" / area)
            if rel == ORCHESTRATION or original.is_file():
                ops.append(_op(prj, rel, ARCHIVE, "adattato al progetto: si conserva"))
            else:
                ops.append(_op(prj, rel, KEEP, "non viene dal sorgente: resta"))

    for name in doctor.STATE_FILES:
        if (prj / "docs" / name).is_file():
            ops.append(_op(prj, f"docs/{name}", KEEP, "stato del progetto"))
    ops.append(
        _op(prj, MANIFEST, ARCHIVE, "per ultimo: finché c'è, framework-sync ritrova il sorgente")
    )
    return ops


def apply_uninstall(
    project_root: Path, framework_root: Path, ops: Sequence[Operation]
) -> None:
    """Esegue un piano di `plan_uninstall`.

    Tutti i digest si ricontrollano **prima** di scrivere: un file cambiato dopo
    il piano ferma tutto, non solo sé stesso. Anche ogni rimozione si
    ricontrolla contro il sorgente: il piano è un file salvato, e una «rimuove»
    scritta a mano col digest giusto cancellerebbe lavoro del progetto. Poi, in
    quest'ordine: settings, `CLAUDE.md`, spostamenti in archivio col manifesto
    per ultimo, rimozioni, cartelle rimaste vuote.
    """
    prj, fw = Path(project_root), Path(framework_root)
    active = [op for op in ops if op.action != KEEP]
    _verify(prj, active)
    unjustified = sorted(
        op.path for op in active if op.action == REMOVE and not _removable(prj, fw, op.path)
    )
    if unjustified:
        raise ValueError(
            "rimozioni di file non identici al sorgente, niente è stato scritto: "
            + ", ".join(unjustified)
        )
    stray = sorted(
        f"{op.action} {op.path}"
        for op in active
        if (op.action == ARCHIVE and not _archivable(op.path))
        or (op.action == MERGE and op.path not in (CLAUDE_MD, SETTINGS))
    )
    if stray:
        raise ValueError(
            "operazioni che la disinstallazione non pianifica mai, niente è stato scritto: "
            + ", ".join(stray)
        )
    archive = prj / doctor.ARCHIVE_DIR
    if archive.exists():
        raise ValueError(f"{doctor.ARCHIVE_DIR.as_posix()} è comparso dopo il piano: rifallo")
    paths = {op.path for op in active}

    if SETTINGS in paths:
        record = (source.read_manifest(prj) or {}).get("settings_added")
        rest, _, _ = _uninstalled_settings(_read_json(prj / SETTINGS), record)
        _write_json(prj / SETTINGS, rest)

    if CLAUDE_MD in paths:
        claude = prj / CLAUDE_MD
        text = claude.read_text(encoding="utf-8")
        region = kernel.parse(text)
        claude.write_text(text[: region.start] + text[region.end :].lstrip("\n"), encoding="utf-8")

    moved = sorted(
        (op.path for op in active if op.action == ARCHIVE), key=lambda rel: rel == MANIFEST
    )
    for rel in moved:
        dest = archive / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        (prj / rel).rename(dest)
    removed = [op.path for op in active if op.action == REMOVE]
    for rel in removed:
        (prj / rel).unlink()
    _prune(prj, moved + removed)


def plan_repair(project_root: Path, framework_root: Path) -> list[Operation]:
    """Rimette ciò che manca, alla versione installata. Niente si sovrascrive.

    Una skill o un hook diversi dal sorgente sono una modifica locale e
    restano. A una versione diversa «ciò che manca» si misurerebbe contro il
    sorgente sbagliato: prima `--down`.
    """
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    version = _version(fw)
    if manifest.get("version") != version:
        raise ValueError(
            f"installazione a v{manifest.get('version')}, sorgente a v{version}: "
            "prima framework-sync --down, poi --repair"
        )
    keep = (KEEP, "diverso dal sorgente: modifica locale, non si sovrascrive")
    ops = []
    for rel, original in _skill_files(fw):
        ops += _against_source(prj, rel, original, *keep)
    current = _current_settings(prj)
    in_use = _referenced_hooks(current) | _referenced_hooks(manifest.get("settings_added"))
    for name in settings.HOOKS:
        if name in in_use:
            ops += _against_source(prj, f".claude/hooks/{name}.py", _hook_source(fw, name), *keep)
    for name in doctor.STATE_FILES:
        if not (prj / "docs" / name).exists():
            ops.append(_op(prj, f"docs/{name}", CREATE, "assente: dal template, da compilare"))
    for ref in _cited_guides(prj):
        rel = f".claude/shared/{ref}"
        if (prj / rel).exists():
            continue
        if (fw / "shared" / ref).is_file():
            ops.append(_op(prj, rel, CREATE, "citata e assente: dal sorgente, da compilare"))
        else:
            ops.append(_op(prj, rel, KEEP, "citata, assente anche dal sorgente: va scritta"))
    settings_ops = _settings_update_ops(prj, fw, manifest, ops)
    if settings_ops:
        ops += settings_ops
        ops.append(_op(prj, MANIFEST, MERGE, "settings_added: si accoda ciò che si aggiunge"))
    return ops


def plan_down(
    project_root: Path, framework_root: Path, hooks: Sequence[str] | None = None
) -> list[Operation]:
    """Cosa porta una versione nuova: regioni kernel, skill, hook, settings.

    Le regioni kernel le riassemblano i passi della skill, non `apply_update`:
    qui si elencano, e una regione ritoccata dice che la modifica si perde.
    `hooks` sono gli hook da avere dopo; `None` vuol dire quelli che il
    progetto usa già — un progetto nato senza hook non ne riceve in silenzio.
    """
    prj, fw = Path(project_root), Path(framework_root)
    manifest = _manifest(prj)
    version = _version(fw)
    ops = []
    for rel in _kernel_files(prj):
        text = (prj / rel).read_text(encoding="utf-8")
        region = kernel.parse(text)
        original = fw / "agents" / Path(rel).name
        is_agent = rel.startswith(".claude/agents/")
        if is_agent and not original.is_file():
            ops.append(_op(prj, rel, KEEP, "scheda non più nel sorgente: resta com'è"))
            continue
        note = _model_note(text, original.read_text(encoding="utf-8")) if is_agent else ""
        if region is None:
            ops.append(_op(prj, rel, KEEP, "senza marker: nessuna regione da riassemblare"))
        elif kernel.verify(text) == "DRIFT":
            ops.append(_op(prj, rel, MERGE, f"v{region.version} → v{version}, regione "
                           f"modificata a mano: la modifica locale si perde{note}"))
        else:
            ops.append(_op(prj, rel, MERGE, f"v{region.version} → v{version}, resto invariato{note}"))

    overwrite = (OVERWRITE, "diverso dal sorgente: si aggiorna")
    for rel, original in _skill_files(fw):
        ops += _against_source(prj, rel, original, *overwrite)
    if hooks is None:
        current = _current_settings(prj)
        in_use = _referenced_hooks(current) | _referenced_hooks(manifest.get("settings_added"))
        in_use |= {n for n in settings.HOOKS if _hook_after(prj, n, ())}
        hooks = [n for n in settings.HOOKS if n in in_use]
    unknown = [n for n in hooks if n not in settings.HOOKS]
    if unknown:
        raise ValueError(f"hook sconosciuti: {', '.join(unknown)}")
    for name in hooks:
        ops += _against_source(prj, f".claude/hooks/{name}.py", _hook_source(fw, name), *overwrite)
    ops += _settings_update_ops(prj, fw, manifest, ops)
    ops.append(_op(prj, MANIFEST, MERGE, f"version {manifest.get('version')} → {version}"))
    return ops


def apply_update(project_root: Path, framework_root: Path, ops: Sequence[Operation]) -> None:
    """Esegue un piano di `plan_repair` o `plan_down`.

    I file con regione kernel si saltano: li riscrivono i passi della skill,
    che conservano le sezioni di progetto, e quando questa funzione gira sono
    già cambiati. Per tutto il resto i digest si ricontrollano prima di
    scrivere. Poi: copie dal sorgente, voci mancanti in `settings.json`,
    manifesto — versione del sorgente e il nuovo delta accodato al record.
    """
    prj, fw = Path(project_root), Path(framework_root)
    active = [op for op in ops if op.action != KEEP and not _is_kernel_file(op.path)]
    _verify(prj, active)
    manifest = _manifest(prj)
    copies = [
        (op.path, _source_of(fw, op.path))
        for op in active
        if op.action in (CREATE, OVERWRITE) and op.path not in (SETTINGS, MANIFEST)
    ]
    paths = {op.path for op in active}

    for rel, original in copies:
        dest = prj / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, dest)

    added: dict = {}
    if SETTINGS in paths:
        current = _current_settings(prj)
        merged, added, _ = settings.merge(
            current, _framework_settings(prj, fw, manifest, (), current)
        )
        _write_json(prj / SETTINGS, merged)

    if MANIFEST in paths:
        data = dict(manifest)
        data["version"] = _version(fw)
        if added:
            record = data.get("settings_added")
            data["settings_added"] = settings.merge(
                record if isinstance(record, dict) else {}, added
            )[0]
        _write_json(prj / MANIFEST, data)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def _op(prj: Path, rel: str, action: str, reason: str = "") -> Operation:
    return Operation(rel, action, reason, _digest(prj / rel))


def _files(directory: Path) -> list[Path]:
    return sorted(p for p in directory.rglob("*") if p.is_file()) if directory.is_dir() else []


def _skill_files(fw: Path) -> list[tuple[str, Path]]:
    """I file delle skill di ciclo di vita: percorso nel progetto, originale."""
    base = fw / "skills"
    return [
        (f".claude/skills/{p.relative_to(base).as_posix()}", p)
        for skill in doctor.LIFECYCLE_SKILLS
        for p in _files(base / skill)
    ]


def _hook_source(fw: Path, name: str) -> Path:
    return fw / "hooks" / f"{name}.py"


def _kernel_files(prj: Path) -> list[str]:
    out = [rel for rel in (CLAUDE_MD, ORCHESTRATION) if (prj / rel).is_file()]
    agents = _files(prj / ".claude" / "agents")
    return out + [p.relative_to(prj).as_posix() for p in agents if p.suffix == ".md"]


MODEL_LINE_RE = re.compile(r"^(model|effort):[ \t]*(\S+)[ \t]*$", re.MULTILINE)


def _model_note(installed: str, original: str) -> str:
    """Modello ed effort stanno nel frontmatter, che resta del progetto: un
    cambio nel sorgente non arriva da solo, e il piano lo nomina."""
    def lines(text: str) -> dict[str, str]:
        head = re.match(r"---\n(.*?)\n---", text.replace("\r\n", "\n"), re.DOTALL)
        return dict(MODEL_LINE_RE.findall(head.group(1))) if head else {}
    here, there = lines(installed), lines(original)
    diff = [f"{k}: {here.get(k, '-')} qui, {v} nel sorgente"
            for k, v in there.items() if here.get(k) != v]
    return f"; {', '.join(diff)} — si chiede" if diff else ""


def _is_kernel_file(rel: str) -> bool:
    return rel in (CLAUDE_MD, ORCHESTRATION) or rel.startswith(".claude/agents/")


def _against_source(
    prj: Path, rel: str, original: Path, action: str, reason: str
) -> list[Operation]:
    """Un file che deve venire dal sorgente: assente → crea, diverso → `action`."""
    p = prj / rel
    if not p.exists():
        return [_op(prj, rel, CREATE, "assente: dal sorgente")]
    if p.read_bytes() != original.read_bytes():
        return [_op(prj, rel, action, reason)]
    return []


def _source_of(fw: Path, rel: str) -> Path:
    for prefix, area in (
        (".claude/skills/", "skills"),
        (".claude/hooks/", "hooks"),
        (".claude/shared/", "shared"),
        (".claude/output-styles/", "output-styles"),
    ):
        if rel.startswith(prefix):
            return fw / area / rel[len(prefix) :]
    name = rel.removeprefix("docs/")
    if rel.startswith("docs/") and name in doctor.STATE_FILES:
        return fw / "templates" / name
    raise ValueError(f"{rel}: nessun file del sorgente da cui copiarlo")


def _verify(prj: Path, ops: Sequence[Operation]) -> None:
    changed = sorted({op.path for op in ops if _digest(prj / op.path) != op.digest})
    if changed:
        raise ValueError(
            "cambiati dopo il piano, niente è stato scritto — rifai il piano: "
            + ", ".join(changed)
        )


def _removable(prj: Path, fw: Path, rel: str) -> bool:
    """La regola di `plan_uninstall`: si cancella solo una skill o un hook
    identico byte per byte al file del sorgente allo stesso percorso."""
    if ".." in Path(rel).parts:
        return False
    for area in ("skills", "hooks"):
        prefix = f".claude/{area}/"
        if rel.startswith(prefix):
            original = fw / area / rel[len(prefix) :]
            p = prj / rel
            return original.is_file() and p.is_file() and original.read_bytes() == p.read_bytes()
    return False


def _archivable(rel: str) -> bool:
    """I soli file che `plan_uninstall` archivia: dentro le cartelle del
    framework in `.claude/`, più il manifesto. Un'«archivia» scritta a mano non
    sposta codice del progetto né file fuori dalla root."""
    if ".." in Path(rel).parts:
        return False
    return rel == MANIFEST or any(rel.startswith(f".claude/{area}/") for area in SHARED_DIRS)


def _prune(prj: Path, rels: Sequence[str]) -> None:
    """Toglie le cartelle che lo spostamento ha lasciato vuote, dal fondo."""
    dirs = {d for rel in rels for d in (prj / rel).parents if prj in d.parents}
    for d in sorted(dirs, key=lambda p: len(p.parts), reverse=True):
        if d.is_dir() and not any(d.iterdir()):
            d.rmdir()


def _manifest(prj: Path) -> dict:
    data = source.read_manifest(prj)
    if data is None:
        raise ValueError(
            f"{MANIFEST} assente o illeggibile: senza, non si sa cosa "
            "l'installazione ha scritto né da quale sorgente"
        )
    return data


def _version(fw: Path) -> str:
    return (fw / "VERSION").read_text(encoding="utf-8").strip()


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ValueError(f"{path}: JSON non valido ({e})") from e
    if not isinstance(data, dict):
        raise ValueError(f"{path}: non è un oggetto JSON")
    return data


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _current_settings(prj: Path) -> dict:
    path = prj / SETTINGS
    return _read_json(path) if path.is_file() else {}


def _cited_guides(prj: Path) -> list[str]:
    refs: set[str] = set()
    for f in doctor._markdown_files(prj):
        refs |= set(doctor.SHARED_REF_RE.findall(f.read_text(encoding="utf-8")))
    return sorted(refs)


def _hook_name(entry: object) -> str | None:
    command = entry.get("command") if isinstance(entry, dict) else None
    if not isinstance(command, str):
        return None
    return next((n for n in HOOK_PATH_RE.findall(command) if n in settings.HOOKS), None)


def _referenced_hooks(data: object) -> set[str]:
    """Gli hook del framework che una porzione di settings nomina."""
    if not isinstance(data, dict):
        return set()
    text = json.dumps(data.get("hooks", {}))
    return {n for n in HOOK_PATH_RE.findall(text) if n in settings.HOOKS}


def _drop_framework_hooks(data: dict) -> tuple[dict, list[str]]:
    """`(resto, tolte)`: via ogni voce hook che lancia uno script del framework.

    Si tolgono le singole voci, non il gruppo: un hook dell'utente messo sotto
    lo stesso `matcher` resta. Si potano solo i contenitori svuotati qui.
    """
    rest = copy.deepcopy(data)
    events = rest.get("hooks")
    if not isinstance(events, dict):
        return rest, []
    dropped: list[str] = []
    for event in list(events):
        groups = events[event]
        if not isinstance(groups, list):
            continue
        survivors = []
        for group in groups:
            inner = group.get("hooks") if isinstance(group, dict) else None
            if not isinstance(inner, list) or not inner:
                survivors.append(group)
                continue
            keep = [h for h in inner if _hook_name(h) is None]
            dropped += [
                f"{event} «{group.get('matcher', '')}» → .claude/hooks/{_hook_name(h)}.py"
                for h in inner
                if _hook_name(h) is not None
            ]
            if keep:
                survivors.append({**group, "hooks": keep})
        if survivors:
            events[event] = survivors
        elif groups:
            del events[event]
    if not events and data.get("hooks"):
        del rest["hooks"]
    return rest, dropped


def _uninstalled_settings(current: dict, record: object) -> tuple[dict, list[str], list[str]]:
    """`(resto, tenuti, tolte)`: il record tolto, poi ogni voce hook rimasta.

    Una voce hook ritoccata dall'utente non è più uguale al record, e senza
    record non se ne toglie nessuna: ma lo script a cui punta se ne va, e un
    hook chiuso senza script blocca ogni Edit e ogni Bash.
    """
    if isinstance(record, dict):
        rest, kept = settings.unmerge(current, record)
    else:
        rest, kept = copy.deepcopy(current), []
    rest, dropped = _drop_framework_hooks(rest)
    return rest, kept, dropped


def _settings_uninstall_ops(prj: Path, manifest: dict) -> list[Operation]:
    if not (prj / SETTINGS).is_file():
        return []
    record = manifest.get("settings_added")
    _, kept, dropped = _uninstalled_settings(_read_json(prj / SETTINGS), record)
    ops = []
    if isinstance(record, dict):
        reason = "via le voci registrate in settings_added"
        if kept:
            reason += f"; restano, cambiate da te: {', '.join(kept)}"
        ops.append(_op(prj, SETTINGS, MERGE, reason))
    elif not dropped:
        return [_op(prj, SETTINGS, KEEP, "nessun settings_added: non si sa cosa è del framework")]
    for entry in dropped:
        ops.append(
            _op(prj, SETTINGS, MERGE, f"via anche la voce hook {entry}: non è quella "
                "registrata, ma lo script se ne va e un hook chiuso senza script "
                "blocca ogni Edit e Bash")
        )
    return ops


def _hook_after(prj: Path, name: str, ops: Sequence[Operation]) -> bool:
    """Se lo script dell'hook ci sarà dopo il piano."""
    rel = f".claude/hooks/{name}.py"
    return (prj / rel).is_file() or any(
        op.path == rel and op.action in (CREATE, OVERWRITE) for op in ops
    )


def _framework_settings(
    prj: Path, fw: Path, manifest: dict, ops: Sequence[Operation], current: dict
) -> dict:
    """Le voci che il framework vuole in `settings.json`: il profilo, quelle
    dell'orchestrazione installata, più una voce per ogni hook il cui script ci
    sarà e che nessuna voce lancia già.

    L'orchestrazione non sta nel manifesto: si ricava dalla regione kernel della
    guida del coordinatore. Senza guida non si sa quale sia, e ricalcolare
    senza le sue variabili lascerebbe spento un modello che il progetto usa.

    Un hook già nominato non si riaggiunge: se il comando è cambiato fra una
    release e l'altra, la voce nuova si accoderebbe a quella vecchia e l'hook
    girerebbe due volte.
    """
    name = manifest.get("profile")
    path = fw / "profiles" / f"{name}.toml"
    if not isinstance(name, str) or not path.is_file():
        raise ValueError(
            f"profilo {name!r} assente dal sorgente: le voci di settings.json "
            "non si possono ricalcolare"
        )
    guide = prj / ORCHESTRATION
    region = kernel.parse(guide.read_text(encoding="utf-8")) if guide.is_file() else None
    if region is None:
        raise ValueError(
            f"{ORCHESTRATION} assente o senza regione kernel: l'orchestrazione "
            "installata non si ricava e le voci di settings.json non si possono "
            "ricalcolare — riassembla la guida con assemble.orchestration_file, poi riprova"
        )
    orchestration = assemble.installed_orchestration(region.body, fw).stem
    referenced = _referenced_hooks(current)
    names = [n for n in settings.HOOKS if n not in referenced and _hook_after(prj, n, ops)]
    merged, _, conflicts = settings.merge(profile.load(path).settings, settings.hooks(names))
    if conflicts:
        raise ValueError(f"profilo e hook in conflitto su: {', '.join(conflicts)}")
    merged, _, conflicts = settings.merge(
        merged, settings.ORCHESTRATION_SETTINGS.get(orchestration, {})
    )
    if conflicts:
        raise ValueError(f"orchestrazione in conflitto su: {', '.join(conflicts)}")
    return merged


def _settings_update_ops(
    prj: Path, fw: Path, manifest: dict, ops: Sequence[Operation]
) -> list[Operation]:
    current = _current_settings(prj)
    _, added, conflicts = settings.merge(
        current, _framework_settings(prj, fw, manifest, ops, current)
    )
    if not added:
        return []
    reason = "mancano: " + ", ".join(sorted(added))
    if conflicts:
        reason += f"; resta il tuo valore su: {', '.join(conflicts)}"
    action = MERGE if (prj / SETTINGS).is_file() else CREATE
    return [_op(prj, SETTINGS, action, reason)]
