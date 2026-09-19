"""Fondere e togliere voci di `.claude/settings.json`, e dichiarare gli hook.

Il file è dell'utente prima che del framework: ciò che l'installazione aggiunge
va registrato per poterlo togliere dopo, e nient'altro va toccato. Non importa
nulla del pacchetto: lo usano l'installazione, `claw-sync` e la prova end
to end, e nessuno di loro deve tirarsi dietro il resto per fondere due dict.
"""

import copy
from collections.abc import Sequence

HOOKS = ("config_protection", "block_no_verify", "gateguard")

# Quello che si installa solo se il progetto lo chiede: nega il primo tocco di
# ogni file, ed è un turno in più per sessione.
OPTIONAL_HOOKS = ("gateguard",)

# Gli hook chiusi bloccano anche quando non possono girare: un controllo che
# sparisce perché manca l'interprete è un controllo che nessuno sa spento.
_CLOSED = ("config_protection", "block_no_verify")

_MATCHER = {
    "config_protection": "Edit|Write|MultiEdit",
    "block_no_verify": "Bash|PowerShell",
    "gateguard": "Edit|Write|MultiEdit",
}

_TIMEOUT_SECONDS = 10

# Ciò che un'orchestrazione pretende da `settings.json` per funzionare. Si
# fonde come il profilo, e finisce nello stesso record: cambiarla o
# disinstallare deve poterlo togliere.
# Gli strumenti Task — la lista condivisa dei team — Claude Code li dà di default
# solo fino a Opus 4.7 e Sonnet 4.6: sui modelli dopo, senza la seconda
# variabile, la lista resta vuota e il team si coordina solo per messaggi.
ORCHESTRATION_SETTINGS = {
    "agent-teams": {
        "env": {
            "CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS": "1",
            "CLAUDE_CODE_ENABLE_TODO_TOOLS": "1",
        }
    },
}


def merge(existing: dict, framework: dict) -> tuple[dict, dict, list[str]]:
    """`(unito, aggiunto, conflitti)`: le voci del framework sopra quelle dell'utente.

    Una chiave assente si aggiunge intera; due dict si fondono ricorsivamente;
    due liste si uniscono accodando i soli elementi assenti; su uno scalare
    diverso vince l'esistente e la chiave va nei conflitti. `aggiunto` porta
    solo ciò che è davvero entrato, nella stessa forma annidata: è il record
    che `unmerge` consuma. I conflitti sono percorsi puntati.
    """
    merged = copy.deepcopy(existing)
    added: dict = {}
    conflicts: list[str] = []
    for key, value in framework.items():
        if key not in merged:
            merged[key] = copy.deepcopy(value)
            added[key] = copy.deepcopy(value)
            continue
        current = merged[key]
        if isinstance(current, dict) and isinstance(value, dict):
            sub, sub_added, sub_conflicts = merge(current, value)
            merged[key] = sub
            if sub_added:
                added[key] = sub_added
            conflicts += [f"{key}.{c}" for c in sub_conflicts]
        elif isinstance(current, list) and isinstance(value, list):
            new = [copy.deepcopy(v) for v in value if v not in current]
            if new:
                merged[key] = current + new
                added[key] = new
        elif current != value:
            conflicts.append(str(key))
    return merged, added, conflicts


def unmerge(current: dict, added: dict) -> tuple[dict, list[str]]:
    """`(resto, tenuti)`: toglie il record di `merge` da ciò che c'è oggi.

    Si toglie solo ciò che è ancora uguale al record: uno scalare cambiato
    dall'utente resta, e il suo percorso va in `tenuti`. Un elemento di lista
    che non c'è più non si segnala: tolto o cambiato, non è distinguibile. I
    contenitori svuotati dalla rimozione si potano — quelli che l'utente aveva
    già vuoti prima di `merge` si perdono con loro, ed è la stessa cosa per
    `settings.json`.
    """
    rest = copy.deepcopy(current)
    kept: list[str] = []
    for key, value in added.items():
        if key not in rest:
            continue
        have = rest[key]
        if isinstance(have, dict) and isinstance(value, dict):
            sub, sub_kept = unmerge(have, value)
            kept += [f"{key}.{k}" for k in sub_kept]
            if sub:
                rest[key] = sub
            else:
                del rest[key]
        elif isinstance(have, list) and isinstance(value, list):
            remaining = list(have)
            for item in value:
                if item in remaining:
                    remaining.remove(item)
            if remaining:
                rest[key] = remaining
            else:
                del rest[key]
        elif have == value:
            del rest[key]
        else:
            kept.append(str(key))
    return rest, kept


def _command(name: str) -> str:
    """Il comando shell di un hook: trova script e interprete, o si ferma.

    Claude Code lo esegue con `sh -c` (Git Bash su Windows). Lo script si
    trova da `$CLAUDE_PROJECT_DIR` e non da un percorso assoluto, perché
    `settings.json` viaggia col repository. `python3` viene dopo `python`
    perché su Windows è lo stub dello Store. Solo ASCII: il comando passa per
    la codifica della shell.

    Un hook chiuso non si esegue con `exec`: uno script che non compila
    (Python 2, o sotto la 3.10) esce 1, e per Claude Code 1 vuol dire «nessuna
    obiezione». Ogni uscita diversa da 0 diventa 2; stdin passa allo script
    perché `sh -c` non lo legge.
    """
    if name not in HOOKS:
        raise ValueError(f"hook sconosciuto: {name}")
    if name in _CLOSED:
        fallback = f'echo "{name}: script o python assente, blocco" >&2; exit 2;'
        run = (
            '"$P" "$F"; c=$?; [ $c -eq 0 ] && exit 0; '
            f'[ $c -eq 2 ] || echo "{name}: script uscito con codice $c, blocco" >&2; exit 2'
        )
    else:
        fallback = f'echo "{name}: script o python assente, lascio passare" >&2; exit 0;'
        run = 'exec "$P" "$F"'
    return (
        f'F="$CLAUDE_PROJECT_DIR/.claude/hooks/{name}.py"; '
        "P=$(command -v python || command -v python3); "
        f'[ -f "$F" ] && [ -n "$P" ] || {{ {fallback} }}; '
        + run
    )


def hooks(names: Sequence[str]) -> dict:
    """La parte di `settings.json` che dichiara gli hook scelti, da fondere.

    Nessun hook → dict vuoto: una chiave `hooks` senza voci sarebbe un
    contenitore che `unmerge` poterebbe, e il giro fondi-togli non tornerebbe.
    """
    unknown = [n for n in names if n not in HOOKS]
    if unknown:
        raise ValueError(f"hook sconosciuti: {', '.join(unknown)}")
    if not names:
        return {}
    return {
        "hooks": {
            "PreToolUse": [
                {
                    "matcher": _MATCHER[name],
                    "hooks": [
                        {
                            "type": "command",
                            "command": _command(name),
                            "timeout": _TIMEOUT_SECONDS,
                        }
                    ],
                }
                for name in names
            ]
        }
    }
