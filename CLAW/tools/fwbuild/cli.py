"""Entry point: python claw.py <command>, or python -m fwbuild <command>."""

import argparse
import dataclasses
import hashlib
import json
import sys
import tempfile
from pathlib import Path

from . import assemble, doctor, lifecycle, profile, report, settings, source

# The source this command runs from: every command that writes works on it.
FW = Path(__file__).resolve().parents[2]
PLANNED = ("install", "update", "uninstall")


def _force_utf8_stdout() -> None:
    """On Windows, Python's stdout uses the local code page (cp1252), which
    does not cover all the characters in the messages. Without this, a finding
    with an out-of-table character makes the command fail instead of printing
    it."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):
                pass


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    parser = argparse.ArgumentParser(
        prog="claw.py",
        description="Everyday: doctor. In a project, Claude Code's /claw does the rest.",
        epilog="Also: install, update, uninstall, report. "
        "`claw.py <command> --help` for any of them.",
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="command")

    d = sub.add_parser("doctor", help="check an installation (default: this folder)")
    d.add_argument("path", type=Path, nargs="?", default=Path("."))
    # A complete installation has no findings of any severity: --strict is that
    # rule made mechanical, for CI and for Step 6.
    # Notes — the warnings `claw.json` declares it accepts — do not make
    # it fail: they have been looked at once and the decision is written down.
    d.add_argument(
        "--strict", action="store_true", help="exit 1 even with warnings only"
    )
    d.add_argument("--json", action="store_true", help="findings and measures as JSON, for CI")

    r = sub.add_parser("report")
    r.add_argument("paths", type=Path, nargs="+")
    r.add_argument(
        "--depth", type=int, default=2, help="how many levels down to look for projects"
    )
    r.add_argument("--json", action="store_true", help="report as JSON, for CI")
    r.add_argument(
        "--strict", action="store_true", help="exit 1 if a project diverges or has findings"
    )

    i = sub.add_parser("install")
    i.add_argument("path", type=Path)
    i.add_argument("--profile", help="a profile in profiles/")
    i.add_argument("--agents", default="", help="extra agents, comma-separated")
    i.add_argument("--drop", default="", help="profile agents to leave out, comma-separated")
    i.add_argument("--guides", default="", help="extra guides under shared/, comma-separated")
    i.add_argument("--gateguard", action="store_true", help="add the optional hook")
    i.add_argument("--orchestration", default=assemble.DEFAULT_ORCHESTRATION)
    u = sub.add_parser(
        "update",
        description="bring an installation to this source and to the choices asked for",
    )
    u.add_argument("path", type=Path)
    u.add_argument("--add", default="", help="agents and guides (core/x.md) to add, comma-separated")
    u.add_argument("--remove", default="", help="agents and guides to remove, comma-separated")
    u.add_argument("--profile", help="a profile in profiles/")
    u.add_argument("--orchestration")
    u.add_argument("--gateguard", choices=("on", "off"))
    u.add_argument(
        "--keep-version",
        action="store_true",
        help="plan and apply in one call; refused if the source is at another version",
    )
    sub.add_parser("uninstall", description="remove the framework from a project").add_argument(
        "path", type=Path
    )
    for p in (i, *(sub.choices[n] for n in PLANNED[1:])):
        p.add_argument("--apply", action="store_true", help="run the plan saved by a previous call")
        p.add_argument("-y", "--yes", action="store_true", help="run it without asking")

    args = parser.parse_args(argv)

    if args.command in PLANNED:
        return _lifecycle(args)

    if args.command == "doctor":
        findings = doctor.check(args.path)
        # The exit code is decided on blocking findings only, and decided
        # **once**: `--json` is a format, not a posture. Computed after the
        # "no findings" branch, it would make a CI that adds the flag to a clean
        # installation exit 1.
        blocking = [f for f in findings if f.blocking]
        code = 1 if (args.strict and blocking) or any(
            f.severity == "ERROR" for f in findings
        ) else 0
        if args.json:
            print(json.dumps(_report(args.path, findings), ensure_ascii=False, indent=2))
            return code
        if not findings:
            print("OK — no findings")
            return code
        for f in findings:
            print(f"{f.severity:5} {f.code:17} {f.message}")
        if not blocking:
            print("OK — only waivers declared in claw.json")
        return code

    if args.command == "report":
        s = report.survey(args.paths, args.depth, _source_version())
        if args.json:
            print(json.dumps(report.as_dict(s), ensure_ascii=False, indent=2))
        else:
            _print_survey(s)
        return 1 if args.strict and not s.clean else 0
    return 0


def _measure(path: Path) -> doctor.Measure | None:
    """The measurement of an installation's CLAUDE.md, or None if absent.

    The missing file is not an error of this layer: the doctor already reports
    it as STATE_MISSING, and duplicating the message would give two entries for
    one fact.
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
    """A number with thousands separators, in the English convention."""
    return f"{value:,.{decimals}f}"


def _source_version() -> str | None:
    """The version of the source this command runs from.

    It is the report's reference: without it, divergence has no direction and
    stays a distribution. The most widespread version is not elected as a
    reference — the majority is not a reference.
    """
    p = Path(__file__).resolve().parents[2] / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


def _print_survey(s) -> None:
    """The report in readable form: the projects first, then what follows.

    The per-project row is for finding which one to fix; the last two lines are
    the answer to the question a single person does not ask — how many versions
    of the method are out there.
    """
    if not s.projects:
        print("no installation found (looking for .claude/claw.json)")
        return

    width = max([len("project")] + [len(p.name) for p in s.projects])
    print(f"{len(s.projects)} installations\n")
    print(f"{'project':<{width}}  {'version':<10} {'findings':<10} CLAUDE.md")
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

    spread = ", ".join(f"{v} ({n})" for v, n in s.versions.items())
    print(f"\nVersions out there: {spread}", end="")
    print(f" — source at {s.source_version}" if s.source_version else "")
    err = sum(1 for p in s.projects if p.errors)
    print(
        f"Diverging from the source: {len(s.behind)} · with errors: {err}"
    )
    if s.behind:
        print(
            "To realign, /claw update in: "
            + ", ".join(sorted(p.name for p in s.behind))
        )


def _confirm(yes: bool) -> bool | None:
    """The ok on a plan just printed: `--yes` gives it; at a terminal it is
    asked; without one — a skill, a script — there is nobody to ask, and
    `None` says so: the caller leaves the plan saved for `--apply`."""
    if yes:
        return True
    if not sys.stdin.isatty():
        return None
    try:
        answer = input("\napply? [Y/n] ").strip().lower()
    except EOFError:
        return None
    return answer in ("", "y", "yes", "s", "si", "sì")


def _csv(text: str | None) -> list[str]:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def _plan_file(prj: Path, mode: str) -> Path:
    key = hashlib.sha256(str(Path(prj).resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir(), f"claw-plan-{key}-{mode}.json")


def _lifecycle(args) -> int:
    """`install | update | uninstall`: without `--apply` the plan is printed and
    saved, bound to project, mode and source; with it, that plan runs — checked
    again against the tree, never one recomputed in its place — and the doctor
    closes. `update --keep-version` does both in one call, for a change that
    cannot move the project to another version."""
    prj, mode = args.path, args.command
    keep_version = getattr(args, "keep_version", False)
    plan = _plan_file(prj, mode)
    try:
        if keep_version:
            _same_version(prj)
        if not args.apply:
            ops, params = _plan(args)
            plan.write_text(
                json.dumps({
                    "project": str(Path(prj).resolve()), "mode": mode, "source": str(FW),
                    "params": params, "ops": [dataclasses.asdict(o) for o in ops],
                }),
                encoding="utf-8",
            )
            print(lifecycle.render(ops))
            for o in ops:
                if o.action == lifecycle.KEEP and o.reason:
                    print(f"{o.action:<11} {o.path} — {o.reason}")
            if not any(o.action != lifecycle.KEEP for o in ops):
                plan.unlink(missing_ok=True)
                print("nothing to do")
                return 0
            ok = True if keep_version else _confirm(args.yes)
            if ok is None:
                print(f'\nplan saved. To run it: python "<FW>/claw.py" {mode} "{prj}" --apply')
                return 0
            if not ok:
                print("nothing written")
                return 0
        data = json.loads(plan.read_text(encoding="utf-8")) if plan.is_file() else {}
        if (data.get("project"), data.get("mode"), data.get("source")) != (
            str(Path(prj).resolve()), mode, str(FW)
        ):
            raise ValueError(f"no {mode} plan saved for {prj} from this source: plan first")
        ops, params = [lifecycle.Operation(**d) for d in data["ops"]], data["params"]
        conflicts: list[str] = []
        if mode == "install":
            conflicts = lifecycle.apply_install(prj, FW, ops, params)
        elif mode == "update":
            conflicts = lifecycle.apply_update(prj, FW, ops, **params)
        else:
            lifecycle.apply_uninstall(prj, FW, ops)
        plan.unlink()
    except (ValueError, FileNotFoundError) as err:
        print(err)
        return 1
    if conflicts:
        print("settings.json: your value stays on " + ", ".join(conflicts))
    if mode == "uninstall":
        print(f"{mode}: done")
        return 0
    findings = doctor.check(prj)
    for f in findings:
        print(f"{f.severity:5} {f.code:17} {f.message}")
    print(f"{mode}: done — doctor " + ("OK" if not findings else f"{len(findings)} findings"))
    return 0


def _same_version(prj: Path) -> None:
    """`--keep-version` is for a change that does not move the project: another
    version means the plan carries a new release's files, and that is read in full."""
    recorded = (source.read_manifest(prj) or {}).get("version")
    ours = _source_version()
    if recorded != ours:
        raise ValueError(
            f"--keep-version: the project is at v{recorded}, the source at v{ours}: "
            "run update without it and read the plan"
        )


def _plan(args) -> tuple[list[lifecycle.Operation], dict]:
    prj = args.path
    if args.command == "uninstall":
        return lifecycle.plan_uninstall(prj, FW), {}
    if args.command == "update":
        params = {
            "add": _csv(args.add),
            "remove": _csv(args.remove),
            "profile_name": args.profile,
            "orchestration": args.orchestration,
            "gateguard": args.gateguard,
        }
        ops = lifecycle.plan_update(prj, FW, **params)
        print(lifecycle.update_summary(prj, FW, **params) + "\n")
        return ops, params
    names = sorted(p.stem for p in (FW / "profiles").glob("*.toml"))
    if args.profile not in names:
        raise ValueError(f"--profile is one of: {', '.join(names)}")
    prof = profile.load(FW / "profiles" / f"{args.profile}.toml")
    roster = profile.roster(prof, _csv(args.agents), _csv(args.drop))
    unknown = [n for n in roster if not (FW / source.CARDS_DIR / f"{n}.md").is_file()]
    if unknown:
        raise ValueError(f"no such agent: {', '.join(unknown)}")
    clash = profile.check_exclusive(roster)
    if clash:
        raise ValueError(f"agents that do not coexist: {', '.join(clash)}")
    assemble.orchestration_file(FW, args.orchestration)
    params = {
        "profile": prof.name,
        "orchestration": args.orchestration,
        "agents": roster,
        "guides": profile.guides(FW, prof, roster, _csv(args.guides)),
        "hooks": [h for h in settings.HOOKS if args.gateguard or h not in settings.OPTIONAL_HOOKS],
    }
    ops = lifecycle.plan_install(prj, FW, params)
    print(
        f"profile {prof.name} · orchestration {args.orchestration} · hooks "
        f"{', '.join(params['hooks'])}\nagents: {', '.join(roster)}\n"
        f"guides: {', '.join(params['guides'])}\n"
    )
    return ops, params
