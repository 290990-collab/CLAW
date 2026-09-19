## Lo stato che si aggiorna da solo

Lo stato lo scrive **esclusivamente il coordinatore**: chi lo scrive deve aver visto il quadro intero, e un agente che ha visto un task solo non ce l'ha. I subagent riportano e basta.

| Liv. | File | Contenuto | Aggiornamento | Tetto |
|---|---|---|---|---|
| 1 | `docs/TODO.md` | stato operativo immediato: in corso, in attesa, prossimo passo, bloccati | a ogni step | ~120 righe, indicativo |
| 2 | `docs/status.md` | decisioni chiuse, risultati misurati, ipotesi confermate o smentite, rimozioni intenzionali | quando un task si chiude | voce telegrafica |
| 3 | `CLAUDE.md § Stato attuale` | il quadro del progetto (sta **fuori dalla regione kernel**: aggiornarlo non deve produrre drift) | solo se cambia il quadro | ~25 righe |
| 4 | memoria persistente | fatti fra sessioni: direttive dell'utente, preferenze, decisioni strutturali, errori che si ripeterebbero | a ogni scoperta o cambio strutturale | 1 fatto per file |

*Nota su `docs/roadmap.md`:* non è un livello. I livelli dicono dove siamo, la roadmap dove andiamo — obiettivi, dipendenze, criteri. Si tocca alla chiusura o all'aggiunta di un obiettivo.

## Regole di aggiornamento

- **Si aggiunge o si spunta, non si riscrive.** Una casella si spunta con l'evidenza accanto — il comando eseguito, `file:riga`, l'esito reale. Senza, resta aperta.
- **Pausa sicura:** si chiude il passo in corso o si torna indietro, mai a metà modifica; nessuna azione irreversibile per fermarsi; ciò che è solo sul disco diventa un commit `wip:` che dichiara in una riga se l'albero è rotto. Il livello 1 riceve dove siamo, cosa è verificato e la prima azione alla ripresa — scritto per chi riparte a freddo, non per chi era qui.
- **Ripresa:** la traccia lasciata è input autorevole: si legge, non si rifà. Ri-verificare da zero ciò che il livello 2 dà per chiuso è lavoro pagato due volte; si verifica ciò su cui si sta per agire.
- **Compressione al tetto:** oltre il tetto si comprime a fine task, non prima di aggiungere; la traccia lunga scende di livello, non gonfia quello corrente.
- **Inizio sessione:** livello 1 per primo, sempre. **Fine task:** livello 1 sempre; livello 2 se qualcosa si è chiuso; livello 3 se cambia il quadro.
- **Operazioni lunghe o asincrone:** appena parte qualcosa che l'utente deve lanciare o attendere, la riga va in *In attesa* sul livello 1, con cosa deve riportare.
- **Zero duplicazione:** TODO = operativo | `status.md` = risultati | `CLAUDE.md` = quadro | memoria = ciò che sopravvive alla sessione.

## Manutenzione della memoria persistente (livello 4)

Per guardarla: la skill `framework-memory` la elenca e appaia ogni conflitto con la riga del repo che lo smentisce.

- **Va rivisitata, non solo riempita:** a ogni cambio di path, contratti o moduli e a ogni ipotesi smentita, chiediti *«questo supera una memoria?»* e correggila o annotala come superata subito.
- **Memoria compatta:** un fatto per file, nessun numero duplicato dal repo, nessun path che non esiste più.
- **Errori:** si registra l'errore che si ripeterebbe — telegrafico, tecnico, con i riferimenti (`file:riga`, comando, messaggio) — non l'episodio. Rimossa la causa, la memoria si cancella: il problema non esiste più. Per trovarli: `conversation-analyzer` estrae dalle trascrizioni i candidati ricorrenti con l'evidenza — regola, memoria o hook — e decide il coordinatore.
- **Una regola si promuove quando si ripete:** un episodio è un caso, due indipendenti sono un pattern, e solo un pattern stretto e verificato più volte diventa regola generale. La voce dice quando vale, quando **non** vale e da dove viene (`file:riga`, comando, PR). Sicurezza, dati e permessi non diventano mai un pattern «da saltare», per quante volte si siano ripetuti.
- **In conflitto vince il repo:** una memoria vecchia non annotata è un bias attivo, fa ripartire la sessione successiva con la visione di un mese prima.
