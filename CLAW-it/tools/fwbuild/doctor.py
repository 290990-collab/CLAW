"""Le verifiche di integrità di un'installazione.

Venti codici di rilievo: otto di gravità ERROR (PLACEHOLDER, ROSTER_MISSING,
SHARED_MISSING, STATE_MISSING, KERNEL_MISSING, FABLE, EXCLUSIVE,
MANIFEST_MISSING) e dodici di gravità WARN (ROSTER_ORPHAN, KERNEL_DRIFT,
COORDINATOR_LEAK, SKILLS_MISSING, VERSION_MISMATCH, SETTINGS_MISSING,
SHARED_ORPHAN, TOKEN_BUDGET, REPORT_FORMAT, ACCEPTED_UNUSED, UNSAFE_UNICODE,
PERSONAL_PATH). MANIFEST_MISSING
è l'unico che esce a entrambe: ERROR se il file manca, WARN se è incompleto.
Ogni codice è spiegato, con cosa farne, nella skill `framework-doctor`.

Una terza gravità, NOTE, non nasce qui: è un WARN che il progetto ha dichiarato
di accettare in `framework.json`. Resta stampato — una deroga invisibile è una
deroga dimenticata — ma non fa cadere `--strict`.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import assemble, kernel, profile, source

# Un marker solo, e non `{{...}}`: quella è la sintassi di mezzo mondo dei
# template (Vue, Angular, Jinja, Handlebars), e un progetto che la nomina nei
# propri vincoli prenderebbe un ERROR senza via d'uscita.
PLACEHOLDER_RE = re.compile(r"DA COMPILARE")
# Il formato superato del report: la confidenza **come** percentuale, cioè
# `CONF:` seguito da un segnaposto con `%` (`<0-100%>`) o da una cifra. Un
# progetto installato con quel formato se lo tiene finché non passa da
# `framework-sync --down`: nessun altro check lo vede, perché l'hash del kernel
# torna su quel testo. Il valore dev'essere la percentuale: `CONF: ALTA —
# copertura all'80%` è un giudizio categorico che cita un numero nel motivo, ed
# è testo legittimo che il pattern non deve toccare.
CONF_PERCENT_RE = re.compile(r"CONF:\s*(?:<[^>\n]*%|\d[^%\n]*%)")
ROUTING_AGENT_RE = re.compile(r"^\|[^|]*\|\s*`([a-z-]+)`\s*\|", re.MULTILINE)
FABLE_RE = re.compile(r"^model:\s*fable\s*$", re.MULTILINE)
SHARED_REF_RE = re.compile(r"\.claude/shared/([A-Za-z0-9_./-]+\.md)")
# Caratteri che il modello legge e chi rivede il file non vede: controlli
# bidirezionali, spazi a larghezza zero, operatori invisibili, riempitivi, il
# blocco dei tag (il veicolo dell'«ASCII smuggling»). Fuori i selettori di
# variante U+FE00-FE0F e U+E0100-E01EF: compongono le emoji, e U+FE0F sta nel
# sorgente stesso. U+FEFF conta solo oltre l'offset 0: a inizio file è il BOM
# che scrivono gli editor, e lo sguardo all'indietro su un carattere qualunque
# lo esclude lì. Solo escape: il sorgente scansiona sé stesso.
UNSAFE_CHARS_RE = re.compile(
    r"[\u200B-\u200D\u2060-\u2064\u202A-\u202E\u2066-\u2069"
    r"\u115F\u1160\u180E\u3164\U000E0000-\U000E007F]"
    r"|(?<=[\s\S])\uFEFF"
)
# Una cartella utente: Windows (anche con le barre raddoppiate del JSON), macOS,
# Linux. I nomi segnaposto dei template non contano, a qualunque maiuscola, e
# nemmeno le cartelle condivise che ogni macchina ha. Su Windows `Users` è
# senza maiuscole: il filesystem non le distingue.
PERSONAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]+(?i:users)[\\/]+|/Users/|/home/)"
    r"(?!(?i:example|me|user|username|you|yourname|yourusername|your-username"
    r"|public|shared|default|all users)"
    r"(?![A-Za-z0-9._-]))"
    r"[A-Za-z][A-Za-z0-9._-]*"
)
STATE_FILES = ("TODO.md", "status.md", "roadmap.md")
# Le skill che ogni installazione riceve. Una lista sola: duplicarla nel
# tooling e nei test significa aggiungerne una e scoprire dal rosso dove
# stavano le copie.
LIFECYCLE_SKILLS = ("framework-doctor", "framework-sync", "framework-memory")
ORCHESTRATION = "shared/orchestration.md"
# Dove la disinstallazione sposta ciò che il progetto aveva adattato, col
# percorso relativo conservato.
ARCHIVE_DIR = Path(".claude") / "framework-archive"

# Titoli che appartengono alla guida del coordinatore. Se ricompaiono in
# CLAUDE.md, ogni subagent li paga a ogni spawn senza poterli usare: è la
# separazione per destinatario che si sta riperdendo.
COORDINATOR_ONLY = (
    "Economia dei token — le dieci regole della delega",
    "Il ciclo del codice",
    "Come si scrive un prompt di delega",
    "Lo stato che si aggiorna da solo",
    "Scegliere fra agenti che sembrano vicini",
    "Roster di questo progetto",
    "Orchestrazione: orchestratore e worker",
    "Orchestrazione: Agent teams",
)


def _source_version() -> str | None:
    """La versione del sorgente, dedotta dalla posizione del pacchetto.

    `fwbuild` vive nella cartella `tools/` del sorgente: la root è due livelli
    sopra. Il nome della cartella del sorgente non è assunto da nessuna parte.
    Se non è raggiungibile il check si salta — il doctor deve restare
    utilizzabile senza il sorgente.
    """
    p = Path(__file__).resolve().parents[2] / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


# Stima: nessun tokenizer sta nella stdlib e il doctor gira offline. Il
# rapporto viene da una misura fatta una volta su una CLAUDE.md assemblata
# (1598 parole ≈ 2,1k token): fissa il rapporto, non descrive il file corrente,
# che cambia a ogni modifica del metodo. Il numero esatto lo dà l'endpoint
# count_tokens, non questo strumento: qui serve un ordine di grandezza.
TOKENS_PER_WORD = 1.33


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str

    @property
    def blocking(self) -> bool:
        """Se conta per `--strict`. Una nota dichiarata no: è già stata vista."""
        return self.severity != "NOTE"


@dataclass(frozen=True)
class Measure:
    """La CLAUDE.md installata, divisa nelle due parti che la compongono.

    `kernel` lo scrive il framework e ha un tetto che rompe la build in fase di
    sorgente; `project` lo scrive chi installa e non ha nessun tetto. È la sola
    delle due che cresce, perché cresce col progetto.
    """

    kernel_words: int
    project_words: int
    has_region: bool

    @property
    def total_words(self) -> int:
        return self.kernel_words + self.project_words

    @property
    def tokens(self) -> int:
        return round(self.total_words * TOKENS_PER_WORD)


def measure(claude_text: str) -> Measure:
    """Misura una CLAUDE.md separando regione kernel e sezioni di progetto.

    Senza marker — installazione senza tracking, legittima — le due parti non
    sono distinguibili: si riporta il totale e si dichiara che la separazione
    non c'è, invece di attribuire tutto a una delle due e far scattare un rilievo
    su un'installazione sana.
    """
    region = kernel.parse(claude_text)
    if region is None:
        return Measure(len(claude_text.split()), 0, has_region=False)
    outside = claude_text[: region.start] + claude_text[region.end :]
    return Measure(len(region.body.split()), len(outside.split()), has_region=True)


def _markdown_files(root: Path) -> list[Path]:
    """I file adattati al progetto, che vanno verificati.

    `.claude/skills/` è escluso: le skill sono file di framework copiati alla
    lettera, senza regione kernel né blocchi da compilare — e `framework-doctor`
    contiene per forza la stringa `DA COMPILARE`, perché ne spiega il rilievo.
    I file di stato in `docs/` sono inclusi: nascono da un template con
    segnaposto, e un template non compilato è indistinguibile da uno stato
    assente per chi lo legge a inizio sessione.

    L'archivio della disinstallazione è escluso: conserva le schede come
    erano, segnaposti e pointer compresi, ed è materiale da consultare.
    """
    files = [root / "CLAUDE.md"]
    claude_dir = root / ".claude"
    if claude_dir.is_dir():
        skipped = (claude_dir / "skills", root / ARCHIVE_DIR)
        files += sorted(
            p
            for p in claude_dir.rglob("*.md")
            if not any(d in p.parents for d in skipped)
        )
    files += [root / "docs" / name for name in STATE_FILES]
    return [f for f in files if f.is_file()]


def _scanned_files(root: Path) -> list[Path]:
    """I file in cui cercare caratteri invisibili e percorsi personali.

    Più larga di `_markdown_files`: le skill e gli hook si copiano alla lettera,
    ma un carattere nascosto in una skill è proprio il veicolo che si cerca, e
    un percorso personale ci arriva allo stesso modo. **Mai `framework.json`:**
    il suo `source` è assoluto per costruzione quando il sorgente sta fuori dal
    progetto, e segnalarlo darebbe un avviso su ogni installazione fatta così.
    """
    claude_dir = root / ".claude"
    files = _markdown_files(root)
    files += sorted((claude_dir / "skills").rglob("*.md"))
    files += sorted((claude_dir / "hooks").glob("*.py"))
    files.append(claude_dir / "settings.json")
    return [f for f in files if f.is_file()]


def check(root: Path) -> list[Finding]:
    root = Path(root)
    out: list[Finding] = []
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        return [Finding("STATE_MISSING", "ERROR", "CLAUDE.md assente")]

    agents_dir = root / ".claude" / "agents"
    present = {p.stem for p in agents_dir.glob("*.md")} if agents_dir.is_dir() else set()

    # I file che nascono **con** una regione kernel. Le guide di `shared/` no:
    # si copiano e si compilano, non contengono metodo generato.
    tracked = {"CLAUDE.md", f".claude/{ORCHESTRATION}"} | {
        f".claude/agents/{name}.md" for name in present
    }

    texts = {
        f.relative_to(root).as_posix(): f.read_text(encoding="utf-8")
        for f in _markdown_files(root)
    }
    claude_text = texts["CLAUDE.md"]
    versions: dict[str, str] = {}
    referenced: set[str] = set()

    # La variante senza marker è legittima: nessun tracking, per scelta. Ma se
    # anche un solo file tracciato ce l'ha, l'installazione è tracciata, e un
    # file che li ha persi non è distinguibile da uno riscritto a mano.
    markers = any(kernel.parse(t) for rel, t in texts.items() if rel in tracked)

    for rel, text in texts.items():
        if PLACEHOLDER_RE.search(text):
            out.append(
                Finding("PLACEHOLDER", "ERROR", f"{rel}: segnaposto non compilato")
            )
        if FABLE_RE.search(text):
            out.append(Finding("FABLE", "ERROR", f"{rel}: model fable non disponibile"))
        if CONF_PERCENT_RE.search(text):
            out.append(
                Finding(
                    "REPORT_FORMAT",
                    "WARN",
                    f"{rel}: schema del report con confidenza in percentuale — "
                    "formato superato, riallinea con framework-sync --down",
                )
            )
        status = kernel.verify(text)
        if status == "DRIFT":
            out.append(
                Finding("KERNEL_DRIFT", "WARN", f"{rel}: regione kernel modificata")
            )
        elif status == "MISSING" and markers and rel in tracked:
            out.append(
                Finding(
                    "KERNEL_MISSING",
                    "ERROR",
                    f"{rel}: marker rimossi — il metodo non è più verificabile",
                )
            )
        if rel in tracked:
            region = kernel.parse(text)
            if region is not None:
                versions[rel] = region.version
        # Il pointer si verifica ovunque, non solo in CLAUDE.md: le guide sono
        # citate dagli agenti, ed è lì che quasi tutti i pointer vivono.
        for ref in sorted(set(SHARED_REF_RE.findall(text))):
            referenced.add(ref)
            if not (root / ".claude" / "shared" / ref).is_file():
                out.append(
                    Finding(
                        "SHARED_MISSING",
                        "ERROR",
                        f"{rel} → .claude/shared/{ref}: referenziata ma assente",
                    )
                )

    # La tabella di routing è contenuto da coordinatore: vive nella sua guida.
    # Si ricade su CLAUDE.md solo dove quella guida non c'è (installazione
    # parziale, o progetto senza delega), così il roster resta verificabile.
    routed = set(ROUTING_AGENT_RE.findall(texts.get(f".claude/{ORCHESTRATION}", claude_text)))

    for name in sorted(routed - present):
        out.append(
            Finding(
                "ROSTER_MISSING",
                "ERROR",
                f"{name}: citato nella tabella di routing, file assente",
            )
        )
    for name in sorted(present - routed):
        out.append(
            Finding(
                "ROSTER_ORPHAN",
                "WARN",
                f"{name}: file presente, assente dalla tabella di routing",
            )
        )

    # Le versioni: prima fra loro, poi contro il sorgente. Nessun altro check
    # le vede — su un metodo vecchio l'hash torna, perché torna su quello.
    # È la biforcazione fra progetti, cioè il difetto che il framework esiste
    # per evitare.
    declared = sorted(set(versions.values()))
    if len(declared) > 1:
        common = max(declared, key=list(versions.values()).count)
        odd = sorted(rel for rel, v in versions.items() if v != common)
        out.append(
            Finding(
                "VERSION_MISMATCH",
                "WARN",
                f"progetto a v{common}, ma: "
                + ", ".join(f"{rel} v{versions[rel]}" for rel in odd),
            )
        )
    # Non `source`: il modulo omonimo serve più sotto, e ombreggiarlo qui è
    # esattamente il modo in cui l'errore si nasconde fino al primo uso.
    source_version = _source_version()
    if source_version is not None and declared and declared != [source_version]:
        out.append(
            Finding(
                "VERSION_MISMATCH",
                "WARN",
                f"installazione a v{'/'.join(declared)}, sorgente a v{source_version}: "
                "riallinea con framework-sync --down",
            )
        )

    # L'inverso di SHARED_MISSING. Una guida che nessuno cita è contesto
    # installato e mai aperto: il costo c'è, l'uso no.
    shared_dir = root / ".claude" / "shared"
    if shared_dir.is_dir():
        for p in sorted(shared_dir.rglob("*.md")):
            rel = p.relative_to(shared_dir).as_posix()
            if rel != "orchestration.md" and rel not in referenced:
                out.append(
                    Finding(
                        "SHARED_ORPHAN",
                        "WARN",
                        f".claude/shared/{rel}: installata e citata da nessuno",
                    )
                )

    for conflict in profile.check_exclusive(sorted(present)):
        out.append(
            Finding("EXCLUSIVE", "ERROR", f"agenti mutuamente esclusivi: {conflict}")
        )

    for name in STATE_FILES:
        if not (root / "docs" / name).is_file():
            out.append(Finding("STATE_MISSING", "ERROR", f"docs/{name} assente"))

    manifest = source.read_manifest(root)
    if manifest is None:
        out.append(
            Finding(
                "MANIFEST_MISSING",
                "ERROR",
                ".claude/framework.json assente o illeggibile: framework-sync non "
                "ritrova il sorgente e il rapporto di flotta non vede il progetto",
            )
        )
    else:
        gaps = [
            k
            for k in ("source", "version", "profile")
            if not isinstance(manifest.get(k), str) or not manifest[k].strip()
        ]
        if gaps:
            out.append(
                Finding(
                    "MANIFEST_MISSING",
                    "WARN",
                    f".claude/framework.json senza {', '.join(gaps)}: "
                    "l'installazione non sa più da cosa è nata",
                )
            )
        # La versione del manifesto è l'unica che si legge senza aprire un
        # documento generato: se diverge dai marker, dichiara una versione che
        # il progetto non ha.
        elif declared and manifest["version"].strip() not in declared:
            out.append(
                Finding(
                    "VERSION_MISMATCH",
                    "WARN",
                    f".claude/framework.json dichiara v{manifest['version'].strip()}, "
                    f"i marker dicono v{'/'.join(declared)}",
                )
            )

    for skill in LIFECYCLE_SKILLS:
        if not (root / ".claude" / "skills" / skill / "SKILL.md").is_file():
            out.append(
                Finding(
                    "SKILLS_MISSING",
                    "WARN",
                    f".claude/skills/{skill}/ assente: la skill non è invocabile "
                    "in questo progetto",
                )
            )

    # Le skill dei pacchetti collegati: il manifesto dice quali il progetto ha
    # ricevuto, e si verifica da lì perché il sorgente può non essere
    # raggiungibile da qui. Un pacchetto staccato dal sorgente e non ancora
    # sincronizzato non lascia rilievi: la voce sparisce dal manifesto.
    declared = manifest.get("skills") if isinstance(manifest, dict) else None
    if isinstance(declared, dict):
        for skill, package in sorted(declared.items()):
            if not (root / ".claude" / "skills" / str(skill) / "SKILL.md").is_file():
                out.append(
                    Finding(
                        "SKILLS_MISSING",
                        "WARN",
                        f".claude/skills/{skill}/ assente: la skill del pacchetto "
                        f"{package} non è invocabile in questo progetto",
                    )
                )

    if present and not (root / ".claude" / "settings.json").is_file():
        out.append(
            Finding(
                "SETTINGS_MISSING",
                "WARN",
                ".claude/settings.json assente: i permessi del profilo non sono "
                "in vigore. Coprono lo strumento Read, non la shell — `Bash(cat "
                ".env)` resta possibile, e nessun file lo impedisce",
            )
        )

    if present and f".claude/{ORCHESTRATION}" not in texts:
        out.append(
            Finding(
                "SHARED_MISSING",
                "ERROR",
                f".claude/{ORCHESTRATION} assente: senza, il coordinatore non ha "
                "le regole di delega",
            )
        )

    # Il tetto sul sorgente vincola ciò che scrive il framework. Questo guarda
    # il file assemblato, che è quello che ogni spawn paga davvero: la soglia è
    # il kernel stesso — l'unica grandezza nota — cioè il progetto non scrive
    # più del metodo. WARN e non ERROR: romperebbe la build di un progetto.
    #
    # Sotto il tetto che il framework si dà per il solo metodo il rilievo tace:
    # su un file piccolo il rapporto è vero e irrilevante, e un avviso su undici
    # token è rumore.
    m = measure(claude_text)
    if (
        m.has_region
        and m.total_words >= assemble.METHOD_WORD_BUDGET
        and m.project_words > m.kernel_words
    ):
        out.append(
            Finding(
                "TOKEN_BUDGET",
                "WARN",
                f"CLAUDE.md: {m.project_words} parole di progetto contro "
                f"{m.kernel_words} di kernel — {m.total_words} in tutto, "
                f"≈{m.tokens} token pagati a ogni spawn",
            )
        )

    for heading in COORDINATOR_ONLY:
        if heading in claude_text:
            out.append(
                Finding(
                    "COORDINATOR_LEAK",
                    "WARN",
                    f'CLAUDE.md contiene "{heading}": è contenuto da coordinatore, '
                    f"pagato da ogni subagent a ogni spawn",
                )
            )

    # Un rilievo per file, alla prima occorrenza: basta per aprirlo. Il
    # percorso trovato non si stampa — è il nome di chi l'ha scritto. Skill e
    # hook dell'utente possono non essere UTF-8: qui si scansionano soltanto, e
    # un byte illeggibile non deve fermare il doctor né `fwbuild report`.
    for f in _scanned_files(root):
        rel = f.relative_to(root).as_posix()
        text = texts[rel] if rel in texts else f.read_text(encoding="utf-8", errors="replace")
        hidden = UNSAFE_CHARS_RE.search(text)
        if hidden:
            line = text.count("\n", 0, hidden.start()) + 1
            out.append(
                Finding(
                    "UNSAFE_UNICODE",
                    "WARN",
                    f"{rel}:{line}: carattere invisibile U+{ord(hidden.group()):04X}"
                    " — il modello lo legge, chi rivede il file no",
                )
            )
        personal = PERSONAL_PATH_RE.search(text)
        if personal:
            line = text.count("\n", 0, personal.start()) + 1
            out.append(
                Finding(
                    "PERSONAL_PATH",
                    "WARN",
                    f"{rel}:{line}: percorso dentro la cartella di un utente — "
                    "non esiste sulla macchina di chi clona",
                )
            )

    return _apply_accepted(root, out)


def _match(finding: Finding, keys: list[str]) -> str | None:
    """La deroga che copre questo rilievo, la più specifica per prima.

    `CODICE` copre tutti i rilievi di quel codice; `CODICE:frammento` solo
    quelli il cui messaggio contiene il frammento — di norma un percorso.
    """
    for key in keys:
        code, _, fragment = key.partition(":")
        if code == finding.code and (not fragment or fragment in finding.message):
            return key
    return None


def _apply_accepted(root: Path, findings: list[Finding]) -> list[Finding]:
    """Declassa a NOTE gli avvisi che il progetto dichiara di accettare.

    **Gli ERROR non si accettano.** Un avviso è un giudizio — «questo file è
    grosso», «questa guida non la cita nessuno» — e su un giudizio un progetto
    può avere ragione contro il default. Un errore è un'installazione che non
    funziona: un segnaposto non compilato o un pointer rotto restano rotti anche
    se qualcuno scrive che gli vanno bene.

    Una deroga che non copre niente diventa a sua volta un avviso: resterebbe
    nel file dopo che il rilievo è sparito, e la volta dopo zittirebbe altro.
    Vale anche per quella senza ragione scritta, che non si applica: sparire in
    silenzio è il modo in cui una regola smette di esistere senza che si veda.
    """
    rules = source.accepted(root)
    if not rules:
        return findings
    keys = sorted(rules, key=lambda k: (":" not in k, k))
    used: set[str] = set()
    refused: set[str] = set()
    out: list[Finding] = []
    for f in findings:
        key = _match(f, keys)
        if key is None or not rules[key]:
            out.append(f)
        elif f.severity == "ERROR":
            refused.add(key)
            out.append(f)
        else:
            used.add(key)
            out.append(Finding(f.code, "NOTE", f"{f.message} — accettato: {rules[key]}"))
    for key in keys:
        if key in used:
            continue
        why = (
            "senza una ragione scritta, quindi non si applica"
            if not rules[key]
            else "copre un ERROR, e gli errori non si accettano"
            if key in refused
            else "nessun rilievo corrisponde"
        )
        out.append(
            Finding("ACCEPTED_UNUSED", "WARN", f'framework.json accetta "{key}": {why}')
        )
    return out
