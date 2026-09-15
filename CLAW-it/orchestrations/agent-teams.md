## Orchestrazione: Agent teams

Il modello di questo progetto: il coordinatore è il *lead* degli Agent teams di Claude Code; i teammate — le schede di `.claude/agents/` valgono come tipo — condividono una lista di task e si scrivono direttamente. Sperimentale: servono una sessione interattiva e, in `.claude/settings.json`, `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` per il team e `CLAUDE_CODE_ENABLE_TODO_TOOLS=1` per la lista dei task, che dopo Opus 4.7 e Sonnet 4.6 senza resta vuota. Teammate che non si formano, o lista vuota → fermati e dillo all'utente.

- **Quando:** ricerca e review con lenti diverse, moduli su file disgiunti, lavoro su più livelli. In sequenza, sullo stesso file o con molte dipendenze: un agente alla volta.
- **Comunicazione:** fra teammate diretta, con le regole di comunicazione fra agenti; al lead il report standard, e il giudizio. Un messaggio su un risultato già scritto rimanda al file della memoria condivisa, non ne ripete il contenuto.
- **Memoria condivisa:** `docs/team/<obiettivo>/`, un file per teammate (`<nome>.md`), creata dal lead insieme al team. Ognuno accoda i propri risultati nel formato del report standard, con `file:riga`, appena li ha e non solo a fine task, e non tocca i file degli altri. Prima di un task si leggono i file dei teammate da cui dipende; gli altri solo se il task li chiede. Un teammate senza `Write` manda il report al lead, che lo accoda nel suo file. Non è un livello di stato: chiuso il lavoro, il lead porta ciò che si è chiuso in `docs/status.md` e `docs/TODO.md`, e la cartella si cancella con l'ok dell'utente.
- **Costo:** ogni teammate è un contesto intero e conta come copia nei tetti della regola 1. Con la variabile accesa, un subagent con un nome parte come teammate.
- **File:** un solo teammate per file, deciso nel piano: due si sovrascrivono.
- **Task:** atomici, verificabili, con le dipendenze (regola 7). Lo stato del progetto lo scrive il lead.
- **Piani:** in plan mode il lead approva il piano del teammate in automatico, senza leggerlo. Chi implementa non parte in plan mode: il piano è dell'`architect` e lo approva l'utente.
- **Il lead aspetta** i teammate al lavoro, non ne esegue il task.
- **Stallo:** un task fermo o una coda bloccata non si aggira né si ripianifica da soli: il lead verifica nella memoria condivisa e nel diff se il lavoro è fatto, e riporta all'utente cosa è fermo e perché.
- **Limiti:** `/resume` non riporta i teammate, la memoria condivisa sì: un teammate nuovo riparte dal file di chi sostituisce. Niente team annidati; i permessi dei teammate si approvano nella sessione del lead.
