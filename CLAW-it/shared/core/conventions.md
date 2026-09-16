# Convenzioni

Regole trasversali di forma.

## Commit

- Messaggi in inglese, imperativi, prima riga ≤ 72 caratteri (`Fix …`, `Add …`, `Remove …`).
- Un commit = un cambiamento logico.
- Corretto un difetto, il repro che falliva entra in cronologia **prima** del fix: chi legge il log vede la prova, non solo l'esito.
- Il corpo spiega il **perché**, non il cosa (il cosa è nel diff).
- Mai riscrivere storie condivise, mai forzare un push, mai saltare i controlli automatici.

## Ambito di una modifica

- Refactoring, aggiornamenti dipendenze e formattazioni di massa sono task separati.
- Non toccare artefatti generati: si rigenerano, non si modificano a mano.

## Nomi

- Un nome esprime **cosa è o cosa fa**, non come è implementato (evitare tipi/strutture nei nomi).
- Coerenza prima dell'eleganza: usa la terminologia già presente nel progetto.
- Nessuna abbreviazione non standard nel dominio.
- I nuovi file seguono la convenzione di naming dei file adiacenti.

## Commenti

- **Vincolo non evidente** = scelta non ovvia, caso limite, formato imposto dall'esterno. Mai ciò che il codice già dice.
- **Nessuna cronaca:** niente storia della modifica («prima era», «fix per») né sigle di documenti interni. Il vincolo si dice al presente; la storia sta nel commit.
- Si aggiornano o si tolgono insieme al codice che descrivono.
- Il codice commentato inutilizzato si elimina.

## Documentazione

- I cambiamenti visibili all'utente vanno annotati nei registri stabiliti dal progetto.
- Qualsiasi modifica a un contratto versionato impone l'aggiornamento della versione e la relativa segnalazione.
- La documentazione comportamentale va verificata contro il codice reale prima di essere scritta.

## Qualità minima non negoziabile

- La build deve passare dopo ogni task.
- Nessun nuovo avviso introdotto senza segnalazione.

## In questo progetto

[DA COMPILARE — lingua di codice e commenti, mappa "tipo di codice → cartella", convenzioni di naming specifiche, dove si annotano i cambiamenti visibili, quali cartelle contengono artefatti generati da non toccare.]
