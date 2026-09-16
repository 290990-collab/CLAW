## Il ciclo del codice

**Capire → Progettare → Implementare → Verificare → Review → Integrare**

1. **Capire:** `explorer` (repo) e/o `api-scout` (librerie e docs esterne).
2. **Progettare:** `architect` SOLO SE il task tocca ≥3 file o un contratto, o se restano aperte scelte di struttura (quelle sul *cosa* si chiudono prima con l'utente). *Altrimenti si salta:* un piano da tre righe lo scrive il coordinatore.
   - *Approvazione:* piano grosso o scelte di struttura aperte → ricapitolalo all'utente e chiedi sì/no prima di implementare. Da lì in poi il piano non si riapre da soli: a cambiare idea è l'utente.
3. **Implementare:** `implementer`, un task alla volta.
   - *Test-first obbligatorio:* nuove feature, bug fix definiti, logica di business o di API.
   - *Test-first escluso:* refactoring, UI, prototipi, dipendenze, documentazione.
4. **Verificare:** `tester` estende la copertura oltre i mini-test dell'implementer (pochi test solidi sui confini del dominio).
5. **Review:** se il diff tocca la **superficie critica** → prima il revisore di quella superficie, poi `final-reviewer`, che verifica da zero senza fidarsi dei report.
   - *Task importante* — lungo, complesso, bloccante per un obiettivo di alto livello, o dichiarato tale dall'utente (correggere o cambiare una funzionalità esistente sì, ritoccare un'interfaccia no) → **doppia revisione:** due `final-reviewer` isolati, stessa rubrica, uno dopo l'altro; passa solo se passano entrambi. Correzioni come da regola 9.
6. **Integrare:** il coordinatore risolve i finding e integra. Commit SOLO su richiesta dell'utente.

**Passo saltato:** resta scritto — `saltato: <motivo>`, una riga, nel report e in `docs/TODO.md`. Cancellarlo toglie la differenza fra valutato e dimenticato.

## Scegliere fra agenti che sembrano vicini

| Dubbio | Decisione |
|---|---|
| Servono >2 file o non sai dove guardare | **`explorer`** \| Path già noto → legge il coordinatore: spawnare costa di più |
| Info dentro o fuori dal repo | Repo → **`explorer`** \| Librerie, servizi, docs → **`api-scout`** |
| Impatto su struttura o contratti | Impatto reale → **`architect`** \| Cambio banale → decide il coordinatore |
| Causa del difetto | Ignota → **`debugger`**, che consegna la diagnosi \| Nota → **`implementer`** |
| Natura della modifica | Aggiunge o cambia comportamento → **`implementer`** \| Comportamento osservabile invariato → **`refactorer`** |
| Frontend o logica | Viste, markup, stile, movimento → **`frontend`** \| Logica e servizi → **`implementer`** (se pesa su entrambi, `architect` spezza il task) |
| Pubblicazione | Hosting semplice, un push aggiorna → **`deploy`** \| Risorse come codice, ambienti multipli → **`infra`**. Non coesistono |
| Tipo di review | «Il codice è corretto?» → **`final-reviewer`** \| «È sicuro / valido / il dato è giusto?» → revisore della superficie critica, PRIMA |
| Review mirata | Errori inghiottiti, default inventati, rami che nascondono la causa → **`silent-failure-hunter`** \| Commenti che non dicono più il vero → **`comment-analyzer`** |
