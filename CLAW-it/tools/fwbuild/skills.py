"""I pacchetti di skill collegati al framework.

Le skill di altri autori non si pubblicano con il framework: qui c'è la presa,
i pacchetti restano sulla macchina di chi li collega. Un pacchetto è un
repository, fissato a un commit, sotto `<FW>/skills/<pacchetto>/`.

Il **pool** è l'elenco delle skill che il coordinatore può invocare da solo.
Tutto ciò che è collegato e fuori dal pool resta invocabile dall'utente e
invisibile al modello: lo fa `skillOverrides` in `settings.json`, non una regola
scritta in prosa.

Nel progetto installato le skill stanno tutte in `.claude/skills/<skill>/`: il
livello del pacchetto vive solo qui, perché Claude Code non scopre una skill
annidata più in basso.
"""

import re
import shutil
import subprocess
import tempfile
import tomllib
from dataclasses import dataclass
from datetime import date
from pathlib import Path

PACKAGE_FILE = "PACKAGE.toml"
POOL_FILE = "pool.toml"
# Il prefisso delle skill del framework: sono pubblicate e non vengono da un
# pacchetto. Un pacchetto che ne porta una dello stesso nome la coprirebbe.
RESERVED = "framework-"
# Come Claude Code nomina una skill: la cartella installata prende questo nome.
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
FRONTMATTER_NAME_RE = re.compile(r"^name:\s*(\S+)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Package:
    """Un repository collegato: come si chiama qui, da dove viene, cosa porta.

    `skills` si legge dal disco e non dal `PACKAGE.toml`: il registro dice da
    dove viene il pacchetto, ma cosa c'è dentro lo dicono le cartelle. Due fonti
    per lo stesso fatto divergono, e la copia sbagliata sarebbe quella che
    l'installazione segue.
    """

    name: str
    repo: str
    commit: str
    skills: list[str]


def packages(framework_root: Path) -> list[Package]:
    """I pacchetti collegati. Vuoto = nessuno, ed è il caso normale."""
    base = Path(framework_root) / "skills"
    out = []
    for d in sorted(p for p in base.glob("*") if (p / PACKAGE_FILE).is_file()):
        data = tomllib.loads((d / PACKAGE_FILE).read_text(encoding="utf-8"))
        out.append(
            Package(
                name=d.name,
                repo=str(data.get("repo", "")),
                commit=str(data.get("commit", "")),
                skills=sorted(
                    s.name for s in d.iterdir() if (s / "SKILL.md").is_file()
                ),
            )
        )
    return out


def installed(framework_root: Path) -> dict[str, str]:
    """`nome skill → pacchetto`: l'inverso che serve ai percorsi appiattiti.

    Due pacchetti con la stessa skill sono un errore e non una precedenza: nel
    progetto finiscono allo stesso percorso, e quale dei due vinca dipenderebbe
    dall'ordine di copia.
    """
    out: dict[str, str] = {}
    for pkg in packages(framework_root):
        for skill in pkg.skills:
            if skill in out:
                raise ValueError(
                    f"skill {skill!r} in due pacchetti ({out[skill]} e {pkg.name}): "
                    "nel progetto stanno allo stesso percorso, togline uno"
                )
            out[skill] = pkg.name
    return out


def source_dir(framework_root: Path, skill: str) -> Path | None:
    """La cartella sorgente di una skill di pacchetto, o `None` se non lo è."""
    pkg = installed(framework_root).get(skill)
    return None if pkg is None else Path(framework_root) / "skills" / pkg / skill


def pool(framework_root: Path) -> list[str]:
    """Le skill che il coordinatore può invocare da solo.

    Un nome che non corrisponde a niente ferma qui: scritto a mano in un file,
    un errore di battitura vorrebbe dire che quella skill resta nascosta al
    coordinatore, ed è esattamente il guasto che nessuno andrebbe a cercare.
    """
    path = Path(framework_root) / "skills" / POOL_FILE
    if not path.is_file():
        return []
    names = [str(n) for n in tomllib.loads(path.read_text(encoding="utf-8")).get("skills", [])]
    known = installed(framework_root)
    unknown = [n for n in names if n not in known]
    if unknown:
        raise ValueError(
            f"{POOL_FILE} nomina skill che non sono collegate: {', '.join(unknown)}"
        )
    return names


def overrides(framework_root: Path) -> dict:
    """La parte di `settings.json` che tiene fuori dal pool ciò che non ci sta.

    Solo le skill dei pacchetti: quelle del framework e quelle dell'utente non
    si toccano. Nessun pacchetto collegato → dict vuoto, e l'installazione resta
    quella di prima invece di scrivere una chiave senza voci.
    """
    in_pool = set(pool(framework_root))
    out = {
        skill: "user-invocable-only"
        for skill in sorted(installed(framework_root))
        if skill not in in_pool
    }
    return {"skillOverrides": out} if out else {}


def set_pool(framework_root: Path, names: list[str]) -> None:
    path = Path(framework_root) / "skills" / POOL_FILE
    body = "".join(f'  "{n}",\n' for n in names)
    path.write_text(
        "# Le skill che il coordinatore può invocare da solo. Locale, non pubblicato.\n"
        + (f"skills = [\n{body}]\n" if names else "skills = []\n"),
        encoding="utf-8",
    )


def package_name(repo: str) -> str:
    """`<proprietario>-<repository>` dalla sorgente, per non confondere due `skills`.

    Le ultime due parti e non il solo nome: `skills` è il nome di mezzo
    repository, e due pacchetti così finirebbero nella stessa cartella. Si
    separa anche sulla barra rovesciata perché la sorgente può essere una
    cartella locale di Windows, e si tiene solo ciò che può fare da nome di
    cartella ovunque.
    """
    parts = [p for p in re.split(r"[/\\:]", repo.rstrip("/\\").removesuffix(".git")) if p]
    name = "-".join(parts[-2:] if len(parts) >= 2 else parts[-1:]).lower()
    return re.sub(r"[^a-z0-9._-]+", "-", name).strip("-")


def add(framework_root: Path, repo: str, commit: str | None = None) -> Package:
    """Collega un repository: lo scarica, lo fissa a un commit, ne copia le skill.

    Si copia ogni cartella che ha un `SKILL.md`, col nome dichiarato nel
    frontmatter — è quello con cui Claude Code la invoca, e una cartella che si
    chiama diversamente installerebbe una skill introvabile. Un nome già
    collegato ferma tutto prima di scrivere: nel progetto le skill stanno a un
    livello solo e la seconda coprirebbe la prima.
    """
    fw = Path(framework_root)
    name = package_name(repo)
    dest = fw / "skills" / name
    if dest.exists():
        raise ValueError(f"{name} è già collegato: staccalo prima di ricollegarlo")

    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        _git("clone", "--quiet", repo, str(clone))
        if commit:
            _git("-C", str(clone), "checkout", "--quiet", commit)
        resolved = _git("-C", str(clone), "rev-parse", "HEAD").strip()

        found: dict[str, Path] = {}
        for skill_md in sorted(clone.rglob("SKILL.md")):
            if ".git" in skill_md.parts:
                continue
            skill = _skill_name(skill_md)
            if skill in found:
                raise ValueError(
                    f"{repo} porta due skill di nome {skill!r}: non sono "
                    "installabili insieme"
                )
            found[skill] = skill_md.parent
        if not found:
            raise ValueError(f"{repo}: nessun SKILL.md, non c'è niente da collegare")

        taken = set(installed(fw)) | {
            p.name for p in (fw / "skills").glob(f"{RESERVED}*")
        }
        clash = sorted(set(found) & taken)
        if clash:
            raise ValueError(
                "nomi di skill già presenti, niente è stato scritto: " + ", ".join(clash)
            )

        dest.mkdir(parents=True)
        for skill, src in found.items():
            shutil.copytree(src, dest / skill)
        for license_file in sorted(clone.glob("LICENSE*")):
            shutil.copyfile(license_file, dest / license_file.name)
        (dest / PACKAGE_FILE).write_text(
            f"repo = {_toml_str(repo)}\ncommit = {_toml_str(resolved)}\n"
            f"added = {_toml_str(date.today().isoformat())}\n",
            encoding="utf-8",
        )
    return next(p for p in packages(fw) if p.name == name)


def remove(framework_root: Path, name: str) -> list[str]:
    """Stacca un pacchetto e toglie le sue skill dal pool. Torna cosa se n'è andato."""
    fw = Path(framework_root)
    dest = fw / "skills" / name
    if not (dest / PACKAGE_FILE).is_file():
        raise ValueError(f"{name} non è un pacchetto collegato")
    gone = next(p.skills for p in packages(fw) if p.name == name)
    keep = [n for n in pool(fw) if n not in gone]
    shutil.rmtree(dest)
    if (fw / "skills" / POOL_FILE).is_file():
        set_pool(fw, keep)
    return gone


def shadowed(names: list[str]) -> list[str]:
    """Quali di questi nomi ha già una skill personale, che vincerebbe.

    La precedenza è dell'utente: `~/.claude/skills/<nome>` copre quella del
    progetto. Non è un errore del framework — è la macchina di chi installa — ma
    scoprirlo dopo vuol dire aver letto la skill sbagliata.
    """
    home = Path.home() / ".claude" / "skills"
    return [n for n in names if (home / n / "SKILL.md").is_file()]


def _toml_str(value: str) -> str:
    """Una stringa TOML scritta a mano: la sorgente può essere una cartella
    locale di Windows, e lì la barra rovesciata è un escape che non si rilegge."""
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _skill_name(skill_md: Path) -> str:
    text = skill_md.read_text(encoding="utf-8", errors="replace")
    match = FRONTMATTER_NAME_RE.search(text)
    name = match.group(1) if match else skill_md.parent.name
    if not NAME_RE.fullmatch(name):
        raise ValueError(
            f"{skill_md}: nome {name!r} non installabile (minuscole, cifre e trattini)"
        )
    return name


def _git(*args: str) -> str:
    """git con l'errore vero in faccia: un clone fallito non è un pacchetto vuoto."""
    try:
        done = subprocess.run(
            ["git", *args], capture_output=True, text=True, encoding="utf-8", check=True
        )
    except FileNotFoundError as err:
        raise RuntimeError("git non è disponibile: serve per collegare un pacchetto") from err
    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"git {' '.join(args)} è fallito: {err.stderr.strip()}") from err
    return done.stdout
