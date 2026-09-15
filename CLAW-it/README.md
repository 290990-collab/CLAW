# CLAW — sorgente

Cartella **autosufficiente**: un master unico sulla macchina, oppure copiata nel
progetto. Tutto ciò che serve è qui dentro, tooling incluso.

```
VERSION              versione del kernel (semantica: patch · minor · major)
method/              kernel COMUNE → CLAUDE.md, letto da tutti a ogni spawn
coordinator/         kernel del COORDINATORE → shared/orchestration.md, on-demand
orchestrations/      modelli di orchestrazione: se ne accoda uno alla guida, orchestrator-worker il default
cycles/              cicli di dominio, accodati alla guida se il profilo li chiede
agents/              29 agenti: metodo + blocco [DA COMPILARE] di progetto
shared/core/         guide generiche, caricate on-demand
shared/domain/       guide di dominio (design, ricerca, dati, llm)
profiles/            7 profili: dominio → roster, guide, cicli, permessi
templates/           i file di stato, generati vuoti ma strutturati
hooks/               config_protection · block_no_verify (chiusi) · gateguard (aperto) → .claude/hooks/
skills/              framework-install · framework-doctor · framework-sync · framework-memory · framework-comply
                     più i pacchetti collegati con `fwbuild skills add` e pool.toml: locali, mai pubblicati
tools/fwbuild/       assemblaggio, hash, verifiche — Python stdlib puro
tools/trial_install.py  la prova: installa un progetto finto, che il doctor verifica
tools/tests/         218 test
```

## La separazione che conta: per destinatario, non per argomento

`CLAUDE.md` è caricato in **ogni** contesto, compreso quello di ogni subagent.
Metterci le regole di delega significa farle pagare a un `explorer` che non
delega, a ogni singolo spawn.

Quindi il metodo è diviso in due, per chi lo legge:

| sorgente | artefatto | destinatario | costo |
|---|---|---|---|
| `method/` | `CLAUDE.md` | tutti | pagato a **ogni spawn** |
| `coordinator/` | `.claude/shared/orchestration.md` | solo chi delega | on-demand |

In `method/` stanno gli **obblighi di chi esegue**, l'evidenza, il report
standard, i principi di modifica. In `coordinator/` le dieci regole della delega,
il ciclo di lavoro, come si scrive un prompt, i quattro livelli di stato.

Le dieci regole restano **complete e numerate in un posto solo**: gli obblighi di
esecuzione sono una lista distinta, non un loro sottoinsieme rinumerato. Il
doctor segnala con `COORDINATOR_LEAK` se il confine si riperde.

## Installazione

Claude Code cerca le skill in `.claude/skills/` o in `~/.claude/skills/`, non
qui dentro: finché `framework-install` non sta in una delle due, non esiste. È
l'unico attrito, e si paga **una volta**, non a ogni progetto.

**Master unico** — consigliato: un sorgente solo sulla macchina, skill personale.

Il repository porta **due sorgenti**, uno per lingua: `CLAW-it/` e
`CLAW-eng/`. Se ne installa **uno**.

```bash
git clone <repo> ~/.claude/CLAW
cp -r ~/.claude/CLAW/CLAW-it ~/.claude/framework
cp -r ~/.claude/framework/skills/framework-install ~/.claude/skills/
cp -r ~/.claude/framework/skills/framework-comply ~/.claude/skills/
```

```powershell
git clone <repo> $HOME\.claude\CLAW
Copy-Item -Recurse $HOME\.claude\CLAW\CLAW-it $HOME\.claude\framework
Copy-Item -Recurse $HOME\.claude\framework\skills\framework-install $HOME\.claude\skills\
Copy-Item -Recurse $HOME\.claude\framework\skills\framework-comply $HOME\.claude\skills\
```

La destinazione si chiama `framework/` perché è uno dei tre posti in cui il
Passo 0 guarda; per lasciarla dov'è, la si indica con `$CLAUDE_FRAMEWORK`.

**Copiato nel progetto** — questa cartella, rinominata `framework/`, nella root
del progetto, più `cp -r framework/skills/framework-* .claude/skills/`. Il
Passo 0 la trova per prima.

Da lì in poi, ogni progetto nuovo è **solo** `/framework-install`: il Passo 0
valida il sorgente prima di scrivere qualunque cosa, il Passo 6 verifica il
risultato con `doctor --strict`. Per controllare a mano che un candidato sia
valido:

```bash
cd <sorgente>/tools && python -m fwbuild source ..
```

Nessuna dipendenza da installare: serve solo Python 3.11+ (per `tomllib`).

Quanto costa il contesto comune di un progetto installato — la `CLAUDE.md` che
ogni subagent paga a ogni spawn — lo dice:

```bash
cd <sorgente>/tools && python -m fwbuild cost <progetto> [--spawns N] [--devs N] [--price USD]
# predefiniti: 100 spawn al giorno, 1 persona, $5 per milione di token in input
```

`doctor --json` stampa gli stessi rilievi più quella misura, per la CI.

Su più repository insieme — quante versioni del metodo sono in giro, e dove:

```bash
cd <sorgente>/tools && python -m fwbuild report <cartella-di-repository>
```

## Come è fatto

**Il metodo è generato, l'adattamento è a mano.** In `CLAUDE.md` e in ogni
agente, il metodo vive dentro una regione delimitata:

```html
<!-- FRAMEWORK:KERNEL v1.1.1 sha256:a3f9c1e4 — generato, non modificare a mano -->
…
<!-- /FRAMEWORK:KERNEL -->
```

Non è bloccata: puoi modificarla. L'hash smette di tornare e `framework-doctor`
te lo dice, così una modifica al metodo diventa **visibile** invece che sepolta.
Da lì `framework-sync` la porta su nel sorgente — ed è la direzione che, mancando,
fa divergere il metodo fra progetti.

Il frontmatter degli agenti resta **fuori** dalla regione: cambiare `model:` è
configurazione, non drift.

## Regole di manutenzione

- **Il metodo non si personalizza per progetto.** Si compila il contesto (i
  blocchi `[DA COMPILARE]`), non si riscrive il metodo. Se una modifica al metodo
  è giusta, è giusta per tutti: sale nel sorgente con `framework-sync`.
- **Si installa solo l'attivo.** Un agente non scelto non è cancellato, è non
  ancora installato: il master resta qui e `--activate` lo prende aggiornato.
- **Contenuto non universale → `shared/`**, dietro un pointer. `CLAUDE.md` è
  pagato a ogni spawn di agente: è il file più caro del sistema.

## Test

```bash
cd tools && python -m unittest discover -s tests -t . -v
```
