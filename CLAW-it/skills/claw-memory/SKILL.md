---
name: claw-memory
description: >
  Mostra cosa c'è nella memoria persistente del progetto e cosa non regge più:
  elenca i fatti, li appaia con lo stato del repository e con le regole del
  framework, e propone cosa correggere, marcare come superato o cancellare. Da
  usare a inizio di una sessione lunga, dopo un cambio di struttura, o quando
  una memoria sembra vecchia: `/claw-memory`.
---

# Memoria persistente — cosa dice, e cosa la smentisce

Il livello 4 dello stato è l'unico che vive **fuori dal repository**: nessun rilievo del doctor lo vede, e in conflitto vince il repo.

**La invoca il coordinatore.** Chi esegue un task la memoria non la legge: riceve nel prompt di delega ciò che gli serve, come per tutto il resto.

## Passo 0 — Trova la memoria

Non assumere il percorso: **guardalo**. Prima cartella che esiste, in quest'ordine:

1. quella dell'harness per questo progetto — in Claude Code `~/.claude/projects/<progetto>/memory/`, col percorso del progetto trasformato in nome di cartella; se non c'è, non inventarla
2. `<PRJ>/.claude/memory/`

Nessuna delle due esiste → dillo e fermati. Un progetto senza memoria è giovane, non guasto, e la cartella non si crea qui: la memoria nasce quando c'è un fatto da scriverci.

Se c'è un indice (`MEMORY.md`) e non corrisponde ai file, quello è già il primo conflitto da riportare.

## Passo 1 — Elenca

Una riga per memoria, **mai** il contenuto integrale: l'elenco serve a decidere cosa aprire.

| memoria | tipo | dice |
|---|---|---|
| `due-edizioni.md` | struttura | le due edizioni differiscono solo per lingua |

## Passo 2 — Riscontro meccanico

Questo per primo: costa poco e non sbaglia. Da ogni memoria estrai i riferimenti **concreti** — percorsi, nomi di file e di funzioni, comandi, numeri, versioni — e verificali uno per uno: il file esiste ancora? il comando è dichiarato dove la memoria dice? il numero coincide con la fonte nel repo?

Ogni riscontro fallito è un conflitto **dimostrato**.

## Passo 3 — Riscontro di giudizio

Poi le contraddizioni con `CLAUDE.md`, `docs/status.md` e le regole del kernel: una decisione chiusa che rovescia una memoria, una preferenza superata da una direttiva nuova.

**Un conflitto di giudizio si dichiara solo se sai citare la riga che lo smentisce.** Senza quella riga non è un conflitto, è un'impressione — e va taciuta.

## Passo 4 — Il rapporto

Una tabella, appaiata:

| memoria | dice | il repo dice | proposta |
|---|---|---|---|
| `conteggio-test.md` | «160 test per edizione» | `README.md:19` — 161 | correggere il numero |
| `percorso-script.md` | «lo script sta in `bin/run.sh`» | non esiste; `tools/run.sh` sì | correggere il percorso |

**Una riga senza la colonna «il repo dice» non si scrive.** Un conflitto senza le due fonti a fianco è un allarme inventato, e la memoria è esattamente il posto dove un allarme inventato sopravvive alle sessioni.

Proposte ammesse: **correggere** · **marcare superata**, con la data e cosa l'ha superata · **cancellare** · **lasciare**, per un fatto ancora vero che *sembra* vecchio.

Cancellare è la proposta giusta in un caso preciso: la memoria registra un errore e **la causa non esiste più**. Lì il problema non esiste, quindi non deve esistere nemmeno la memoria.

## Passo 5 — Applica, una riga alla volta

Niente si scrive e niente si cancella senza l'ok dell'utente, riga per riga: quella memoria è sua e sopravvive a questa sessione. Applicata una modifica, aggiorna anche l'indice.

Se una memoria è caduta per una **decisione**, la decisione va in `docs/status.md`: la memoria dice cosa vale adesso, `status.md` perché è cambiato.

## Quando invocarla

- a inizio di una sessione lunga, prima di fidarsi di ciò che si «ricorda»;
- dopo un cambio di percorsi, contratti o moduli: il livello 4 lo chiede già, questa skill è il come;
- quando **una** memoria sembra vecchia — e allora si guarda quella, non tutte.

Non a ogni task: rileggere tutta la memoria a ogni giro è un costo pagato per un cambiamento che non c'è stato.
