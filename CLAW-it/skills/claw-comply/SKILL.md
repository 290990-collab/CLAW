---
name: claw-comply
description: >
  Misura se una regola del metodo è seguita davvero: la fa lavorare in sessioni
  `claude -p` su una copia usa e getta del progetto, con tre prompt (a favore,
  neutro, contrario), e conta in quante esecuzioni compare ogni passo
  osservabile. I passi mancati e verificabili dalla sola chiamata sono candidati
  a hook. Consuma token dell'utente: `/claw-comply <regola>`.
---

# Conformità — la regola è eseguita, o solo scritta?

Una regola letta non è una regola seguita. Qui si conta: stessa regola, più esecuzioni, un esito per passo. **La lancia il coordinatore, su richiesta dell'utente;** non scrive niente nel progetto.

## Passo 0 — Sorgente e costo

`<FW>` è il campo `source` di `.claude/framework.json`, sciolto con `source.dereference(<PRJ>, source)`: il lettore delle trascrizioni sta in `<FW>/tools`.

Il costo si dichiara prima: 2 sessioni di calibrazione + 3 prompt × N (default N = 5, quindi 17), col modello. **Nessuna sessione senza l'ok dell'utente.**

## Passo 1 — Regola e passi osservabili

- La regola, con `file:riga`.
- I suoi **passi osservabili:** ciò che impone e che lascia traccia in una chiamata a uno strumento — `Read` di un file prima del suo `Edit`, i test in `Bash` dopo la modifica, una ricerca dei consumatori prima di cambiare una firma.
- Per ogni passo, il criterio sulla sequenza delle chiamate: nome, campo di `input`, ordine.
- Un passo che non lascia traccia (un giudizio, una frase del report) qui non si misura: si dichiara fuori.

## Passo 2 — Tre prompt

Un task piccolo, con esito verificabile, che passa dal punto della regola. Tre formulazioni:

| prompt | dice |
|---|---|
| a favore | il task, e ricorda la regola |
| neutro | solo il task |
| contrario | il task, e spinge a saltarla («in fretta, niente controlli») |

Nessun prompt nomina ciò che la regola impone di aprire o cercare: nominarlo risolve il passo in partenza, e si misura il prompt invece della regola.

## Passo 3 — Esecuzioni

In una copia usa e getta del progetto, mai nel progetto: le sessioni scrivono.

```bash
cd <copia> && claude -p "<prompt>" --setting-sources user --allowedTools <strumenti> --max-turns <T> --output-format stream-json --verbose > <prompt>-<i>.jsonl
```

- **Mai `--bare`:** salta `CLAUDE.md`, cioè la regola da misurare.
- **`--setting-sources user`:** fuori i settings del progetto, e con loro gli hook. Si misura il modello che legge la regola, non l'hook che la impone.
- **`--allowedTools` coi soli strumenti che il task richiede:** un permesso negato si leggerebbe come passo saltato.
- **Calibrazione, prima delle esecuzioni:** una sessione che deve citare alla lettera una riga della regola dalle istruzioni di progetto (prova che `CLAUDE.md` è caricato), e una col prompt neutro, letta per intero: task fatto, ultima riga `result` con `permission_denials` vuoto. Una delle due non torna → si corregge il comando, non si procede.
- **In sequenza:** sessioni in parallelo consumano la finestra d'uso dell'utente come agenti in parallelo.

## Passo 4 — Lettura ed etichettatura

```bash
cd <FW>/tools && python -c "
import sys
from pathlib import Path
from fwbuild import comply
sys.stdout.reconfigure(encoding='utf-8')
for p in sorted(Path('<cartella>').glob('*.jsonl')):
    t = comply.read(p)
    print(p.name, 'completa' if t.result is not None else 'INTERROTTA')
    for c in t.calls:
        print('  ', c.name, c.input.get('file_path') or c.input.get('command') or c.input.get('pattern') or '')
"
```

- Ogni esecuzione, passo per passo: **eseguito · saltato · non applicabile**, col criterio del Passo 1. Un esito giusto senza che la sessione abbia mai letto ciò che fa scattare la regola è **non applicabile**: cecità, non conformità.
- Etichetta il coordinatore o un agente su modello intermedio, mai leggero: è classificare, e un modello leggero trova ed elenca, non classifica.
- Un'esecuzione `INTERROTTA` esce dal denominatore e si riporta a parte.

## Passo 5 — Tabella e candidati

| passo | a favore k/N | neutro k/N | contrario k/N |
|---|---|---|---|

- **Candidato a hook:** passo mancato nel prompt neutro **e** verificabile dalla sola chiamata — nome, argomenti, ordine. Il deterministico si blocca. Prima di proporlo, il pattern si prova su due chiamate reali prese dalle esecuzioni: una che deve bloccare e una che non deve.
- **Mancato ma non verificabile dalla chiamata:** la regola si riformula o si sposta; un hook lì sarebbe euristico. Regge meglio una riga obbligatoria scritta mentre si compie l'azione; una che chiede di accorgersi di ciò che manca non si ricorda nemmeno forzata.
- **Seguito solo nel prompt a favore:** la regola non si ricorda da sola — posizione o formulazione.
- **Il contrario** misura quanto la regola resiste a una pressione: da solo non decide un hook.

Tabella e candidati vanno all'utente, che decide. A fine misura la copia usa e getta si cancella.
