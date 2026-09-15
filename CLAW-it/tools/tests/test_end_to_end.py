import io
import json
import re
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import trial_install
from fwbuild import assemble, cli, doctor, kernel, lifecycle, profile, settings, source

FRAMEWORK = Path(__file__).resolve().parents[2]
SURFACE_ONLY = {"compliance-reviewer", "perf-analyst"}
CONF_PERCENT_RE = re.compile(r"CONF:.*%")


class TestRealFramework(unittest.TestCase):
    def test_version_file_exists(self):
        self.assertTrue((FRAMEWORK / "VERSION").is_file())

    def test_all_twenty_nine_agents_present(self):
        self.assertEqual(len(list((FRAMEWORK / "agents").glob("*.md"))), 29)

    def test_no_agent_declares_fable(self):
        for p in (FRAMEWORK / "agents").glob("*.md"):
            self.assertNotIn("model: fable", p.read_text(encoding="utf-8"), p.name)

    def test_architect_is_opus_xhigh(self):
        text = (FRAMEWORK / "agents" / "architect.md").read_text(encoding="utf-8")
        self.assertIn("model: opus", text)
        self.assertIn("effort: xhigh", text)

    def test_agent_colors_are_platform_values(self):
        """`color` ha otto valori documentati. Una configurazione che la
        piattaforma non riconosce non fallisce, viene ignorata, che è il modo in
        cui resta sbagliata per sempre."""
        valid = {"red", "blue", "green", "yellow", "purple", "orange", "pink", "cyan"}
        for path in sorted((FRAMEWORK / "agents").glob("*.md")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.startswith("color:"):
                    self.assertIn(line.split(":", 1)[1].strip(), valid, path.name)
                    break

    def test_read_only_reviewers_have_no_shell(self):
        """«Non modifica il codice» sopra una shell è una promessa, non una
        garanzia. Per chi non deve eseguire niente, toglierla la rende la
        configurazione della scheda."""
        for name in (
            "security-reviewer",
            "compliance-reviewer",
            "data-quality-reviewer",
            "scientific-reviewer",
            "claim-reviewer",
        ):
            text = (FRAMEWORK / "agents" / f"{name}.md").read_text(encoding="utf-8")
            self.assertIn("tools: Read, Grep, Glob\n", text, name)

    def test_every_profile_denies_the_same_secrets(self):
        """Un permesso che dipende dal campo è un permesso che qualcuno ha
        dimenticato di copiare."""
        needed = {
            "Read(./**/.env)",
            "Read(./**/.env.*)",
            "Read(./**/*.env)",
            "Read(./**/*.key)",
            "Read(./**/*.pem)",
        }
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            prof = profile.load(path)
            deny = set(prof.settings["permissions"]["deny"])
            self.assertEqual(needed - deny, set(), prof.name)

    def test_state_templates_use_one_placeholder_syntax(self):
        """Il doctor riconosce una sola sintassi di segnaposto: una seconda
        lascerebbe sopravvivere all'installazione una riga da riempire, senza
        rilievo."""
        for name in ("TODO.md", "status.md", "roadmap.md"):
            text = (FRAMEWORK / "templates" / name).read_text(encoding="utf-8")
            self.assertNotIn("{{", text, name)
            for line in text.splitlines():
                self.assertFalse(line.strip().startswith("<"), f"{name}: {line}")

    def test_profiles_declare_no_deferred_roster(self):
        """Nessun campo per gli agenti «da installare più tardi»: `roster`
        installa tutto ciò che il profilo elenca, e il campo direbbe il
        contrario di quello che fa."""
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            self.assertNotIn("on_demand", path.read_text(encoding="utf-8"), path.name)

    def test_every_agent_splits_and_assembles(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        for p in sorted((FRAMEWORK / "agents").glob("*.md")):
            fm, method, domain = assemble.split_source(p.read_text(encoding="utf-8"))
            built = assemble.build_agent(fm, method, domain, version)
            self.assertEqual(kernel.verify(built), "OK", p.name)
            self.assertIn("[DA COMPILARE", domain, p.name)

    def test_kernel_assembles_and_verifies(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        out = assemble.build_document(FRAMEWORK / "method", version, "## Il progetto\n\nX\n")
        self.assertEqual(kernel.verify(out), "OK")

    def test_coordinator_guide_assembles_and_verifies(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        out = assemble.build_document(FRAMEWORK / "coordinator", version, "## Roster\n\nX\n")
        self.assertEqual(kernel.verify(out), "OK")

    def test_kernel_has_no_placeholders(self):
        for d in ("method", "coordinator"):
            text = assemble.read_method(FRAMEWORK / d)
            self.assertNotIn("DA COMPILARE", text, d)
            self.assertNotIn("{{", text, d)

    def test_coordinator_content_is_not_in_common_kernel(self):
        """Il kernel comune è pagato da ogni subagent a ogni spawn: ciò che
        serve solo a chi delega non deve finirci. La lista dei titoli è quella
        del doctor, non una copia: due liste divergono in silenzio."""
        common = assemble.read_method(FRAMEWORK / "method")
        for heading in doctor.COORDINATOR_ONLY:
            self.assertNotIn(heading, common, heading)

    def test_watched_headings_still_exist_where_they_belong(self):
        """COORDINATOR_LEAK confronta stringhe: se un titolo viene rinominato
        alla fonte, il check smette di vedere la sezione senza far fallire
        niente. Questo test è ciò che rende visibile il rinomino."""
        sources = (
            assemble.read_method(FRAMEWORK / "coordinator")
            + (FRAMEWORK / "skills" / "framework-install" / "SKILL.md").read_text(
                encoding="utf-8"
            )
            + assemble.read_method(FRAMEWORK / "orchestrations")
        )
        for heading in doctor.COORDINATOR_ONLY:
            self.assertIn(heading, sources, heading)

    def test_coordinator_guide_stays_under_budget(self):
        """Anche la guida del coordinatore ha un tetto: è on-demand, non pagata
        a ogni spawn, ma senza soglia è il prossimo posto dove il metodo si
        gonfia. Si misura l'artefatto reale, cicli del profilo inclusi, con
        ogni orchestrazione: la sceglie chi installa, non il profilo."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            for orch in sorted((FRAMEWORK / "orchestrations").glob("*.md")):
                text = assemble.read_method(
                    FRAMEWORK / "coordinator",
                    [orch, *assemble.cycle_files(FRAMEWORK, prof.cycles)],
                )
                self.assertLess(
                    len(text.split()),
                    assemble.COORDINATOR_WORD_BUDGET,
                    f"{prof.name} + {orch.stem}",
                )

    def test_common_kernel_stays_under_budget(self):
        """Soglia sul costo pagato a ogni spawn. Se la supera, non si aggiunge:
        si sposta in shared/ o si comprime."""
        self.assertLess(
            len(assemble.read_method(FRAMEWORK / "method").split()),
            assemble.METHOD_WORD_BUDGET,
        )

    def test_ten_delegation_rules_are_complete_and_in_one_place(self):
        coord = assemble.read_method(FRAMEWORK / "coordinator")
        numbered = re.findall(r"^(\d+)\. \*\*", coord, re.MULTILINE)
        self.assertEqual([int(n) for n in numbered[:10]], list(range(1, 11)))

    def test_variant_b_has_no_markers(self):
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        for d, sentinel in (("method", "Evidence Before Action"), ("coordinator", "delega")):
            out = assemble.build_document(
                FRAMEWORK / d, version, "## Il progetto\n\nX\n", markers=False
            )
            self.assertNotIn("FRAMEWORK:KERNEL", out, d)
            self.assertIn(sentinel, out, d)
            self.assertIn("Il progetto", out, d)

    def test_every_profile_resolves_to_existing_agents(self):
        available = {p.stem for p in (FRAMEWORK / "agents").glob("*.md")}
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            names = profile.roster(prof, [], [])
            self.assertEqual([n for n in names if n not in available], [], prof.name)
            self.assertEqual(profile.check_exclusive(names), [], prof.name)

    def test_every_declared_cycle_exists(self):
        """Un ciclo dichiarato in un profilo e assente da cycles/ farebbe
        promettere al profilo un metodo che il progetto non riceve."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            assemble.cycle_files(FRAMEWORK, prof.cycles)  # solleva se manca

    def test_no_orphan_cycle_files(self):
        declared = set()
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            declared |= set(profile.load(path).cycles)
        on_disk = {p.stem for p in (FRAMEWORK / "cycles").glob("*.md")}
        self.assertEqual(on_disk - declared, set(), "cicli su disco che nessun profilo usa")

    def test_every_named_orchestration_exists(self):
        """Il default, le raccomandazioni dei profili e le chiavi dei settings
        nominano moduli per nome: un nome senza file rompe l'installazione di
        chi lo sceglie, e le chiavi orfane accenderebbero una variabile per
        un'orchestrazione che nessuno può installare."""
        assemble.orchestration_file(FRAMEWORK, assemble.DEFAULT_ORCHESTRATION)
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            for name in profile.load(path).recommended_orchestrations:
                assemble.orchestration_file(FRAMEWORK, name)  # solleva se manca
        for name in settings.ORCHESTRATION_SETTINGS:
            assemble.orchestration_file(FRAMEWORK, name)

    def test_orchestration_headings_are_recognizable(self):
        """`installed_orchestration` riconosce un modulo dal primo titolo dentro
        la regione: se quel titolo comparisse nel kernel del coordinatore, in un
        ciclo o in un altro modulo, `--down` troverebbe un'orchestrazione che il
        progetto non ha, o due, e riscriverebbe la guida sbagliata. Vale anche
        il verso opposto: il titolo di un ciclo dentro un modulo farebbe
        trovare a `installed_cycles` un ciclo che il profilo non ha."""
        modules = sorted((FRAMEWORK / "orchestrations").glob("*.md"))
        self.assertGreaterEqual(len(modules), 2)
        coordinator = assemble.read_method(FRAMEWORK / "coordinator")
        cycles = assemble.read_method(FRAMEWORK / "cycles")
        for p in modules:
            heading = p.read_text(encoding="utf-8").lstrip().splitlines()[0]
            self.assertTrue(heading.startswith("## "), p.name)
            others = "\n".join(
                q.read_text(encoding="utf-8") for q in modules if q != p
            )
            for where, text in (
                ("coordinator/", coordinator),
                ("cycles/", cycles),
                ("altri moduli", others),
            ):
                self.assertNotIn(heading, text, f"{p.name} in {where}")
        all_modules = assemble.read_method(FRAMEWORK / "orchestrations")
        for c in sorted((FRAMEWORK / "cycles").glob("*.md")):
            heading = c.read_text(encoding="utf-8").lstrip().splitlines()[0]
            self.assertNotIn(heading, all_modules, f"{c.name} in orchestrations/")

    def test_every_profile_shared_guide_exists(self):
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            for rel in prof.shared:
                self.assertTrue((FRAMEWORK / "shared" / rel).is_file(), f"{prof.name}: {rel}")

    def test_surface_only_agents_are_in_no_profile(self):
        """Conformità e prestazioni non sono campi: un progetto software può
        trattare dati personali e un altro no. Chi le presidia lo sceglie la
        domanda sulla superficie critica, non il profilo: metterli in un profilo
        li installerebbe in ogni progetto del campo, come costo fisso."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            leaked = SURFACE_ONLY & set(prof.agents)
            self.assertEqual(leaked, set(), f"{prof.name}: {leaked} lo sceglie la domanda 2")

    def test_surface_only_agents_are_reachable_from_the_question(self):
        """Fuori da ogni profilo, la domanda 2 è la loro **unica** via d'ingresso.
        Se una riga della tabella sparisce, l'agente resta in catalogo e non lo
        raggiunge più nessuno: installato mai, e nessun rilievo che lo dica."""
        skill = (FRAMEWORK / "skills" / "framework-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        blocco = skill[skill.index("**2. Superficie critica**") : skill.index("**3. Base")]
        for name in sorted(SURFACE_ONLY):
            self.assertIn(f"`{name}`", blocco, name)

    def test_question_one_offers_every_profile(self):
        """La domanda 1 è l'unica via per scegliere un profilo, e la tabella è
        scritta a mano: un profilo senza la sua riga non si
        può scegliere, e nessun rilievo lo vede — il difetto sta nella skill,
        prima che un'installazione esista."""
        skill = (FRAMEWORK / "skills" / "framework-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        blocco = skill[
            skill.index("**1. Campo del progetto**") : skill.index("**2. Superficie critica**")
        ]
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            self.assertIn(f"| `{profile.load(path).name}` |", blocco, path.name)

    def test_exclusive_pairs_declare_their_boundary(self):
        """`EXCLUSIVE` è una guardia, non una spiegazione: dice che i due non
        convivono, non dove passa la linea. Se la linea vive solo nel check, un
        agente attivato a mano arriva senza sapere cosa non è suo — e la
        riga di confine è proprio il genere di prosa che sparisce a una
        riscrittura, senza che niente lo veda."""
        for a, b in profile.EXCLUSIVE:
            for one, other in ((a, b), (b, a)):
                text = (FRAMEWORK / "agents" / f"{one}.md").read_text(encoding="utf-8")
                self.assertIn(f"`{other}`", text, f"{one} non nomina {other}")
                flat = " ".join(text.split())
                self.assertIn("mai entrambi", flat, one)

    def test_critical_surface_table_routes_to_agents_that_exist(self):
        """La domanda 2 del questionario è una tabella di routing, e ha lo stesso
        modo di rompersi di quella del coordinatore: rinominare un agente lascia
        in piedi la riga che lo cita, e chi installa sceglie una risposta che non
        porta a nessun file. Il doctor qui non può aiutare: il difetto sta nella
        skill, prima che un'installazione esista."""
        skill = (FRAMEWORK / "skills" / "framework-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        blocco = skill[skill.index("**2. Superficie critica**") : skill.index("**3. Base")]
        # Più permissivo di `doctor.ROUTING_AGENT_RE`, e di proposito: quello accetta
        # solo minuscole, quindi un rinomino con una maiuscola sfuggirebbe alla
        # riga invece di farla fallire.
        revisori = re.findall(r"^\|[^|]*\|\s*`([^`]+)`\s*\|$", blocco, re.MULTILINE)
        self.assertGreaterEqual(len(revisori), 3, "tabella dei revisori non letta")
        for name in revisori:
            self.assertTrue((FRAMEWORK / "agents" / f"{name}.md").is_file(), name)

    def test_the_install_skill_protects_material_that_was_already_there(self):
        """L'installazione è l'unico passo che può cancellare lavoro altrui:
        `CLAUDE.md` lo scrive e i tre template li copia in `docs/`. Su un
        progetto che aveva già istruzioni, la regola che lo impedisce vive solo
        nella prosa della skill — sparirebbe a una riscrittura, e il difetto si
        vedrebbe a file già persi, sulla macchina di chi installa."""
        text = (FRAMEWORK / "skills" / "framework-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        blocco = text[
            text.index("### Materiale preesistente") : text.index(
                "### `CLAUDE.md` — sezioni di progetto"
            )
        ]
        for path in (
            "CLAUDE.md",
            "TODO.md",
            "status.md",
            "roadmap.md",
            ".claude/skills/",
            ".claude/settings.json",
            ".claude/output-styles/",
            ".claude/hooks/",
        ):
            self.assertIn(path, blocco, path)

    def test_final_reviewer_asks_for_the_uncovered_critical_surface(self):
        """Le superfici senza revisore dedicato (contratto pubblico,
        accessibilità) non hanno un agente e non devono averne uno: finiscono
        nel mandato di chi verifica per ultimo. Se il segnaposto smette di
        chiederle, chi installa non le scrive e la superficie sparisce."""
        text = (FRAMEWORK / "agents" / "final-reviewer.md").read_text(encoding="utf-8")
        _, _, domain = assemble.split_source(text)
        self.assertIn("superficie critica", domain)

    def test_the_memory_skill_pairs_every_conflict_with_the_repo(self):
        """La memoria è fuori dal repository: nessun rilievo la vede, e un
        conflitto dichiarato senza la riga che lo smentisce diventa un allarme
        inventato che sopravvive alle sessioni. La colonna appaiata è l'unica
        cosa che lo impedisce, ed è prosa: sparirebbe a una riscrittura."""
        text = (FRAMEWORK / "skills" / "framework-memory" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        blocco = text[text.index("## Passo 4") : text.index("## Passo 5")]
        self.assertIn("| il repo dice |", blocco)
        self.assertIn("non si scrive", blocco)

    def test_every_skill_is_present_with_matching_name(self):
        for name in (
            "framework-install",
            "framework-doctor",
            "framework-sync",
            "framework-memory",
            "framework-comply",
        ):
            p = FRAMEWORK / "skills" / name / "SKILL.md"
            self.assertTrue(p.is_file(), name)
            self.assertIn(f"name: {name}", p.read_text(encoding="utf-8"))

    def test_promoting_from_a_stale_project_is_forbidden(self):
        """Due progetti sullo stesso sorgente promuovono a turno. Chi promuove
        da un'installazione rimasta indietro ha una regione che differisce dal
        sorgente per due motivi: la propria modifica e quella che l'altro ha
        gia' promosso. Il passo 1 confronta due alberi e non li distingue,
        quindi senza la precondizione la seconda sparisce senza un rilievo.

        Il drift copre solo cio' che ha una regione kernel: una guida nuova in
        `shared/` non ne ha, e senza la riga che la nomina resta invisibile
        proprio al caso piu' comune, l'aggiunta."""
        text = (FRAMEWORK / "skills" / "framework-sync" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        blocco = text[text.index("## `--up") : text.index("## `--upgrade")]
        self.assertIn("allineato", blocco)
        self.assertIn("`.claude/framework.json`", blocco)
        self.assertIn("una cosa alla volta", blocco)
        self.assertIn("non vede i file nuovi", blocco)

    def test_state_templates_present(self):
        for name in ("TODO.md", "status.md", "roadmap.md"):
            self.assertTrue((FRAMEWORK / "templates" / name).is_file(), name)

    def test_every_profile_selects_the_style_that_exists(self):
        """`outputStyle` nomina lo stile per **nome**, non per percorso: se il
        frontmatter viene rinominato da un lato solo, Claude Code non trova
        nulla e ricade sul Default senza dirlo. Lo stile resta installato, la
        comunicazione torna quella di prima, e nessun rilievo lo vede.

        Serve anche `keep-coding-instructions`: senza, uno stile custom
        **toglie** le istruzioni native di software engineering."""
        text = (FRAMEWORK / "output-styles" / "reporting.md").read_text(
            encoding="utf-8"
        )
        nome = re.search(r"^name:\s*(.+)$", text, re.MULTILINE).group(1).strip()
        self.assertIn("keep-coding-instructions: true", text)
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            self.assertEqual(
                profile.load(path).settings.get("outputStyle"), nome, path.name
            )

    def test_an_unfilled_response_style_is_a_finding(self):
        """Lo stile non ha regione kernel e non è tracciato: l'unica cosa che
        pretende l'adattamento è che `_markdown_files` lo scandisca. Restringere
        quella lista (esclude skill e archivio) spegnerebbe il controllo senza
        rompere niente, e il blocco di progetto resterebbe vuoto sul disco di
        chi installa."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "prova"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root)
            rel = ".claude/output-styles/reporting.md"
            self.assertEqual(doctor.check(root), [])
            (root / rel).write_text(
                (FRAMEWORK / "output-styles" / "reporting.md").read_text(
                    encoding="utf-8"
                ),
                encoding="utf-8",
            )
            codici = [(f.code, f.message) for f in doctor.check(root)]
            self.assertIn(("PLACEHOLDER", f"{rel}: segnaposto non compilato"), codici)

    def test_review_checklist_keeps_generic_block_separable(self):
        text = (FRAMEWORK / "shared" / "core" / "review-checklist.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("## Blocco generico", text)
        self.assertIn("## Blocco di progetto", text)
        self.assertLess(text.index("## Blocco generico"), text.index("## Blocco di progetto"))

    def test_report_confidence_is_categorical_not_a_percentage(self):
        """La confidenza auto-riportata da un LLM è mal calibrata: una
        percentuale mette precisione finta nella posizione che il coordinatore
        legge per prima. Il formato vive in un punto solo di tutto il
        framework, e un punto solo si riscrive per distrazione: questo test è
        ciò che impedisce al formato vecchio di tornare senza che nessuno lo
        veda."""
        for p in FRAMEWORK.rglob("*.md"):
            self.assertNotRegex(p.read_text(encoding="utf-8"), CONF_PERCENT_RE, str(p))

    def test_report_schema_carries_a_falsifier(self):
        """`SMENTIRE` è ciò che rende utile un giudizio categorico: senza, il
        coordinatore legge un'etichetta e non sa cosa la smentirebbe."""
        text = assemble.read_method(FRAMEWORK / "method")
        self.assertIn("CONF: ALTA | MEDIA | BASSA", text)
        self.assertIn("SMENTIRE:", text)

    def test_no_reference_to_source_projects(self):
        forbidden = ("RPLAN", "AbletonLoader", "FindShop", "Avalonia", "Typesense", "CVCS")
        for p in FRAMEWORK.rglob("*.md"):
            text = p.read_text(encoding="utf-8")
            for word in forbidden:
                self.assertNotIn(word, text, f"{p.name} cita {word}")

    def test_the_source_ships_no_personal_path_and_no_hidden_character(self):
        """Il doctor guarda l'installazione, ma ciò che vi trova arriva quasi
        sempre dal sorgente, che si copia alla lettera. Le regex sono le sue:
        una copia divergerebbe in silenzio. I test compresi — per questo i
        loro percorsi si costruiscono per concatenazione e i caratteri sono
        escape."""
        for p in sorted(FRAMEWORK.rglob("*")):
            if not p.is_file() or p.suffix not in {".md", ".py", ".toml", ".json", ".jsonl"}:
                continue
            text = p.read_text(encoding="utf-8")
            rel = p.relative_to(FRAMEWORK).as_posix()
            self.assertNotRegex(text, doctor.PERSONAL_PATH_RE, rel)
            self.assertNotRegex(text, doctor.UNSAFE_CHARS_RE, rel)

    def test_sync_down_preserves_domain_cycles(self):
        """La procedura `--down` riassembla la guida del coordinatore dal
        sorgente: se non ripassa i cicli, un progetto `web` perde il ciclo del
        design a ogni aggiornamento, in silenzio e senza rilievi."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        prof = profile.load(FRAMEWORK / "profiles" / "web.toml")
        installed = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            "## Roster di questo progetto",
            extra=assemble.cycle_files(FRAMEWORK, prof.cycles),
        )
        region = kernel.parse(installed)
        rebuilt = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            installed[region.end :],
            extra=assemble.installed_cycles(region.body, FRAMEWORK),
        )
        self.assertIn("Il ciclo del design", rebuilt)

    def test_sync_down_preserves_the_orchestration(self):
        """Come i cicli, l'orchestrazione sta dentro la regione e nessun file
        dice quale sia: `--down` la deve ritrovare, nello stesso ordine, perché
        la regione riassemblata verifichi. Una regione in cui non se ne
        riconosce nessuna si rifiuta: il default al suo posto nasconderebbe un
        titolo rinominato."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        prof = profile.load(FRAMEWORK / "profiles" / "web.toml")
        teams = assemble.orchestration_file(FRAMEWORK, "agent-teams")
        installed = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            "## Roster di questo progetto",
            extra=[teams, *assemble.cycle_files(FRAMEWORK, prof.cycles)],
        )
        region = kernel.parse(installed)
        rebuilt = assemble.build_document(
            FRAMEWORK / "coordinator",
            version,
            installed[region.end :],
            extra=[
                assemble.installed_orchestration(region.body, FRAMEWORK),
                *assemble.installed_cycles(region.body, FRAMEWORK),
            ],
        )
        self.assertIn("## Orchestrazione: Agent teams", rebuilt)
        self.assertIn("Il ciclo del design", rebuilt)
        self.assertEqual(kernel.verify(rebuilt), "OK")
        self.assertEqual(kernel.parse(rebuilt).body, region.body)

        without = assemble.build_document(
            FRAMEWORK / "coordinator", version, "## Roster di questo progetto"
        )
        with self.assertRaises(ValueError):
            assemble.installed_orchestration(kernel.parse(without).body, FRAMEWORK)

    def test_unfilled_roadmap_is_detectable(self):
        """Un template di stato con scheletro non compilato è indistinguibile
        da uno stato assente per chi lo legge a inizio sessione: deve
        contenere un segnaposto che il doctor riconosce."""
        text = (FRAMEWORK / "templates" / "roadmap.md").read_text(encoding="utf-8")
        self.assertRegex(text, doctor.PLACEHOLDER_RE)

    def test_status_template_is_deliberately_not_a_placeholder(self):
        """`status.md` nasce vuoto per costruzione — ci si scrive quando
        qualcosa si chiude. Segnalarlo renderebbe il Passo 6 impossibile da
        superare a installazione appena fatta."""
        text = (FRAMEWORK / "templates" / "status.md").read_text(encoding="utf-8")
        self.assertNotRegex(text, doctor.PLACEHOLDER_RE)


class TestInstalledBudget(unittest.TestCase):
    """`TOKEN_BUDGET`: la soglia sulla parte che il sorgente non vede."""

    def _installed(self, d, extra_words):
        root = Path(d) / "prova"
        with redirect_stdout(io.StringIO()):
            trial_install.install(root)
        if extra_words:
            claude = root / "CLAUDE.md"
            claude.write_text(
                claude.read_text(encoding="utf-8")
                + "\n## Extra\n\n"
                + ("parola " * extra_words)
                + "\n",
                encoding="utf-8",
            )
        return root

    def test_measure_separates_kernel_from_project_sections(self):
        """Le due parti hanno discipline opposte — una col tetto sul sorgente,
        l'altra senza nessun tetto — e la misura è ciò che le distingue. Se
        tornassero indistinte, il rilievo guarderebbe il totale e non direbbe
        di chi è la crescita."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        text = assemble.build_document(
            FRAMEWORK / "method", version, "## Il progetto\n\nuno due tre\n"
        )
        m = doctor.measure(text)
        self.assertTrue(m.has_region)
        self.assertEqual(
            m.kernel_words, len(assemble.read_method(FRAMEWORK / "method").split())
        )
        self.assertEqual(m.project_words, 6)
        self.assertEqual(m.total_words, m.kernel_words + 6)

    def test_measure_does_not_invent_a_split_without_markers(self):
        """La variante senza marker è legittima. Attribuire tutto al progetto
        farebbe scattare il rilievo su un'installazione sana."""
        m = doctor.measure("## Il progetto\n\nuno due tre\n")
        self.assertFalse(m.has_region)
        self.assertEqual(m.project_words, 0)

    def test_a_small_file_is_below_the_floor_and_stays_quiet(self):
        """Il rapporto su un file minuscolo è vero e irrilevante: un avviso sul
        costo di undici token è rumore, e un avviso che scatta sempre non lo
        legge più nessuno."""
        version = (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip()
        text = assemble.build_document_from_text(
            "## Metodo\n\nuno\n", version, "## Il progetto\n\n" + ("x " * 50) + "\n"
        )
        m = doctor.measure(text)
        self.assertGreater(m.project_words, m.kernel_words)
        self.assertLess(m.total_words, assemble.METHOD_WORD_BUDGET)

    def test_a_normal_install_is_under_budget(self):
        """Se il rilievo scattasse sull'installazione di riferimento sarebbe
        rumore, e un avviso che scatta sempre non lo legge più nessuno."""
        with tempfile.TemporaryDirectory() as d:
            root = self._installed(d, 0)
            self.assertNotIn("TOKEN_BUDGET", [f.code for f in doctor.check(root)])

    def test_project_sections_larger_than_the_kernel_are_reported(self):
        """La soglia è il kernel, unica grandezza nota: il progetto non scrive
        più del metodo."""
        with tempfile.TemporaryDirectory() as d:
            root = self._installed(d, 1400)
            found = [f for f in doctor.check(root) if f.code == "TOKEN_BUDGET"]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0].severity, "WARN")

    def test_old_report_format_is_reported_in_an_installed_project(self):
        """Un progetto installato col formato in percentuale se lo tiene:
        l'hash della regione kernel torna, perché torna su quel testo lì, e la
        versione dichiarata è quella con cui il progetto è nato. Senza questo
        rilievo nessun check lo vede."""
        with tempfile.TemporaryDirectory() as d:
            root = self._installed(d, 0)
            claude = root / "CLAUDE.md"
            claude.write_text(
                claude.read_text(encoding="utf-8").replace(
                    "CONF: ALTA | MEDIA | BASSA", "CONF: <0-100" + "%>"
                ),
                encoding="utf-8",
            )
            self.assertIn("REPORT_FORMAT", [f.code for f in doctor.check(root)])

    def test_every_code_the_doctor_can_emit_is_documented(self):
        """Un rilievo senza una voce nella skill è un codice che chi lo riceve
        non sa cosa farne."""
        skill = (FRAMEWORK / "skills" / "framework-doctor" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        src = (FRAMEWORK / "tools" / "fwbuild" / "doctor.py").read_text(encoding="utf-8")
        emitted = set(re.findall(r'Finding\(\s*"([A-Z_]+)"', src))
        self.assertTrue(emitted)
        for code in sorted(emitted):
            self.assertIn("### `" + code + "`", skill, code)


class TestSourceReference(unittest.TestCase):
    """Come `.claude/framework.json` cita il sorgente."""

    def test_source_inside_the_project_is_recorded_relative(self):
        """Il primo dei tre modi previsti è il sorgente dentro il progetto: lì
        un assoluto è la macchina di chi ha installato, e muore al clone."""
        self.assertEqual(
            source.reference(Path("/prj"), Path("/prj/framework")), "framework"
        )

    def test_source_outside_the_project_stays_absolute(self):
        """Fuori dal progetto il relativo non regge: la profondità del clone
        non è nota."""
        out = Path("/altrove/framework").resolve()
        self.assertEqual(source.reference(Path("/prj"), out), str(out))

    def test_recorded_reference_resolves_back(self):
        recorded = source.reference(Path("/prj"), Path("/prj/framework"))
        self.assertEqual(
            source.dereference(Path("/prj"), recorded),
            Path("/prj/framework").resolve(),
        )

    def test_install_records_a_portable_source(self):
        """La regola sta nella skill, cioè in prosa: qui si verifica
        sull'artefatto scritto."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "prova"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root)
            recorded = json.loads(
                (root / ".claude" / "framework.json").read_text(encoding="utf-8")
            )["source"]
            self.assertEqual(
                source.dereference(root, recorded).resolve(), FRAMEWORK.resolve()
            )


class TestProfilesAreDistinguishable(unittest.TestCase):
    def test_every_profile_declares_its_critical_surface(self):
        """La superficie critica del campo è nota prima di conoscere il
        progetto: è la sola risposta che un profilo può dare da solo alla
        domanda del Passo 3.2."""
        for path in (FRAMEWORK / "profiles").glob("*.toml"):
            prof = profile.load(path)
            self.assertTrue(prof.critical_surface.strip(), prof.name)

    def test_no_two_profiles_are_interchangeable(self):
        """Due profili che differiscono solo per `name` e `description` sono una
        scelta senza nessuna conseguenza meccanica."""
        seen = {}
        for path in sorted((FRAMEWORK / "profiles").glob("*.toml")):
            prof = profile.load(path)
            key = (
                tuple(prof.agents),
                tuple(prof.cycles),
                tuple(prof.shared),
                repr(prof.settings),
                prof.critical_surface,
            )
            self.assertNotIn(key, seen, prof.name + " == " + str(seen.get(key)))
            seen[key] = prof.name

    def test_the_install_skill_starts_from_the_declared_surface(self):
        """Un campo che nessun passo legge è configurazione morta."""
        text = (FRAMEWORK / "skills" / "framework-install" / "SKILL.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("critical_surface", text)


class TestCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = cli.main(argv)
        return code, buf.getvalue()

    def _install(self, d):
        root = Path(d) / "prova"
        with redirect_stdout(io.StringIO()):
            trial_install.install(root)
        return root

    def test_doctor_json_carries_findings_and_measure(self):
        """Il formato per la CI: un consumatore che non deve leggere prosa."""
        with tempfile.TemporaryDirectory() as d:
            code, out = self._run(["doctor", "--json", str(self._install(d))])
            self.assertEqual(code, 0)
            payload = json.loads(out)
            self.assertTrue(payload["ok"])
            self.assertEqual(payload["findings"], [])
            self.assertTrue(payload["measure"]["split"])
            self.assertGreater(payload["measure"]["tokens"], 0)

    def test_doctor_json_keeps_the_strict_exit_code(self):
        """`--json` è un formato, non una postura: l'uscita dev'essere la stessa
        col flag e senza. Su un'installazione pulita è 0."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            for argv in (
                ["doctor", str(root)],
                ["doctor", "--strict", str(root)],
                ["doctor", "--json", str(root)],
                ["doctor", "--strict", "--json", str(root)],
            ):
                with self.subTest(argv=" ".join(argv[:-1])):
                    self.assertEqual(self._run(argv)[0], 0)

            # E quando un rilievo c'è, entrambe le forme lo fanno cadere.
            (root / ".claude" / "settings.json").unlink()
            self.assertEqual(self._run(["doctor", "--strict", str(root)])[0], 1)
            self.assertEqual(
                self._run(["doctor", "--strict", "--json", str(root)])[0], 1
            )

    def test_install_writes_a_complete_manifest(self):
        """`framework.json` è l'unico posto che dice da dove il progetto è nato
        e di cosa è fatto: la prova guarda il file scritto, non la prosa che lo
        prescrive."""
        with tempfile.TemporaryDirectory() as d:
            root = self._install(d)
            data = json.loads(
                (root / ".claude" / "framework.json").read_text(encoding="utf-8")
            )
            self.assertEqual(data["profile"], "software")
            self.assertEqual(
                data["version"],
                (FRAMEWORK / "VERSION").read_text(encoding="utf-8").strip(),
            )
            self.assertTrue(data["source"])

    def test_cost_prints_its_assumptions_with_the_number(self):
        """Una cifra senza le sue ipotesi è un numero che nessuno può
        contestare: prezzo, spawn e persone stanno accanto al totale."""
        with tempfile.TemporaryDirectory() as d:
            code, out = self._run(
                ["cost", str(self._install(d)), "--spawns", "200", "--devs", "12"]
            )
            self.assertEqual(code, 0)
            self.assertIn("200 spawn al giorno", out)
            self.assertIn("12 persone", out)
            self.assertIn("$/Mtok", out)
            self.assertIn("--price", out)

    def test_cost_without_an_installation_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            code, out = self._run(["cost", d])
            self.assertEqual(code, 1)
            self.assertIn("CLAUDE.md assente", out)


class TestRealInstall(unittest.TestCase):
    def test_full_install_passes_doctor(self):
        """Il resto della suite verifica i pezzi; questo verifica **l'atto di
        installare**. È l'unico test che cade se l'installazione, tutta intera,
        smette di reggere il Passo 6."""
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "prova"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root)
            self.assertEqual(doctor.check(root), [])

    def test_agent_teams_settings_go_in_and_come_out(self):
        """Le variabili di `agent-teams` sono l'unica parte dell'orchestrazione
        che vive fuori dalla guida: entrano in `settings.json` e nel record, o la
        disinstallazione le lascia accese in un progetto che non ha più il
        framework."""
        env = settings.ORCHESTRATION_SETTINGS["agent-teams"]["env"]
        self.assertTrue(env)
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / "prova"
            with redirect_stdout(io.StringIO()):
                trial_install.install(root, orchestration="agent-teams")
            data = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            record = json.loads(
                (root / ".claude" / "framework.json").read_text(encoding="utf-8")
            )["settings_added"]
            for key, value in env.items():
                self.assertEqual(data["env"][key], value, key)
                self.assertEqual(record["env"][key], value, key)
            guide = (root / ".claude" / "shared" / "orchestration.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                assemble.installed_orchestration(kernel.parse(guide).body, FRAMEWORK).stem,
                "agent-teams",
            )
            self.assertEqual(doctor.check(root), [])

            ops = lifecycle.plan_uninstall(root, FRAMEWORK)
            lifecycle.apply_uninstall(root, FRAMEWORK, ops)

            left = json.loads((root / ".claude" / "settings.json").read_text(encoding="utf-8"))
            for key in env:
                self.assertNotIn(key, left.get("env", {}), key)


if __name__ == "__main__":
    unittest.main()
