## Il ciclo del contenuto

Si affianca al ciclo del codice, non lo sostituisce. Qui il prodotto non è software che gira ma **attenzione guadagnata**: un contenuto corretto che nessuno apre non è un successo parziale, è costo.

**Posizionamento → Confezione → Testo → Rifinitura → Pubblicazione → Analisi → Posizionamento.**

1. **Posizionamento** (`market-researcher`): per chi, contro quale alternativa, quale promessa. Si decide una volta e si riapre solo quando l'analisi lo smentisce: cambiarlo a ogni pezzo azzera il riconoscimento.
2. **Confezione** (`campaign-planner` con `visual-designer`): idea, titolo, immagine. Si decide **prima** del testo — è ciò che il pubblico vede per primo, e un testo buono in una confezione muta non viene aperto. Qui si scrive anche la **previsione**: cosa ci si aspetta, su quale metrica.
3. **Testo** (`copywriter`): la voce sta in `.claude/shared/domain/marketing-voice.md`, default sostituibile e non regola del metodo.
4. **Rifinitura** (`copywriter`): a passate, una dimensione per volta — chiarezza, prova, obiezioni, taglio e ritmo, lunghezza del canale — ricontrollando le precedenti. Ogni affermazione resta attaccata alla sua prova.
5. **Pubblicazione: la fa l'utente.** L'agente prepara il pezzo **e la misura da raccogliere**; la riga va in *In attesa* su `docs/TODO.md`, con cosa riportare e quando.
6. **Analisi** (`content-analyst`): le metriche si leggono contro la previsione del passo 2, mai contro l'ultimo pezzo. Delta dentro il rumore significa nessun risultato, e si dice.

Regole del ciclo:

- **La revisione delle affermazioni precede la pubblicazione:** `claim-reviewer` presidia la superficie critica e il passo 5 è irreversibile — ciò che è stato letto resta letto anche dopo la correzione.
- **L'obiettivo sta in `docs/roadmap.md`, non nel prompt:** «finché non arrivo a N» non è un criterio di completamento — l'esito non è verificabile nella sessione e il singolo pezzo è dominato dal rumore. Si chiude **l'iterazione**, con la sua previsione.
- **Non si ripubblica per riavere un numero** già presente in un riepilogo: si legge da lì.
