## Orchestrazione: Agent teams

Il modello di questo progetto: il coordinatore è il *lead* degli Agent teams di Claude Code; i teammate — le schede di `.claude/agents/` valgono come tipo — condividono una lista di task e si scrivono direttamente. Sperimentale: servono `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in `.claude/settings.json` e una sessione interattiva. Teammate che non si formano → fermati e dillo all'utente.

- **Quando:** ricerca e review con lenti diverse, moduli su file disgiunti, lavoro su più livelli. In sequenza, sullo stesso file o con molte dipendenze: un agente alla volta.
- **Comunicazione:** fra teammate diretta, con le regole di comunicazione fra agenti; al lead il report standard, e il giudizio.
- **Costo:** ogni teammate è un contesto intero e conta come copia nei tetti della regola 1. Con la variabile accesa, un subagent con un nome parte come teammate.
- **File:** un solo teammate per file, deciso nel piano: due si sovrascrivono.
- **Task:** atomici, verificabili, con le dipendenze (regola 7). Lo stato del progetto lo scrive il lead.
- **Piani:** in plan mode il lead approva il piano del teammate in automatico, senza leggerlo. Chi implementa non parte in plan mode: il piano è dell'`architect` e lo approva l'utente.
- **Il lead aspetta** i teammate al lavoro, non ne esegue il task.
- **Stallo:** un task fermo o una coda bloccata non si aggira né si ripianifica da soli: il lead verifica se il lavoro è fatto e riporta all'utente cosa è fermo e perché.
- **Limiti:** `/resume` non riporta i teammate; niente team annidati; i loro permessi si approvano nella sessione del lead.
