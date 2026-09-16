# Orchestrazione — guida del coordinatore

## Chi fa cosa

- **Coordinatore:** pianifica, delega, verifica e integra.
- **Esecuzione diretta:** modifiche piccole (≤2-3 file, poche decine di righe, nessun contratto toccato) si eseguono direttamente: delegare costa di più.
- **Subagent:** eseguono il task e riportano al coordinatore, e non spawnano subagent. Chi comunica con chi lo dice il modello di orchestrazione, nella sezione che gli dà nome in questa guida.

## Skill esterne

Le skill collegate stanno in `.claude/skills/`. Quelle che puoi invocare da solo sono quelle che ti vengono elencate: le altre restano all'utente, e i settings te le nascondono.

- **Di rado, e solo se serve:** una skill è lunga e vale per un compito solo. Invocarne una per abitudine è contesto che paga tutta la sessione.
- **Non la esegui tu:** deleghi a `skill-runner`, che la invoca e riporta. Le sue istruzioni restano nel contesto di lui e se ne vanno con lui; tu verifichi il report come ogni altro.
- **Se la lancia l'utente, la esegui tu:** l'ha scelta lui, e passare da un subagent perderebbe ciò che aveva in mente.
- **Le skill personali e dei plugin non si invocano in autonomia:** non le ha scelte questo progetto.
- **Ciò che vale solo per quella skill muore lì:** non si salva in memoria, non si scrive nei file di stato, non si cita come regola generale.

## Economia dei token — le dieci regole della delega

1. **Parallelismo per ruolo e per costo**
   - `architect`, e ogni agente che decide per l'intero lavoro: uno solo, mai duplicato né rilanciato sullo stesso task: due controllori collidono.
   - Modello di punta: di norma in sequenza. In parallelo solo se il task lo richiede, su lavori che non si toccano né si influenzano: fino a 2 copie dello stesso agente, o agenti diversi su campi diversi (`architect` sul backend, `frontend` sull'interfaccia, `debugger` su un guasto).
   - Modello intermedio: fino a 3 copie in parallelo, alle stesse condizioni. Leggero: senza limite.
   - Nessun lavoro ripetuto: lo stesso task a più agenti di punta, o in più giri, costa più di quanto aggiunge. Due eccezioni: la doppia revisione (regola 9) e il guasto a causa ignota su un task importante — due `debugger` isolati sullo stesso sintomo, poi confronta tu le diagnosi. Isolati apposta: il guadagno viene dall'indipendenza, non dal dibattito. Chi duplica dichiara **prima** dello spawn come sceglierà fra i risultati — il primo che passa, la classifica, la sintesi — e se un agente cade procede con quelli rimasti dicendolo: deciderlo dopo è scegliere il risultato che piace.
   - Il parallelo non abbassa il costo, lo concentra, anche fra agenti diversi: la finestra d'uso dell'utente si esaurisce prima e il lavoro si interrompe a metà.
2. **Agente e modello al task, non al ruolo:** niente `architect` per decisioni ovvie né `debugger` per cause evidenti. Il modello della scheda è il default: lo spawn lo abbassa per task meccanici, privi di decisioni o a basso rischio (l'effort della scheda resta), e non lo alza mai. Una decisione che il mandato non dà all'esecutore torna a chi ha delegato, e la risposta va allo stesso agente fermo, in una riga (regola 8). Più decisioni che tornano → mancava il piano, non il modello. Un modello troppo debole sbaglia, e il giro a vuoto costa più del premium: un modello leggero regge «trova ed elenca», non «classifica».
3. **Pre-digerire il contesto:** una domanda a cui risponde un comando — una ricerca testuale, i test, il doctor — si risolve col comando, non con un agente che legge file. Il resto va prima a `explorer` (repo) o `api-scout` (librerie, servizi, docs) a costo basso per estrarre `file:riga` e firme precise, e gli estratti vanno agli agenti costosi. **Scansionare non è lavoro del contesto principale:** compito ampio, risposta stretta, nessun giudizio delegato («di N file, quali toccano X» → una tabella) va a `explorer` anche quando farlo da sé sembra più rapido, perché il coordinatore costa di più per token e si tiene il rumore per tutta la sessione. Resta a te ciò di cui il **giudizio** è il prodotto, non la scansione che lo precede.
4. **Passa range, non file:** nel prompt solo estratti e `file:riga` esatti; chi li riceve non allarga la lettura.
5. **Struttura del prompt:** tassativa, sezione «Come si scrive un prompt di delega». Istruzioni ai bordi, dati ed estratti al centro.
6. **Load-on-demand:** passa i pointer a risorse e guide. L'agente le apre se e quando servono.
7. **Un task per agente,** con criterio di completamento verificabile. Zero task ombrello («sistema X»); un piano di task atomici ordinati, ognuno verificabile, conta come uno. Si spezza solo ciò che non entra in un contesto: la profondità è un esito, non un piano.
8. **Riuso della sessione, mai ri-spawn:** l'agente che ha il contesto di un task — lo stesso o uno successivo sugli stessi file — resta aperto finché quel contesto serve, e il lavoro nuovo gli arriva come messaggio con la sola novità, non come agente nuovo che ridigerisce tutto. Ogni messaggio però rilegge l'intera sua conversazione: un ritocco di poche righe lo fa il coordinatore.
9. **Revisione proporzionata, un solo giro:** nessun revisore per le modifiche piccole, uno per un task normale, due isolati per un task importante (§ Il ciclo del codice, passo 5); il revisore della superficie critica è fuori da questo conto. Il revisore finale **oppure** una skill di review nativa, mai entrambe; le native pesanti solo su richiesta dell'utente. I finding li corregge chi ha il quadro — il coordinatore, o l'agente ancora aperto che ha scritto quel codice; un finding che chiede lavoro nuovo diventa un task e segue il ciclo. Il revisore non corregge e non si rilancia sulle correzioni: le verifica il coordinatore coi test. Un rilievo che blocca (sicurezza, perdita di dati) va all'utente, che decide.
10. **Zero ri-verifiche inutili:** non spawnare agenti per rieseguire build/test appena passati se nulla è cambiato.
