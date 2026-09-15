"""Assembly of the installable artefacts.

The generated method lives inside the kernel region; front matter and project
blocks stay outside, because they are the surface the user adapts.
"""

from collections.abc import Sequence
from pathlib import Path

from . import kernel

METHOD_HEADING = "## Method"
DOMAIN_HEADING = "## Project context"

# The two source ceilings, in words. They are real tests — the build fails
# above the threshold — and they live here because the doctor reads them too:
# the `TOKEN_BUDGET` finding stays silent until the assembled file reaches at
# least the ceiling the framework sets itself for the method alone.
METHOD_WORD_BUDGET = 2000
COORDINATOR_WORD_BUDGET = 2900

# The orchestration of whoever does not choose one.
DEFAULT_ORCHESTRATION = "orchestrator-worker"


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
    `coordinator/` without this would silently delete them at every `--down`,
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
