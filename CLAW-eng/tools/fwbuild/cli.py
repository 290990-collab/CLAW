"""Entry point: python claw.py <command>, or python -m fwbuild <command>."""

import argparse
import dataclasses
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

from . import assemble, doctor, lifecycle, master, profile, report, settings, skills, source, upgrade

# The source this command runs from: every command that writes works on it.
FW = Path(__file__).resolve().parents[2]
SKILLS_HOME = Path.home() / ".claude" / "skills"
PLANNED = ("install", "down", "repair", "uninstall")


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
    parser = argparse.ArgumentParser(prog="claw")
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

    i = sub.add_parser("install", help="install the framework in a project: plan, then --apply")
    i.add_argument("path", type=Path)
    i.add_argument("--profile", help="a profile in profiles/")
    i.add_argument("--agents", default="", help="extra agents, comma-separated")
    i.add_argument("--drop", default="", help="profile agents to leave out, comma-separated")
    i.add_argument("--guides", default="", help="extra guides under shared/, comma-separated")
    i.add_argument("--no-gateguard", action="store_true", help="leave out the optional hook")
    i.add_argument("--orchestration", default=assemble.DEFAULT_ORCHESTRATION)
    for name, help_text in (
        ("down", "bring this source's version into a project"),
        ("repair", "put back what an installation is missing"),
        ("uninstall", "remove the framework from a project"),
    ):
        p = sub.add_parser(name, help=f"{help_text}: plan, then --apply")
        p.add_argument("path", type=Path)
        if name == "down":
            p.add_argument("--hooks", help="hooks to have afterwards; default: those in use")
            p.add_argument("--adopt", default="", help="cards taking the source's front matter, or all")
    for p in (i, *(sub.choices[n] for n in PLANNED[1:])):
        p.add_argument("--apply", action="store_true", help="run the saved plan")
    st = sub.add_parser("status", help="source and project versions, and what changed")
    st.add_argument("path", type=Path, nargs="?")
    for name, help_text in (
        ("setup", "install the user-level skills from this source"),
        ("upgrade", "merge the master's tracked branch"),
    ):
        p = sub.add_parser(name, help=f"{help_text}: plan, then --apply")
        p.add_argument("--apply", action="store_true")

    args = parser.parse_args(argv)

    if args.command in PLANNED:
        return _lifecycle(args)
    if args.command == "status":
        return _status(args.path)
    if args.command == "setup":
        return _setup(args.apply)
    if args.command == "upgrade":
        return _upgrade(args.apply)
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


def _claw() -> str:
    return f'python "{FW.as_posix()}/claw.py"'


def _csv(text: str | None) -> list[str]:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def _plan_file(prj: Path, mode: str) -> Path:
    key = hashlib.sha256(str(Path(prj).resolve()).encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir(), f"claw-plan-{key}-{mode}.json")


def _lifecycle(args) -> int:
    """`install | down | repair | uninstall`: without `--apply` the plan is
    printed and saved, bound to project, mode and source; with it, that plan
    runs — never one recomputed — and the doctor closes."""
    prj, mode = args.path, args.command
    plan = _plan_file(prj, mode)
    try:
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
            print(f'\nplan saved. To run it: {_claw()} {mode} "{prj}" --apply')
            return 0
        data = json.loads(plan.read_text(encoding="utf-8")) if plan.is_file() else {}
        if (data.get("project"), data.get("mode"), data.get("source")) != (
            str(Path(prj).resolve()), mode, str(FW)
        ):
            raise ValueError(f"no {mode} plan saved for {prj} from this source: plan first")
        ops, params = [lifecycle.Operation(**d) for d in data["ops"]], data["params"]
        if mode == "install":
            conflicts, to_fill = lifecycle.apply_install(prj, FW, ops, **params)
            if conflicts:
                print("settings.json: your value stays on " + ", ".join(conflicts))
            print("to fill in, then doctor --strict:\n  " + "\n  ".join(to_fill))
        elif mode == "down":
            lifecycle.apply_down(prj, FW, ops, params["adopt"])
        elif mode == "repair":
            lifecycle.apply_update(prj, FW, ops)
        else:
            lifecycle.apply_uninstall(prj, FW, ops)
        plan.unlink()
    except (ValueError, FileNotFoundError) as err:
        print(err)
        return 1
    if mode in ("install", "uninstall"):
        print(f"{mode}: done")
        return 0
    findings = doctor.check(prj)
    for f in findings:
        print(f"{f.severity:5} {f.code:17} {f.message}")
    print(f"{mode}: done — doctor " + ("OK" if not findings else f"{len(findings)} findings"))
    return 0


def _plan(args) -> tuple[list[lifecycle.Operation], dict]:
    prj = args.path
    if args.command == "down":
        params = {
            "hooks": None if args.hooks is None else _csv(args.hooks),
            "adopt": _csv(args.adopt),
        }
        return lifecycle.plan_down(prj, FW, params["hooks"], params["adopt"]), params
    if args.command == "repair":
        return lifecycle.plan_repair(prj, FW), {}
    if args.command == "uninstall":
        return lifecycle.plan_uninstall(prj, FW), {}
    names = sorted(p.stem for p in (FW / "profiles").glob("*.toml"))
    if args.profile not in names:
        raise ValueError(f"--profile is one of: {', '.join(names)}")
    prof = profile.load(FW / "profiles" / f"{args.profile}.toml")
    roster = profile.roster(prof, _csv(args.agents), _csv(args.drop))
    unknown = [n for n in roster if not (FW / "agents" / f"{n}.md").is_file()]
    if unknown:
        raise ValueError(f"no such agent: {', '.join(unknown)}")
    clash = profile.check_exclusive(roster)
    if clash:
        raise ValueError(f"agents that do not coexist: {', '.join(clash)}")
    assemble.orchestration_file(FW, args.orchestration)
    params = {
        "profile_name": prof.name,
        "roster": roster,
        "guides": profile.guides(FW, prof, roster, _csv(args.guides)),
        "hooks": [h for h in settings.HOOKS if not (args.no_gateguard and h == "gateguard")],
        "orchestration": args.orchestration,
    }
    print(
        f"profile {prof.name} · orchestration {args.orchestration} · hooks "
        f"{', '.join(params['hooks'])}\nagents: {', '.join(roster)}\n"
        f"guides: {', '.join(params['guides'])}\n"
    )
    ops = lifecycle.plan_install(
        prj, lifecycle.targets(FW, roster, params["guides"], params["hooks"])
    )
    return ops, params


def _status(path: Path | None) -> int:
    """Where the source stands against its branch, and a project against the source."""
    version = (FW / "VERSION").read_text(encoding="utf-8").strip()
    clone = master.is_clone(FW)
    print(f"source   {FW} v{version}")
    if not clone:
        print("         not a git clone: upgraded by replacing it (claw-sync --upgrade)")
    elif not master.upstream(FW):
        print("         git clone with no tracked branch")
    else:
        behind = len(master.lines(FW, "rev-list", "HEAD..@{u}"))
        ahead = len(master.lines(FW, "rev-list", "@{u}..HEAD"))
        local = len(master.lines(FW, "status", "--porcelain", "--", "."))
        print(
            f"         {master.upstream(FW)}: {behind} behind, {ahead} ahead as of the last "
            f"fetch · {local} uncommitted changes"
        )
    if path is None:
        return 0
    data = source.read_manifest(path)
    if data is None:
        print(f"project  {path}: not installed")
        return 1
    findings = doctor.check(path)
    counts = " ".join(
        f"{sum(1 for f in findings if f.severity == s)}{s[0]}"
        for s in ("ERROR", "WARN", "NOTE")
        if any(f.severity == s for f in findings)
    )
    installed = data.get("version")
    print(f"project  {path} v{installed} · doctor {counts or 'OK'}")
    if installed == version:
        return 0
    commits = master.since(FW, str(installed)) if clone else None
    if commits is None:
        print(f"         v{installed} → v{version}: no commit declares v{installed}")
    else:
        print(f"         v{installed} → v{version}, {len(commits)} commits:")
        for c in commits:
            print(f"           {c}")
    print(f'         to bring it up: {_claw()} down "{path}"')
    return 0


def _setup(apply: bool) -> int:
    gaps = source.missing(FW)
    if gaps:
        print(f"{FW} is not a complete source: missing {', '.join(gaps)}")
        return 1
    if not apply:
        for action, folder in master.skill_plan(FW, SKILLS_HOME):
            print(f"{action:<11} {folder}")
        print(f"<FW> written as {FW.as_posix()}")
        if not master.is_clone(FW):
            print("not a git clone: `upgrade` will not work on this source")
        print(f"\nto run it: {_claw()} setup --apply")
        return 0
    master.install_skills(FW, SKILLS_HOME)
    print(f"setup: done — /claw-install in a project installs the framework from {FW}")
    return 0


def _upgrade(apply: bool) -> int:
    """The master up to its tracked branch: what arrives is shown, then merged."""
    try:
        if not master.is_clone(FW) or not master.upstream(FW):
            print("not a git clone with a tracked branch: claw-sync --upgrade")
            return 1
        master.git(FW, "fetch", "--quiet")
        incoming = master.lines(FW, "log", "--oneline", "HEAD..@{u}")
        local = master.lines(FW, "status", "--porcelain")
        if not apply:
            print(f"{len(incoming)} incoming commits:")
            for c in incoming:
                print(f"  {c}")
            if local:
                print(f"{len(local)} uncommitted changes: commit them (they are promotions) first")
            print(
                f"\nthen the user-level skills are refreshed. To run it: {_claw()} upgrade --apply"
            )
            return 0
        if local:
            print("uncommitted changes in the master, nothing merged: commit or discard them")
            return 1
        conflicts = master.merge(FW)
    except RuntimeError as err:
        print(err)
        return 1
    if conflicts:
        print("conflicts, the merge is left open: resolve them, then git commit\n  "
              + "\n  ".join(conflicts))
        return 1
    master.install_skills(FW, SKILLS_HOME)
    version = (FW / "VERSION").read_text(encoding="utf-8").strip()
    print(f"upgrade: done — source at v{version}. Projects: {_claw()} status <project>")
    return 0
