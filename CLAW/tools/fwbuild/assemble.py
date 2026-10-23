"""Assembly of the installable artefacts.

The generated method lives inside the kernel region; front matter and project
blocks stay outside, because they are the surface the user adapts.
"""

import re
import tomllib
from collections.abc import Sequence
from pathlib import Path

from . import kernel, profile
from .rules import Rules
from .source import CARDS_DIR, STYLES_DIR

METHOD_HEADING = "## Method"
DOMAIN_HEADING = "## Project context"

# The two source ceilings, in words. They are real tests — the build fails
# above the threshold — and they live here because the doctor reads them too:
# the `TOKEN_BUDGET` finding stays silent until the assembled file reaches at
# least the ceiling the framework sets itself for the method alone.
METHOD_WORD_BUDGET = 2000
COORDINATOR_WORD_BUDGET = 3800

# The orchestration of whoever does not choose one.
DEFAULT_ORCHESTRATION = "orchestrator-worker"

# The frontmatter keys generated from `cards/agents.toml`; name and description stay in the card.
CARD_KEYS = ("model", "effort", "maxTurns", "tools", "color")
REQUIRED_CARD_KEYS = ("model", "effort", "tools", "color")


def read_method(method_dir: Path, extra: Sequence[Path] = ()) -> str:
    """Concatenates the modules of a method folder, in file-name order.

    `extra` appends files chosen by the profile — the domain cycles — after the
    fixed modules: they are method content to all intents and purposes, but not
    every project wants them.
    """
    parts = [
        p.read_text(encoding="utf-8")
        for p in sorted(method_dir.glob("*.md"), key=lambda p: p.name)
    ]
    parts += [p.read_text(encoding="utf-8") for p in extra]
    return kernel.normalize("\n".join(parts))


def build_document_from_text(
    method: str,
    version: str,
    project_sections: str,
    *,
    markers: bool = True,
) -> str:
    head = kernel.wrap(method, version) if markers else kernel.normalize(method)
    return f"{head}\n{kernel.normalize(project_sections)}"


def build_document(
    method_dir: Path,
    version: str,
    project_sections: str,
    *,
    markers: bool = True,
    extra: Sequence[Path] = (),
) -> str:
    return build_document_from_text(
        read_method(method_dir, extra), version, project_sections, markers=markers
    )


def cycle_files(framework_root: Path, names: Sequence[str]) -> list[Path]:
    """Resolves the cycles a profile declares into files in `cycles/`.

    A declared but non-existent cycle is a configuration error, not a field to
    ignore: if it passed silently, the profile would promise a method the
    project does not receive.
    """
    out = []
    for name in names:
        p = framework_root / "cycles" / f"{name}.md"
        if not p.is_file():
            raise FileNotFoundError(f"cycle declared but absent: cycles/{name}.md")
        out.append(p)
    return out


def installed_cycles(region_body: str, framework_root: Path) -> list[Path]:
    """The domain cycles already present in an installed kernel region.

    A project does not record which profile it was born from: reassembling from
    `coordinator/` without this would silently delete them at every `down`,
    and no doctor finding would see it. They are recognised by their first
    heading.
    """
    out = []
    for p in sorted((framework_root / "cycles").glob("*.md")):
        heading = p.read_text(encoding="utf-8").lstrip().splitlines()[0]
        if heading and heading in region_body:
            out.append(p)
    return out


def orchestration_file(framework_root: Path, name: str) -> Path:
    """Resolves the chosen orchestration into a file in `orchestrations/`.

    As with cycles: a name that does not exist, passed silently, would leave the
    coordinator's guide without a delegation model, and no finding would see it.
    """
    p = framework_root / "orchestrations" / f"{name}.md"
    if not p.is_file():
        raise FileNotFoundError(
            f"orchestration declared but absent: orchestrations/{name}.md"
        )
    return p


def installed_orchestration(region_body: str, framework_root: Path) -> Path:
    """The orchestration already present in an installed kernel region.

    Same reason as `installed_cycles`, same recognition by first heading. The
    project has exactly one: none recognised usually means a heading renamed in
    the source, and falling back on the default would silently rewrite the
    wrong model; two are not a choice to guess.
    """
    found = []
    for p in sorted((framework_root / "orchestrations").glob("*.md")):
        heading = p.read_text(encoding="utf-8").lstrip().splitlines()[0]
        if heading and heading in region_body:
            found.append(p)
    if not found:
        raise ValueError(
            "no orchestration recognised in the region: choose one and pass it "
            "with assemble.orchestration_file"
        )
    if len(found) > 1:
        names = ", ".join(p.stem for p in found)
        raise ValueError(f"more than one orchestration in the region: {names}")
    return found[0]


def build_agent(
    frontmatter: str,
    method_body: str,
    domain_block: str,
    version: str,
    *,
    markers: bool = True,
) -> str:
    body = kernel.wrap(method_body, version) if markers else kernel.normalize(method_body)
    return f"{kernel.normalize(frontmatter)}\n{body}\n{kernel.normalize(domain_block)}"


def split_source(text: str) -> tuple[str, str, str]:
    """Splits an agent source into (front matter, method, domain block).

    The front matter is delimited on the first two '---' at line start, not on
    a global split: a '---' used as a horizontal rule in the body must not
    break the parsing.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("source without front matter")
    close = next(
        (i for i in range(1, len(lines)) if lines[i].strip() == "---"), None
    )
    if close is None:
        raise ValueError("front matter not closed")
    frontmatter = "\n".join(lines[: close + 1]) + "\n"
    rest = "\n".join(lines[close + 1 :])

    if METHOD_HEADING not in rest:
        raise ValueError(f"missing the {METHOD_HEADING!r} section")
    if DOMAIN_HEADING not in rest:
        raise ValueError(f"missing the {DOMAIN_HEADING!r} section")
    m_at = rest.index(METHOD_HEADING)
    d_at = rest.index(DOMAIN_HEADING)
    if d_at < m_at:
        raise ValueError(f"{DOMAIN_HEADING} precedes {METHOD_HEADING}")
    return frontmatter, rest[m_at:d_at], rest[d_at:]


def agent_rows(framework_root: Path) -> dict[str, dict[str, str | int]]:
    """The calibration row of each agent, from `cards/agents.toml`.

    Rows and cards must match one to one: a row without a card, or a card
    without a row, would leave an agent calibrated by nobody.
    """
    text = (framework_root / CARDS_DIR / "agents.toml").read_text(encoding="utf-8")
    rows = tomllib.loads(text)
    for name, row in rows.items():
        for key, value in row.items():
            if key not in CARD_KEYS:
                raise ValueError(f"agents.toml [{name}]: unknown key {key!r}")
            if isinstance(value, bool) or not isinstance(value, (str, int)):
                raise ValueError(f"agents.toml [{name}]: {key} must be a string or an integer")
        for key in REQUIRED_CARD_KEYS:
            if key not in row:
                raise ValueError(f"agents.toml [{name}]: missing {key}")
    cards = {p.stem for p in (framework_root / CARDS_DIR).glob("*.md")}
    for name in rows:
        if name not in cards:
            raise ValueError(f"agents.toml [{name}]: no cards/{name}.md")
    orphans = sorted(cards - set(rows))
    if orphans:
        raise ValueError(f"cards/{orphans[0]}.md has no row in agents.toml")
    return rows


def render_card(text: str, row: dict) -> str:
    """Rewrites the calibration keys of an agent card from its row.

    Idempotent: the old calibration lines are dropped and the row's are placed
    just before the closing '---'; the rest of the card is left as it is.
    """
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("source without front matter")
    close = next(
        (i for i in range(1, len(lines)) if lines[i].strip() == "---"), None
    )
    if close is None:
        raise ValueError("front matter not closed")
    kept = [
        line
        for line in lines[:close]
        if not any(line.startswith(f"{key}:") for key in CARD_KEYS)
    ]
    kept += [f"{key}: {row[key]}" for key in CARD_KEYS if key in row]
    return "\n".join(kept + lines[close:])


# --- Reading a card -------------------------------------------------------

FIELD_RE = re.compile(r"[A-Za-z][\w-]*(?=:)")


def fields(text: str) -> dict[str, str]:
    """A card's front matter: top-level key -> its normalised lines, continuation
    lines included."""
    lines = text.replace("\r\n", "\n").split("\n")
    if not lines or lines[0].strip() != "---":
        raise ValueError("card without front matter")
    out: dict[str, str] = {}
    key = None
    for line in lines[1:]:
        if line.strip() == "---":
            return {k: kernel.normalize(v) for k, v in out.items()}
        m = FIELD_RE.match(line)
        if m:
            key = m.group(0)
            out[key] = line + "\n"
        elif key is not None:
            out[key] += line + "\n"
        elif line.strip():
            raise ValueError(f"front matter line outside any key: {line!r}")
    raise ValueError("front matter not closed")


def situation(card: str) -> str:
    """The roster's Situation for a card: its description up to the first colon or full stop."""
    block = fields(card).get("description", "description:")
    text = " ".join(
        line.strip() for line in block.split(":", 1)[1].splitlines() if line.strip() not in ("", ">")
    )
    return re.split(r"(?<=[.:])\s", text)[0].rstrip(".:")


def guide_line(text: str) -> str:
    """A guide's line in `CLAUDE.md § Shared guides`: the first sentence under its title."""
    line = next(
        (s.strip() for s in text.splitlines()[1:] if s.strip() and not s.startswith("#")), ""
    )
    return re.split(r"(?<=\.)\s", line)[0]


def model_cell(card: str) -> str:
    """The roster's Model cell for a card: `model effort`."""
    f = fields(card)
    return " ".join(f[k].split(":", 1)[1].strip() for k in ("model", "effort") if k in f)


# --- Generating an installation -------------------------------------------

STATE_FILES = ("TODO.md", "status.md", "roadmap.md")
USER_RULES_TITLE = "User rules — on conflict they win over every other rule in this file"
ORCHESTRATION_GUIDE_LINE = (
    "- `.claude/shared/orchestration.md` — coordinator only, first on any task above one "
    "small change: when to delegate and to whom, the work cycle, delegation prompts, state."
)


def is_create_only(path: str) -> bool:
    """True for the files `generate` offers but the caller writes only if absent:
    the state templates, which the project fills in and no update may replace."""
    return path.startswith("docs/")


def _user_rules_region(title: str, body: str) -> str:
    return kernel.wrap_user_rules(f"## {title}\n\n{body}")


def _effective_card(text: str, row: dict, overrides: dict[str, str]) -> str:
    return render_card(text, {**row, **overrides})


def _claude_md(method: str, version: str, claude_md: str | None, rules: str) -> str:
    """The kernel region, then the project part exactly as it was, then the user rules.

    `claude_md` is the file as it is now. Its kernel region and its user-rules
    region are replaced; everything else is the project part and is kept. A
    file with no kernel region is taken whole as the project part: the caller
    decides whether that case is an installation or an error. `None` is a new
    file: kernel region only.
    """
    project = ""
    if claude_md:
        rest, _ = kernel.strip_user_rules(claude_md)
        region = kernel.parse(rest)
        project = rest if region is None else rest[: region.start] + rest[region.end :]
        project = project.strip("\n")
    out = kernel.wrap(method, version)
    if project:
        out += "\n" + project + "\n"
    if rules:
        out += "\n" + _user_rules_region(USER_RULES_TITLE, rules)
    return out


def generate(
    framework_root: Path,
    choices: dict,
    rules: Rules,
    claude_md: str | None = None,
) -> dict[str, str]:
    """Every framework file of an installation, `{path in the project: text}`.

    The one producer: the same inputs give the same text, byte for byte.
    `choices` carries the `claw.json` fields `profile`, `orchestration`,
    `agents`, `guides`, `hooks`. `claude_md` is the project's current
    `CLAUDE.md` (None: a new one). `settings.json`, `claw.json` and the skill
    packages are not here: they merge with what the project already has.

    Paths for which `is_create_only` holds are the state templates; the caller
    writes them only where the file is missing.

    The source cards still end in a `## Project context` block: it is read only
    to split the card and dropped, since a project's own words now live in the
    user-rules file. The kernel marker still carries the hash.
    """
    fw = Path(framework_root)
    version = (fw / "VERSION").read_text(encoding="utf-8").strip()
    prof = profile.load(fw / "profiles" / f"{choices['profile']}.toml")
    roster = list(choices["agents"])
    out: dict[str, str] = {}

    rows = agent_rows(fw)
    cards: dict[str, str] = {}
    for name in roster:
        fm, method, _domain = split_source((fw / CARDS_DIR / f"{name}.md").read_text(encoding="utf-8"))
        fm = _effective_card(fm, rows[name], rules.overrides.get(name, {}))
        card = kernel.normalize(fm) + "\n" + kernel.wrap(method, version)
        if name in rules.agents:
            card += "\n" + _user_rules_region(USER_RULES_TITLE, rules.agents[name])
        cards[name] = fm
        out[f".claude/agents/{name}.md"] = card

    guides = list(dict.fromkeys([*choices["guides"], *profile.required_guides(fw, roster)]))
    texts = {rel: (fw / "shared" / rel).read_bytes().decode("utf-8") for rel in guides}
    listed = "\n".join(
        [ORCHESTRATION_GUIDE_LINE]
        + [f"- `.claude/shared/{rel}` — {guide_line(texts[rel])}" for rel in guides]
    )
    method = read_method(fw / "method") + f"\n## Shared guides\n\n{listed}\n"
    out["CLAUDE.md"] = _claude_md(method, version, claude_md, rules.all)

    table = "\n".join(f"| {situation(c)} | `{n}` | {model_cell(c)} |" for n, c in cards.items())
    roster_section = f"## This project's roster\n\n| Situation | Agent | Model |\n|---|---|---|\n{table}\n"
    out[".claude/shared/orchestration.md"] = build_document(
        fw / "coordinator",
        version,
        roster_section,
        markers=False,
        extra=[orchestration_file(fw, choices["orchestration"]), *cycle_files(fw, prof.cycles)],
    )

    for rel, text in texts.items():
        out[f".claude/shared/{rel}"] = text
    for p in sorted((fw / STYLES_DIR).rglob("*")):
        if p.is_file():
            out[f".claude/output-styles/{p.relative_to(fw / STYLES_DIR).as_posix()}"] = (
                p.read_bytes().decode("utf-8")
            )
    for name in choices["hooks"]:
        out[f".claude/hooks/{name}.py"] = (fw / "hooks" / f"{name}.py").read_bytes().decode("utf-8")
    for name in STATE_FILES:
        out[f"docs/{name}"] = (fw / "templates" / name).read_bytes().decode("utf-8")
    return out
