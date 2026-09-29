# `/claw change` — profile or orchestration

## Change of field

A project does not stay where it was born: a library grows a demo, a tool becomes a service. The field lives in `profile` inside `.claude/framework.json`, the only place that knows it. These are the same four operations of an installation, on the new profile.

1. **Roster** — `/claw add` what the new field implies, `/claw remove` the rest. Check for conflicts afterwards.
2. **Guides** — copy those of `profile.guides` on the new profile and the roster after the change, and add the line in `CLAUDE.md § Shared guides`: what the guide holds, taken from the line under its title. The doctor demands that the path be cited (`SHARED_ORPHAN`), not that the line be written well: that is on whoever installs.
3. **Cycles** — reassemble the coordinator's guide appending, after the installed orchestration (`assemble.installed_orchestration`), the new field's (`assemble.cycle_files`), or none if it drops them. They live **inside** the kernel region: no finding sees them vanish. Same precondition as § Change of orchestration.
4. **Permissions** — `settings.unmerge(current, settings_added)` removes what the old field had added and is still equal; then `settings.merge(rest, new)`, with `new` = `settings.framework(<new Profile.settings>, <hooks in .claude/hooks/>, <installed_orchestration>, skills.overrides(<FW>))`: the record contains base, hooks and orchestration, and without merging them again the change of field switches them off. Show `kept` and the conflicts before writing. Without a record, `merge` only: the old `deny` stays until the user removes it. A flat regeneration deletes permissions no profile ever wrote.

Then update `profile` in `framework.json`; `settings_added` becomes what the `merge` added. Skipping it leaves the project declaring a field it no longer has: the next maintenance regenerates the wrong permissions and no finding notices — the file declares, it does not verify.

---

## Change of orchestration

One per project, inside the kernel region of the coordinator's guide.

**Precondition:** `version` in `framework.json` equal to `<FW>/VERSION` and no `KERNEL_DRIFT` on `orchestration.md`; otherwise `/claw update` first. Reassembling the guide alone would bring it to the source's version while `CLAUDE.md` stays behind (`VERSION_MISMATCH`), and a local change in the region would vanish silently.

`old` and `new` are the `settings.ORCHESTRATION_SETTINGS` entries of the two orchestrations, `{}` if they have none.

1. **Guide** — reassemble `.claude/shared/orchestration.md`: `assemble.build_document(<FW>/coordinator, <VERSION>, <its project sections, unchanged>, extra=[assemble.orchestration_file(<FW>, '<new>'), *assemble.installed_cycles(region.body, <FW>)])`.
2. **Settings** — remove only what the installation really added: `rec = settings.unmerge(old, settings.unmerge(old, settings_added)[0])[0]` is the part of `old` still in the record. `settings.unmerge(current, rec)` removes it — a variable the user already had stays —, then `settings.merge(rest, new)` adds the new one's. Conflicts and `kept` are shown before writing.
3. **Manifest** — `settings_added` becomes `settings.merge(settings.unmerge(settings_added, rec)[0], added)[0]`, with `added` the second value of the `merge` in step 2: without it, `/claw uninstall` leaves on a variable no orchestration asks for any more.
4. **Verify** with `doctor`.
