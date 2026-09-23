"""Entry point: python -m fwbuild <command>."""

import argparse
import json
import os
import sys
from pathlib import Path

from . import doctor, report, skills, source, upgrade

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


def _bases(path: Path | None) -> list[Path]:
    """The source search order. It is the impure part, and it is here on purpose.

    A path that was given is the **only** candidate: if it does not hold it is
    an error, not a fallback onto the next one.
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

    d = sub.add_parser("doctor", help="check an installation")
    d.add_argument("path", type=Path)
    # A complete installation has no findings of any severity: --strict is that
    # rule made mechanical, for CI and for Step 6.
    # Notes — the warnings `framework.json` declares it accepts — do not make
    # it fail: they have been looked at once and the decision is written down.
    d.add_argument(
        "--strict", action="store_true", help="exit 1 even with warnings only"
    )
    d.add_argument("--json", action="store_true", help="findings and measures as JSON, for CI")

    r = sub.add_parser("report", help="method divergence across several projects")
    r.add_argument("paths", type=Path, nargs="+")
    r.add_argument(
        "--depth", type=int, default=2, help="how many levels down to look for projects"
    )
    r.add_argument("--json", action="store_true", help="report as JSON, for CI")
    r.add_argument(
        "--strict", action="store_true", help="exit 1 if a project diverges or has findings"
    )

    s = sub.add_parser("source", help="resolve and validate the source root")
    s.add_argument("path", type=Path, nargs="?")

    k = sub.add_parser("skills", help="skill packages connected to the source")
    ks = k.add_subparsers(dest="skills_command", required=True)
    for name, help_text in (
        ("list", "connected packages, skills and pool"),
        ("add", "connect a repository, pinned to a commit"),
        ("remove", "disconnect a package"),
    ):
        p = ks.add_parser(name, help=help_text)
        if name == "add":
            p.add_argument("repo", help="repository URL or local folder")
            p.add_argument("--commit", help="commit to pin; without it, the branch tip")
        if name == "remove":
            p.add_argument("package", help="package name, as `skills list` prints it")
        p.add_argument("--source", type=Path, dest="path", help="source root")

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
        # Without the record, `--upgrade` takes the source to be intact and
        # replaces it with the release: what `--up` promoted is lost there.
        record = upgrade.read_record(root)
        if record is None:
            print("no upstream record: intact, updated by replacing it")
        else:
            print(
                f"modified with --up: base v{upgrade.base_version(root)}, "
                f"from {record.get('repo') or 'repo not declared'}"
            )
        return 0

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
            print("OK — only waivers declared in framework.json")
        return code

    if args.command == "report":
        s = report.survey(args.paths, args.depth, _source_version())
        if args.json:
            print(json.dumps(report.as_dict(s), ensure_ascii=False, indent=2))
        else:
            _print_survey(s)
        return 1 if args.strict and not s.clean else 0
    return 0


def _skills(args) -> int:
    """`skills list | add | remove`: the socket other people's skills plug into.

    It writes into the **source**, not into the projects: installations receive
    the packages at the next pass of `claw-sync`, like every other
    framework file. Saying it here avoids believing that an `add` has already
    changed something in the projects that are open.
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
                    "these already have a personal skill of the same name, which "
                    "wins over the project one: " + ", ".join(covered)
                )
            print(
                f"outside the pool: invocable by you, not by the coordinator. "
                f"To put them in the pool: skills/{skills.POOL_FILE}"
            )
            print("they reach projects with claw-sync --down or --repair")
            return 0
        if args.skills_command == "remove":
            gone = skills.remove(root, args.package)
            print(f"{args.package} disconnected: {', '.join(gone) or 'no skill'}")
            print("in projects it stays until you run claw-sync --uninstall or --down")
            return 0
        in_pool = set(skills.pool(root))
        packages = skills.packages(root)
        if not packages:
            print(f"no package connected in {root / 'skills'}")
            return 0
        for pkg in packages:
            print(f"{pkg.name} @ {pkg.commit[:7]} — {pkg.repo}")
            for name in pkg.skills:
                print(f"  {name:<30} {'pool' if name in in_pool else 'user only'}")
    except (ValueError, RuntimeError) as err:
        print(err)
        return 1
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
        print("no installation found (looking for .claude/framework.json)")
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
    drift = sum(1 for p in s.projects if p.drifted)
    err = sum(1 for p in s.projects if p.errors)
    print(
        f"Diverging from the source: {len(s.behind)} · with kernel drift: {drift} · "
        f"with errors: {err}"
    )
    if s.behind:
        print(
            "To realign with claw-sync --down: "
            + ", ".join(sorted(p.name for p in s.behind))
        )
