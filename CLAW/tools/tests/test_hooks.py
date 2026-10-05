import __future__
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from fwbuild import settings

FRAMEWORK = Path(__file__).resolve().parents[2]
HOOKS_DIR = FRAMEWORK / "hooks"


def hook_env(**extra: str) -> dict:
    """Claude Code's environment, not that of whoever runs the tests: without
    `PYTHONIOENCODING` and without UTF-8 mode, so a hook that reads stdin as
    text falls on cp1252 the way it would in use."""
    drop = ("PYTHONIOENCODING", "PYTHONUTF8", "FRAMEWORK_GATEGUARD", "CLAUDE_PROJECT_DIR")
    env = {k: v for k, v in os.environ.items() if k not in drop}
    env.update(extra)
    return env


def encode(payload: dict | bytes) -> bytes:
    if isinstance(payload, bytes):
        return payload
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def run_hook(name: str, payload: dict | bytes, *, env=None, cwd=None, stderr=subprocess.PIPE):
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / f"{name}.py")],
        input=encode(payload),
        stdout=subprocess.PIPE,
        stderr=stderr,
        env=env or hook_env(),
        cwd=cwd,
        timeout=60,
    )


def edit(prj: Path, file_path: str, *, tool: str = "Edit", session: str = "s1") -> dict:
    return {
        "session_id": session,
        "cwd": str(prj),
        "tool_name": tool,
        "tool_input": {"file_path": file_path},
    }


def shell(command: str, tool: str = "Bash") -> dict:
    return {"session_id": "s1", "cwd": ".", "tool_name": tool, "tool_input": {"command": command}}


class TestConfigProtection(unittest.TestCase):
    def test_config_protection_blocks_editing_an_existing_lint_config(self):
        """The name is compared in lowercase (on NTFS `.ESLINTRC.JSON` is the
        same file), a relative path resolves against `cwd` and not against the
        hook's directory, and a non-ASCII path arrives intact only if stdin is
        read as UTF-8 bytes."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d) / "prj"
            for rel in (".eslintrc.json", "sub/.ESLINTRC.JSON", "src/app.py", "città/.eslintrc.json"):
                (prj / rel).parent.mkdir(parents=True, exist_ok=True)
                (prj / rel).write_text("{}", encoding="utf-8")
            cases = (
                (str(prj / ".eslintrc.json"), 2),
                ("sub/.ESLINTRC.JSON", 2),
                ("città/.eslintrc.json", 2),
                ("new/.prettierrc", 0),
                ("src/app.py", 0),
            )
            for file_path, expected in cases:
                with self.subTest(file_path=file_path):
                    r = run_hook("config_protection", edit(prj, file_path), cwd=d)
                    self.assertEqual(r.returncode, expected, r.stderr.decode("utf-8", "replace"))

    def test_closed_hooks_block_on_input_they_cannot_read(self):
        """Every branch that cannot decide blocks, even when the reason cannot
        be printed: exit 1 or 120 mean "let it through" to Claude Code."""
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d)
            (prj / "città").mkdir()
            (prj / "città" / ".eslintrc.json").write_text("{}", encoding="utf-8")
            not_utf8 = json.dumps(edit(prj, "città/.eslintrc.json"), ensure_ascii=False).encode("cp1252")
            cases = (
                ("config_protection", b'{"tool_input": {"file_path": '),
                ("config_protection", {"cwd": str(prj), "tool_input": {}}),
                ("config_protection", {"cwd": str(prj), "tool_input": {"file_path": 3}}),
                ("config_protection", not_utf8),
                ("block_no_verify", b"{broken"),
                ("block_no_verify", {"tool_input": {}}),
            )
            for name, payload in cases:
                with self.subTest(name=name, payload=payload):
                    self.assertEqual(run_hook(name, payload).returncode, 2)
            unwritable = prj / "stderr.txt"
            unwritable.write_bytes(b"")
            for name in ("config_protection", "block_no_verify"):
                with self.subTest(name=name, stderr="not writable"):
                    with open(unwritable, "rb") as err:
                        self.assertEqual(run_hook(name, b"{broken", stderr=err).returncode, 2)


class TestBlockNoVerify(unittest.TestCase):
    def test_block_no_verify_blocks_every_bypass_form(self):
        cases = (
            shell("git commit -an"),
            shell("git push --no-verify origin main"),
            shell("git -c core.hooksPath=/dev/null commit -m x"),
            shell('bash -c "git commit --no-verify -m x"'),
            shell("git config core.hooksPath .nohooks"),
            shell("& C:\\Tools\\Git\\cmd\\git.exe commit -n -m x", tool="PowerShell"),
            shell(
                "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hooksPath "
                "GIT_CONFIG_VALUE_0=/dev/null git commit -m x"
            ),
            shell('git -c alias.ci="commit --no-verify" ci -m x'),
            shell("git commit -u -n -m x"),
        )
        for payload in cases:
            with self.subTest(command=payload["tool_input"]["command"]):
                self.assertEqual(run_hook("block_no_verify", payload).returncode, 2)

    def test_block_no_verify_lets_ordinary_commands_through(self):
        ordinary = (
            'git commit -am "fix"',
            'git commit -m "-n"',
            'git commit --message "-n"',
            'echo "unclosed',
            "git log -n 5",
            "git commit -uno -m x",
            "git commit -Sjohn@example.com -m x",
        )
        for command in ordinary:
            with self.subTest(command=command):
                r = run_hook("block_no_verify", shell(command))
                self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))

    def test_an_open_quote_is_prose_not_a_block(self):
        """An apostrophe — Italian `l'utente`, English `don't`, a heredoc body —
        leaves a quote open: the text passes, a bypass next to it does not."""
        prose = (
            # Three apostrophes: shlex cannot pair them, as in the real case.
            "git add docs && cat >> docs/status.md <<'EOF'\nl'utente decide\nEOF",
            "git commit -m \"it's done\"",
            "git commit -m it's",
            'git commit -m "unclosed',
        )
        for command in prose:
            with self.subTest(command=command):
                r = run_hook("block_no_verify", shell(command))
                self.assertEqual(r.returncode, 0, r.stderr.decode("utf-8", "replace"))
        bypass = (
            "git commit -m l'utente --no-verify",
            "git commit -m it's -n",
            "git commit '--no-verify",
            "git -c core.hooksPath=/dev/null commit -m l'utente",
        )
        for command in bypass:
            with self.subTest(command=command):
                self.assertEqual(run_hook("block_no_verify", shell(command)).returncode, 2)

    def test_block_no_verify_reads_past_a_git_that_is_an_option_value(self):
        """A `git` that is an option's value does not close the segment: the
        `-n` after it must still be looked at."""
        for command in ("git commit -m git -n", "git commit -F /usr/bin/git -n"):
            with self.subTest(command=command):
                self.assertEqual(run_hook("block_no_verify", shell(command)).returncode, 2)


class TestGateguard(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.base = Path(tmp.name)
        self.prj = self.base / "prj"
        (self.prj / "src").mkdir(parents=True)
        (self.prj / "src" / "a.py").write_text("", encoding="utf-8")
        state = self.base / "tmp"
        state.mkdir()
        self.env = hook_env(
            CLAUDE_PROJECT_DIR=str(self.prj), TMP=str(state), TEMP=str(state), TMPDIR=str(state)
        )

    def gate(self, payload, **extra):
        return run_hook("gateguard", payload, env={**self.env, **extra})

    def test_gateguard_denies_the_first_touch_and_lets_the_retry_through(self):
        """The second attempt passes even if it names the file in another form:
        without normalising, the agent would be denied again on the same file."""
        first = self.gate(edit(self.prj, str(self.prj / "src" / "a.py")))
        self.assertEqual(first.returncode, 2)
        self.assertIn("a.py", first.stderr.decode("utf-8"))
        self.assertEqual(self.gate(edit(self.prj, "src/a.py")).returncode, 0)
        self.assertEqual(self.gate(edit(self.prj, "src/a.py", session="s2")).returncode, 2)

    def test_gateguard_skips_outside_the_project_and_when_disabled(self):
        outside = self.base / "elsewhere" / "b.py"
        self.assertEqual(self.gate(edit(self.prj, str(outside))).returncode, 0)
        self.assertEqual(self.gate(edit(self.prj, "docs/status.md")).returncode, 0)
        off = self.gate(edit(self.prj, "src/a.py"), FRAMEWORK_GATEGUARD="off")
        self.assertEqual(off.returncode, 0)
        # Turned off, it records nothing: turned back on, the first touch is still to come.
        self.assertEqual(self.gate(edit(self.prj, "src/a.py")).returncode, 2)

    def test_gateguard_fails_open_with_a_warning(self):
        broken = self.base / "broken"
        broken.mkdir()
        (broken / "claw-gateguard").write_text("", encoding="utf-8")
        cases = (
            (edit(self.prj, "src/a.py"), {"TMP": str(broken), "TEMP": str(broken), "TMPDIR": str(broken)}),
            (b"{broken", {}),
        )
        for payload, extra in cases:
            with self.subTest(payload=payload):
                r = self.gate(payload, **extra)
                self.assertEqual(r.returncode, 0)
                self.assertNotEqual(r.stderr.strip(), b"")


class TestHookSources(unittest.TestCase):
    def test_every_hook_postpones_its_annotations(self):
        """The first `python` on the PATH can be a 3.9 (the stock one on macOS):
        there `str | None` in a signature raises at definition, and a closed
        hook that never reaches `main` blocks every `git` command and linter-configuration edit.
        Compiled without inheriting the caller's flags, the import must be
        there."""
        for p in sorted(HOOKS_DIR.glob("*.py")):
            with self.subTest(hook=p.name):
                code = compile(
                    p.read_text(encoding="utf-8"), str(p), "exec", flags=0, dont_inherit=True
                )
                self.assertTrue(code.co_flags & __future__.annotations.compiler_flag)


class TestInstalledCommand(unittest.TestCase):
    def test_every_protected_name_passes_the_shell_prefilter(self):
        """A protected name missing from the stems would never reach the script:
        the closed hook would let its edit through."""
        sys.path.insert(0, str(HOOKS_DIR))
        try:
            import config_protection
        finally:
            sys.path.remove(str(HOOKS_DIR))
        stems = settings._RELEVANT["config_protection"]
        for name in config_protection.PROTECTED:
            with self.subTest(name=name):
                self.assertTrue(any(s in name for s in stems))

    @unittest.skipUnless(shutil.which("sh"), "sh not available")
    def test_the_installed_hook_command_runs_under_sh(self):
        """The real command, run the way Claude Code runs it: `sh -c`, with a
        space in the project path. A script that does not compile, that exits
        with a code other than 0 and 2, or that is missing closes the closed
        hooks: to Claude Code a 1 means "no objection". Gateguard stays open in
        the same cases."""
        entries = settings.hooks(settings.HOOKS)["hooks"]["PreToolUse"]
        commands = dict(zip(settings.HOOKS, (e["hooks"][0]["command"] for e in entries)))
        with tempfile.TemporaryDirectory() as d:
            prj = Path(d) / "project with space"
            installed = prj / ".claude" / "hooks"
            installed.mkdir(parents=True)
            for name in settings.HOOKS:
                shutil.copy(HOOKS_DIR / f"{name}.py", installed)
            (prj / ".eslintrc.json").write_text("{}", encoding="utf-8")
            env = hook_env(CLAUDE_PROJECT_DIR=str(prj))

            def sh(name: str, file_path: str = ".eslintrc.json", payload=None, run_env=None) -> int:
                return subprocess.run(
                    ["sh", "-c", commands[name]],
                    input=encode(payload or edit(prj, str(prj / file_path))),
                    capture_output=True,
                    env=run_env or env,
                    cwd=prj,
                    timeout=60,
                ).returncode

            self.assertEqual(sh("config_protection"), 2)
            # A 0 arrives only if the script read the payload: an empty stdin
            # would give 2 here too.
            self.assertEqual(sh("config_protection", "new/.ESLINTRC.json"), 0)
            self.assertEqual(sh("block_no_verify", payload=shell("GIT commit --no-verify")), 2)
            for broken in ("def (:\n", "import sys\nsys.exit(3)\n"):
                with self.subTest(script=broken):
                    (installed / "config_protection.py").write_text(broken, encoding="utf-8")
                    self.assertEqual(sh("config_protection", "new/.eslintrc.json"), 2)
                    # Nothing for the hook to say: the broken script is not reached.
                    self.assertEqual(sh("config_protection", "src/app.py"), 0)
            (installed / "config_protection.py").unlink()
            self.assertEqual(sh("config_protection"), 2)
            self.assertEqual(sh("config_protection", "src/app.py"), 0)
            shutil.copy(HOOKS_DIR / "config_protection.py", installed)

            # The Windows Store stub: found by `command -v`, it runs nothing.
            stub = Path(d) / "stub"
            stub.mkdir()
            for exe in ("python", "python3"):
                (stub / exe).write_text("#!/bin/sh\nexit 49\n", encoding="utf-8")
                (stub / exe).chmod(0o755)
            stubbed = {**env, "PATH": f"{stub}{os.pathsep}{env.get('PATH', '')}"}
            with self.subTest(python="stub only"):
                # 0 with a real Python: the 2 comes from the stub being refused.
                self.assertEqual(sh("config_protection", "new/.eslintrc.json", run_env=stubbed), 2)
                self.assertEqual(sh("block_no_verify", payload=shell("git status"), run_env=stubbed), 2)
                refused = subprocess.run(
                    ["sh", "-c", commands["block_no_verify"]],
                    input=encode(shell("git status")),
                    capture_output=True,
                    env=stubbed,
                    cwd=prj,
                    timeout=60,
                )
                self.assertIn(b"python missing", refused.stderr)
                self.assertEqual(sh("config_protection", "src/app.py", run_env=stubbed), 0)
                self.assertEqual(sh("block_no_verify", payload=shell("npm test"), run_env=stubbed), 0)
            (installed / "gateguard.py").write_text("import sys\nsys.exit(1)\n", encoding="utf-8")
            self.assertNotEqual(sh("gateguard"), 2)
            (installed / "gateguard.py").unlink()
            self.assertEqual(sh("gateguard"), 0)


if __name__ == "__main__":
    unittest.main()
