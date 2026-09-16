# Principi di ricerca

Per i progetti il cui prodotto non è «software che gira» ma **evidenza riproducibile**.

> **Principio guida.** Ogni decisione è motivata da dati, esperimenti o letteratura; ogni risultato è spiegabile, riproducibile e verificabile da altri.

## Evidenza e onestà

1. **Evidence first** — ogni affermazione tecnica poggia su una misura, una fonte o un esperimento, mai su una supposizione plausibile.
2. **Fatti, interpretazioni e idee restano separati**, anche tipograficamente: confonderli è il modo più comune di scrivere qualcosa di falso senza mentire.
3. **Assunzioni esplicite** su problema, dati e modello: quelle taciute sono quelle che si rivelano sbagliate.
4. **I risultati negativi si riportano:** un'ipotesi smentita è informazione acquisita, nasconderla significa ripagarne il costo più avanti.
5. **Scetticismo verso i propri miglioramenti:** un guadagno è un'ipotesi da verificare, non un risultato acquisito.
6. **Si riportano forze e debolezze:** un lavoro che espone solo i punti forti non è valutabile.

## Metodo sperimentale

7. **Baseline prima della complessità** — prima il riferimento semplice, anche banale o casuale. Senza il denominatore giusto un guadagno può essere sopravvalutato di un ordine di grandezza.
8. **Una variabile alla volta:** cambiandone due l'effetto non è attribuibile e l'esperimento è sprecato.
9. **Ogni componente aggiunta va giustificata da un'ablazione:** se toglierla non cambia nulla, non serviva.
10. **Il criterio di successo si decide prima** di guardare i risultati. Deciderlo dopo è scegliere la conclusione.
11. **Misura contro intuizione:** decidono le metriche, non la sensazione che una cosa «dovrebbe» funzionare meglio.
12. **Confronti equi:** stessi dati, stesso protocollo, stesse esclusioni, capacità dei modelli dichiarata quando differisce.
13. **Rispetta la significatività:** differenze dell'ordine del rumore non sono risultati finché non è mostrato il contrario.
14. **Analisi degli errori prima del miglioramento:** capire *come* sbaglia precede il tentativo di farlo sbagliare meno.
15. **Capire prima di ottimizzare.**

## Integrità dei dati

16. **L'insieme di test non seleziona nulla:** iperparametri, varianti e checkpoint si scelgono sulla validazione; il test si tocca una volta, per il numero finale.
17. **Statistiche di normalizzazione dal solo insieme di addestramento.**
18. **Attenzione alla circolarità:** se il modello riceve in ingresso ciò che la verità di riferimento misura in uscita, su quella dimensione il risultato è un limite superiore, non una prestazione. Va dichiarato ogni volta.
19. **Non si ottimizza per un singolo benchmark:** ciò che ne risulta misura il benchmark, non il problema.

## Riproducibilità

20. **Semi e sorgenti di casualità fissati e dichiarati.**
21. **Configurazione fuori dal codice**, versionata insieme al risultato che ha prodotto.
22. **Ogni numero riportato dev'essere rintracciabile:** quale configurazione, quale esecuzione, quale file. Un numero senza provenienza non è citabile.
23. **Non si rilancia un esperimento** per riavere un numero che esiste già in un log o in un riepilogo.

## In questo progetto

[DA COMPILARE — l'ipotesi di ricerca corrente, quali insiemi esistono e quale seleziona cosa, le metriche adottate e cosa possono nascondere, le baseline disponibili, le circolarità note, chi lancia le esecuzioni pesanti e come, dove si scrivono i risultati.]
