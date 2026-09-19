---
name: claw-doctor
description: >
  Verifica l'integrità di un'installazione del framework: segnaposto non
  compilati, roster incoerente con la tabella di routing, guide mancanti, drift
  della regione kernel, file di stato assenti. Da usare quando qualcosa non torna,
  dopo modifiche a mano al framework, o prima di aggiornarlo.
---

# Diagnosi di un'installazione

```bash
cd <FW>/tools && python -m fwbuild doctor --strict <PRJ>
```

`<PRJ>` è la root del progetto. `<FW>` è il campo `source` di `.claude/framework.json` (se il file manca, `./framework/`): può essere **relativo alla root del progetto**, e `source.dereference(<PRJ>, source)` lo scioglie.

I sottocomandi di `fwbuild` sono **cinque** — `doctor`, `source`, `cost`, `report`, `skills`. Le modalità `--down`, `--up`, `--upgrade`, `--repair`, `--uninstall`, `--activate`, `--deactivate` appartengono a `claw-sync`, non sono flag da shell.

- Installazione completa → `OK — nessun rilievo`.
- **Usa sempre `--strict`**, in CI e a mano: senza, l'uscita è 0 anche con avvisi.
- `--json` aggiunge la misura di `CLAUDE.md` ed è **un formato, non una postura**: l'exit code non cambia.
- Le **note** non fanno cadere `--strict`: sono avvisi che il progetto dichiara di accettare, e restano stampati (→ *Deroghe dichiarate*).

## Come si legge ogni rilievo

### `PLACEHOLDER` — ERRORE

Un blocco `[DA COMPILARE — …]` non compilato: l'agente che lo legge riceve istruzioni al posto di direttive. È l'**unico** marker di segnaposto — non `{{…}}`, che è la sintassi di template di mezzo mondo (Vue, Angular, Jinja, Handlebars): un progetto che la citasse fra i propri vincoli si prenderebbe un errore da cui non può uscire.

**Cosa fare:** compila il segnaposto con le direttive reali del progetto. Se l'informazione non c'è, chiedila all'utente — non inventarla.

### `ROSTER_MISSING` — ERRORE

Un agente è nella tabella di routing di `.claude/shared/orchestration.md` (o di `CLAUDE.md`, se quella guida non c'è) ma il file non esiste in `.claude/agents/`: il coordinatore delegherà a qualcosa che non c'è.

**Cosa fare:** installa l'agente (`claw-sync --activate <nome>`, che prende la versione corrente dal master) o togli la riga dalla tabella.

### `ROSTER_ORPHAN` — AVVISO

Il file dell'agente esiste ma non è in tabella: costa contesto a ogni sessione e non verrà mai scelto.

**Cosa fare:** aggiungilo alla tabella o disattivalo (`claw-sync --deactivate <nome>`). Nessuna eccezione: o l'agente è di troppo, o la tabella è incompleta.

### `SHARED_MISSING` — ERRORE

Un file installato — `CLAUDE.md`, un agente, una guida — punta a una guida non installata. Un pointer rotto è peggio di un pointer assente: l'agente ci prova e non trova nulla. Il rilievo dice **da quale file** parte.

Caso particolare: **`orchestration.md` assente** con agenti installati. Senza, chi delega non ha né le regole di delega né la tabella di routing, e il doctor non può verificare il roster.

**Cosa fare:** copia la guida da `<FW>/shared/` e compilane il blocco di progetto, oppure togli il pointer. Per `orchestration.md`, rigenerala assemblando `<FW>/coordinator/` e aggiungendo la tabella di routing del progetto.

### `SHARED_ORPHAN` — AVVISO

Guida installata in `.claude/shared/` che nessun file cita: contesto portato dietro e mai aperto, l'inverso esatto di `SHARED_MISSING`.

**Cosa fare:** citala da dove serve — le guide generiche in `CLAUDE.md § Guide condivise`, quelle di ruolo dall'agente che le usa — oppure toglila.

### `COORDINATOR_LEAK` — AVVISO

`CLAUDE.md` contiene una sezione della guida del coordinatore: regole di delega, ciclo di lavoro, template del prompt, livelli di stato, disambiguazione fra agenti.

**Perché conta:** `CLAUDE.md` è caricato in **ogni** contesto, quello di ogni subagent incluso. Un `explorer` su Haiku paga il ciclo del codice e i quattro livelli di stato senza poterne usare nulla — è sperpero sul file più caro del sistema.

**Cosa fare:** sposta la sezione in `.claude/shared/orchestration.md`, lasciando al massimo un pointer di una riga. Se il contenuto serve davvero a chi esegue, riscrivilo come obbligo di esecuzione in `<FW>/method/`: è un'altra cosa.

⚠️ Il check confronta i **titoli**, non il senso: la stessa sezione sotto un altro titolo non lo fa scattare. Il rilievo copre solo i sei titoli noti; sulla fuga di contenuto vale la lettura.

### `KERNEL_MISSING` — ERRORE

I marker della regione kernel sono spariti da un file che ne ha una per costruzione — `CLAUDE.md`, `orchestration.md`, un agente. **Più grave di un drift:** senza marker sparisce il controllo, e il metodo riscritto a mano diventa indistinguibile da quello generato. Non scatta se **nessun** file tracciato ha marker: quella è l'installazione senza tracking, ed è una scelta.

**Cosa fare:** riassembla con `claw-sync --down`, dopo aver confrontato il contenuto attuale col sorgente — dentro potrebbe esserci una modifica da promuovere.

### `KERNEL_DRIFT` — AVVISO, e non è un errore

La regione kernel è stata modificata a mano. **È informazione, non un guasto:** il framework non vieta di modificare il metodo, lo rende visibile.

**Chiedi all'utente, una sola domanda:**

> «Hai modificato il metodo in `<file>`. È un miglioramento che vale per tutti i progetti — quindi lo promuovo nel sorgente — o è una deroga specifica di questo progetto?»

- **Miglioramento** → `claw-sync --up`: risale nel sorgente, incrementa la versione, il prossimo progetto nasce con dentro.
- **Deroga locale** → si annota nel progetto, perché il prossimo che legge il rilievo sappia che è voluta.

Non «correggere» mai un drift riscrivendoci sopra prima di aver posto quella domanda: butteresti via una modifica che qualcuno aveva ragione di fare.

### `VERSION_MISMATCH` — AVVISO

Le regioni kernel non dichiarano tutte la stessa versione, oppure il progetto è a una versione diversa dal sorgente. **Nessun altro rilievo lo vede:** su un metodo vecchio l'hash torna, perché torna su quello vecchio. È la biforcazione fra progetti, il difetto che il framework esiste per evitare.

**Cosa fare:** `claw-sync --down` su **entrambi** i documenti versionati e su ogni agente installato. Uno scarto fra un singolo agente e il resto è normale subito dopo un `--activate`, che prende il master corrente: si chiude con lo stesso `--down`.

### `SETTINGS_MISSING` — AVVISO

Manca `.claude/settings.json` con agenti installati. È il file che porta i permessi del profilo — fra cui il divieto di leggere `.env`, chiavi e certificati: senza, quel divieto non è in vigore e nessuno se ne accorge.

⚠️ **Quel divieto copre lo strumento `Read`, non la shell.** Un agente con `Bash` legge un `.env` con `cat` e nessuna configurazione lo impedisce. Dove il segreto conta, l'unica guardia meccanica è non dare la shell a quell'agente: è il motivo per cui i revisori che non eseguono niente hanno solo `Read, Grep, Glob`.

**Cosa fare:** rigeneralo serializzando `Profile.settings` del profilo del progetto — il nome sta in `profile` dentro `.claude/framework.json` — come al Passo 5 dell'installazione.

### `SKILLS_MISSING` — AVVISO

`claw-doctor`, `claw-sync`, `claw-memory` o `claw-fair` non sono in `.claude/skills/`: esistono nel sorgente ma non sono invocabili qui. Nessuno se ne accorge finché non servono, cioè quando qualcosa è già andato storto.

**Cosa fare:** copiale da `<FW>/skills/`. Non si adattano: sono file di framework, si copiano alla lettera.

### `STATE_MISSING` — ERRORE

Manca uno fra `docs/TODO.md`, `docs/status.md`, `docs/roadmap.md`.

**Cosa fare:** copia il template mancante da `<FW>/templates/`. Senza il livello 1, ogni sessione riparte a indovinare.

### `MANIFEST_MISSING` — ERRORE se il file manca, AVVISO se è incompleto

`.claude/framework.json` assente, illeggibile, o senza uno fra `source`, `version`, `profile`. È il file che collega un'installazione al suo sorgente: senza, `claw-sync` non sa da dove aggiornare e `fwbuild report` non conta nemmeno il progetto — sparisce dal rapporto di flotta invece di comparirci come rotto.

**Cosa fare:** riscrivilo con `source.manifest(<PRJ>, <FW>, versione, profilo)`. Il profilo è quello scelto al Passo 3; se nessuno lo ricorda si deduce dagli agenti installati e dalle guide, e si scrive **prima** di averne di nuovo bisogno.

### `ACCEPTED_UNUSED` — AVVISO

Una deroga dichiarata in `framework.json` non copre nessun rilievo: o il rilievo è sparito, o è un ERROR (che non si accetta), o è scritta senza ragione. Una deroga che non si applica resta lì e la volta dopo zittisce qualcos'altro.

**Cosa fare:** toglila se il rilievo è sparito, scrivi la ragione se manca, risolvi l'errore se è un errore.

### `FABLE` — ERRORE

È stato generato `model: fable`. Quel modello non è disponibile: l'agente non parte.

**Cosa fare:** sostituire con `model: opus`. Per `architect`, `effort: xhigh`.

### `EXCLUSIVE` — ERRORE

`deploy` e `infra` installati insieme. Coprono lo stesso spazio con posture opposte — pubblicazione semplice contro infrastruttura come codice — e la sovrapposizione produce routing ambiguo.

**Cosa fare:** scegli quale descrive davvero il progetto e disattiva l'altro.

### `TOKEN_BUDGET` — AVVISO

Le sezioni di progetto di `CLAUDE.md` hanno superato in parole la regione kernel. Il tetto che rompe la build sta sul **sorgente** e vincola solo il metodo; la `CLAUDE.md` assemblata è ciò che ogni subagent paga a **ogni spawn**, e la parte scritta dall'installazione non aveva nessuna soglia — ed è la sola che cresce, perché cresce col progetto.

La soglia è il kernel stesso, l'unica grandezza nota: *il progetto non scrive più del metodo*. È una scelta a giudizio, non una misura di efficacia. Sotto il tetto che il framework si dà per il solo metodo il rilievo tace: su un file piccolo il rapporto è vero e irrilevante.

**Cosa fare:** non tagliare a caso. Sposta in `.claude/shared/` ciò che serve a pochi agenti, lasciandone il pointer; togli ciò che il repository già dice da sé (struttura ricavabile, comandi già in `Makefile` o `package.json`); tieni in `CLAUDE.md` solo ciò che un agente non può dedurre — vincoli duri, contratti con chi li consuma, superficie critica. Se dopo il taglio il file resta sopra soglia perché il progetto è grande, è un avviso da accettare consapevolmente.

Per tradurlo in una cifra: `python -m fwbuild cost <PRJ> --spawns N --devs N`.

### `REPORT_FORMAT` — AVVISO

Lo schema del report installato porta ancora la confidenza come percentuale: formato precedente, precisione finta nel campo che il coordinatore legge per primo, mentre la confidenza auto-riportata da un modello è mal calibrata. Nessun altro rilievo lo vede: l'hash torna su quel testo lì, e la versione dichiarata è quella con cui il progetto è nato.

**Cosa fare:** `claw-sync --down`. Il formato attuale è categorico e porta con sé il falsificatore (`SMENTIRE`), che è ciò che rende leggibile un giudizio senza numeri.

### `UNSAFE_UNICODE` — AVVISO

Un file installato contiene un carattere invisibile: controllo bidirezionale (U+202A–202E, U+2066–2069), spazio o operatore a larghezza zero (U+200B–200D, U+2060–2064), carattere tag (U+E0000–E007F), riempitivo (U+115F, U+1160, U+180E, U+3164), U+FEFF oltre l'inizio del file. Il modello lo legge, chi rivede il file no: è la via con cui un'istruzione nascosta entra in un agente o in una skill. Si guardano i file del progetto, le skill, gli hook e `settings.json`. Non contano i selettori di variante (U+FE00–FE0F, U+E0100–E01EF), che compongono le emoji, né il BOM a inizio file, che scrivono gli editor.

AVVISO e non errore: lo ZWJ (U+200D) compone anche emoji e scritture legittime.

**Cosa fare:** apri il file alla riga indicata con un editor che mostri i caratteri invisibili. In una skill o in un hook, confronta col sorgente in `<FW>/`: una differenza che nessuno sa spiegare si tratta come manomissione. Se il carattere è voluto, accettalo con `UNSAFE_UNICODE:<file>` e la ragione.

### `PERSONAL_PATH` — AVVISO

Un file installato contiene un percorso dentro la cartella di un utente — `C:\Users\<nome>`, `/Users/<nome>`, `/home/<nome>`, anche con le barre raddoppiate del JSON. Il file viaggia col repository: su un'altra macchina il percorso non esiste, e porta con sé il nome di chi l'ha scritto. I nomi segnaposto dei template (`user`, `username`, `yourname`, `you`, `me`, `example`) non contano. Il messaggio dà file e riga, non il percorso.

**`.claude/framework.json` non si guarda:** il suo `source` è assoluto per costruzione quando il sorgente sta fuori dal progetto, perché lì un relativo non regge — la profondità del clone non è nota. Segnalarlo darebbe un avviso su ogni installazione fatta così.

⚠️ Il check confronta testo: un URL con `/home/` o `/Users/` nel percorso lo fa scattare.

**Cosa fare:** sostituisci con un percorso relativo alla root del progetto o con un segnaposto (`<PRJ>`, `<FW>`). Se il percorso assoluto serve davvero, accettalo con `PERSONAL_PATH:<file>` e la ragione.

## Deroghe dichiarate

Un avviso può essere sbagliato **per questo progetto**: un `KERNEL_DRIFT` voluto, una `CLAUDE.md` grande perché il progetto è grande. Senza una valvola `--strict` resta rosso per sempre e la squadra impara a ignorarlo — il modo in cui un controllo muore.

In `.claude/framework.json`:

```json
"accepted": {
  "KERNEL_DRIFT:CLAUDE.md": "deroga voluta: il vincolo X vale solo qui",
  "TOKEN_BUDGET": "monorepo, i contratti stanno in CLAUDE.md apposta"
}
```

La chiave è il codice, o `codice:frammento` per limitarla a un file. Il valore è la **ragione, obbligatoria**: senza, la deroga non si applica e diventa `ACCEPTED_UNUSED`. Il rilievo accettato resta stampato come `NOTE` — visibile, non bloccante.

**Gli ERROR non si accettano.** Un avviso è un giudizio, e su un giudizio un progetto può avere ragione contro il default; un errore è un'installazione che non funziona, e un segnaposto non compilato resta non compilato anche se qualcuno scrive che gli va bene.

Prima di aggiungere una riga qui, la domanda è quella del drift: *deroga di questo progetto, o default sbagliato per tutti?* Nel secondo caso la strada è `claw-sync --up`, non `accepted`.

## Più progetti insieme

```bash
cd <FW>/tools && python -m fwbuild report <cartella-di-repository>
```

`doctor` risponde «questa installazione regge?». `report` risponde a **quante versioni del metodo sono in giro, e dove**: cerca `.claude/framework.json` sotto i percorsi dati (due livelli, `--depth` per cambiarli), chiama il doctor su ognuno e mette in fila versione, rilievi e dimensione della `CLAUDE.md`.

Il riferimento è la versione del **sorgente** da cui giri, non la più diffusa: la maggioranza non è un riferimento. `--strict` esce 1 se un progetto diverge o ha rilievi; `--json` dà lo stesso rapporto per la CI.

## Dopo la diagnosi

Riporta all'utente: quanti rilievi per gravità, cosa hai corretto, cosa richiede una sua decisione. I `KERNEL_DRIFT` si elencano sempre, anche a resto pulito: sono la parte utile del rapporto. Le note pure — deroghe già decise — in una riga sola.
