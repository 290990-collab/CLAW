---
name: claw-fair
description: >
  Tara modello ed effort dei subagent di un progetto con il framework installato
  sull'ambito reale del progetto — profilo (web, software, ricerca, dati, llm,
  marketing, libreria) e idea descritta — invece dei valori uguali per tutti
  del sorgente: alza dove un errore costa, abbassa dove si paga un modello che
  il lavoro non chiede. Tetto assoluto opus/xhigh. Tocca solo le righe `model:`
  ed `effort:` delle schede e la colonna Modello del roster; se l'ambito non è
  descritto né deducibile si ferma senza modificare nulla. Da usare quando
  l'utente vuole regolare, tarare o rivedere modelli ed effort degli agenti,
  ridurre il costo dei subagent, o chiede se gli agenti hanno il modello giusto
  per questo progetto: `/claw-fair`.
---

# Claw-fair — il modello che il lavoro chiede, in questo progetto

Il sorgente assegna a ogni agente modello ed effort pensati per un progetto qualunque. Un `security-reviewer` su Opus ha senso per un servizio con autenticazione, non per un sito statico; un `copywriter` su Sonnet va bene per un changelog, meno per la pagina che presenta una persona. Qui si tara ogni scheda sull'ambito di **questo** progetto.

**Cosa diventa il valore scritto.** Il valore della scheda è il default del coordinatore e il suo tetto: la regola di delega «agente e modello al task» lo può solo abbassare allo spawn, mai alzare. Claw-fair sposta quel tetto, in su o in giù, entro il tetto assoluto.

**La invoca il coordinatore, su richiesta dell'utente.** Non scrive nulla senza il suo ok sul piano.

## Vincoli — non si negoziano

- **Si modificano solo:** la riga `model:` e la riga `effort:` nel frontmatter di `.claude/agents/<agente>.md`, e la cella *Modello* della riga di quell'agente nella tabella del roster. Nessun'altra riga di nessun file: né il metodo, né il `## Contesto di progetto`, né `framework.json`, né `CLAUDE.md` fuori dalla tabella. Un problema notato altrove va nel report, non nel diff.
- **Tetto assoluto: `opus` / `xhigh`.** Mai `max`, nemmeno se l'idea sembra chiederlo: il costo di `max` non è mai stato misurato su questi ruoli.
- **Modelli ammessi:** `haiku` < `sonnet` < `opus`. **Mai `fable`**: non è disponibile, l'agente non parte e il doctor lo tratta come ERROR.
- **Effort ammessi:** `low` < `medium` < `high` < `xhigh`. `xhigh` **solo con `opus`**: è l'unica combinazione con `xhigh` che il sorgente usa; le altre non sono verificate.
- **Agenti senza scheda nel sorgente** (creati nel progetto): non si toccano, si elencano nel report.

## Passo 0 — È un progetto del framework?

`<PRJ>` è la root del progetto. Serve `<PRJ>/.claude/framework.json`: se manca, il framework non è installato → dillo e fermati.

`<FW>` è il suo campo `source`, che può essere relativo alla root del progetto: scioglilo con `source.dereference(<PRJ>, source)` da `<FW>/tools`, come fanno le altre skill del ciclo di vita. `<FW>/agents/` non esiste → fermati: senza il valore sorgente non c'è da dove partire.

Il roster è l'elenco dei file in `<PRJ>/.claude/agents/`. La tabella del roster sta in `<PRJ>/.claude/shared/orchestration.md` (sezione `## Roster di questo progetto`, colonne `| Situazione | Agente | Modello |`), o in `CLAUDE.md` se quella guida non c'è.

## Passo 1 — Leggi l'ambito, o fermati

Fonti, in quest'ordine:

1. `profile` in `.claude/framework.json` — il dominio.
2. `CLAUDE.md`, sezioni `## Il progetto` e `## Superficie critica` — l'idea e dove un errore costa di più.
3. `README.md`, `docs/` (roadmap, TODO) e, se c'è, il codice: cosa fa il prodotto, chi lo usa, cosa espone in rete.

**Condizione di stop.** Il profilo da solo non basta: c'è sempre, e dice «web», non «portfolio statico» né «e-commerce con pagamenti». Se `## Il progetto` è vuota o contiene ancora `DA COMPILARE`, **e** né README, né `docs/`, né il codice dicono cosa sia il prodotto → **fermati senza modificare nulla**. Scrivi all'utente cosa manca e dove va scritto: `## Il progetto` in `CLAUDE.md`, o la risposta al questionario di `claw-install`. Tarare sul solo profilo darebbe valori diversi dal sorgente senza una ragione che li regga.

Dall'ambito ricava, in una riga ciascuno:
- **cosa si produce** (sito, servizio, pipeline, evidenza, testo);
- **la superficie critica**, come la dichiara il progetto;
- **cosa il progetto non ha**: niente backend, niente dati personali, niente test automatici, niente pubblico esterno. Spesso è questo a giustificare un ribasso.

## Passo 2 — Valori di partenza

Per ogni agente installato, una riga:

| agente | sorgente | attuale |
|---|---|---|
| `frontend` | opus / high | opus / high |

- **sorgente**: `model:` ed `effort:` di `<FW>/agents/<agente>.md`.
- **attuale**: le stesse righe nella scheda del progetto.

**Si ragiona sempre dal sorgente, mai dall'attuale.** Una seconda esecuzione deve dare lo stesso risultato della prima, non spostare ancora i valori a ogni giro. Se attuale ≠ sorgente, la differenza viene da un claw-fair precedente o da una mano: si segnala nel piano, non si somma.

## Passo 3 — Taratura

Ogni agente parte dal valore sorgente e si sposta solo se **l'ambito dà una ragione concreta**, scritta in una riga che nomina un fatto del Passo 1. «Per sicurezza» o «per risparmiare» non sono ragioni: lo sono «il sito non ha backend né form» o «la bio è il primo testo che legge un selezionatore». Senza una ragione così il valore resta quello del sorgente: è il risultato atteso per la maggior parte degli agenti.

### Quattro domande per agente

1. **Quanto è vicino alla superficie critica?** Un agente che produce o giudica ciò che il progetto ha dichiarato critico si tiene alto, o si alza. Uno che lavora su una parte che nel progetto non esiste, o quasi, si abbassa.
2. **Che tipo di lavoro fa?** «Trova ed elenca» regge su `haiku`. «Classifica, giudica, confronta» no: chiede almeno `sonnet`. «Decide una struttura», «trova una causa ignota», «è l'ultimo controllo prima di dire fatto»: `opus`.
3. **Quanto costa un suo errore, e chi lo intercetta?** Un errore che un revisore a valle ferma costa un giro in più; uno che arriva all'utente o in rete costa di più. Si abbassa dove c'è rete di sicurezza, non dove si è l'ultima.
4. **Quanto spesso lavora?** Un agente usato di continuo su compiti di routine pesa sul costo, e abbassarlo rende. Uno chiamato di rado per casi critici costa poco anche su `opus`: abbassarlo risparmia poco e rischia molto.

**Modello ed effort sono due leve diverse.** Il modello decide *se* un compito è alla portata. L'effort decide *quanto a fondo* ragiona su un compito che è alla portata: serve a chi segue catene causali lunghe (diagnosi, piano, revisione), molto meno a chi esegue lavoro ripetitivo. Se un agente sbaglia per mancanza di capacità, si alza il modello, non l'effort.

### Invarianti

- **Un revisore non è più debole di ciò che rivede.** Se `frontend` è `opus`, `final-reviewer` non scende a `sonnet`. Se `implementer` sale a `opus`, lo stesso vale per il revisore del suo lavoro.
- **`explorer` resta `haiku`.** Il suo lavoro è il caso d'uso del modello leggero; alzarlo moltiplica il costo della ricognizione.
- **Non si abbassa sotto il lavoro dichiarato.** Se la scheda di un agente gli dà decisioni o giudizi, `haiku` non basta, qualunque sia il profilo.

### Dove guardare per profilo

Un punto di partenza per la domanda 1, non una tabella da applicare: vince sempre l'idea descritta. Vale solo per gli agenti installati: un profilo non li porta tutti.

| profilo | di solito al centro | di solito ai margini |
|---|---|---|
| `web` | `frontend`, `final-reviewer` | `security-reviewer` se il sito è statico, `silent-failure-hunter` senza I/O |
| `software` | `architect`, `debugger`, `security-reviewer` | `copywriter`, `visual-designer` |
| `library` | `architect` (il contratto pubblico è il prodotto), `tester` | `deploy`, `frontend` |
| `data` | `data-ingestion`, `data-quality-reviewer` | `frontend`, `copywriter` |
| `research` | `scientific-reviewer`, `results-analyst` | `deploy`, `frontend` |
| `llm` | `results-analyst`, `scientific-reviewer` | `visual-designer` |
| `marketing` | `copywriter`, `claim-reviewer`, `market-researcher` | `debugger`, `refactorer` |

### Esempio

Portfolio statico, ambizione di premi di design, niente backend, pubblicato su hosting statico:

| agente | sorgente | proposto | perché |
|---|---|---|---|
| `security-reviewer` | opus / high | sonnet / high | nessun backend né form: la superficie è intestazioni e dipendenze |
| `copywriter` | sonnet / high | opus / high | bio e descrizioni dei lavori sono poche righe con tutto il peso della prima impressione |
| `architect` | opus / xhigh | opus / high | le decisioni di struttura di un sito statico sono poche e poco profonde |
| `frontend` | opus / high | opus / high | — (al centro: resta) |

## Passo 4 — Piano, poi ok

Mostra all'utente **una tabella sola**, con tutti gli agenti installati, anche quelli che non cambiano:

| agente | sorgente | attuale | proposto | perché |
|---|---|---|---|---|

Sotto la tabella, tre righe:
- quanti agenti cambiano, e quanti salgono e quanti scendono;
- gli agenti non toccati perché non esistono nel sorgente;
- **cosa succede dopo:** a ogni `claw-sync`, ogni scheda diversa dal sorgente viene nominata e sync chiede se riportarla al valore del sorgente. Per tenere la taratura, si risponde no.

Chiedi con lo strumento a scelta multipla: applica tutto / applica solo alcuni (quali) / annulla. **Nessuna scrittura senza risposta.** Annulla → fermati: non è un fallimento.

Una selezione parziale può rompere un invariante — alzare `frontend` senza `final-reviewer`. In quel caso dillo prima di scrivere, con la coppia coinvolta, e richiedi.

Tutti i valori proposti coincidono con gli attuali → dillo e fermati, senza chiedere nulla.

## Passo 5 — Applica

Per ogni agente approvato il cui valore cambia:

1. Nella scheda, sostituisci **la riga intera** `model: <vecchio>` con `model: <nuovo>`, e lo stesso per `effort:`. Formato invariato — chiave, due punti, uno spazio, valore — perché sync le legge con `^(model|effort):[ \t]*(\S+)[ \t]*$`. Se `effort:` manca, aggiungila subito dopo `model:`.
2. Nella tabella del roster, sostituisci il valore **nella terza colonna** della riga che ha l'agente fra backtick nella seconda. La seconda colonna è un contratto (il doctor ci legge il nome dell'agente): non si tocca.

Prima di scrivere, leggi il file: se la riga attesa non c'è, o è diversa da quella del piano, fermati su quel file e riportalo. Non indovinare dove metterla.

## Passo 6 — Verifica, poi report

**Verifica che il diff sia solo quello promesso.** Prima delle modifiche copia ogni file che toccherai in una cartella temporanea fuori dal progetto; dopo, confronta riga per riga (`difflib` della stdlib basta). Ogni riga cambiata deve essere una riga `model:`/`effort:` di una scheda, o una riga del roster in cui è cambiata solo la terza cella. Qualunque altra differenza → ripristina il file dal testo conservato e riportalo come errore.

Poi `doctor`, come in chiusura di `claw-sync`: da `<FW>/tools`, `python -m fwbuild doctor <PRJ>`, lanciato anche prima di scrivere: conta solo un rilievo che prima non c'era. Si riporta, non si corregge fuori dalle righe permesse.

Poi il report all'utente, breve:
- la tabella finale `agente | prima | dopo`;
- i file toccati;
- il risultato della verifica del diff;
- cosa resta non misurato: nessuno ha verificato che la qualità tenga dove si è abbassato. Il primo segnale sono i giri a vuoto — un agente che torna con decisioni sbagliate o incomplete. In quel caso si rialza quella scheda, non tutte.
