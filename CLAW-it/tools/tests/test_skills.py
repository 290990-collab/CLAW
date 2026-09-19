import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import cli, lifecycle, skills

FRAMEWORK = Path(__file__).resolve().parents[2]


def git(*args: str) -> None:
    subprocess.run(["git", *args], check=True, capture_output=True, text=True)


def repo(root: Path, layout: dict[str, str]) -> str:
    """Un repository locale con le skill descritte: `percorso → nome dichiarato`."""
    root.mkdir(parents=True)
    for rel, name in layout.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(f"---\nname: {name}\n---\n\nprova\n", encoding="utf-8")
    (root / "LICENSE").write_text("MIT\n", encoding="utf-8")
    git("-C", str(root), "init", "--quiet")
    git("-C", str(root), "add", "-A")
    git(
        "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
        "commit", "--quiet", "-m", "prova",
    )
    return str(root)


def framework(d: Path) -> Path:
    """Un sorgente finto con la sola cartella che questo modulo guarda."""
    fw = d / "fw"
    (fw / "skills" / "claw-doctor").mkdir(parents=True)
    (fw / "skills" / "claw-doctor" / "SKILL.md").write_text(
        "---\nname: claw-doctor\n---\n", encoding="utf-8"
    )
    return fw


class TestAdd(unittest.TestCase):
    def test_add_takes_every_skill_and_pins_the_commit(self):
        """Il commit è la sola cosa che rende ripetibile un pacchetto: senza,
        «collegato» non dice quale versione, e un aggiornamento a monte cambia
        le istruzioni senza che nessuno lo veda."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            url = repo(d / "src", {"skills/alfa/SKILL.md": "alfa", "beta/SKILL.md": "beta"})
            pkg = skills.add(fw, url)
            self.assertEqual(pkg.skills, ["alfa", "beta"])
            self.assertEqual(len(pkg.commit), 40)
            self.assertTrue((fw / "skills" / pkg.name / "alfa" / "SKILL.md").is_file())
            self.assertTrue((fw / "skills" / pkg.name / "LICENSE").is_file())
            self.assertEqual(skills.installed(fw), {"alfa": pkg.name, "beta": pkg.name})

    def test_the_folder_name_does_not_decide_the_skill_name(self):
        """Claude Code invoca una skill col nome del frontmatter: installarla
        sotto il nome della cartella la renderebbe introvabile."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            url = repo(d / "src", {"cartella-diversa/SKILL.md": "vero-nome"})
            pkg = skills.add(fw, url)
            self.assertEqual(pkg.skills, ["vero-nome"])

    def test_a_name_already_connected_stops_the_add(self):
        """Nel progetto le skill stanno a un livello solo: due pacchetti con lo
        stesso nome si sovrascriverebbero, e vincerebbe l'ordine di copia."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            skills.add(fw, repo(d / "uno", {"a/SKILL.md": "alfa"}))
            with self.assertRaises(ValueError) as e:
                skills.add(fw, repo(d / "due", {"b/SKILL.md": "alfa"}))
            self.assertIn("alfa", str(e.exception))
            self.assertEqual(sorted(skills.installed(fw)), ["alfa"])

    def test_a_framework_skill_name_stops_the_add(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            with self.assertRaises(ValueError):
                skills.add(fw, repo(d / "src", {"x/SKILL.md": "claw-doctor"}))

    def test_a_repo_without_skills_is_an_error(self):
        """Un pacchetto vuoto collegato in silenzio è un pool che non funziona
        e nessun rilievo che lo dica."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            (d / "vuoto").mkdir()
            (d / "vuoto" / "README.md").write_text("niente\n", encoding="utf-8")
            git("-C", str(d / "vuoto"), "init", "--quiet")
            git("-C", str(d / "vuoto"), "add", "-A")
            git(
                "-C", str(d / "vuoto"), "-c", "user.email=t@t", "-c", "user.name=t",
                "commit", "--quiet", "-m", "vuoto",
            )
            with self.assertRaises(ValueError):
                skills.add(fw, str(d / "vuoto"))
            self.assertEqual(skills.packages(fw), [])


class TestPool(unittest.TestCase):
    def test_only_what_is_outside_the_pool_is_hidden_from_the_model(self):
        """È il pool: dentro, il coordinatore la invoca; fuori, resta all'utente.
        Un override su una skill del pool la spegnerebbe proprio a chi deve
        poterla chiamare."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            skills.add(fw, repo(d / "src", {"a/SKILL.md": "alfa", "b/SKILL.md": "beta"}))
            skills.set_pool(fw, ["alfa"])
            self.assertEqual(skills.pool(fw), ["alfa"])
            self.assertEqual(
                skills.overrides(fw), {"skillOverrides": {"beta": "user-invocable-only"}}
            )

    def test_no_package_means_no_settings_entry(self):
        """Senza pacchetti l'installazione dev'essere identica a prima: una
        chiave vuota entrerebbe in settings_added e la disinstallazione
        toglierebbe una voce che nessuno ha messo."""
        with tempfile.TemporaryDirectory() as d:
            fw = framework(Path(d))
            self.assertEqual(skills.overrides(fw), {})

    def test_a_pool_name_that_is_not_connected_is_an_error(self):
        """Un nome sbagliato nel pool vuol dire che quella skill resta nascosta
        al coordinatore: il guasto è silenzioso e nessuno va a cercarlo."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            skills.add(fw, repo(d / "src", {"a/SKILL.md": "alfa"}))
            skills.set_pool(fw, ["alfa", "alfaa"])
            with self.assertRaises(ValueError) as e:
                skills.pool(fw)
            self.assertIn("alfaa", str(e.exception))


class TestRemove(unittest.TestCase):
    def test_remove_takes_the_package_out_of_the_pool_too(self):
        """Il pool sopravvive allo stacco: un nome rimasto lì dentro farebbe
        fallire ogni installazione successiva."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            fw = framework(d)
            pkg = skills.add(fw, repo(d / "src", {"a/SKILL.md": "alfa"}))
            other = skills.add(fw, repo(d / "due", {"b/SKILL.md": "beta"}))
            skills.set_pool(fw, ["alfa", "beta"])
            self.assertEqual(skills.remove(fw, pkg.name), ["alfa"])
            self.assertEqual(skills.pool(fw), ["beta"])
            self.assertEqual([p.name for p in skills.packages(fw)], [other.name])

    def test_removing_something_that_is_not_a_package_is_an_error(self):
        with tempfile.TemporaryDirectory() as d:
            fw = framework(Path(d))
            with self.assertRaises(ValueError):
                skills.remove(fw, "claw-doctor")
            self.assertTrue((fw / "skills" / "claw-doctor").is_dir())


class TestInstalledProject(unittest.TestCase):
    """Il giro completo su un progetto vero: un pacchetto collegato a una copia
    del sorgente, poi riparazione e disinstallazione.

    Si copia il sorgente perché collegare un pacchetto scrive dentro
    `<FW>/skills/`, e un test non tocca il framework con cui gira."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.fw = d / "fw"
        shutil.copytree(
            FRAMEWORK, self.fw, ignore=shutil.ignore_patterns("__pycache__", ".git")
        )
        self.pkg = skills.add(self.fw, repo(d / "src", {"a/SKILL.md": "alfa"}))
        self.prj = d / "prova"
        with redirect_stdout(io.StringIO()):
            trial_install.install(self.prj)

    def tearDown(self):
        self.tmp.cleanup()

    def test_repair_brings_the_package_skill_in_flattened(self):
        """Nel progetto le skill stanno a un livello: installata sotto il nome
        del pacchetto, Claude Code non la troverebbe (provato)."""
        ops = lifecycle.plan_repair(self.prj, self.fw)
        rel = ".claude/skills/alfa/SKILL.md"
        self.assertEqual({op.path: op.action for op in ops}[rel], lifecycle.CREATE)
        lifecycle.apply_update(self.prj, self.fw, ops)
        self.assertEqual(
            (self.prj / rel).read_bytes(),
            (self.fw / "skills" / self.pkg.name / "alfa" / "SKILL.md").read_bytes(),
        )

    def test_a_skill_outside_the_pool_is_hidden_from_the_coordinator(self):
        """Il pool vive in `settings.json`: senza la voce, il coordinatore vede
        e invoca ogni skill collegata, e il pool resta una frase in una guida."""
        lifecycle.apply_update(self.prj, self.fw, lifecycle.plan_repair(self.prj, self.fw))
        data = json.loads((self.prj / ".claude" / "settings.json").read_text(encoding="utf-8"))
        self.assertEqual(data["skillOverrides"], {"alfa": "user-invocable-only"})
        record = json.loads(
            (self.prj / ".claude" / "framework.json").read_text(encoding="utf-8")
        )
        self.assertEqual(record["settings_added"]["skillOverrides"], {"alfa": "user-invocable-only"})
        self.assertEqual(record["skills"], {"alfa": self.pkg.name})

    def test_uninstall_removes_a_package_skill_it_recognises(self):
        """Identica al sorgente vuol dire «non contiene lavoro di nessuno»:
        senza l'inverso del percorso appiattito, la disinstallazione la
        crederebbe roba del progetto e la lascerebbe lì."""
        lifecycle.apply_update(self.prj, self.fw, lifecycle.plan_repair(self.prj, self.fw))
        ops = lifecycle.plan_uninstall(self.prj, self.fw)
        rel = ".claude/skills/alfa/SKILL.md"
        self.assertEqual({op.path: op.action for op in ops}[rel], lifecycle.REMOVE)
        lifecycle.apply_uninstall(self.prj, self.fw, ops)
        self.assertFalse((self.prj / ".claude" / "skills" / "alfa").exists())


class TestCommand(unittest.TestCase):
    def test_list_works_on_a_framework_without_packages(self):
        """Il caso normale è «nessun pacchetto»: se il comando cade lì, cade
        per chiunque non abbia ancora collegato niente."""
        out = io.StringIO()
        with redirect_stdout(out):
            code = cli.main(["skills", "list", "--source", str(FRAMEWORK)])
        self.assertEqual(code, 0)
        self.assertIn("nessun pacchetto", out.getvalue())


class TestSource(unittest.TestCase):
    def test_the_framework_itself_has_no_packages(self):
        """Il sorgente pubblicato non porta skill di altri: se ne compare una,
        è finita in git un'integrazione che doveva restare locale."""
        self.assertEqual(skills.packages(FRAMEWORK), [])


if __name__ == "__main__":
    unittest.main()
