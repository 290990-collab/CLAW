# Guida ai test

Il principio — **pochi test sensati, mai molti test deboli** — sta nel metodo. Qui il come applicarlo.

## Come si sceglie un test

**Quale difetto plausibile lo farebbe fallire?** Senza risposta il test non serve; se la risposta è «nessuno, verifica che il codice esista», è un test da non scrivere.

Test utile: fallisce quando il comportamento è sbagliato, passa quando è giusto, non cambia quando cambia solo l'implementazione. Se un refactoring a comportamento invariato lo rompe, verificava i dettagli interni.

## Il livello giusto

| Il rischio è… | Il test va… |
|---|---|
| una regola di calcolo o trasformazione | sull'unità, con casi limite reali |
| l'interazione fra due moduli | sulla giunzione, con entrambi veri |
| un contratto verso l'esterno | sul contratto: forma, campi, compatibilità |
| il comportamento con dati reali sporchi | su un campione reale, non ideale |
| un flusso end-to-end | uno o due percorsi critici, non tutti |
| un controllo di accesso | con l'id di un altro utente autenticato, non solo senza credenziali |
| hash, codifiche, aritmetica | contro una risposta nota calcolata fuori dal codice, mai contro il suo output |

Errore più comune: testare tutto al livello più comodo — l'unità — lasciando scoperto il livello a cui i difetti nascono davvero.

## Invarianti prima degli esempi

Un'invariante copre infiniti casi e non invecchia:

- **idempotenza:** applicare due volte dà lo stesso risultato di una;
- **round-trip:** serializza e rileggi, ottieni l'originale;
- **stabilità:** input equivalenti danno output identici, anche fra esecuzioni;
- **conservazione:** nessun elemento perso o duplicato in una trasformazione;
- **monotonia:** aggiungere non può diminuire il risultato;
- **gestione dell'errore:** un fallimento non lascia stato parziale.

## Cosa non fare

- Test che replicano l'implementazione riga per riga: si rompono a ogni modifica e non trovano nulla.
- Asserzioni su messaggi di log o su formattazioni non contrattuali.
- Dipendenze dall'ordine di esecuzione o da stato lasciato da un altro test.
- Sostituti finti così permissivi da passare qualunque cosa: verificano il finto, non il vero.
- Attese temporali fisse al posto di una condizione: lente e intermittenti.
- Indebolire un'asserzione per far passare un test rosso.

## Quando un rischio non è testabile

Resa visiva, prestazioni su hardware reale, integrazione con un servizio esterno, comportamento sotto carico: non si compensa con test unitari che non c'entrano. Il rischio va in `UNVERIFIED` con i **passi di verifica manuale**, rifacibili da chiunque.

Lo stesso vale per il test-first impraticabile — imbracatura pesante, stato che esiste solo in produzione, riproduzione vaga: non si salta in silenzio. Si dichiara perché e si nomina il controllo eseguibile più vicino — uno script mirato, un comando che riproduce, un confronto di output — che vale più di un test scritto per rispettare la forma.

## In questo progetto

[DA COMPILARE — comando di esecuzione dei test, framework in uso, dove vivono i test e come si nominano, cosa è escluso per natura e come si verifica invece, tempi di esecuzione, dati di prova disponibili, difetti già capitati che hanno una regressione dedicata.]
