"""Installazione di prova: simula framework-install sul profilo `software`.

Progetto finto: `logtail`, strumento a riga di comando che segue e filtra file
di log. Serve a dimostrare che un'installazione completa passa il doctor e che
il drift viene rilevato.
"""

import json
import re
import shutil
import sys
from datetime import date
from pathlib import Path

from fwbuild import assemble, doctor, profile, settings, source

FRAMEWORK = Path(__file__).resolve().parents[1]
# Fuori dal sorgente: nel pacchetto entra il codice che fa la prova, non la prova.
DEFAULT_OUT = FRAMEWORK.parent / "_build" / "prova"
VERSION = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
# La risposta alla domanda 5: `software` non ne raccomanda nessuna, vale il default.
ORCHESTRATION = assemble.DEFAULT_ORCHESTRATION

DOMAIN = {
    "explorer": (
        "La logica vera sta in `src/logtail/`; `tests/` contiene i test, "
        "`dist/` è generato e non si apre. I comandi sono in `pyproject.toml`. "
        "I file di log di esempio in `fixtures/` possono essere grandi: "
        "leggerne solo le prime righe."
    ),
    "architect": (
        "Vincoli non negoziabili: `src/logtail/core/` non importa nulla da "
        "`src/logtail/cli/` (la direzione è una sola); il formato del file di "
        "configurazione `~/.logtail.toml` è un contratto con gli utenti "
        "esistenti; lo streaming deve restare a memoria costante, qualunque sia "
        "la dimensione del file."
    ),
    "implementer": (
        "Build: `python -m build`. Verifica rapida: `python -m pytest -q`. "
        "Zone delicate: la lettura incrementale in `core/follow.py` (rotazione "
        "del file mentre lo si legge) e il parsing in `core/parse.py`, che deve "
        "tollerare righe malformate senza fermarsi."
    ),
    "tester": (
        "Comando: `python -m pytest -q`. I test stanno in `tests/`, uno per "
        "modulo di `core/`. Non è testabile in automatico il comportamento "
        "interattivo del terminale: si verifica a mano. Regressione già "
        "esistente: rotazione del file durante il follow (`tests/test_follow.py`)."
    ),
    "refactorer": (
        "`core/` ha copertura, `cli/` quasi no: lì il refactoring va fatto a "
        "piccoli passi con verifica manuale. I nomi dei sottocomandi e delle "
        "opzioni sono contratto pubblico: rinominarli rompe gli script degli "
        "utenti anche se il codice compila."
    ),
    "final-reviewer": (
        "Verificato significa: `python -m pytest -q` verde e `python -m build` "
        "senza errori, output alla mano. Non è verificabile in automatico la "
        "resa a terminale: va guardata. Regressioni già viste: gestione della "
        "rotazione del file e encoding non UTF-8 nei log."
    ),
    "debugger": (
        "I guasti visti finora: file ruotato durante il follow (il descrittore "
        "resta sul vecchio inode), encoding non UTF-8 nei log di sistema, "
        "buffer non svuotato quando l'output è una pipe invece di un terminale. "
        "Riproducibile tutto in locale con `fixtures/`."
    ),
    "security-reviewer": (
        "Superfici: i pattern di filtro forniti dall'utente vengono compilati "
        "come espressioni regolari (rischio di backtracking esponenziale su "
        "input ostile); i percorsi dei file di log arrivano da riga di comando "
        "e da `~/.logtail.toml`; i log possono contenere credenziali, quindi "
        "l'output non va mai inviato altrove."
    ),
    "api-scout": (
        "Dipendenze: `click` per la riga di comando, `rich` per la resa a "
        "terminale, versioni bloccate in `requirements.lock`. `rich` cambia API "
        "fra minori con una certa frequenza: verificare sempre nel pacchetto "
        "installato sotto `.venv/lib/`, non nella documentazione online."
    ),
    "silent-failure-hunter": (
        "Errori per eccezione, mai per valore di ritorno. Ripiego voluto e "
        "documentato: una riga malformata si salta e si conta in "
        "`--stats`. Nessun timeout: si leggono solo file locali."
    ),
    "conversation-analyzer": (
        "Errori già corretti più volte: rispondere col contenuto di "
        "`fixtures/big.log` invece che col comando che lo misura; rinominare "
        "un'opzione della riga di comando senza avvisare."
    ),
    "comment-analyzer": (
        "Debito tracciato solo nelle issue, non nei `TODO`. Da non analizzare: "
        "`dist/` e i file generati da `python -m build`."
    ),
}

GUIDES = {
    "core/conventions.md": (
        "Lingua: codice e commit in inglese. Struttura: logica riusabile in "
        "`src/logtail/core/`, interfaccia a riga di comando in "
        "`src/logtail/cli/`. `dist/` e `*.egg-info/` sono generati. I "
        "cambiamenti visibili all'utente vanno in `CHANGELOG.md`."
    ),
    "core/coding-standards.md": (
        "Python 3.11+. Formattazione con `ruff format`, analisi con `ruff "
        "check` — entrambi obbligatori prima di dichiarare finito. Annotazioni "
        "di tipo su tutto ciò che è pubblico. Nessuna dipendenza nuova senza "
        "conferma esplicita dell'utente."
    ),
    "core/architecture-guide.md": (
        "Due moduli: `core/` (logica pura, nessun I/O di terminale, testabile "
        "in isolamento) e `cli/` (analisi degli argomenti e presentazione). La "
        "dipendenza va in una sola direzione: `cli` importa `core`, mai il "
        "contrario. Contratti: formato di `~/.logtail.toml`, nomi dei "
        "sottocomandi, codici di uscita."
    ),
    "core/testing-guide.md": (
        "`python -m pytest -q`, test in `tests/`. Dati sporchi reali in "
        "`fixtures/`: righe troncate, encoding misti, file ruotati. Non "
        "testabile: la resa interattiva a terminale."
    ),
    "core/debugging-playbook.md": (
        "Guasti ricorrenti: rotazione del file durante il follow, encoding non "
        "UTF-8, buffer non svuotato su pipe. `LOGTAIL_DEBUG=1` attiva la "
        "traccia dettagliata su stderr."
    ),
    "core/review-checklist.md": (
        "Verifiche obbligatorie qui: memoria costante durante il follow (un "
        "accumulo si vede solo su file grandi); comportamento su file ruotato; "
        "encoding non UTF-8; output su pipe oltre che su terminale; codici di "
        "uscita invariati."
    ),
    "core/security-guide.md": (
        "Input non fidato: il contenuto dei log e i path da riga di comando. "
        "Nessun segreto e nessuna autenticazione; `~/.logtail.toml` non "
        "contiene credenziali. Un path fuori dalla cartella indicata si rifiuta."
    ),
}

RIGA_DECISIONE = (
    "| D1 | [DA COMPILARE — la scelta in poche parole] | cosa cambierebbe | "
    "i file che tocca | cosa la rende necessaria | cosa la rende rischiosa, "
    "o cosa manca per deciderla |\n"
)

PRIMO_TASK = (
    "coprire `core/follow.py` sulla rotazione del file durante il follow "
    "(regressione nota, `tests/test_follow.py`)"
)

PRIMO_PASSO = (
    "isolare la lettura incrementale in `core/follow.py` dietro un'interfaccia "
    "sola, perché il caso «file ruotato» sia testabile senza terminale"
)

# Il Passo 5 vuole il primo obiettivo col suo criterio, non lo scheletro: un
# segnaposto residuo è un PLACEHOLDER al Passo 6.
PRIMO_OBIETTIVO = (
    "| 1 | Follow affidabile su file ruotato | segue il file oltre rotazione, "
    "troncamento e ricreazione | `core/follow.py`, `tests/test_follow.py` | è la "
    "regressione che rende `logtail -f` inservibile in produzione, e blocca ogni "
    "lavoro sui filtri incrementali | `tests/test_follow.py` copre i tre casi e "
    "passa su `fixtures/big.log` a memoria costante | il comportamento della "
    "rotazione dipende dal filesystem: da provare anche su volume di rete |"
)

PROJECT_SECTIONS = """## Il progetto

`logtail` — strumento a riga di comando che segue e filtra file di log in tempo
reale.

| Path | Ruolo |
|---|---|
| `src/logtail/core/` | logica pura: lettura incrementale, parsing, filtri |
| `src/logtail/cli/` | analisi degli argomenti, resa a terminale |
| `tests/` | test per ogni modulo di `core/` |
| `fixtures/` | log reali e sporchi per i test |

**Vincoli DURI:**

- `core/` non importa da `cli/`: la dipendenza va in una direzione sola.
- Memoria costante durante il follow, qualunque sia la dimensione del file.
- Righe malformate non fermano l'elaborazione e finiscono in un conteggio.

**Contratti:** formato di `~/.logtail.toml` · nomi dei sottocomandi e delle
opzioni · codici di uscita. Cambiarli rompe gli script degli utenti.

## Comandi

```bash
python -m pytest -q          # test — verifica rapida che fa l'agente
ruff check && ruff format    # analisi e formattazione
python -m build              # build completa
```

Le misure di prestazione su `fixtures/big.log` (2 GB) le lancia l'utente.

## Superficie critica

Sicurezza: i pattern di filtro dell'utente diventano espressioni regolari, i
percorsi arrivano da riga di comando e da configurazione, e i log possono
contenere credenziali. Rivede `security-reviewer` prima della verifica finale.

## Stato attuale

Progetto appena inizializzato. Nessuna conclusione consolidata.

## Guide condivise

**Solo il coordinatore, e per primo se la sessione delega:**
`.claude/shared/orchestration.md` — quando delegare e a chi, il ciclo di lavoro,
come si scrive un prompt, come si tiene aggiornato lo stato.

Da aprire quando il task rientra nel dominio:

- `.claude/shared/core/conventions.md` — regole trasversali di forma: nomi, commit, commenti.
- `.claude/shared/core/coding-standards.md` — come si struttura il codice, più il blocco dello stack di questo progetto. Prima di scrivere codice.
- `.claude/shared/core/architecture-guide.md` — confini, contratti, direzione delle dipendenze. Prima di cambiare un contratto.
- `.claude/shared/core/testing-guide.md` — come si applica «pochi test sensati, mai molti test deboli».
- `.claude/shared/core/debugging-playbook.md` — mappa sintomo → sospetti, su un guasto a causa ignota.
- `.claude/shared/core/review-checklist.md` — cosa si guarda in una review, in chiusura di task.
"""

STILE_PROGETTO = """Si danno per noti Python, i test e la riga di comando; si introduce alla prima
comparsa tutto ciò che riguarda i descrittori di file e gli encoding.
"""

ROUTING = """## Roster di questo progetto

| Situazione | Agente | Modello |
|---|---|---|
| Dove sta / chi usa X | `explorer` | haiku low |
| Design, piani multi-file, contratti | `architect` | opus xhigh |
| Scrivere codice di produzione | `implementer` | sonnet high |
| Estendere i test | `tester` | sonnet medium |
| Refactoring a comportamento invariato | `refactorer` | sonnet high |
| Bug a causa ignota | `debugger` | opus high |
| Firme di librerie esterne | `api-scout` | sonnet medium |
| Superficie raggiungibile da un attaccante | `security-reviewer` | opus high |
| Errori inghiottiti, ripieghi che nascondono | `silent-failure-hunter` | sonnet medium |
| Commenti che non dicono più il vero | `comment-analyzer` | sonnet medium |
| Errori ricorrenti nelle trascrizioni | `conversation-analyzer` | sonnet medium |
| Verifica finale | `final-reviewer` | opus high |

## Note di delega per questo progetto

Le misure di prestazione su `fixtures/big.log` (2 GB) le lancia l'utente, non
l'agente: preparare il comando e attendere l'output incollato.
"""

PLACEHOLDER_BLOCK = re.compile(r"\[DA COMPILARE[^\]]*\]", re.DOTALL)


def fill(text: str, replacement: str) -> str:
    filled, n = PLACEHOLDER_BLOCK.subn(replacement, text)
    if n == 0:
        raise SystemExit("nessun blocco [DA COMPILARE] trovato")
    return filled


def choices() -> tuple[profile.Profile, list[str], list[str], tuple[str, ...]]:
    """Le risposte del questionario: profilo, roster, guide, hook.

    Una funzione e non variabili dentro `install()`: il piano di installazione
    si calcola dalle stesse scelte, e due copie divergerebbero in silenzio.
    """
    prof = profile.load(FRAMEWORK / "profiles" / "software.toml")
    roster = profile.roster(prof, extras=[], drop=[])
    return prof, roster, profile.guides(FRAMEWORK, prof, roster), settings.HOOKS


def install(out: Path) -> int:
    """Installa il progetto finto e restituisce il numero di agenti."""
    if out.exists():
        shutil.rmtree(out)
    (out / ".claude" / "agents").mkdir(parents=True)
    (out / ".claude" / "shared" / "core").mkdir(parents=True)
    (out / ".claude" / "output-styles").mkdir(parents=True)
    (out / ".claude" / "hooks").mkdir(parents=True)
    (out / "docs").mkdir(parents=True)

    prof, roster, guides, hooks = choices()

    (out / "CLAUDE.md").write_text(
        assemble.build_document(FRAMEWORK / "method", VERSION, PROJECT_SECTIONS),
        encoding="utf-8",
    )

    # La guida del coordinatore: stessa meccanica, altro destinatario. Non entra
    # in CLAUDE.md, quindi i subagent non la pagano. L'orchestrazione scelta e
    # i cicli dichiarati dal profilo si accodano qui, in quest'ordine: sono
    # orchestrazione, non esecuzione.
    (out / ".claude" / "shared" / "orchestration.md").write_text(
        assemble.build_document(
            FRAMEWORK / "coordinator",
            VERSION,
            ROUTING,
            extra=[
                assemble.orchestration_file(FRAMEWORK, ORCHESTRATION),
                *assemble.cycle_files(FRAMEWORK, prof.cycles),
            ],
        ),
        encoding="utf-8",
    )

    for name in roster:
        src = (FRAMEWORK / "agents" / f"{name}.md").read_text(encoding="utf-8")
        fm, method, domain = assemble.split_source(src)
        domain = fill(domain, DOMAIN[name])
        (out / ".claude" / "agents" / f"{name}.md").write_text(
            assemble.build_agent(fm, method, domain, VERSION), encoding="utf-8"
        )

    for rel in guides:
        text = (FRAMEWORK / "shared" / rel).read_text(encoding="utf-8")
        (out / ".claude" / "shared" / rel).write_text(fill(text, GUIDES[rel]), encoding="utf-8")

    for name in hooks:
        shutil.copy(FRAMEWORK / "hooks" / f"{name}.py", out / ".claude" / "hooks")

    # Il profilo e gli hook prima fra loro, poi sopra ciò che il progetto ha già
    # — qui niente, ma il passo è lo stesso di un progetto vero: è l'aggiunto
    # che il manifesto registra, perché la disinstallazione tolga solo quello.
    framework_settings, _, conflicts = settings.merge(prof.settings, settings.hooks(hooks))
    if conflicts:
        raise SystemExit(f"profilo e hook in conflitto su: {', '.join(conflicts)}")
    framework_settings, _, conflicts = settings.merge(
        framework_settings, settings.ORCHESTRATION_SETTINGS.get(ORCHESTRATION, {})
    )
    if conflicts:
        raise SystemExit(f"orchestrazione in conflitto su: {', '.join(conflicts)}")
    merged, added, conflicts = settings.merge({}, framework_settings)
    if conflicts:
        raise SystemExit(f"settings.json in conflitto su: {', '.join(conflicts)}")
    (out / ".claude" / "settings.json").write_text(
        json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )

    # Come `framework-doctor` e `framework-sync` ritrovano il sorgente dopo, e
    # con quale profilo il progetto è nato. La forma la decide `source.manifest`:
    # il percorso è relativo quando il sorgente sta dentro il progetto, così il
    # file sopravvive al clone.
    (out / ".claude" / "framework.json").write_text(
        json.dumps(
            source.manifest(out, FRAMEWORK, VERSION, prof.name, settings_added=added),
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )

    for name in ("TODO.md", "status.md", "roadmap.md"):
        shutil.copy(FRAMEWORK / "templates" / name, out / "docs" / name)

    # Passo 5: il TODO nasce con la prima voce reale e la data. Un template
    # copiato e non compilato lascia la sessione successiva a indovinare.
    todo = out / "docs" / "TODO.md"
    todo.write_text(
        todo.read_text(encoding="utf-8")
        .replace("[DA COMPILARE — il task attivo, uno solo]", PRIMO_TASK)
        .replace(
            "[DA COMPILARE — il passo successivo, in ordine di dipendenza]",
            PRIMO_PASSO,
        )
        .replace("[DA COMPILARE — la data di oggi]", date.today().isoformat())
        # Nessuna decisione aperta alla nascita: la riga di esempio se ne va,
        # l'intestazione resta a dire la forma.
        .replace(RIGA_DECISIONE, ""),
        encoding="utf-8",
    )

    roadmap = out / "docs" / "roadmap.md"
    roadmap.write_text(
        re.sub(
            r"^\| 1 \| \[DA COMPILARE.*|^\*\*Ordine:\*\* \[DA COMPILARE[^\]]*\]",
            lambda m: PRIMO_OBIETTIVO if m.group().startswith("| 1 |") else "**Ordine:** 1",
            roadmap.read_text(encoding="utf-8"),
            flags=re.MULTILINE,
        ),
        encoding="utf-8",
    )

    # Le skill di ciclo di vita vanno dove Claude Code le cerca, altrimenti
    # non sono invocabili nel progetto.
    for skill in doctor.LIFECYCLE_SKILLS:
        shutil.copytree(FRAMEWORK / "skills" / skill, out / ".claude" / "skills" / skill)

    # Lo stile di risposta: `outputStyle` nei settings lo nomina, questo file lo
    # definisce. Il blocco di progetto si compila subito, come ogni segnaposto.
    stile = (FRAMEWORK / "output-styles" / "reporting.md").read_text(encoding="utf-8")
    (out / ".claude" / "output-styles" / "reporting.md").write_text(
        fill(stile, STILE_PROGETTO), encoding="utf-8"
    )

    print(f"installato: {len(roster)} agenti, {len(guides)} guide -> {out}")
    return len(roster)


if __name__ == "__main__":
    install(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT)
