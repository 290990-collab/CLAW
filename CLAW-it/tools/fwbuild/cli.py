"""Entrypoint: python -m fwbuild <comando>."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import doctor, report, skills, source, upgrade

# Listino Claude Opus 5, token di input non in cache, in dollari per milione.
# È un default dichiarato, non una verità: i prezzi cambiano e la cache abbassa
# la cifra reale. `--price` esiste perché il numero lo scelga chi legge.
PRICE_PER_MTOK = 5.00
WORKING_DAYS = 22


def _force_utf8_stdout() -> None:
    """Su Windows lo stdout di Python usa la codepage locale (cp1252), che non
    copre tutti i caratteri dei messaggi. Senza questo, un rilievo con un
    carattere fuori tabella fa fallire il comando invece di stamparlo."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def _bases(path: Path | None) -> list[Path]:
    """L'ordine di ricerca del sorgente. È la parte impura, e sta qui apposta.

    Un percorso indicato è l'**unico** candidato: se non regge è un errore, non
    un fallback sul successivo.
    """
    if path is not None:
        return [path]
    env = os.environ.get("CLAUDE_FRAMEWORK")
    return [
        Path.cwd(),
        *([Path(env)] if env else []),
        Path.home() / ".claude" / "framework",
    ]


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(prog="fwbuild")
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("doctor", help="verifica un'installazione")
    d.add_argument("path", type=Path)
    # Un'installazione completa non ha rilievi di nessuna gravità:
    # --strict è quella regola resa meccanica, per la CI e per il Passo 6.
    # Le note — gli avvisi che `framework.json` dichiara di accettare — non la
    # fanno cadere: sono state guardate una volta e la decisione è scritta.
    d.add_argument(
        "--strict", action="store_true", help="uscita 1 anche con soli avvisi"
    )
    d.add_argument("--json", action="store_true", help="rilievi e misure in JSON, per la CI")

    r = sub.add_parser("report", help="divergenza del metodo su più progetti")
    r.add_argument("paths", type=Path, nargs="+")
    r.add_argument(
        "--depth", type=int, default=2, help="quanti livelli scendere cercando progetti"
    )
    r.add_argument("--json", action="store_true", help="rapporto in JSON, per la CI")
    r.add_argument(
        "--strict", action="store_true", help="uscita 1 se un progetto diverge o ha rilievi"
    )

    c = sub.add_parser("cost", help="cosa costa la CLAUDE.md installata")
    c.add_argument("path", type=Path)
    c.add_argument("--spawns", type=int, default=100, help="spawn al giorno per persona")
    c.add_argument("--devs", type=int, default=1, help="quante persone lavorano sul repo")
    c.add_argument(
        "--price", type=float, default=PRICE_PER_MTOK, help="$ per milione di token di input"
    )

    s = sub.add_parser("source", help="risolve e valida la root del sorgente")
    s.add_argument("path", type=Path, nargs="?")

    k = sub.add_parser("skills", help="pacchetti di skill collegati al sorgente")
    ks = k.add_subparsers(dest="skills_command", required=True)
    for name, help_text in (
        ("list", "pacchetti collegati, skill e pool"),
        ("add", "collega un repository, fissato a un commit"),
        ("remove", "stacca un pacchetto"),
    ):
        p = ks.add_parser(name, help=help_text)
        if name == "add":
            p.add_argument("repo", help="URL del repository o cartella locale")
            p.add_argument("--commit", help="commit da fissare; senza, l'ultimo del ramo")
        if name == "remove":
            p.add_argument("package", help="nome del pacchetto, come lo stampa `skills list`")
        p.add_argument("--source", type=Path, dest="path", help="root del sorgente")

    args = parser.parse_args(argv)

    if args.command == "skills":
        return _skills(args)

    if args.command == "source":
        try:
            root = source.resolve(_bases(args.path))
        except LookupError as err:
            print(err)
            return 1
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
        print(f"{root} v{version}")
        # Senza record, `--upgrade` considera il sorgente intatto e lo
        # sostituisce con la release: ciò che `--up` ha promosso si perde lì.
        record = upgrade.read_record(root)
        if record is None:
            print("nessun record upstream: intatto, si aggiorna sostituendolo")
        else:
            print(
                f"modificato con --up: base v{upgrade.base_version(root)}, "
                f"da {record.get('repo') or 'repo non dichiarato'}"
            )
        return 0

    if args.command == "doctor":
        findings = doctor.check(args.path)
        # L'uscita si decide sui soli rilievi bloccanti, e si decide **una
        # volta**: `--json` è un formato, non una postura. Calcolata dopo il
        # ramo «nessun rilievo», farebbe uscire 1 una CI che aggiunge il flag a
        # un'installazione pulita.
        blocking = [f for f in findings if f.blocking]
        code = 1 if (args.strict and blocking) or any(
            f.severity == "ERROR" for f in findings
        ) else 0
        if args.json:
            print(json.dumps(_report(args.path, findings), ensure_ascii=False, indent=2))
            return code
        if not findings:
            print("OK — nessun rilievo")
            return code
        for f in findings:
            print(f"{f.severity:5} {f.code:17} {f.message}")
        if not blocking:
            print("OK — solo deroghe dichiarate in framework.json")
        return code

    if args.command == "cost":
        return _cost(args.path, args.spawns, args.devs, args.price)

    if args.command == "report":
        s = report.survey(args.paths, args.depth, _source_version())
        if args.json:
            print(json.dumps(report.as_dict(s), ensure_ascii=False, indent=2))
        else:
            _print_survey(s)
        return 1 if args.strict and not s.clean else 0
    return 0


def _skills(args) -> int:
    """`skills list | add | remove`: la presa a cui si collegano le skill di altri.

    Scrive nel **sorgente**, non nei progetti: le installazioni ricevono i
    pacchetti al passaggio successivo di `framework-sync`, come ogni altro file
    del framework. Dirlo qui evita di credere che un `add` abbia già cambiato
    qualcosa nei progetti aperti.
    """
    try:
        root = source.resolve(_bases(args.path))
    except LookupError as err:
        print(err)
        return 1
    try:
        if args.skills_command == "add":
            pkg = skills.add(root, args.repo, args.commit)
            print(f"{pkg.name} @ {pkg.commit[:7]} — {', '.join(pkg.skills)}")
            covered = skills.shadowed(pkg.skills)
            if covered:
                print(
                    "hanno già una skill personale con lo stesso nome, che vince "
                    "su quella del progetto: " + ", ".join(covered)
                )
            print(
                f"fuori dal pool: invocabili da te, non dal coordinatore. "
                f"Per metterle nel pool: skills/{skills.POOL_FILE}"
            )
            print("nei progetti arrivano con framework-sync --down o --repair")
            return 0
        if args.skills_command == "remove":
            gone = skills.remove(root, args.package)
            print(f"{args.package} staccato: {', '.join(gone) or 'nessuna skill'}")
            print("nei progetti resta finché non passi da framework-sync --uninstall o --down")
            return 0
        in_pool = set(skills.pool(root))
        packages = skills.packages(root)
        if not packages:
            print(f"nessun pacchetto collegato in {root / 'skills'}")
            return 0
        for pkg in packages:
            print(f"{pkg.name} @ {pkg.commit[:7]} — {pkg.repo}")
            for name in pkg.skills:
                print(f"  {name:<30} {'pool' if name in in_pool else 'solo utente'}")
    except (ValueError, RuntimeError) as err:
        print(err)
        return 1
    return 0


def _measure(path: Path) -> doctor.Measure | None:
    """La misura della CLAUDE.md di un'installazione, o None se non c'è.

    Il file assente non è un errore di questo strato: il doctor lo riporta già
    come STATE_MISSING, e duplicare il messaggio darebbe due voci per un fatto.
    """
    claude_md = Path(path) / "CLAUDE.md"
    if not claude_md.is_file():
        return None
    return doctor.measure(claude_md.read_text(encoding="utf-8"))


def _report(path: Path, findings: list[doctor.Finding]) -> dict:
    m = _measure(path)
    return {
        "path": str(path),
        "ok": not any(f.blocking for f in findings),
        "errors": sum(1 for f in findings if f.severity == "ERROR"),
        "warnings": sum(1 for f in findings if f.severity == "WARN"),
        "notes": sum(1 for f in findings if f.severity == "NOTE"),
        "measure": None
        if m is None
        else {
            "kernel_words": m.kernel_words,
            "project_words": m.project_words,
            "total_words": m.total_words,
            "tokens": m.tokens,
            "split": m.has_region,
        },
        "findings": [
            {"code": f.code, "severity": f.severity, "message": f.message}
            for f in findings
        ],
    }


def _n(value: float, decimals: int = 0) -> str:
    """Numero all'italiana: punto per le migliaia, virgola per i decimali."""
    whole, _, frac = f"{value:,.{decimals}f}".partition(".")
    whole = whole.replace(",", ".")
    return f"{whole},{frac}" if frac else whole


def _cost(path: Path, spawns: int, devs: int, price: float) -> int:
    """La dimensione di CLAUDE.md tradotta in una voce di bilancio.

    Il costo pieno, cioè il tetto: la cache dei prompt abbassa la cifra reale e
    non è misurabile da qui. Ogni assunzione viene stampata insieme al numero —
    un totale senza le sue ipotesi è un numero che nessuno può contestare.
    """
    m = _measure(path)
    if m is None:
        print(f"{path}: CLAUDE.md assente — niente da misurare")
        return 1

    per_day = m.tokens * spawns * devs
    daily = per_day / 1_000_000 * price
    persone = "persona" if devs == 1 else "persone"

    print(f"CLAUDE.md: {_n(m.total_words)} parole ≈ {_n(m.tokens)} token, pagati a ogni spawn.")
    if m.has_region:
        print(
            f"  di cui kernel {_n(m.kernel_words)} (con tetto) e progetto "
            f"{_n(m.project_words)} (senza)."
        )
    print(
        f"{_n(spawns)} spawn al giorno × {devs} {persone} = "
        f"{_n(per_day / 1_000_000, 1)} milioni di token al giorno di solo contesto comune."
    )
    print(
        f"A {_n(price, 2)} $/Mtok: {_n(daily, 2)} $ al giorno, "
        f"{_n(daily * WORKING_DAYS, 2)} $ al mese ({WORKING_DAYS} giorni lavorativi)."
    )
    print(
        "Costo pieno: la cache dei prompt lo abbassa. Prezzo di listino Claude Opus 5 "
        "(input) — cambialo con --price."
    )
    return 0


def _source_version() -> str | None:
    """La versione del sorgente da cui gira questo comando.

    È il riferimento del rapporto: senza, la divergenza non ha un verso e resta
    una distribuzione. Non si elegge a riferimento la versione più diffusa — la
    maggioranza non è un riferimento.
    """
    p = Path(__file__).resolve().parents[2] / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


def _print_survey(s) -> None:
    """Il rapporto in forma leggibile: prima i progetti, poi cosa se ne ricava.

    La riga per progetto serve a trovare quale sistemare; le due righe finali
    sono la risposta alla domanda che il singolo non si pone — quante versioni
    del metodo sono in giro.
    """
    if not s.projects:
        print("nessuna installazione trovata (cerco .claude/framework.json)")
        return

    width = max([len("progetto")] + [len(p.name) for p in s.projects])
    print(f"{len(s.projects)} installazioni\n")
    print(f"{'progetto':<{width}}  {'versione':<10} {'rilievi':<10} CLAUDE.md")
    for p in sorted(s.projects, key=lambda p: p.name):
        mark = " " if s.source_version in (None, p.version) else "!"
        counts = " ".join(
            part
            for part in (
                f"{p.errors}E" if p.errors else "",
                f"{p.warnings}W" if p.warnings else "",
                f"{p.notes}N" if p.notes else "",
            )
            if part
        ) or "-"
        size = "-" if p.measure is None else f"{_n(p.measure.tokens)} tok"
        print(f"{p.name:<{width}}  {p.version:<9}{mark} {counts:<10} {size}")

    giro = ", ".join(f"{v} ({n})" for v, n in s.versions.items())
    print(f"\nVersioni in giro: {giro}", end="")
    print(f" — sorgente a {s.source_version}" if s.source_version else "")
    drift = sum(1 for p in s.projects if p.drifted)
    err = sum(1 for p in s.projects if p.errors)
    print(
        f"Divergenti dal sorgente: {len(s.behind)} · con drift del kernel: {drift} · "
        f"con errori: {err}"
    )
    if s.behind:
        print(
            "Da riallineare con framework-sync --down: "
            + ", ".join(sorted(p.name for p in s.behind))
        )
