"""The integrity checks of an installation.

Twenty finding codes: eight of severity ERROR (PLACEHOLDER, ROSTER_MISSING,
SHARED_MISSING, STATE_MISSING, KERNEL_MISSING, FABLE, EXCLUSIVE,
MANIFEST_MISSING) and twelve of severity WARN (ROSTER_ORPHAN, KERNEL_DRIFT,
COORDINATOR_LEAK, SKILLS_MISSING, VERSION_MISMATCH, SETTINGS_MISSING,
SHARED_ORPHAN, TOKEN_BUDGET, REPORT_FORMAT, ACCEPTED_UNUSED, UNSAFE_UNICODE,
PERSONAL_PATH). MANIFEST_MISSING
is the only one that comes out at both: ERROR if the file is missing, WARN if it
is incomplete.
Every code is explained, with what to do about it, in the `framework-doctor`
skill.

A third severity, NOTE, is not produced here: it is a WARN the project has
declared it accepts in `framework.json`. It stays printed — an invisible waiver
is a forgotten waiver — but it does not make `--strict` fail.
"""

import re
from dataclasses import dataclass
from pathlib import Path

from . import assemble, kernel, profile, source

# One marker only, and deliberately not `{{...}}`: that is the template syntax
# of half the world (Vue, Angular, Jinja, Handlebars), and a project naming it
# among its own constraints would get an ERROR with no way out.
PLACEHOLDER_RE = re.compile(r"TO FILL IN")
# The superseded report format: confidence **as** a percentage, that is `CONF:`
# followed by a placeholder with `%` (`<0-100%>`) or by a digit. A project
# installed with that format keeps it until it goes through `framework-sync
# --down`: no other check sees it, because the kernel hash matches that text. The value must be the percentage: `CONF: HIGH — 80% coverage` is a
# categorical judgement quoting a number in its reason, and it is legitimate
# text the pattern must not touch.
CONF_PERCENT_RE = re.compile(r"CONF:\s*(?:<[^>\n]*%|\d[^%\n]*%)")
ROUTING_AGENT_RE = re.compile(r"^\|[^|]*\|\s*`([a-z-]+)`\s*\|", re.MULTILINE)
FABLE_RE = re.compile(r"^model:\s*fable\s*$", re.MULTILINE)
SHARED_REF_RE = re.compile(r"\.claude/shared/([A-Za-z0-9_./-]+\.md)")
# Characters the model reads and whoever reviews the file does not see:
# bidirectional controls, zero-width spaces, invisible operators, fillers, the
# tag block (the vehicle of "ASCII smuggling"). Variation selectors
# U+FE00-FE0F and U+E0100-E01EF are out: they compose emoji, and U+FE0F sits
# in the source itself. U+FEFF counts only past offset 0: at the start of a
# file it is the BOM editors write, and the lookbehind on any character
# excludes it there. Escapes only: the source scans itself.
UNSAFE_CHARS_RE = re.compile(
    r"[\u200B-\u200D\u2060-\u2064\u202A-\u202E\u2066-\u2069"
    r"\u115F\u1160\u180E\u3164\U000E0000-\U000E007F]"
    r"|(?<=[\s\S])\uFEFF"
)
# A user's folder: Windows (doubled JSON backslashes included), macOS, Linux.
# Template placeholder names do not count, in any case, and neither do the
# shared folders every machine has. On Windows `Users` ignores case: the file
# system does not distinguish it.
PERSONAL_PATH_RE = re.compile(
    r"(?:[A-Za-z]:[\\/]+(?i:users)[\\/]+|/Users/|/home/)"
    r"(?!(?i:example|me|user|username|you|yourname|yourusername|your-username"
    r"|public|shared|default|all users)"
    r"(?![A-Za-z0-9._-]))"
    r"[A-Za-z][A-Za-z0-9._-]*"
)
STATE_FILES = ("TODO.md", "status.md", "roadmap.md")
# The skills every installation receives. One single list: duplicating it in
# the tooling and in the tests means adding one and discovering from the red
# where the copies were.
LIFECYCLE_SKILLS = ("framework-doctor", "framework-sync", "framework-memory")
ORCHESTRATION = "shared/orchestration.md"
# Where the uninstall moves what the project had adapted, keeping the relative
# path.
ARCHIVE_DIR = Path(".claude") / "framework-archive"

# Titles that belong to the coordinator's guide. If they reappear in
# CLAUDE.md, every subagent pays for them at every spawn without being able to
# use them: it is the separation by recipient being lost again.
COORDINATOR_ONLY = (
    "Token economy — the ten rules of delegation",
    "The code cycle",
    "How to write a delegation prompt",
    "State that keeps itself up to date",
    "Choosing between agents that look close",
    "This project's roster",
    "Orchestration: orchestrator and worker",
    "Orchestration: Agent teams",
)


def _source_version() -> str | None:
    """The source's version, deduced from the package's position.

    `fwbuild` lives in the source's `tools/` directory: the root is two levels
    up. The source directory's name is not assumed anywhere. If it is not
    reachable the check is skipped — the doctor must stay usable without the
    source.
    """
    p = Path(__file__).resolve().parents[2] / "VERSION"
    return p.read_text(encoding="utf-8").strip() if p.is_file() else None


# Estimate: no tokeniser is in the stdlib and the doctor runs offline. The
# ratio comes from a measurement taken once on an assembled CLAUDE.md (1598
# words ≈ 2.1k tokens): it fixes the ratio, it does not describe the current
# file, which changes with every edit to the method. The exact number is given
# by the count_tokens endpoint, not by this tool: here an order of magnitude is
# what is needed.
TOKENS_PER_WORD = 1.33


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    message: str

    @property
    def blocking(self) -> bool:
        """Whether it counts for `--strict`. A declared note does not: it has
        already been looked at."""
        return self.severity != "NOTE"


@dataclass(frozen=True)
class Measure:
    """The installed CLAUDE.md, split into the two parts that compose it.

    `kernel` is written by the framework and has a ceiling that breaks the
    build at source stage; `project` is written by whoever installs and has no
    ceiling at all. It is the only one of the two that grows, because it grows
    with the project.
    """

    kernel_words: int
    project_words: int
    has_region: bool

    @property
    def total_words(self) -> int:
        return self.kernel_words + self.project_words

    @property
    def tokens(self) -> int:
        return round(self.total_words * TOKENS_PER_WORD)


def measure(claude_text: str) -> Measure:
    """Measures a CLAUDE.md, separating kernel region and project sections.

    Without markers — an installation without tracking, which is legitimate —
    the two parts are not distinguishable: the total is reported and the
    absence of the split is declared, instead of attributing everything to one
    of the two and firing a finding on a healthy installation.
    """
    region = kernel.parse(claude_text)
    if region is None:
        return Measure(len(claude_text.split()), 0, has_region=False)
    outside = claude_text[: region.start] + claude_text[region.end :]
    return Measure(len(region.body.split()), len(outside.split()), has_region=True)


def _markdown_files(root: Path) -> list[Path]:
    """The files adapted to the project, which have to be checked.

    `.claude/skills/` is excluded: the skills are framework files copied
    verbatim, with no kernel region and no blocks to fill in — and
    `framework-doctor` necessarily contains the string `TO FILL IN`, because it
    explains that finding. The state files in `docs/` are included: they are
    born from a template with placeholders, and an unfilled template is
    indistinguishable from absent state for whoever reads it at session start.

    The uninstall archive is excluded: it keeps the cards as they were,
    placeholders and pointers included, and it is material to consult.
    """
    files = [root / "CLAUDE.md"]
    claude_dir = root / ".claude"
    if claude_dir.is_dir():
        skipped = (claude_dir / "skills", root / ARCHIVE_DIR)
        files += sorted(
            p
            for p in claude_dir.rglob("*.md")
            if not any(d in p.parents for d in skipped)
        )
    files += [root / "docs" / name for name in STATE_FILES]
    return [f for f in files if f.is_file()]


def _scanned_files(root: Path) -> list[Path]:
    """The files in which to look for invisible characters and personal paths.

    Wider than `_markdown_files`: skills and hooks are copied verbatim, but a
    hidden character in a skill is exactly the vehicle being looked for, and a
    personal path gets there the same way. **Never `framework.json`:** its
    `source` is absolute by construction when the source sits outside the
    project, and flagging it would give a warning on every installation made
    that way.
    """
    claude_dir = root / ".claude"
    files = _markdown_files(root)
    files += sorted((claude_dir / "skills").rglob("*.md"))
    files += sorted((claude_dir / "hooks").glob("*.py"))
    files.append(claude_dir / "settings.json")
    return [f for f in files if f.is_file()]


def check(root: Path) -> list[Finding]:
    root = Path(root)
    out: list[Finding] = []
    claude_md = root / "CLAUDE.md"
    if not claude_md.is_file():
        return [Finding("STATE_MISSING", "ERROR", "CLAUDE.md absent")]

    agents_dir = root / ".claude" / "agents"
    present = {p.stem for p in agents_dir.glob("*.md")} if agents_dir.is_dir() else set()

    # The files that are born **with** a kernel region. The guides in `shared/`
    # are not: they are copied and filled in, they contain no generated method.
    tracked = {"CLAUDE.md", f".claude/{ORCHESTRATION}"} | {
        f".claude/agents/{name}.md" for name in present
    }

    texts = {
        f.relative_to(root).as_posix(): f.read_text(encoding="utf-8")
        for f in _markdown_files(root)
    }
    claude_text = texts["CLAUDE.md"]
    versions: dict[str, str] = {}
    referenced: set[str] = set()

    # The variant without markers is legitimate: no tracking, by choice. But if
    # even a single tracked file has them, the installation is tracked, and a
    # file that lost them is indistinguishable from one rewritten by hand.
    markers = any(kernel.parse(t) for rel, t in texts.items() if rel in tracked)

    for rel, text in texts.items():
        if PLACEHOLDER_RE.search(text):
            out.append(
                Finding("PLACEHOLDER", "ERROR", f"{rel}: placeholder not filled in")
            )
        if FABLE_RE.search(text):
            out.append(Finding("FABLE", "ERROR", f"{rel}: model fable not available"))
        if CONF_PERCENT_RE.search(text):
            out.append(
                Finding(
                    "REPORT_FORMAT",
                    "WARN",
                    f"{rel}: report schema with confidence as a percentage — "
                    "superseded format, realign with framework-sync --down",
                )
            )
        status = kernel.verify(text)
        if status == "DRIFT":
            out.append(
                Finding("KERNEL_DRIFT", "WARN", f"{rel}: kernel region modified")
            )
        elif status == "MISSING" and markers and rel in tracked:
            out.append(
                Finding(
                    "KERNEL_MISSING",
                    "ERROR",
                    f"{rel}: markers removed — the method is no longer verifiable",
                )
            )
        if rel in tracked:
            region = kernel.parse(text)
            if region is not None:
                versions[rel] = region.version
        # The pointer is checked everywhere, not only in CLAUDE.md: the guides
        # are cited by the agents, and that is where almost all pointers live.
        for ref in sorted(set(SHARED_REF_RE.findall(text))):
            referenced.add(ref)
            if not (root / ".claude" / "shared" / ref).is_file():
                out.append(
                    Finding(
                        "SHARED_MISSING",
                        "ERROR",
                        f"{rel} → .claude/shared/{ref}: referenced but absent",
                    )
                )

    # The routing table is coordinator content: it lives in its guide. We fall
    # back to CLAUDE.md only where that guide is absent (partial installation,
    # or project without delegation), so the roster stays verifiable.
    routed = set(ROUTING_AGENT_RE.findall(texts.get(f".claude/{ORCHESTRATION}", claude_text)))

    for name in sorted(routed - present):
        out.append(
            Finding(
                "ROSTER_MISSING",
                "ERROR",
                f"{name}: cited in the routing table, file absent",
            )
        )
    for name in sorted(present - routed):
        out.append(
            Finding(
                "ROSTER_ORPHAN",
                "WARN",
                f"{name}: file present, absent from the routing table",
            )
        )

    # The versions: first against each other, then against the source. No other
    # check sees them — on an old method the hash matches, because it matches
    # the old one. It is the fork between projects, that is, the defect the
    # framework exists to avoid.
    declared = sorted(set(versions.values()))
    if len(declared) > 1:
        common = max(declared, key=list(versions.values()).count)
        odd = sorted(rel for rel, v in versions.items() if v != common)
        out.append(
            Finding(
                "VERSION_MISMATCH",
                "WARN",
                f"project at v{common}, but: "
                + ", ".join(f"{rel} v{versions[rel]}" for rel in odd),
            )
        )
    # Not `source`: the module of the same name is used further down, and
    # shadowing it here is exactly how such a mistake stays hidden until the
    # first use.
    source_version = _source_version()
    if source_version is not None and declared and declared != [source_version]:
        out.append(
            Finding(
                "VERSION_MISMATCH",
                "WARN",
                f"installation at v{'/'.join(declared)}, source at v{source_version}: "
                "realign with framework-sync --down",
            )
        )

    # The inverse of SHARED_MISSING. A guide nobody cites is context installed
    # and never opened: the cost is there, the use is not.
    shared_dir = root / ".claude" / "shared"
    if shared_dir.is_dir():
        for p in sorted(shared_dir.rglob("*.md")):
            rel = p.relative_to(shared_dir).as_posix()
            if rel != "orchestration.md" and rel not in referenced:
                out.append(
                    Finding(
                        "SHARED_ORPHAN",
                        "WARN",
                        f".claude/shared/{rel}: installed and cited by nobody",
                    )
                )

    for conflict in profile.check_exclusive(sorted(present)):
        out.append(
            Finding("EXCLUSIVE", "ERROR", f"mutually exclusive agents: {conflict}")
        )

    for name in STATE_FILES:
        if not (root / "docs" / name).is_file():
            out.append(Finding("STATE_MISSING", "ERROR", f"docs/{name} absent"))

    manifest = source.read_manifest(root)
    if manifest is None:
        out.append(
            Finding(
                "MANIFEST_MISSING",
                "ERROR",
                ".claude/framework.json absent or unreadable: framework-sync cannot "
                "find the source and the fleet report does not see the project",
            )
        )
    else:
        gaps = [
            k
            for k in ("source", "version", "profile")
            if not isinstance(manifest.get(k), str) or not manifest[k].strip()
        ]
        if gaps:
            out.append(
                Finding(
                    "MANIFEST_MISSING",
                    "WARN",
                    f".claude/framework.json without {', '.join(gaps)}: "
                    "the installation no longer knows what it was born from",
                )
            )
        # The manifest's version is the only one readable without opening a
        # generated document: if it diverges from the markers, it declares a
        # version the project does not have.
        elif declared and manifest["version"].strip() not in declared:
            out.append(
                Finding(
                    "VERSION_MISMATCH",
                    "WARN",
                    f".claude/framework.json declares v{manifest['version'].strip()}, "
                    f"the markers say v{'/'.join(declared)}",
                )
            )

    for skill in LIFECYCLE_SKILLS:
        if not (root / ".claude" / "skills" / skill / "SKILL.md").is_file():
            out.append(
                Finding(
                    "SKILLS_MISSING",
                    "WARN",
                    f".claude/skills/{skill}/ absent: the skill is not invocable "
                    "in this project",
                )
            )

    if present and not (root / ".claude" / "settings.json").is_file():
        out.append(
            Finding(
                "SETTINGS_MISSING",
                "WARN",
                ".claude/settings.json absent: the profile's permissions are not "
                "in force. They cover the Read tool, not the shell — `Bash(cat "
                ".env)` remains possible, and no file prevents it",
            )
        )

    if present and f".claude/{ORCHESTRATION}" not in texts:
        out.append(
            Finding(
                "SHARED_MISSING",
                "ERROR",
                f".claude/{ORCHESTRATION} absent: without it, the coordinator has "
                "no delegation rules",
            )
        )

    # The source ceiling constrains what the framework writes. This looks at the
    # assembled file, which is what every spawn really pays for: the threshold
    # is the kernel itself — the only known quantity — that is, the project does
    # not write more than the method. WARN and not ERROR: it would break a
    # project's build.
    #
    # Below the ceiling the framework sets itself for the method alone the
    # finding stays silent: on a small file the ratio is true and irrelevant,
    # and a warning about eleven tokens is noise.
    m = measure(claude_text)
    if (
        m.has_region
        and m.total_words >= assemble.METHOD_WORD_BUDGET
        and m.project_words > m.kernel_words
    ):
        out.append(
            Finding(
                "TOKEN_BUDGET",
                "WARN",
                f"CLAUDE.md: {m.project_words} project words against "
                f"{m.kernel_words} of kernel — {m.total_words} in all, "
                f"≈{m.tokens} tokens paid at every spawn",
            )
        )

    for heading in COORDINATOR_ONLY:
        if heading in claude_text:
            out.append(
                Finding(
                    "COORDINATOR_LEAK",
                    "WARN",
                    f'CLAUDE.md contains "{heading}": it is coordinator content, '
                    f"paid by every subagent at every spawn",
                )
            )

    # One finding per file, at the first occurrence: enough to open it. The
    # path found is not printed — it is the name of whoever wrote it. The user's
    # skills and hooks may not be UTF-8: here they are only scanned, and an
    # unreadable byte must not stop the doctor or `fwbuild report`.
    for f in _scanned_files(root):
        rel = f.relative_to(root).as_posix()
        text = texts[rel] if rel in texts else f.read_text(encoding="utf-8", errors="replace")
        hidden = UNSAFE_CHARS_RE.search(text)
        if hidden:
            line = text.count("\n", 0, hidden.start()) + 1
            out.append(
                Finding(
                    "UNSAFE_UNICODE",
                    "WARN",
                    f"{rel}:{line}: invisible character U+{ord(hidden.group()):04X}"
                    " — the model reads it, whoever reviews the file does not",
                )
            )
        personal = PERSONAL_PATH_RE.search(text)
        if personal:
            line = text.count("\n", 0, personal.start()) + 1
            out.append(
                Finding(
                    "PERSONAL_PATH",
                    "WARN",
                    f"{rel}:{line}: path inside a user's folder — "
                    "it does not exist on the machine of whoever clones",
                )
            )

    return _apply_accepted(root, out)


def _match(finding: Finding, keys: list[str]) -> str | None:
    """The waiver covering this finding, most specific first.

    `CODE` covers every finding with that code; `CODE:fragment` only those whose
    message contains the fragment — usually a path.
    """
    for key in keys:
        code, _, fragment = key.partition(":")
        if code == finding.code and (not fragment or fragment in finding.message):
            return key
    return None


def _apply_accepted(root: Path, findings: list[Finding]) -> list[Finding]:
    """Downgrades to NOTE the warnings the project declares it accepts.

    **Errors cannot be accepted.** A warning is a judgement — "this file is
    large", "nobody cites this guide" — and on a judgement a project may be right
    against the default. An error is an installation that does not work: an
    unfilled placeholder or a broken pointer stay broken even if somebody writes
    that they are fine.

    A waiver covering nothing becomes a warning itself: it would stay in the file
    after its finding is gone, and next time it would silence something else. The
    same holds for one written without a reason, which does not apply: vanishing
    silently is how a rule stops existing without anyone seeing it.
    """
    rules = source.accepted(root)
    if not rules:
        return findings
    keys = sorted(rules, key=lambda k: (":" not in k, k))
    used: set[str] = set()
    refused: set[str] = set()
    out: list[Finding] = []
    for f in findings:
        key = _match(f, keys)
        if key is None or not rules[key]:
            out.append(f)
        elif f.severity == "ERROR":
            refused.add(key)
            out.append(f)
        else:
            used.add(key)
            out.append(Finding(f.code, "NOTE", f"{f.message} — accepted: {rules[key]}"))
    for key in keys:
        if key in used:
            continue
        why = (
            "no reason written, so it does not apply"
            if not rules[key]
            else "covers an ERROR, and errors cannot be accepted"
            if key in refused
            else "no finding matches"
        )
        out.append(
            Finding("ACCEPTED_UNUSED", "WARN", f'framework.json accepts "{key}": {why}')
        )
    return out
