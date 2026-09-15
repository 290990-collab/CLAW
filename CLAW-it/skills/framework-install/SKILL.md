---
name: framework-install
description: >
  Installa e adatta il framework in un progetto: rileva se il progetto è vuoto o
  ha già del codice, fa il questionario, sceglie il roster di agenti, genera
  CLAUDE.md, gli agenti attivi, le guide e i file di stato, e verifica il
  risultato. Da usare una volta per progetto: `/framework-install`.
---

# Installazione e adattamento del framework

Sei il coordinatore: leggi un progetto, fai domande, decidi un roster, compili contenuti. Il tooling fa solo il meccanico — assemblaggio, hash, verifiche.

**Non installi nulla** (pacchetti, dipendenze, estensioni) in nessun passo. Se qualcosa sembra mancare, lo segnali e chiedi.

---

## Passo 0 — Trova e valida il sorgente

Il sorgente sta in uno di questi posti, **in quest'ordine**: `./framework/` (copiato nel progetto), `$CLAUDE_FRAMEWORK`, `~/.claude/framework/`. Prendi il **primo che esiste** — non il primo che funziona — e validalo:

```bash
cd <FW>/tools && python -m fwbuild source ..
```

Stampa root, versione e stato del record upstream, oppure cosa manca ed esce 1.

**Se esce 1, fermati qui:** niente cartelle, niente file — un sorgente sbagliato scoperto a metà lascia un progetto peggiore di uno vergine. Chiedi all'utente dov'è il framework e riprova con quel percorso. **Trovato ma incompleto è un errore, non un motivo per provare il successivo.**

Da qui `<FW>` è la root validata e `<PRJ>` la root del progetto: sostituiscili coi percorsi reali, non lasciarli letterali.

## Passo 1 — Rileva il tipo di installazione

```bash
ls -A | head -50
```

- **Progetto vuoto** (o solo configurazione): l'adattamento parte da un'**idea**, che l'utente descrive a parole → Passo 3.
- **Codebase esistente:** l'adattamento parte dal **codice** → Passo 2.
- **Istruzioni già scritte** — `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`, `.claude/skills/`, `docs/TODO.md`, `docs/status.md`, `docs/roadmap.md` — in **entrambi** i casi → Passo 2, blocco *Istruzioni già presenti*. Sono gli unici file che l'installazione può distruggere: qui si guarda se esistono, al Passo 5 si decide cosa farne.

## Passo 2 — Ricognizione a costo basso

### Il codice — solo se ce n'è

**Non leggere il repository tu:** delega a `explorer`. Prompt nella struttura obbligatoria:

```
TASK: mappare questo repository per adattare un framework di lavoro.

DONE QUANDO: hai consegnato, in forma compatta:
  1. linguaggi e stack, con le versioni dove dichiarate
  2. mappa "cartella → responsabilità" dei moduli reali (non generati)
  3. comandi di build, test, avvio — presi dai file di configurazione, non dedotti
  4. punti di ingresso
  5. presenza o assenza di: interfaccia utente, pipeline di dati,
     configurazione di pubblicazione, test, documentazione,
     modelli linguistici, notebook
  6. contratti visibili: API pubbliche, formati persistiti, schemi
  7. cosa sembra rilevante ma è generato o di terze parti
  8. segnali del campo — dipendenze, file, cartelle che dicono di che
     progetto si tratta — ognuno con file:riga, senza classificarli

VINCOLI:
  - sola lettura, nessuna modifica
  - non aprire artefatti pesanti o cartelle di dipendenze
  - se un comando non è dichiarato da nessuna parte, dillo invece di inventarlo

DONE QUANDO: gli 8 punti sopra, in forma compatta, con file:riga dove serve.
```

Repository grande → più `explorer` in parallelo su sottoalberi disgiunti: è l'unico agente a parallelismo libero.

### Istruzioni già presenti — solo se ce ne sono

Questi **leggili tu**: sono pochi file e giudicare cosa il framework copre già non si delega. Leggi quelli elencati al Passo 1 e basta — un `.md` per cartella su un repo grande costa più dell'installazione intera.

Poi mostra all'utente **una tabella sola**:

| direttiva trovata | dove | il framework la copre? |
|---|---|---|
| una modifica per volta, niente refactoring non chiesto | `CLAUDE.md:12` | sì — `method/30-code-principles.md`, *Minimal Safe Change* |
| messaggi di commit in inglese | `CLAUDE.md:40` | no |

**Il «sì» si cita, non si afferma:** la colonna porta il file del framework che copre quella direttiva. Senza, è una dichiarazione a memoria — esattamente ciò che le regole di evidenza vietano, e l'installazione non può essere la prima a violarle. Nel dubbio: «no», e la si integra.

Sulle righe con «no» fai **una domanda sola** — quali tenere — e per quelle scelte:

| la direttiva riguarda… | va in |
|---|---|
| chiunque esegua un task | sezioni di progetto di `CLAUDE.md` |
| delega, ciclo di lavoro, stato | sezioni di progetto di `.claude/shared/orchestration.md` |
| un dominio intero (dati, sicurezza, stile, dominio applicativo) | una guida in `.claude/shared/`, nuova se serve |
| un ruolo solo | il blocco `## Contesto di progetto` di quell'agente |

Si riscrivono nella forma **più compressa che conserva il senso**: sono parole pagate a ogni spawn, e una direttiva importata verbosa costa più di quanto valga. Mai dentro la regione kernel — lì il testo viene dal sorgente e l'assemblaggio del Passo 5 lo riscrive. Una guida nuova va citata da almeno un agente e messa in `CLAUDE.md § Guide condivise`, o nasce orfana (`SHARED_ORPHAN`).

## Passo 3 — Questionario

**Una domanda alla volta**, non un blocco unico: ogni risposta può cambiare le successive. Proponi opzioni concrete e una raccomandazione motivata dal codice o dall'idea.

**Proposta** — una volta per installazione, prima della domanda 1: profilo, agenti e guide extra, hook, ciascuno con la sua evidenza — i segnali del punto 8 di `explorer` con `file:riga`, o la frase dell'idea che lo motiva. Sta **accanto** alle domande, mai al loro posto: si fanno tutte, e ognuna conferma o corregge la sua parte.

### Sempre — cinque domande

**1. Campo del progetto** → profilo in `<FW>/profiles/`:

| profilo | quando |
|---|---|
| `software` | applicazioni, servizi, strumenti a riga di comando, desktop |
| `library` | librerie e pacchetti: il contratto pubblico è il prodotto |
| `web` | siti e applicazioni dove la resa visiva è parte del prodotto |
| `research` | il prodotto è evidenza riproducibile, non software che gira |
| `data` | pipeline di acquisizione, trasformazione, indicizzazione |
| `llm` | un modello linguistico produce testo, decisioni o azioni che il codice usa |
| `marketing` | il prodotto va fatto conoscere: posizionamento, testo, immagini, campagne |

Un progetto software che pubblica anche contenuti resta `software`: agenti e guide del marketing si aggiungono come extra.

Se nessuno calza, chiedi all'utente di descrivere il campo e costruisci il roster a mano dal profilo più vicino.

**2. Superficie critica** — *«qual è la superficie critica di questo lavoro?»* Determina il revisore, e se ne attiva **uno**.

Il profilo ne dichiara già una in `critical_surface`: è quella del **campo**, nota prima del progetto. Leggila all'utente come punto di partenza, non come risposta data, e falla confermare, restringere o sostituire — un progetto può averne una che il suo campo non implica.

| risposta | revisore |
|---|---|
| **Sicurezza** — qualcuno potrebbe abusarne | `security-reviewer` |
| **Validità scientifica** — le conclusioni potrebbero non reggere | `scientific-reviewer` |
| **Qualità dei dati** — potrebbero essere sbagliati a monte | `data-quality-reviewer` |
| **Normativa e licenze** — dati personali, licenze delle dipendenze, obblighi di legge | `compliance-reviewer` |
| **Prestazioni** — solo se il requisito è dichiarato e misurabile | `perf-analyst` |

Due revisori solo se il progetto ha davvero due superfici critiche distinte.

**Se la risposta non è in tabella** — contratto pubblico, accessibilità, costo operativo — **non si inventa un agente**: sarebbe un ruolo pagato da tutti per un caso solo. La superficie si scrive in due posti: la sezione *Superficie critica* di `CLAUDE.md`, e il contesto di progetto di `final-reviewer`, come una riga «qui verificato significa anche». Il punto 4 della sua checklist copre già consumatori esterni e contratti; ciò che senza quella riga non sa è **quale** superficie, qui, viene prima delle altre.

**3. Base di conoscenza assunta** — cosa dare per noto e cosa introdurre alla prima comparsa. Chiedilo così: *«cosa dovrei dare per scontato che sai già, e cosa preferisci che ti spieghi ogni volta?»* La risposta va nel blocco `## Questo progetto` dello stile `Reporting`, non in `CLAUDE.md`: la forma delle risposte la fissa già lo stile, e riguarda solo il coordinatore.

**4. Autonomia** — cosa si può fare senza chiedere. Default conservativo: **nulla di tutto questo**. Commit · pubblicazione · installazione di dipendenze · esecuzioni lunghe o costose · modifiche irreversibili.

Nella stessa domanda, **`gateguard` sì o no**: nega il primo tocco di ogni file in una sessione finché non si presentano i fatti — chi lo importa, cosa cambia di pubblico — ed è un turno in più per file; `FRAMEWORK_GATEGUARD=off` lo spegne. Gli altri hook di `settings.HOOKS` si installano sempre.

**5. Orchestrazione** → un file di `<FW>/orchestrations/`, **uno** per progetto. Proponi `assemble.DEFAULT_ORCHESTRATION`; nomina come utili per il campo quelle di `recommended_orchestrations` del profilo, col punto **Quando** del loro modulo, e le altre come disponibili. `agent-teams` è sperimentale e vuole una sessione interattiva: dillo prima della scelta. Si cambia dopo con `framework-sync` (§ Cambio di orchestrazione).

### Condizionali — solo per ciò che il profilo non installa già

**Chiedi solo di agenti che il roster non ha.** Calcolalo prima (Passo 4) e salta le domande già risolte: una domanda che non può cambiare niente insegna all'utente che il questionario è una formalità.

C'è un'interfaccia? → `frontend` · Entrano dati esterni? → `data-ingestion` ·
Ci sono misure da interpretare? → `results-analyst` · Serve letteratura o
scrittura accademica? → `literature` · Il progetto va pubblicato, e con hosting
semplice o infrastruttura definita come codice? → `deploy` **oppure** `infra`,
mai entrambi · Commenti e docstring da tenere veri? → `comment-analyzer` ·
Serve una guida di `<FW>/shared/` che il profilo non porta? → guida extra ·
Ci sono operazioni pesanti che lancia l'utente e non l'agente? → va nei comandi.

Vincoli normativi e requisiti di prestazione stanno nella **domanda 2**: sono superfici critiche, non contorni del profilo.

## Passo 4 — Roster e installazione selettiva

Si installa **solo l'attivo**. Il master resta in `<FW>/agents/`: un agente non scelto non è cancellato, è *non ancora installato*, e si aggiunge più tardi già aggiornato con `framework-sync --activate`. Motivo: nome e `description` di ogni file in `.claude/agents/` entrano nel contesto del coordinatore a ogni sessione.

**Sei non si tolgono** — `explorer`, `architect`, `implementer`, `tester`, `refactorer`, `final-reviewer`: sono il ciclo del codice, e `drop` li ignora di proposito. Tutti gli altri sono opzionali e si riprendono con `--activate`.

I comandi partono da `<FW>/tools`: lì la root del framework è `..`, quella del progetto è `<PRJ>`.

```bash
cd <FW>/tools && python -c "
from pathlib import Path
from fwbuild import profile
prof = profile.load(Path('../profiles/<PROFILO>.toml'))
r = profile.roster(prof, extras=[], drop=[])
print(r)
print('conflitti:', profile.check_exclusive(r))
print('guide:', profile.guides(Path('..'), prof, r, extras=[]))
"
```

`guides` unisce le guide del profilo, quelle che le schede scelte citano e gli extra delle condizionali; un extra che non esiste è `FileNotFoundError`, non una guida in meno.

## Passo 5 — Generazione

Si generano **due** documenti con regione kernel, non uno. La differenza è il destinatario:

| documento | sorgente del kernel | chi lo legge | costo |
|---|---|---|---|
| `CLAUDE.md` | `<FW>/method/` | **tutti**, a ogni spawn | pagato sempre |
| `.claude/shared/orchestration.md` | `<FW>/coordinator/` | solo chi delega | on-demand |

**Mai in `CLAUDE.md`:** tabella di routing, ciclo di lavoro, regole di delega, livelli di stato. Sono istruzioni che un `tester` o un `explorer` paga a ogni spawn senza poterle usare, e il doctor le rileva (`COORDINATOR_LEAK`).

### Materiale preesistente — si legge prima di scrivere

Vale ovunque, ma qui è dove si perde roba: **nessuno di questi file si sovrascrive prima di averlo letto.**

**Prima del primo file scritto, il piano e l'ok dell'utente:**

```bash
cd <FW>/tools && python -c "
import sys
from pathlib import Path
from fwbuild import lifecycle
sys.stdout.reconfigure(encoding='utf-8')
ops = lifecycle.plan_install(Path('<PRJ>'), lifecycle.targets(Path('..'), <ROSTER>, <GUIDE>, <HOOK>))
print(lifecycle.render(ops))
print(*(f'lascia      {o.path} — {o.reason}' for o in ops if o.action == 'lascia'), sep='\n')
"
```

`<HOOK>` è `settings.HOOKS`, senza `gateguard` se la domanda 4 ha detto no. `sovrascrive` e `fonde` si leggono per nome; `lascia` è materiale del progetto che resterà accanto al framework. `ValueError` su `framework.json` presente: il progetto è già installato → `framework-sync`.

- **`CLAUDE.md` che c'era già:** il suo contenuto è materiale di progetto. Le direttive tenute al Passo 2 vanno nelle sezioni di progetto, il resto (comandi, architettura, stato, vincoli) nella sezione che gli corrisponde. Solo allora si scrive il file nuovo, che ora contiene anche il vecchio. Ciò che non trova posto si chiede, non si butta.
- **`docs/TODO.md`, `status.md`, `roadmap.md` che c'erano già:** si compila il template **col loro contenuto**, invece di copiarci sopra quello vuoto. Un TODO cancellato all'installazione è il primo file che il framework promette di far leggere a ogni sessione.
- **Skill già presenti in `.claude/skills/`:** non si toccano e non si spostano. Elencale in `CLAUDE.md` accanto a quelle di ciclo di vita, una riga a testa: una skill che nessuno sa di avere non viene invocata.
- **`.claude/settings.json` che c'era già:** i permessi che ci sono dentro sono dell'utente, e serializzare `Profile.settings` sopra li cancella. Si fonde con `settings.merge`: le liste si uniscono, su uno scalare diverso resta il suo e la chiave va nei conflitti, che si mostrano prima di scrivere.
- **Hook già presenti in `.claude/hooks/`, o voci `hooks` nei settings:** sono dell'utente. Gli script restano; uno con il nome di un hook del framework compare come `sovrascrive` e si chiede. Le voci si fondono con quelle del framework, mai sostituite.
- **Output style già presenti in `.claude/output-styles/`, o un `outputStyle` già scritto nei settings:** l'utente ha già scelto come vuole essere parlato. Mostraglielo accanto a `Reporting` e chiedi quale vale; il perdente resta sul disco, non si cancella.

### `CLAUDE.md` — sezioni di progetto

```
[REGIONE KERNEL da <FW>/method/]

## Il progetto
descrizione in una riga · mappa "path → ruolo" · vincoli DURI (violarli
invalida il lavoro, non solo il codice) · contratti, con chi li consuma

## Comandi
build, test, avvio · verifica rapida che fa l'agente · operazioni pesanti che
lancia l'utente, con cosa deve riportare

## Superficie critica
qual è la superficie critica — cosa rende il lavoro sbagliato anche a codice
perfetto — e chi la rivede. Parte da `prof.critical_surface` e dalla risposta
alla domanda 2: se coincidono si scrive una riga sola, se divergono valgono
entrambe

## Stato attuale
vuoto alla nascita — è il livello 3 dello stato auto-aggiornante

## Guide condivise
prima riga: `orchestration.md`, solo per il coordinatore e per primo se la
sessione delega. Poi **una riga per guida installata**: cosa contiene — la si
copia dalla riga sotto il titolo della guida, non la si inventa — e quando
aprirla. Un elenco di soli percorsi non è consultabile: per decidere se aprirla
bisogna già sapere cosa c'è dentro
```

**Lo stile delle risposte non sta qui.** È un output style — `.claude/output-styles/` — e Claude Code lo applica **solo alla conversazione principale**: un subagent gira col proprio system prompt. Scriverlo in `CLAUDE.md` lo farebbe pagare a ogni spawn da chi non parla mai con l'utente.

### `.claude/shared/orchestration.md` — sezioni di progetto

```
[REGIONE KERNEL da <FW>/coordinator/]

## Roster di questo progetto
tabella GENERATA dal roster reale, mai copiata: | Situazione | Agente | Modello |
una riga per ogni agente installato, nessuno escluso.
**Le colonne sono un contratto**, non una scelta di stile: il doctor legge il
nome dell'agente fra backtick nella **seconda**. Invertirle produce un roster
tutto orfano e nomi che non esistono

## Note di delega per questo progetto
operazioni che lancia l'utente e non l'agente · vincoli di parallelismo
specifici · quando saltare un passo del ciclo
```

### Assemblaggio

```bash
cd <FW>/tools && python -c "
from pathlib import Path
from fwbuild import assemble
F = Path('..'); V = (F/'VERSION').read_text(encoding='utf-8').strip()
P = Path('<PRJ>')
for d in ('.claude/shared', '.claude/agents', '.claude/skills', '.claude/output-styles', '.claude/hooks', 'docs'):
    P.joinpath(d).mkdir(parents=True, exist_ok=True)
P.joinpath('CLAUDE.md').write_text(
    assemble.build_document(F/'method', V, SEZIONI_PROGETTO), encoding='utf-8')
ORCH = '<ORCHESTRAZIONE>'; CICLI = [<cycles del profilo>]
P.joinpath('.claude/shared/orchestration.md').write_text(
    assemble.build_document(F/'coordinator', V, SEZIONI_ROSTER,
        extra=[assemble.orchestration_file(F, ORCH), *assemble.cycle_files(F, CICLI)]),
    encoding='utf-8')
"
```

**Agenti attivi** — per ciascuno: leggi il sorgente con `assemble.split_source`, **compila il blocco `## Contesto di progetto`** con le direttive specifiche (ogni segnaposto dichiara cosa metterci), riassembla con `assemble.build_agent`, scrivi in `.claude/agents/`.

**Orchestrazione e cicli di dominio** — il modulo della domanda 5, poi i cicli se il profilo dichiara `cycles`, si accodano **in quest'ordine** alla regione kernel della guida del coordinatore: `--down` li ripassa così. Sono orchestrazione, non esecuzione, quindi mai in `CLAUDE.md`.

**Guide** — copia da `<FW>/shared/` l'elenco di `profile.guides` del Passo 4, compilando anche lì il blocco di progetto. Un agente extra porta le sue: senza, la scheda esce con un pointer morto che il doctor vede solo a installazione già scritta (`SHARED_MISSING`).

**Skill di ciclo di vita** — copia `<FW>/skills/framework-doctor`, `framework-sync` e `framework-memory` in `.claude/skills/`. Senza, non sono invocabili e il doctor lo segnala (`SKILLS_MISSING`).

**Stile delle risposte** — copia `<FW>/output-styles/reporting.md` in `.claude/output-styles/` e **compila il blocco `## Questo progetto`** con la risposta alla domanda 3. Non compilato è un `PLACEHOLDER`: il doctor legge ogni `.md` sotto `.claude/` tranne le skill.

**Hook** — copia `<FW>/hooks/<nome>.py` in `.claude/hooks/` per ogni nome di `<HOOK>`. Una voce nei settings senza il suo script, per un hook chiuso, blocca ogni modifica o ogni comando.

**`.claude/settings.json`** — profilo e hook fra loro, poi sopra ciò che c'era (→ *Materiale preesistente*):

```python
fw_settings, _, c = settings.merge(prof.settings, settings.hooks(<HOOK>))   # c non vuoto: difetto del sorgente, fermati
fw_settings, _, c = settings.merge(fw_settings, settings.ORCHESTRATION_SETTINGS.get(ORCH, {}))   # idem
merged, added, conflitti = settings.merge(<settings.json esistente, o {}>, fw_settings)
```

`conflitti` si mostrano prima di scrivere `merged`. Porta `outputStyle`, cioè il nome dello stile appena copiato: senza, il file è installato e nessuno lo seleziona.

**`.claude/framework.json`** — `source`, `version`, `profile`: è come le due skill ritrovano il sorgente, e l'unico posto in cui resta scritto **di cosa** è fatta l'installazione. Senza il profilo, «rigenera i permessi del profilo del progetto» non è eseguibile. `settings_added` è `added`: il solo pezzo di `settings.json` che `framework-sync --uninstall` potrà togliere. La forma **non la scrivi tu**: `source.manifest` rende il percorso relativo quando il sorgente sta dentro il progetto e assoluto solo quando sta fuori — un assoluto su un sorgente interno è la macchina di chi ha installato, e muore al primo clone.

```python
source.manifest(PRJ, FW, version, prof.name, settings_added=added)
```

Il campo `accepted` **non si scrive all'installazione**: nasce vuoto e lo aggiunge chi decide di convivere con un avviso (→ skill `framework-doctor`).

**File di stato** — copia i tre template in `docs/` e compila **subito** ogni blocco `[DA COMPILARE — …]`: prima voce e primo passo in `TODO.md` con la data di oggi, primo obiettivo col suo criterio in `roadmap.md`. `status.md` nasce vuoto per costruzione — ci si scrive quando qualcosa si chiude. Le sezioni che possono restare vuote (in attesa, bloccati, decisioni aperte) non hanno segnaposto: portano già il testo giusto e si sostituisce quando ci sarà qualcosa. Va fatto qui: al Passo 6 un segnaposto residuo è un `PLACEHOLDER`, e `TODO.md` è il file che ogni sessione futura legge per primo.

**Niente `@import`:** il kernel si concatena fisicamente.

## Passo 6 — Verifica

```bash
cd <FW>/tools && python -m fwbuild doctor --strict <PRJ>
```

Deve stampare `OK — nessun rilievo` e uscire con 0. `--strict` rende meccanica la regola: **finché resta un rilievo, di qualunque gravità, l'installazione non è completa.** Cosa significa ogni codice: skill `framework-doctor`.
