import json
import re
import tempfile
import unittest
from pathlib import Path

from fwbuild import assemble, doctor, kernel

AGENT_FM = "---\nname: {n}\nmodel: opus\neffort: high\n---\n"
# La versione del sorgente, non un letterale: `VERSION_MISMATCH` confronta il
# progetto col sorgente, e un valore fisso farebbe fallire la suite al primo
# bump di VERSION.
VERSION = (Path(__file__).resolve().parents[2] / "VERSION").read_text(
    encoding="utf-8"
).strip()


def make_project(
    tmp,
    *,
    agents=("explorer",),
    routing=("explorer",),
    placeholder=False,
    fable=False,
    state=True,
    orchestration=True,
    leak=False,
    skills=True,
    markers=True,
    settings=True,
    guides=(),
    manifest=True,
    accepted=None,
):
    root = Path(tmp)
    (root / ".claude" / "agents").mkdir(parents=True)
    (root / ".claude" / "shared").mkdir(parents=True)
    if manifest:
        data = {"source": "framework", "version": VERSION, "profile": "software"}
        if accepted is not None:
            data["accepted"] = accepted
        (root / ".claude" / "framework.json").write_text(
            json.dumps(data), encoding="utf-8"
        )
    if skills:
        for name in doctor.LIFECYCLE_SKILLS:
            d = root / ".claude" / "skills" / name
            d.mkdir(parents=True)
            (d / "SKILL.md").write_text(f"name: {name}\n", encoding="utf-8")
    if settings:
        (root / ".claude" / "settings.json").write_text("{}", encoding="utf-8")
    for rel in guides:
        g = root / ".claude" / "shared" / rel
        g.parent.mkdir(parents=True, exist_ok=True)
        g.write_text("# guida", encoding="utf-8")
    (root / "docs").mkdir(parents=True)
    rows = "\n".join(f"| dove | `{n}` | haiku |" for n in routing)
    if orchestration:
        # La tabella di routing vive nella guida del coordinatore, non in
        # CLAUDE.md: è contenuto che i subagent non devono pagare.
        (root / ".claude" / "shared" / "orchestration.md").write_text(
            assemble.build_document_from_text(
                "## Delega\n",
                VERSION,
                "| Situazione | Agente | Modello |\n|---|---|---|\n" + rows + "\n",
                markers=markers,
            ),
            encoding="utf-8",
        )
    project = "## Il progetto\n\nProgetto di prova.\n"
    if placeholder:
        project += "\n[DA COMPILARE] — mappa moduli\n"
    if leak:
        project += "\n## Il ciclo del codice\n\nExplorer, poi architect.\n"
    (root / "CLAUDE.md").write_text(
        assemble.build_document_from_text("## Metodo\n", VERSION, project, markers=markers),
        encoding="utf-8",
    )
    for n in agents:
        model = "fable" if fable else "opus"
        fm = AGENT_FM.format(n=n).replace("model: opus", f"model: {model}")
        (root / ".claude" / "agents" / f"{n}.md").write_text(
            assemble.build_agent(
                fm, "## Metodo\n", "## Dominio\n", VERSION, markers=markers
            ),
            encoding="utf-8",
        )
    if state:
        for f in ("TODO.md", "status.md", "roadmap.md"):
            (root / "docs" / f).write_text("# vuoto\n", encoding="utf-8")
    return root


def strip_markers(text):
    return re.sub(r"<!-- /?FRAMEWORK:KERNEL[^>]*-->", "", text)


def codes(findings):
    return {f.code for f in findings}


class TestDoctor(unittest.TestCase):
    def test_clean_project_has_no_findings(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(doctor.check(make_project(d)), [])

    def test_detects_placeholder(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, placeholder=True))
            self.assertIn("PLACEHOLDER", codes(found))

    def test_detects_agent_in_routing_without_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, agents=("explorer",), routing=("explorer", "frontend"))
            self.assertIn("ROSTER_MISSING", codes(doctor.check(p)))

    def test_detects_agent_file_not_in_routing(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, agents=("explorer", "frontend"), routing=("explorer",))
            self.assertIn("ROSTER_ORPHAN", codes(doctor.check(p)))

    def test_detects_kernel_drift(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / "CLAUDE.md"
            f.write_text(
                f.read_text(encoding="utf-8").replace("## Metodo", "## Altro"),
                encoding="utf-8",
            )
            self.assertIn("KERNEL_DRIFT", codes(doctor.check(p)))

    def test_detects_missing_state_files(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, state=False))
            self.assertIn("STATE_MISSING", codes(found))

    def test_detects_fable(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertIn("FABLE", codes(doctor.check(make_project(d, fable=True))))

    def test_skills_are_not_scanned_for_placeholders(self):
        """framework-doctor spiega il rilievo PLACEHOLDER e contiene per forza
        quella stringa: scansionarlo produrrebbe un falso positivo a ogni run."""
        with tempfile.TemporaryDirectory() as d:
            root = make_project(d)
            (root / ".claude" / "skills" / "framework-doctor" / "SKILL.md").write_text(
                "Il rilievo `PLACEHOLDER` segnala un `[DA COMPILARE]` residuo.\n",
                encoding="utf-8",
            )
            self.assertNotIn("PLACEHOLDER", codes(doctor.check(root)))

    def test_detects_a_declared_package_skill_that_is_not_there(self):
        """Le skill dei pacchetti stanno nel manifesto perché nel progetto
        arrivano appiattite e non si vede più da dove vengono. Senza questo
        controllo, un pacchetto che la sincronizzazione non ha portato è un
        pool che nomina una skill assente, e nessun rilievo lo dice."""
        with tempfile.TemporaryDirectory() as d:
            root = make_project(d)
            path = root / ".claude" / "framework.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["skills"] = {"alfa": "tizio-skills"}
            path.write_text(json.dumps(data), encoding="utf-8")
            found = [f for f in doctor.check(root) if f.code == "SKILLS_MISSING"]
            self.assertEqual(len(found), 1)
            self.assertIn("tizio-skills", found[0].message)

    def test_detects_missing_lifecycle_skills(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, skills=False))
            self.assertIn("SKILLS_MISSING", codes(found))

    def test_detects_missing_orchestration_guide(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, orchestration=False))
            self.assertIn("SHARED_MISSING", codes(found))

    def test_detects_coordinator_content_leaking_into_claude_md(self):
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, leak=True))
            self.assertIn("COORDINATOR_LEAK", codes(found))

    def test_detects_deploy_infra_conflict(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d,
                agents=("explorer", "deploy", "infra"),
                routing=("explorer", "deploy", "infra"),
            )
            self.assertIn("EXCLUSIVE", codes(doctor.check(p)))

    def test_detects_stripped_kernel_markers(self):
        """Togliere i marker non è meno grave che riscrivere il metodo dentro
        la regione: senza marker, il drift smette di essere visibile."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / ".claude" / "agents" / "explorer.md"
            f.write_text(strip_markers(f.read_text(encoding="utf-8")), encoding="utf-8")
            self.assertIn("KERNEL_MISSING", codes(doctor.check(p)))

    def test_installation_without_markers_is_not_flagged(self):
        """La variante senza tracking è una scelta legittima: nessun marker in
        nessun file tracciato, nessun rilievo."""
        with tempfile.TemporaryDirectory() as d:
            self.assertNotIn("KERNEL_MISSING", codes(doctor.check(make_project(d, markers=False))))

    def test_detects_dangling_shared_pointer_in_an_agent(self):
        """Quasi tutti i pointer alle guide vivono negli agenti: verificarli
        solo in CLAUDE.md lascia scoperta la maggioranza."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / ".claude" / "agents" / "explorer.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "Vedi `.claude/shared/core/assente.md`.",
                encoding="utf-8",
            )
            self.assertIn("SHARED_MISSING", codes(doctor.check(p)))

    def test_detects_unfilled_state_template(self):
        """Un template di stato copiato e non compilato è indistinguibile da
        uno stato assente per chi lo legge a inizio sessione."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / "docs" / "TODO.md").write_text(
                "- [ ] [DA COMPILARE — task attivo]", encoding="utf-8"
            )
            self.assertIn("PLACEHOLDER", codes(doctor.check(p)))

    def _rewrap(self, f, version):
        """Riscrive la regione kernel di un file a un'altra versione,
        lasciando l'hash coerente: è il caso che nessun altro check vede."""
        text = f.read_text(encoding="utf-8")
        r = kernel.parse(text)
        f.write_text(
            text[: r.start] + kernel.wrap(r.body, version) + text[r.end + 1 :],
            encoding="utf-8",
        )

    def test_detects_missing_settings_file(self):
        """`settings.json` porta i permessi del profilo, fra cui il divieto
        di leggere segreti: assente, quel divieto non esiste."""
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, settings=False))
            self.assertIn("SETTINGS_MISSING", codes(found))

    def test_detects_shared_guide_nobody_cites(self):
        """L'inverso di SHARED_MISSING: una guida installata e mai citata è
        contesto pagato e mai aperto."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, guides=("core/mai-citata.md",))
            self.assertIn("SHARED_ORPHAN", codes(doctor.check(p)))

    def test_cited_shared_guide_is_not_an_orphan(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, guides=("core/citata.md",))
            f = p / "CLAUDE.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "`.claude/shared/core/citata.md`",
                encoding="utf-8",
            )
            self.assertNotIn("SHARED_ORPHAN", codes(doctor.check(p)))

    def test_detects_missing_manifest(self):
        """Senza `framework.json` `framework-sync` non ritrova il sorgente e il
        rapporto di flotta non conta il progetto: non è un'installazione pulita."""
        with tempfile.TemporaryDirectory() as d:
            found = doctor.check(make_project(d, manifest=False))
            self.assertIn("MANIFEST_MISSING", codes(found))

    def test_detects_manifest_without_the_profile(self):
        """Senza il profilo, «rigenera i permessi del profilo» non si può eseguire."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / ".claude" / "framework.json").write_text(
                json.dumps({"source": "framework", "version": VERSION}),
                encoding="utf-8",
            )
            found = [f for f in doctor.check(p) if f.code == "MANIFEST_MISSING"]
            self.assertEqual([f.severity for f in found], ["WARN"])
            self.assertIn("profile", found[0].message)

    def test_template_syntax_is_not_a_placeholder(self):
        """`{{...}}` è la sintassi dei template di mezzo mondo: un progetto che
        la cita fra i propri vincoli prenderebbe un ERROR senza uscita."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / "CLAUDE.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "\nLe viste usano `{{ user.name }}`.\n",
                encoding="utf-8",
            )
            self.assertNotIn("PLACEHOLDER", codes(doctor.check(p)))

    def test_categorical_confidence_with_a_percentage_is_not_the_old_format(self):
        """Il formato superato è la confidenza **come** percentuale. Un giudizio
        categorico che cita un 80% nel motivo è testo legittimo."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / "docs" / "status.md").write_text(
                "CONF: ALTA — copertura all'80% sul modulo\n", encoding="utf-8"
            )
            self.assertNotIn("REPORT_FORMAT", codes(doctor.check(p)))
            (p / "docs" / "status.md").write_text("CONF: 85%\n", encoding="utf-8")
            self.assertIn("REPORT_FORMAT", codes(doctor.check(p)))

    def test_accepted_warning_becomes_a_note(self):
        """La valvola: un avviso che il progetto dichiara di accettare resta
        stampato e smette di bloccare, invece di tenere rossa una CI per
        sempre finché qualcuno impara a ignorarla."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d,
                guides=("core/mai-citata.md",),
                accepted={"SHARED_ORPHAN": "voluta, la cita solo un agente futuro"},
            )
            found = [f for f in doctor.check(p) if f.code == "SHARED_ORPHAN"]
            self.assertEqual([f.severity for f in found], ["NOTE"])
            self.assertFalse([f for f in found if f.blocking])

    def test_accepted_does_not_cover_errors(self):
        """Un avviso è un giudizio, e su un giudizio un progetto può avere
        ragione. Un errore è un'installazione rotta: resta rotta."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d, placeholder=True, accepted={"PLACEHOLDER": "ci convivo"}
            )
            found = doctor.check(p)
            self.assertIn("PLACEHOLDER", {f.code for f in found if f.severity == "ERROR"})
            self.assertIn("ACCEPTED_UNUSED", codes(found))

    def test_accepted_without_a_reason_does_not_apply(self):
        """Una deroga senza motivo non è una deroga: si vede, non si applica."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(
                d, guides=("core/mai-citata.md",), accepted={"SHARED_ORPHAN": "  "}
            )
            found = doctor.check(p)
            self.assertIn("SHARED_ORPHAN", {f.code for f in found if f.severity == "WARN"})
            self.assertIn("ACCEPTED_UNUSED", codes(found))

    def test_accepted_that_matches_nothing_is_reported(self):
        """Una deroga sopravvissuta al suo rilievo zittisce il prossimo."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, accepted={"TOKEN_BUDGET": "monorepo"})
            self.assertEqual(codes(doctor.check(p)), {"ACCEPTED_UNUSED"})

    def test_accepted_can_be_scoped_to_one_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d, accepted={"KERNEL_DRIFT:CLAUDE.md": "deroga locale"})
            f = p / "CLAUDE.md"
            f.write_text(
                f.read_text(encoding="utf-8").replace("## Metodo", "## Altro"),
                encoding="utf-8",
            )
            found = [f for f in doctor.check(p) if f.code == "KERNEL_DRIFT"]
            self.assertEqual([f.severity for f in found], ["NOTE"])

    def test_detects_version_skew_between_documents(self):
        """Due documenti dello stesso progetto a versioni diverse: l'hash
        torna su entrambi, perché torna ognuno sul proprio metodo."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            self._rewrap(p / ".claude" / "agents" / "explorer.md", "0.3.0")
            self.assertIn("VERSION_MISMATCH", codes(doctor.check(p)))

    def test_detects_a_manifest_left_on_the_previous_version(self):
        """La versione di `framework.json` è quella che si legge senza aprire un
        documento generato — il rapporto di flotta parte da lì: se resta a
        quella di prima, il rilievo lo dice."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            path = p / ".claude" / "framework.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["version"] = "0.3.0"
            path.write_text(json.dumps(data), encoding="utf-8")
            found = [f for f in doctor.check(p) if f.code == "VERSION_MISMATCH"]
            self.assertEqual([f.severity for f in found], ["WARN"])
            self.assertIn("framework.json", found[0].message)

    def test_detects_installation_behind_the_source(self):
        """Metodo vecchio ma internamente coerente: è la biforcazione fra
        progetti, e l'hash non la vede."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            tracked = [p / "CLAUDE.md", p / ".claude" / "shared" / "orchestration.md"]
            tracked += list((p / ".claude" / "agents").glob("*.md"))
            for f in tracked:
                self._rewrap(f, "0.3.0")
            self.assertEqual(codes(doctor.check(p)), {"VERSION_MISMATCH"})

    def test_detects_bidi_control_in_an_agent(self):
        """Un controllo bidirezionale rovescia a video il testo che segue: il
        modello legge un'istruzione, chi rivede la scheda ne vede un'altra."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            f = p / ".claude" / "agents" / "explorer.md"
            f.write_text(
                f.read_text(encoding="utf-8") + "Leggi \u202evne.\n", encoding="utf-8"
            )
            self.assertIn("UNSAFE_UNICODE", codes(doctor.check(p)))

    def test_emoji_variation_selector_and_leading_bom_are_not_unsafe(self):
        """U+FE0F compone le emoji e sta nel sorgente stesso; il BOM a inizio
        file lo scrivono gli editor. Segnalarli farebbe cadere `--strict` su
        un'installazione sana."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / "docs" / "status.md").write_text(
                "\ufeff# Stato\n\nChiuso \u2714\ufe0f\n", encoding="utf-8"
            )
            self.assertNotIn("UNSAFE_UNICODE", codes(doctor.check(p)))

    def test_detects_personal_path_but_not_a_placeholder(self):
        """Una cartella utente non esiste sulla macchina di chi clona; il
        `YourName` di un esempio non è di nessuno. `settings.json` è JSON, e il
        JSON raddoppia le barre."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            settings = p / ".claude" / "settings.json"
            home = "C:" + "\\Users\\"
            settings.write_text(
                json.dumps({"env": {"PRJ": home + "YourName"}}), encoding="utf-8"
            )
            self.assertNotIn("PERSONAL_PATH", codes(doctor.check(p)))
            settings.write_text(
                json.dumps({"env": {"PRJ": home + "mrossi"}}), encoding="utf-8"
            )
            self.assertIn("PERSONAL_PATH", codes(doctor.check(p)))

    def test_shared_user_folders_are_not_personal_and_case_does_not_hide_one(self):
        """`Public`, `Shared`, `Default`, `All Users` stanno su ogni macchina e
        non sono di nessuno; su Windows `c:\\users\\` è la stessa cartella di
        `C:\\Users\\`."""
        shared = (
            "C:" + "/Users/" + "Public",
            "/Users/" + "Shared",
            "C:" + "\\Users\\" + "Default",
            "C:" + "\\Users\\" + "All Users",
        )
        for text in shared:
            with self.subTest(text=text):
                self.assertIsNone(doctor.PERSONAL_PATH_RE.search(text))
        self.assertIsNotNone(doctor.PERSONAL_PATH_RE.search("c:" + "\\users\\" + "mrossi"))

    def test_a_scanned_file_that_is_not_utf8_is_still_scanned(self):
        """Skill e hook dell'utente si scansionano e basta: uno salvato in
        cp1252 non deve far cadere il doctor, né `fwbuild report`."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            home = ("C:" + "\\Users\\" + "mrossi").encode("utf-8")
            hooks = p / ".claude" / "hooks"
            hooks.mkdir()
            (hooks / "mio.py").write_bytes(b"# citt\xe0\n")
            (p / ".claude" / "skills" / "framework-doctor" / "SKILL.md").write_bytes(
                b"name: framework-doctor\ncitt\xe0 " + home + b"\n"
            )
            self.assertEqual(codes(doctor.check(p)), {"PERSONAL_PATH"})

    def test_absolute_source_in_manifest_is_not_a_personal_path(self):
        """Col sorgente fuori dal progetto `source` è assoluto per costruzione:
        il relativo non regge, perché la profondità del clone non è nota."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            (p / ".claude" / "framework.json").write_text(
                json.dumps(
                    {
                        "source": "C:" + "\\Users\\" + "mrossi" + "\\framework",
                        "version": VERSION,
                        "profile": "software",
                    }
                ),
                encoding="utf-8",
            )
            self.assertNotIn("PERSONAL_PATH", codes(doctor.check(p)))

    def test_an_uninstall_archive_is_not_checked(self):
        """L'archivio conserva le schede come erano, segnaposti e pointer
        compresi: è materiale da consultare, non installazione. Scandirlo
        darebbe errori che nessun intervento sul progetto può togliere."""
        with tempfile.TemporaryDirectory() as d:
            p = make_project(d)
            old = p / doctor.ARCHIVE_DIR / ".claude" / "agents" / "vecchio.md"
            old.parent.mkdir(parents=True)
            old.write_text(
                "[DA COMPILARE]\nVedi `.claude/shared/core/perduta.md`.\n",
                encoding="utf-8",
            )
            self.assertEqual(doctor.check(p), [])


if __name__ == "__main__":
    unittest.main()
