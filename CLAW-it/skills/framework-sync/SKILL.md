---
name: framework-sync
description: >
  Allinea un'installazione con il framework sorgente: porta giù una versione
  nuova del metodo preservando l'adattamento, promuove su una modifica locale
  perché il prossimo progetto la erediti, attiva o disattiva un agente o una
  guida, cambia l'orchestrazione, rimette ciò che manca, disinstalla. Da usare quando esce una versione
  nuova, quando una modifica locale merita di diventare generale, quando
  un'installazione ha perso dei file o va tolta.
---

# Sincronizzazione con il sorgente

Collega il **sorgente** (il master) alle **installazioni** (i progetti). Requisito: il sorgente dev'essere raggiungibile dalla macchina; se non lo è, solo `doctor` è utilizzabile.

`--down`, `--up`, `--upgrade`, `--activate`, `--deactivate`, `--repair`, `--uninstall` sono **modalità di questa skill**, non flag da shell: `fwbuild` ha `doctor`, `source`, `cost` e `report`. Il rapporto di divergenza su più repository — `python -m fwbuild report <cartella>` — è invece da shell: legge molti progetti e non ne modifica nessuno.

I frammenti partono da `<FW>/tools`. `<PRJ>` è la root del progetto; `<FW>` è il campo `source` di `.claude/framework.json` (se manca, `./framework/`), che può essere **relativo alla root del progetto**, non alla directory da cui giri: scioglilo con `source.dereference(<PRJ>, source)`.

**Ogni modalità che scrive mostra prima il piano, file per file, e attende l'ok.** Dove esiste un `plan_*` di `lifecycle`, il piano si salva legato al progetto e alla modalità, e si esegue **quello**, non uno ricalcolato: l'esecuzione rifiuta il piano di un altro progetto o di un'altra modalità, ricontrolla ogni file e si ferma se l'albero è cambiato dopo l'ok.

```bash
# piano: si stampa e si salva col path del progetto e la modalità, niente si scrive
cd <FW>/tools && python -c "
import dataclasses, hashlib, json, sys, tempfile
from pathlib import Path
from fwbuild import lifecycle
sys.stdout.reconfigure(encoding='utf-8')   # i motivi hanno '→': cp1252 non lo stampa
P = str(Path('<PRJ>').resolve())
M = '<down | repair | uninstall>'
H = None   # solo down: None tiene gli hook in uso; su un progetto senza, i nomi scelti al passo 0
ops = getattr(lifecycle, 'plan_' + M)(Path(P), Path('..'), **({'hooks': H} if M == 'down' else {}))
print(lifecycle.render(ops))
f = Path(tempfile.gettempdir(), 'fw-plan-' + hashlib.sha256(P.encode()).hexdigest()[:16] + '.json')
f.write_text(json.dumps({'project': P, 'mode': M, 'ops': [dataclasses.asdict(o) for o in ops]}), encoding='utf-8')
"
# dopo l'ok: solo il piano di questo progetto e di questa modalità
cd <FW>/tools && python -c "
import hashlib, json, sys, tempfile
from pathlib import Path
from fwbuild import lifecycle
sys.stderr.reconfigure(encoding='utf-8')
P = str(Path('<PRJ>').resolve())
M = '<down | repair | uninstall>'   # la modalità che esegui, non quella letta dal file
f = Path(tempfile.gettempdir(), 'fw-plan-' + hashlib.sha256(P.encode()).hexdigest()[:16] + '.json')
plan = json.loads(f.read_text(encoding='utf-8')) if f.is_file() else {}
if plan.get('project') != P or plan.get('mode') != M: sys.exit(f'nessun piano {M} salvato per {P}: rifai il piano')
ops = [lifecycle.Operation(**d) for d in plan['ops']]
if M == 'uninstall': lifecycle.apply_uninstall(Path(P), Path('..'), ops)
else: lifecycle.apply_update(Path(P), Path('..'), ops)
"
```

Nelle altre modalità il piano è l'elenco dei file e di cosa gli succede, scritto prima di toccarli.

---

## `--down` — portare una versione nuova nel progetto

Aggiorna il metodo preservando l'adattamento.

0. **Piano** con `plan_down`: regioni kernel da riassemblare, skill e hook da aggiornare, voci mancanti in `settings.json`, versione del manifesto. `hooks=None` tiene gli hook che il progetto usa; se non ne usa nessuno, **una domanda sola** — li vuole, `gateguard` compreso? — e il sì diventa `hooks=[…]` coi nomi scelti di `settings.HOOKS`.
1. **Confronta le versioni:** quella del progetto sta nel marker della regione kernel, quella del sorgente in `<FW>/VERSION`.
2. **Diagnosi prima.** I `KERNEL_DRIFT` vanno risolti *prima*: aggiornare sopra una modifica locale la cancella in silenzio.
3. **Riassembla** col metodo nuovo e le sezioni di progetto esistenti, estratte dall'installazione corrente e riscritte invariate.

```bash
cd <FW>/tools && python -c "
from pathlib import Path
from fwbuild import assemble, kernel
p = Path('<PRJ>/CLAUDE.md')
text = p.read_text(encoding='utf-8')
region = kernel.parse(text)
sezioni = text[region.end:].lstrip('\n')          # l'adattamento, invariato
version = Path('../VERSION').read_text(encoding='utf-8').strip()
p.write_text(assemble.build_document(Path('../method'), version, sezioni), encoding='utf-8')
"
```

4. **Stessa operazione su `.claude/shared/orchestration.md`**, col kernel da `<FW>/coordinator/`: i documenti versionati sono **due**, aggiornarne uno solo li lascia disallineati. Lì orchestrazione e cicli di dominio stanno **dentro** la regione e il progetto non registra da cosa è nato: vanno ripassati, in quest'ordine, con `extra=[assemble.installed_orchestration(region.body, Path('..')), *assemble.installed_cycles(region.body, Path('..'))]`, o spariscono senza che nessun rilievo lo veda. Una regione senza orchestrazione riconoscibile è un `ValueError`: l'orchestrazione si sceglie esplicitamente con `assemble.orchestration_file`, non si indovina.
5. **Stessa operazione su ogni agente installato**, con `split_source` e `build_agent`: frontmatter e blocco `## Contesto di progetto` restano del progetto, il metodo viene dal master. Se il piano nomina `model` o `effort` diversi dal sorgente, si chiede: sì → quella riga del frontmatter prende il valore del sorgente.
6. **Esegui il piano** del passo 0 con `apply_update`: copia skill e hook, fonde `settings.json`, scrive `version` in `.claude/framework.json` e accoda il nuovo delta a `settings_added`. Le regioni kernel le salta: le hanno già riscritte i passi 3-5.
7. **Verifica** con `doctor`: deve uscire con 0.

**I conflitti si presentano, non si risolvono da soli:** su una regione modificata localmente l'utente deve vedere entrambe le versioni e decidere.

---

## `--up [cosa]` — promuovere una modifica locale nel sorgente

**Precondizione: il progetto dev'essere allineato al sorgente.** Se `version` in `.claude/framework.json` non è quella di `<FW>/VERSION`, prima `--down`, poi la promozione. Da un progetto rimasto indietro la regione locale differisce dal sorgente per **due** motivi — la tua modifica, e quella che un altro progetto ha già promosso — e il passo 1 non li distingue: promuovere in blocco cancella la seconda in silenzio. Allineato vuol dire che base e sorgente coincidono, ed è la sola condizione in cui un confronto a due alberi è corretto.

`[cosa]` nomina **una** modifica. Senza argomento, elenca ciò che è promovibile e procedi **una cosa alla volta**: il passo 2 va posto caso per caso, e una promozione in blocco quella domanda non la può porre.

1. **Individua la modifica:** `doctor` la segnala come `KERNEL_DRIFT`; il contenuto si ottiene confrontando la regione kernel del progetto col sorgente corrispondente. **Il drift non vede i file nuovi:** una regione kernel ce l'hanno solo `CLAUDE.md`, `orchestration.md` e le schede agente, quindi elenca anche i file che stanno in `.claude/shared/` o `.claude/agents/` del progetto e mancano dal sorgente, e gli hook di `.claude/hooks/` diversi dal loro originale. Una guida aggiunta a mano è promovibile e nessun rilievo la nomina.
2. **Chiedi se vale per tutti.** Un miglioramento del metodo sale, una deroga specifica di quel progetto no: la domanda va posta all'utente, non decisa.
3. **Applica al sorgente**, e la scelta della destinazione è **per destinatario**:

   | la modifica riguarda… | va in |
   |---|---|
   | ciò che vale per chiunque esegua un task | `<FW>/method/` |
   | quando delegare, a chi, con che prompt, lo stato del progetto | `<FW>/coordinator/` |
   | il mandato di un ruolo specifico | `<FW>/agents/<nome>.md` |
   | materiale di consultazione di un dominio | `<FW>/shared/` |
   | un controllo che l'agente non deve poter saltare | `<FW>/hooks/`, e la sua voce in `<FW>/tools/fwbuild/settings.py` |

   Sbagliare qui costa: una regola di delega in `method/` la pagano tutti i subagent a ogni spawn senza poterla usare; una regola di esecuzione in `coordinator/` non la vedrà mai chi esegue.
4. **Registra la base, se non c'è già**, **prima** di toccare `VERSION`:

   ```bash
   cd <FW>/tools && python -c "
   from pathlib import Path
   from fwbuild import upgrade
   F = Path('..')
   if upgrade.read_record(F) is None:
       print(upgrade.write_record(F, (F/'VERSION').read_text(encoding='utf-8').strip(),
                                  '<EDIZIONE>', '<URL del repository>'))
   "
   ```

   Da qui in avanti `VERSION` non è più un numero pubblicato, e senza questa riga nessuno sa più da quale release il sorgente veniva: è la sola cosa che rende recuperabile il tuo lavoro al prossimo aggiornamento (→ `--upgrade`). **Se il record c'è già non si tocca:** la base resta quella, per quante promozioni tu faccia.
5. **Incrementa `<FW>/VERSION`:** correzione → patch; regola nuova o riformulata → minor; cambio strutturale → major.
6. **Dichiara cosa è cambiato**, così chi aggiorna sa cosa riceve.
7. **Riallinea il progetto di origine** con `--down`, perché l'hash torni.

⚠️ **Una traduzione di questo sorgente è un sorgente a sé**, col proprio `VERSION`: `--up` non la raggiunge. Una regola che vale in ogni lingua va portata a mano anche là — finché non lo è, le due edizioni dicono cose diverse.

---

## `--upgrade` — portare una release nuova sopra un sorgente modificato

Serve solo a chi ha usato `--up`: un sorgente intatto si aggiorna sostituendolo. L'assenza di `upstream.json` **è** quella risposta, non un guasto.

1. **Prendi la release nuova** dove non disturba, e da lì `<NEW>` è la cartella di edizione dentro il clone:

   ```bash
   git clone <repo> <NEW>   # oppure: git -C <clone esistente> pull
   ```

2. **Ricostruisci la base**, cioè l'edizione com'era alla release da cui il tuo sorgente veniva. `upgrade.base_version(<FW>)` dà il numero; nel clone, la base è il commit in cui `VERSION` di quell'edizione valeva quel numero, estratto dove non tocca niente:

   ```bash
   git -C <NEW> log --format=%H -- <EDIZIONE>/VERSION   # dal più recente
   git -C <NEW> show <commit>:<EDIZIONE>/VERSION        # finché non corrisponde
   git -C <NEW> worktree add --detach <BASE> <commit>
   ```

   **Base sbagliata, confronto inutile:** se nessun commit corrisponde — repository sbagliato, storia troncata, numero mai pubblicato — fermati e chiedi. Non ripiegare su `VERSION`: quella è la risposta giusta solo quando `upstream.json` manca.

3. **Classifica**, senza scrivere niente:

   ```bash
   cd <FW>/tools && python -c "
   from pathlib import Path
   from fwbuild import upgrade
   plan = upgrade.classify(Path('<BASE>/<EDIZIONE>'), Path('<FW>'), Path('<NEW>/<EDIZIONE>'))
   for nome in ('theirs', 'yours', 'conflict'):
       print(nome, len(getattr(plan, nome)), getattr(plan, nome)[:20])
   "
   ```

   | esito | cosa vuol dire | cosa si fa |
   |---|---|---|
   | `same` | tu e la release dite la stessa cosa — anche quando la tua aggiunta è arrivata a monte identica | niente |
   | `theirs` | l'hai lasciato com'era e a monte è cambiato | si copia dalla release |
   | `yours` | l'hai cambiato tu e a monte no | **si tiene il tuo** |
   | `conflict` | cambiato da tutti e due, in modo diverso | lo decide l'utente |

4. **Mostra il piano prima di applicarlo**, coi conteggi e i percorsi in conflitto. `same`, `theirs` e `yours` sono meccanici: si applicano copiando dalla release i primi, non toccando i secondi.
5. **Un conflitto per volta:** leggi le tre versioni — base, tua, nuova — e proponi una fusione che tenga la tua aggiunta *dentro* il testo nuovo, non accanto. Se la tua modifica è già coperta dal testo nuovo, si prende quello e lo si dice. Nessun conflitto si risolve senza mostrare all'utente cosa perde.
6. **`VERSION` non è un conflitto:** si prende quella della release. Un sorgente che dichiara un numero mai pubblicato è ciò che ha creato il problema.
7. **Riscrivi il record** con la release appena presa: è la base del prossimo aggiornamento.

   ```bash
   cd <FW>/tools && python -c "
   from pathlib import Path
   from fwbuild import upgrade
   F = Path('..')
   print(upgrade.write_record(F, (F/'VERSION').read_text(encoding='utf-8').strip(),
                              '<EDIZIONE>', '<URL del repository>'))
   "
   ```

8. **Chiudi con `--down` sui progetti**, che ora sono indietro di una versione, e con `doctor` su ciascuno.

⚠️ Il sorgente si aggiorna **sul posto**: prima di applicare, copialo da parte. È l'unica operazione della skill che tocca il master, e non ha un annulla.

---

## `--activate <agente|guida>` / `--deactivate <agente|guida>`

**Attivare** copia l'agente dal master alla **versione corrente**, compila il suo blocco `## Contesto di progetto` e aggiunge la riga alla tabella di routing in `.claude/shared/orchestration.md` — mai in `CLAUDE.md`: il routing è contenuto da coordinatore.

Forma obbligatoria della riga, perché il doctor la legge:

```
| Situazione | `nome-agente` | Modello |
```

Il nome sta fra backtick nella **seconda** colonna. Altrove, quell'agente risulta `ROSTER_ORPHAN` e la tabella cita un `ROSTER_MISSING` che non esiste.

Attivare più tardi è *meglio* di un file dormiente: si prende sempre l'ultima versione, non una ferma al giorno dell'installazione.

**Disattivare** rimuove il file da `.claude/agents/` e la riga dal routing. **Il master non si tocca.** Se il blocco di progetto conteneva informazioni non ricostruibili, salvalo prima.

**Una guida** si nomina col percorso sotto `shared/` (`domain/llm-guide.md`). Attivarla: copiala in `.claude/shared/`, compila il blocco di progetto, aggiungi la sua riga in `CLAUDE.md § Guide condivise` — senza, è `SHARED_ORPHAN`. Disattivarla: via file e riga. Una guida che un file installato cita ancora non si disattiva: il pointer resterebbe morto (`SHARED_MISSING`).

Controlla sempre i conflitti dopo un'attivazione:

```bash
cd <FW>/tools && python -c "
from fwbuild import profile
import pathlib
present = sorted(p.stem for p in pathlib.Path('<PRJ>/.claude/agents').glob('*.md'))
print('conflitti:', profile.check_exclusive(present) or 'nessuno')
"
```

Chiudi sempre con `doctor`.

---

## `--repair` — rimettere ciò che manca

Alla versione installata, che dev'essere quella del sorgente: altrimenti `plan_repair` si rifiuta, e prima va `--down`. Rimette le skill di ciclo di vita, gli hook in uso, i file di stato e le guide citate che mancano, e le voci mancanti in `settings.json`. **Non sovrascrive niente:** un file diverso dal sorgente è una modifica locale e resta.

1. Piano con `plan_repair`, ok, `apply_update`.
2. Guide e file di stato ricreati arrivano dal template: compila i blocchi `[DA COMPILARE]` come all'installazione.
3. Chiudi con `doctor`.

---

## `--uninstall` — togliere il framework dal progetto

Si cancella solo ciò che è identico byte per byte al sorgente; ciò che il progetto ha adattato va in `.claude/framework-archive/`, al suo percorso relativo. Servono il sorgente raggiungibile e il manifesto; un archivio già presente ferma il piano.

| file | cosa succede |
|---|---|
| `CLAUDE.md` | via la sola regione kernel, le sezioni di progetto restano |
| skill e hook | identici al sorgente → rimossi; diversi → archiviati |
| schede, guide e stili che vengono dal sorgente, `orchestration.md` | archiviati |
| `.claude/settings.json` | via le voci di `settings_added` ancora uguali; quelle cambiate dall'utente restano, e il piano le nomina. Senza record, il resto non si tocca |
| voci hook del framework, anche ritoccate dall'utente | via, **una riga del piano per voce**: lo script se ne va, e un hook chiuso senza script blocca ogni modifica o ogni comando |
| `docs/` | restano |
| `.claude/framework.json` | archiviato per ultimo |

Piano con `plan_uninstall`, ok, `apply_uninstall`: un file cambiato dopo il piano ferma tutto, prima del primo byte scritto.

---

## Cambio di campo

Un progetto non resta dov'è nato: una libreria si fa una demo, uno strumento diventa un servizio. Il campo sta in `profile` dentro `.claude/framework.json`, unico posto che lo sa. Nessuna modalità apposta: sono le stesse quattro operazioni dell'installazione, sul profilo nuovo.

1. **Roster** — `--activate` per ciò che il campo nuovo implica, `--deactivate` per il resto. Controlla i conflitti dopo.
2. **Guide** — copia quelle di `profile.guides` sul profilo nuovo e il roster di dopo, e aggiungi la riga in `CLAUDE.md § Guide condivise`: cosa contiene la guida, presa dalla riga sotto il suo titolo. Il doctor pretende che il percorso sia citato (`SHARED_ORPHAN`), non che la riga sia scritta bene: quella è responsabilità di chi installa.
3. **Cicli** — riassembla la guida del coordinatore accodando, dopo l'orchestrazione installata (`assemble.installed_orchestration`), quelli del campo nuovo (`assemble.cycle_files`), o nessuno se ne toglie. Stanno **dentro** la regione kernel: nessun rilievo li vede sparire. Stessa precondizione del § Cambio di orchestrazione.
4. **Permessi** — `settings.unmerge(corrente, settings_added)` toglie ciò che il campo vecchio aveva aggiunto ed è ancora uguale; poi `settings.merge(resto, nuovo)`, con `nuovo` = `Profile.settings` del profilo nuovo fuso con `settings.hooks` degli hook in `.claude/hooks/` e con `settings.ORCHESTRATION_SETTINGS` dell'orchestrazione installata (`installed_orchestration`): il record le contiene, e senza rifonderle il cambio di campo spegne il team. Mostra `tenuti` e conflitti prima di scrivere. Senza record, solo `merge`: il `deny` vecchio resta finché l'utente non lo toglie. Una rigenerazione secca cancella permessi che nessun profilo ha mai scritto.

Poi aggiorna `profile` in `framework.json`; `settings_added` diventa l'aggiunto del `merge`. Saltarlo lascia il progetto a dichiarare un campo che non ha più: la prossima manutenzione rigenera i permessi sbagliati e nessun rilievo se ne accorge — il file dichiara, non verifica.

---

## Cambio di orchestrazione

Una per progetto, dentro la regione kernel della guida del coordinatore. Nessuna modalità apposta.

**Precondizione:** `version` di `framework.json` uguale a `<FW>/VERSION` e nessun `KERNEL_DRIFT` su `orchestration.md`; altrimenti prima `--down`. Riassemblare la sola guida la porterebbe alla versione del sorgente mentre `CLAUDE.md` resta indietro (`VERSION_MISMATCH`), e una modifica locale nella regione sparirebbe in silenzio.

`vecchia` e `nuova` sono le voci di `settings.ORCHESTRATION_SETTINGS` delle due orchestrazioni, `{}` se non ne hanno.

1. **Guida** — riassembla `.claude/shared/orchestration.md` come al passo 4 di `--down`, con `assemble.orchestration_file(Path('..'), '<nuova>')` al posto di `installed_orchestration`; i cicli si ripassano invariati.
2. **Settings** — si toglie solo ciò che l'installazione aveva davvero aggiunto: `reg = settings.unmerge(vecchia, settings.unmerge(vecchia, settings_added)[0])[0]` è la parte di `vecchia` ancora nel record. `settings.unmerge(corrente, reg)` la toglie — una variabile che l'utente aveva già prima resta —, poi `settings.merge(resto, nuova)` aggiunge quella della nuova. Conflitti e `tenuti` si mostrano prima di scrivere.
3. **Manifesto** — `settings_added` diventa `settings.merge(settings.unmerge(settings_added, reg)[0], aggiunto)[0]`, con `aggiunto` il secondo valore del `merge` del passo 2: senza, `--uninstall` lascia accesa una variabile che nessuna orchestrazione chiede più.
4. **Verifica** con `doctor`.
