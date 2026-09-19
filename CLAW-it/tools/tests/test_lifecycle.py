import hashlib
import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import doctor, kernel, lifecycle, settings, source

FRAMEWORK = Path(__file__).resolve().parents[2]
VERSION = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
ARCHIVE = doctor.ARCHIVE_DIR.as_posix() + "/"
SETTINGS = ".claude/settings.json"


def install(d) -> Path:
    root = Path(d) / "prova"
    with redirect_stdout(io.StringIO()):
        trial_install.install(root)
    return root


def tree(root: Path) -> dict[str, str]:
    """Ogni file sotto `root`, relativo, con l'impronta del contenuto."""
    return {
        p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in root.rglob("*")
        if p.is_file()
    }


def actions(ops) -> dict[str, str]:
    return {op.path: op.action for op in ops}


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestInstallPlan(unittest.TestCase):
    def test_the_plan_names_every_file_the_install_writes(self):
        """Il piano è ciò che l'utente approva, e la disinstallazione parte
        dallo stesso elenco: un file che l'installazione scrive e il piano non
        nomina è scritto senza approvazione e resta dopo la disinstallazione."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            _, roster, guides, hooks = trial_install.choices()
            self.assertEqual(
                sorted(tree(root)), lifecycle.targets(FRAMEWORK, roster, guides, hooks)
            )

    def test_install_plan_on_a_project_with_its_own_material(self):
        """Su un progetto che aveva già istruzioni, permessi e agenti propri il
        piano deve dire «fondo» e «lascio», non «sovrascrivo»; e una seconda
        installazione sopra la prima non è un'installazione."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            agents = prj / ".claude" / "agents"
            agents.mkdir(parents=True)
            (prj / "CLAUDE.md").write_text("# Le mie istruzioni\n", encoding="utf-8")
            (prj / SETTINGS).write_text('{"env": {"A": "1"}}', encoding="utf-8")
            (agents / "mio.md").write_text("---\nname: mio\n---\n", encoding="utf-8")
            (agents / "explorer.md").write_text("vecchia\n", encoding="utf-8")
            (prj / "AGENTS.md").write_text("# Altro strumento\n", encoding="utf-8")
            _, roster, guides, hooks = trial_install.choices()
            targets = lifecycle.targets(FRAMEWORK, roster, guides, hooks)

            ops = lifecycle.plan_install(prj, targets)
            got = actions(ops)
            self.assertEqual(got["CLAUDE.md"], lifecycle.MERGE)
            self.assertEqual(got[SETTINGS], lifecycle.MERGE)
            self.assertEqual(got[".claude/agents/mio.md"], lifecycle.KEEP)
            self.assertEqual(got["AGENTS.md"], lifecycle.KEEP)
            self.assertEqual(got[".claude/agents/explorer.md"], lifecycle.OVERWRITE)
            self.assertEqual(got["docs/TODO.md"], lifecycle.CREATE)
            # Ciò che cambia un file che c'era si legge per nome; il resto si conta.
            text = lifecycle.render(ops)
            self.assertIn(".claude/agents/explorer.md", text)
            self.assertNotIn("docs/TODO.md", text)

            (prj / ".claude" / "framework.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ValueError):
                lifecycle.plan_install(prj, targets)


class TestUninstall(unittest.TestCase):
    def uninstall(self, root: Path):
        ops = lifecycle.plan_uninstall(root, FRAMEWORK)
        lifecycle.apply_uninstall(root, FRAMEWORK, ops)
        return ops

    def test_uninstall_leaves_only_the_project_and_an_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
            data = read_json(root / SETTINGS)
            data["env"] = {"A": "1"}
            write_json(root / SETTINGS, data)
            claude = (root / "CLAUDE.md").read_text(encoding="utf-8")

            self.uninstall(root)

            left = {rel for rel in tree(root) if not rel.startswith(ARCHIVE)}
            self.assertEqual(
                left,
                {
                    "CLAUDE.md",
                    SETTINGS,
                    "docs/TODO.md",
                    "docs/status.md",
                    "docs/roadmap.md",
                    "src/app.py",
                },
            )
            self.assertEqual(read_json(root / SETTINGS), {"env": {"A": "1"}})
            self.assertEqual(
                (root / "CLAUDE.md").read_text(encoding="utf-8"),
                claude[kernel.parse(claude).end :].lstrip("\n"),
            )
            self.assertFalse((root / ".claude" / "agents").exists())
            archive = root / doctor.ARCHIVE_DIR
            self.assertTrue((archive / ".claude" / "framework.json").is_file())
            self.assertTrue((archive / ".claude" / "agents" / "explorer.md").is_file())

    def test_uninstall_never_deletes_what_it_did_not_write(self):
        """Un file sparisce dal progetto solo se era identico al sorgente;
        tutto il resto o resta o finisce in archivio con lo stesso contenuto."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            for rel in (".claude/skills/claw-sync/SKILL.md", ".claude/hooks/gateguard.py"):
                p = root / rel
                p.write_text(p.read_text(encoding="utf-8") + "\n# nota mia\n", encoding="utf-8")
            mine = root / ".claude" / "skills" / "mia" / "SKILL.md"
            mine.parent.mkdir()
            mine.write_text("name: mia\n", encoding="utf-8")
            (root / ".claude" / "hooks" / "mio.py").write_text("pass\n", encoding="utf-8")
            before = tree(root)

            ops = self.uninstall(root)

            after = tree(root)
            self.assertEqual(
                actions(ops)[".claude/skills/claw-sync/SKILL.md"], lifecycle.ARCHIVE
            )
            archived = {rel[len(ARCHIVE) :] for rel in after if rel.startswith(ARCHIVE)}
            for rel in archived:
                self.assertEqual(after[ARCHIVE + rel], before[rel], rel)
            gone = sorted(set(before) - set(after) - archived)
            self.assertTrue(gone)
            originals = {
                ".claude/skills/": FRAMEWORK / "skills",
                ".claude/hooks/": FRAMEWORK / "hooks",
            }
            for rel in gone:
                prefix = next((p for p in originals if rel.startswith(p)), None)
                self.assertIsNotNone(prefix, f"{rel}: cancellato senza venire dal sorgente")
                original = originals[prefix] / rel[len(prefix) :]
                self.assertEqual(
                    hashlib.sha256(original.read_bytes()).hexdigest(), before[rel], rel
                )
            self.assertTrue(mine.is_file())
            self.assertTrue((root / ".claude" / "hooks" / "mio.py").is_file())

    def test_uninstall_refuses_a_plan_the_tree_has_outgrown(self):
        """Il piano approvato vale per l'albero su cui è stato fatto: una skill
        ritoccata dopo non è più «identica al sorgente», e cancellarla perché lo
        era ieri cancella il lavoro di oggi. Il rifiuto arriva prima del primo
        byte scritto, non a metà."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            skill = root / ".claude" / "skills" / "claw-doctor" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nnota\n", encoding="utf-8")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_uninstall(root, FRAMEWORK, ops)
            self.assertIn(".claude/skills/claw-doctor/SKILL.md", str(e.exception))
            self.assertEqual(tree(root), before)

            (root / doctor.ARCHIVE_DIR).mkdir()
            with self.assertRaises(ValueError):
                lifecycle.plan_uninstall(root, FRAMEWORK)

    def test_uninstall_refuses_a_plan_outgrown_outside_its_removals(self):
        """`_removable` ricontrolla solo le «rimuove». Una scheda ritoccata dopo
        il piano finirebbe in archivio senza che nessuno l'abbia approvata, e un
        `CLAUDE.md` rimasto senza marker fa cadere l'esecuzione dopo che
        `settings.json` è già stato riscritto: un'installazione a metà."""
        retouches = {
            "CLAUDE.md": lambda text: text.replace(kernel.CLOSE, ""),
            ".claude/agents/explorer.md": lambda text: text + "\nnota\n",
        }
        for rel, retouch in retouches.items():
            with self.subTest(rel=rel), tempfile.TemporaryDirectory() as d:
                root = install(d)
                ops = lifecycle.plan_uninstall(root, FRAMEWORK)
                p = root / rel
                p.write_text(retouch(p.read_text(encoding="utf-8")), encoding="utf-8")
                before = tree(root)
                with self.assertRaises(ValueError) as e:
                    lifecycle.apply_uninstall(root, FRAMEWORK, ops)
                self.assertIn(rel, str(e.exception))
                self.assertEqual(tree(root), before)

    def test_uninstall_refuses_to_move_what_it_never_plans_to(self):
        """Il piano è un file salvato: un'«archivia» o una «fonde» scritta a mano
        col digest giusto sposterebbe codice del progetto nell'archivio, o un
        file fuori dalla root.
        Il rifiuto arriva prima del primo byte scritto."""
        forged = (
            ("src/app.py", lifecycle.ARCHIVE),
            ("../fuori.txt", lifecycle.ARCHIVE),
            ("src/app.py", lifecycle.MERGE),
        )
        for rel, action in forged:
            with self.subTest(rel=rel, action=action), tempfile.TemporaryDirectory() as d:
                root = install(d)
                (root / "src").mkdir()
                (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
                (Path(d) / "fuori.txt").write_text("non del progetto\n", encoding="utf-8")
                ops = lifecycle.plan_uninstall(root, FRAMEWORK)
                before = tree(Path(d))
                digest = hashlib.sha256((root / rel).read_bytes()).hexdigest()
                plan = [*ops, lifecycle.Operation(rel, action, "", digest)]
                with self.assertRaises(ValueError) as e:
                    lifecycle.apply_uninstall(root, FRAMEWORK, plan)
                self.assertIn(rel, str(e.exception))
                self.assertEqual(tree(Path(d)), before)

    def test_uninstall_refuses_a_removal_the_source_does_not_justify(self):
        """Una «rimuove» messa a mano nel piano, col digest giusto, cancellerebbe
        codice del progetto. Ogni
        rimozione si ricontrolla contro il sorgente, e il rifiuto arriva prima
        del primo byte scritto."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / "src").mkdir()
            (root / "src" / "app.py").write_text("print(1)\n", encoding="utf-8")
            (root / ".claude" / "hooks" / "mio.py").write_text("pass\n", encoding="utf-8")
            skill = root / ".claude" / "skills" / "claw-sync" / "SKILL.md"
            skill.write_text(skill.read_text(encoding="utf-8") + "\nnota\n", encoding="utf-8")
            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            before = tree(root)
            for rel in ("src/app.py", ".claude/hooks/mio.py", ".claude/skills/claw-sync/SKILL.md"):
                with self.subTest(rel=rel):
                    forged = [op for op in ops if op.path != rel]
                    forged.append(lifecycle.Operation(rel, lifecycle.REMOVE, "", before[rel]))
                    with self.assertRaises(ValueError) as e:
                        lifecycle.apply_uninstall(root, FRAMEWORK, forged)
                    self.assertIn(rel, str(e.exception))
                    self.assertEqual(tree(root), before)

    def test_uninstall_drops_a_framework_hook_the_user_retouched(self):
        """Una voce hook col timeout ritoccato non è più uguale al record, e
        `unmerge` la lascia; senza record non se ne toglie nessuna. Ma lo
        script a cui punta se ne va: un hook chiuso senza script blocca ogni
        Edit e ogni Bash del progetto, per sempre e senza un rilievo."""
        cases = {
            "timeout ritoccato": lambda data, manifest: data["hooks"]["PreToolUse"][0][
                "hooks"
            ][0].update(timeout=30),
            "senza record": lambda data, manifest: manifest.pop("settings_added"),
        }
        for label, retouch in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as d:
                root = install(d)
                data = read_json(root / SETTINGS)
                manifest = read_json(root / source.MANIFEST)
                retouch(data, manifest)
                write_json(root / SETTINGS, data)
                write_json(root / source.MANIFEST, manifest)
                first = data["hooks"]["PreToolUse"][0]["hooks"][0]["command"]
                name = re.search(r"\.claude/hooks/(\w+)\.py", first).group(1)

                ops = self.uninstall(root)

                named = [op for op in ops if op.path == SETTINGS and name in op.reason]
                self.assertTrue(named, "la voce tolta non compare nel piano")
                self.assertNotIn(".claude/hooks/", (root / SETTINGS).read_text(encoding="utf-8"))


class TestRepair(unittest.TestCase):
    def test_repair_restores_what_went_missing(self):
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            skill = ".claude/skills/claw-sync/SKILL.md"
            hook = ".claude/hooks/config_protection.py"
            for rel in (skill, hook, "docs/status.md"):
                (root / rel).unlink()
            data = read_json(root / SETTINGS)
            del data["hooks"]
            data["permissions"]["deny"].remove("Read(./**/*.pem)")
            write_json(root / SETTINGS, data)
            # Un permesso che il record non ha: quello che il repair rimette deve
            # entrarci, o la disinstallazione non lo toglierà. Gli hook restano
            # nel record: è l'unica traccia che dice quali sono in uso.
            manifest = read_json(root / source.MANIFEST)
            manifest["settings_added"]["permissions"]["deny"].remove("Read(./**/*.pem)")
            write_json(root / source.MANIFEST, manifest)

            ops = lifecycle.plan_repair(root, FRAMEWORK)
            got = actions(ops)
            for rel in (skill, hook, "docs/status.md"):
                self.assertEqual(got[rel], lifecycle.CREATE, rel)
            self.assertEqual(got[SETTINGS], lifecycle.MERGE)

            lifecycle.apply_update(root, FRAMEWORK, ops)

            self.assertEqual(doctor.check(root), [])
            self.assertEqual(
                (root / hook).read_bytes(),
                (FRAMEWORK / "hooks" / "config_protection.py").read_bytes(),
            )
            data = read_json(root / SETTINGS)
            self.assertIn("Read(./**/*.pem)", data["permissions"]["deny"])
            self.assertIn(".claude/hooks/config_protection.py", json.dumps(data))
            # Ciò che il repair ha rimesso è nel record: la disinstallazione lo toglie.
            record = read_json(root / source.MANIFEST)["settings_added"]
            self.assertEqual(settings.unmerge(data, record)[0], {})

    def test_repair_restores_the_variables_of_the_installed_orchestration(self):
        """L'orchestrazione non è nel manifesto: se il ricalcolo dei settings
        guarda solo profilo e hook, un progetto `agent-teams` che ha perso una
        variabile resta con il modello spento, e il repair dice che è tutto a
        posto."""
        env = settings.ORCHESTRATION_SETTINGS["agent-teams"]["env"]
        lost = sorted(env)[0]
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "prova"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root, orchestration="agent-teams")
            data = read_json(root / SETTINGS)
            del data["env"][lost]
            write_json(root / SETTINGS, data)

            ops = lifecycle.plan_repair(root, FRAMEWORK)
            self.assertEqual(actions(ops).get(SETTINGS), lifecycle.MERGE)
            lifecycle.apply_update(root, FRAMEWORK, ops)

            self.assertEqual(read_json(root / SETTINGS)["env"], env)
            self.assertEqual(doctor.check(root), [])

    def test_repair_refuses_without_the_coordinator_guide(self):
        """Senza guida l'orchestrazione installata non si sa: ricalcolare i
        settings senza le sue variabili le perderebbe in silenzio."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            (root / lifecycle.ORCHESTRATION).unlink()
            with self.assertRaises(ValueError) as e:
                lifecycle.plan_repair(root, FRAMEWORK)
            self.assertIn(lifecycle.ORCHESTRATION, str(e.exception))

    def test_repair_overwrites_nothing_and_refuses_an_old_install(self):
        """Il repair rimette ciò che manca, non riporta al sorgente ciò che
        l'utente ha cambiato; e su un'installazione di un'altra versione
        «ciò che manca» si misura contro il sorgente sbagliato."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            skill = ".claude/skills/claw-doctor/SKILL.md"
            (root / skill).write_text("name: claw-doctor\nmia\n", encoding="utf-8")
            ops = lifecycle.plan_repair(root, FRAMEWORK)
            self.assertNotIn(lifecycle.OVERWRITE, {op.action for op in ops})
            self.assertEqual(actions(ops)[skill], lifecycle.KEEP)
            before = tree(root)
            lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertEqual(tree(root), before)

            manifest = read_json(root / source.MANIFEST)
            manifest["version"] = "0.1.0"
            write_json(root / source.MANIFEST, manifest)
            with self.assertRaises(ValueError):
                lifecycle.plan_repair(root, FRAMEWORK)


class TestDown(unittest.TestCase):
    def test_down_plan_on_an_older_install(self):
        """`--down` porta anche skill e hook, non solo le regioni kernel. Una
        regione ritoccata a mano si perde, e il piano lo dice prima."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            manifest = read_json(root / source.MANIFEST)
            manifest["version"] = "1.0.0"
            write_json(root / source.MANIFEST, manifest)
            claude = root / "CLAUDE.md"
            drifted = claude.read_text(encoding="utf-8").replace(
                "Evidence Before Action", "Evidence Before Action, a modo mio"
            )
            claude.write_text(drifted, encoding="utf-8")
            agents = root / ".claude" / "agents"
            (agents / "obsoleto.md").write_bytes((agents / "explorer.md").read_bytes())
            skill = ".claude/skills/claw-sync/SKILL.md"
            (root / skill).write_text("name: claw-sync\nvecchia\n", encoding="utf-8")
            hook = ".claude/hooks/block_no_verify.py"
            (root / hook).unlink()
            before = tree(root)

            ops = lifecycle.plan_down(root, FRAMEWORK)

            self.assertEqual(tree(root), before)
            got = {op.path: op for op in ops}
            self.assertEqual(got["CLAUDE.md"].action, lifecycle.MERGE)
            self.assertIn("si perde", got["CLAUDE.md"].reason)
            self.assertNotIn("si perde", got[".claude/shared/orchestration.md"].reason)
            self.assertEqual(got[".claude/agents/obsoleto.md"].action, lifecycle.KEEP)
            self.assertEqual(got[skill].action, lifecycle.OVERWRITE)
            self.assertEqual(got[hook].action, lifecycle.CREATE)
            self.assertEqual(got[".claude/framework.json"].action, lifecycle.MERGE)

            lifecycle.apply_update(root, FRAMEWORK, ops)

            self.assertEqual(
                (root / skill).read_bytes(),
                (FRAMEWORK / "skills" / "claw-sync" / "SKILL.md").read_bytes(),
            )
            self.assertTrue((root / hook).is_file())
            # Le regioni kernel sono dei passi della skill, non di questo codice.
            self.assertEqual(claude.read_text(encoding="utf-8"), drifted)
            self.assertEqual(read_json(root / source.MANIFEST)["version"], VERSION)

    def test_down_names_a_model_the_source_changed(self):
        """Il frontmatter resta del progetto: un agente declassato nel sorgente
        resterebbe sul modello vecchio, e il piano deve nominarlo."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rel = ".claude/agents/implementer.md"
            card = root / rel
            src = (FRAMEWORK / "agents" / "implementer.md").read_text(encoding="utf-8")
            model = re.search(r"^model:\s*(\S+)", src, re.MULTILINE).group(1)
            other = "opus" if model != "opus" else "sonnet"
            text = card.read_text(encoding="utf-8")
            card.write_text(text.replace(f"model: {model}", f"model: {other}", 1), encoding="utf-8")

            got = {op.path: op for op in lifecycle.plan_down(root, FRAMEWORK)}

            self.assertIn(f"model: {other} qui, {model} nel sorgente", got[rel].reason)
            self.assertNotIn("nel sorgente", got[".claude/agents/explorer.md"].reason)

    def test_down_refuses_a_plan_the_tree_has_outgrown(self):
        """Una skill che il piano sovrascrive e che è cambiata dopo l'ok non è
        più quella che l'utente ha visto sostituire: sovrascriverla perde il
        ritocco di dopo. Il rifiuto arriva prima del primo byte scritto."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rel = ".claude/skills/claw-sync/SKILL.md"
            skill = root / rel
            skill.write_text("name: claw-sync\nvecchia\n", encoding="utf-8")
            ops = lifecycle.plan_down(root, FRAMEWORK)
            self.assertEqual(actions(ops)[rel], lifecycle.OVERWRITE)
            skill.write_text("name: claw-sync\nvecchia, ritoccata dopo\n", encoding="utf-8")
            before = tree(root)
            with self.assertRaises(ValueError) as e:
                lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertIn(rel, str(e.exception))
            self.assertEqual(tree(root), before)

    def test_down_brings_guides_and_style_keeping_the_project_block(self):
        """Guide e stile non hanno regione kernel, e `--down` non li toccava: una
        regola nuova in una guida non arrivava a nessun progetto installato. Il
        testo viene dal sorgente, il blocco compilato dal progetto resta."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            cases = {}
            for rel, src in (
                (".claude/shared/core/review-checklist.md", "shared/core/review-checklist.md"),
                (".claude/output-styles/reporting.md", "output-styles/reporting.md"),
            ):
                text = (FRAMEWORK / src).read_text(encoding="utf-8")
                heading = lifecycle.project_heading(text)
                self.assertIsNotNone(heading, src)
                p = root / rel
                installed = p.read_text(encoding="utf-8")
                block = installed[installed.rindex(heading) :]
                self.assertIsNone(doctor.PLACEHOLDER_RE.search(block), rel)
                p.write_text("# Versione vecchia\n\nregola di prima\n\n" + block, encoding="utf-8")
                cases[rel] = text[: text.rindex(heading)] + block

            ops = lifecycle.plan_down(root, FRAMEWORK)
            for rel in cases:
                self.assertEqual(actions(ops)[rel], lifecycle.MERGE, rel)

            lifecycle.apply_update(root, FRAMEWORK, ops)

            for rel, expected in cases.items():
                self.assertEqual((root / rel).read_text(encoding="utf-8"), expected, rel)

    def test_down_keeps_a_guide_whose_project_block_is_gone(self):
        """Senza l'intestazione del blocco `--down` non sa cosa è del progetto, e
        sostituire il file intero cancellerebbe l'adattamento: resta com'è, e il
        piano lo nomina."""
        with tempfile.TemporaryDirectory() as d:
            root = install(d)
            rel = ".claude/shared/core/testing-guide.md"
            heading = lifecycle.project_heading(
                (FRAMEWORK / "shared" / "core" / "testing-guide.md").read_text(encoding="utf-8")
            )
            p = root / rel
            p.write_text(p.read_text(encoding="utf-8").replace(heading, "## Note mie"), encoding="utf-8")
            before = p.read_bytes()

            ops = lifecycle.plan_down(root, FRAMEWORK)
            got = {op.path: op for op in ops}
            self.assertEqual(got[rel].action, lifecycle.KEEP)
            self.assertIn("a mano", got[rel].reason)

            lifecycle.apply_update(root, FRAMEWORK, ops)
            self.assertEqual(p.read_bytes(), before)

    def test_every_placeholder_in_a_guide_sits_in_its_last_section(self):
        """`--down` riconosce il blocco di progetto dal segnaposto nell'ultima
        sezione. Una sezione aggiunta dopo il blocco lo sposterebbe, e quella
        guida smetterebbe di aggiornarsi nei progetti senza che niente cada."""
        paths = sorted((FRAMEWORK / "shared").rglob("*.md")) + sorted(
            (FRAMEWORK / "output-styles").glob("*.md")
        )
        for path in paths:
            text = path.read_text(encoding="utf-8")
            if doctor.PLACEHOLDER_RE.search(text):
                with self.subTest(path=path.relative_to(FRAMEWORK).as_posix()):
                    self.assertIsNotNone(lifecycle.project_heading(text))


if __name__ == "__main__":
    unittest.main()
