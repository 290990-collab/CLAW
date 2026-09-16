## Obblighi di esecuzione

Valgono per ogni agente che riceve un task, coordinatore incluso quando lavora direttamente.

- **Niente sub-deleghe:** i subagent non spawnano altri agenti. Se serve lavoro fuori dal tuo mandato, riportalo al coordinatore.
- **Scope rigido:** esegui *solo* il task assegnato. Qualsiasi problema extra notato va nel report, MAI nel diff.
- **Decisioni fuori mandato:** una scelta che il task non ti assegna — struttura, contratto, alternative non indicate — non la prendi: ti fermi e la riporti in testa al report con le opzioni, e riprendi alla risposta.
- **Lettura a range:** leggi i range `file:riga` che ricevi, non i file interi. Allarga solo se l'estratto non basta, dichiarandolo.
- **Zero ridondanza:** build/test passati e nessun file cambiato → non rieseguire.
- **Richiesta aperta:** più letture plausibili portano a lavori diversi e repo o documenti non scelgono → non ne scegli una: chiedi prima di agire. Domande raggruppate, solo su ciò che cambia il lavoro — obiettivo, cosa fa e cosa non fa, requisiti e vincoli, priorità —, mai su ciò che repo, documenti o un default ovvio già risolvono. Procedi quando le risposte bastano a fissare il criterio di completamento. **Un fatto osservabile non si chiede:** se la risposta si ottiene eseguendo qualcosa — comportamento, tempi, output, se un controllo distingue davvero — la si osserva. All'utente restano le scelte di prodotto o di preferenza che nessuna esecuzione chiude.
- **Criterio di stop:** manca un criterio di completamento verificabile → chiedilo prima di procedere. Diventa insoddisfacibile in corso d'opera → non si abbandona né si aggira: ti fermi e lo riporti in testa al report, col vincolo che lo impedisce.
