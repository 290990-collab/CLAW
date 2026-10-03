"""PreToolUse hook: git hooks are not skipped.

Blocks `--no-verify`, its `-n` on `commit` (inside a group like `-an` too) and
any touch of `core.hooksPath`. A command that does not name `git` passes with no
analysis.

Closed hook: unreadable input, any error → exit 2. A quote left open is read
as prose, not as an error: an apostrophe in any language is normal text.

Exit: 0 lets it through, 2 blocks with the reason on stderr.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import sys

NAME = "block_no_verify"

# A command inside an argument (`bash -c "git ..."`) is analysed again; past
# this nesting level it blocks instead of giving up looking.
MAX_DEPTH = 3

# Git's global options whose value is in the next token: that token is not the
# subcommand.
GLOBAL_WITH_VALUE = frozenset(
    {"-c", "-C", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env"}
)

# `commit` options whose value is in the next token: the value is text, and a
# message `-m "-n"` is not a `-n`.
COMMIT_WITH_VALUE = frozenset(
    {
        "-m",
        "--message",
        "-F",
        "--file",
        "-C",
        "--reuse-message",
        "-c",
        "--reedit-message",
        "--author",
        "--date",
        "-t",
        "--template",
        "--fixup",
        "--squash",
        "--pathspec-from-file",
    }
)

# Short `commit` options that take a value: in a group like `-mn` the rest of
# the group is the value, and the `n` is text.
COMMIT_SHORT_WITH_VALUE = frozenset("mFCct")

# Short `commit` options with an optional value, attached only: `-uno` and
# `-S<key>` do not contain a `-n`. They do not take the next token, and putting
# them in the set above would let `-u -n` through.
COMMIT_SHORT_OPTIONAL_VALUE = frozenset("uS")


def verdict(data: object) -> str | None:
    """The reason for the block, or `None` if the command passes."""
    if not isinstance(data, dict) or not isinstance(data.get("tool_input"), dict):
        raise ValueError("tool_input missing or not an object")
    command = data["tool_input"].get("command")
    if not isinstance(command, str):
        raise ValueError("command missing or not a string")
    if "git" not in command.lower():
        return None
    return _scan(command, posix=data.get("tool_name") != "PowerShell", depth=0)


def _scan(command: str, posix: bool, depth: int) -> str | None:
    if depth > MAX_DEPTH:
        return f"command with git nested beyond {MAX_DEPTH} levels"
    tokens = _tokens(command, posix)
    values: set[int] = set()
    for i, (tok, punct) in enumerate(tokens):
        if punct or i in values:
            continue
        # On every token, not only after `git`: the configuration also comes
        # from an environment variable (`GIT_CONFIG_KEY_0=core.hooksPath git ...`)
        # or from an alias (`-c alias.ci="commit --no-verify"`).
        low = tok.lower()
        if "core.hookspath" in low:
            return f"{tok}: core.hooksPath is not touched"
        if any(_is_no_verify(part) for part in low.split()):
            return f"{tok}: --no-verify"
        if _is_git(tok):
            end = next((j for j in range(i + 1, len(tokens)) if tokens[j][1]), len(tokens))
            reason, taken = _git_args([t for t, _ in tokens[i + 1 : end]])
            if reason:
                return reason
            values.update(i + 1 + k for k in taken)
        elif re.search(r"\s", tok) and "git" in tok.lower():
            reason = _scan(tok, posix, depth + 1)
            if reason:
                return reason
    return None


def _tokens(command: str, posix: bool) -> list[tuple[str, bool]]:
    """`(token, is punctuation)`. PowerShell is not POSIX: `\\` is a path
    separator, not an escape, and the quotes stay in the token.

    A quote left open is almost always prose — an apostrophe (`l'utente`,
    `don't`) or the body of a heredoc — not a bypass: the command is read again
    with quotes as plain characters, stripped from every token, so a
    `--no-verify` or a `-n` is still found and the text goes through."""
    try:
        return _lex(command, posix, quoting=True)
    except ValueError:
        return _lex(command, posix, quoting=False)


def _lex(command: str, posix: bool, quoting: bool) -> list[tuple[str, bool]]:
    lex = shlex.shlex(command, posix=posix, punctuation_chars=True)
    lex.whitespace_split = True
    if not quoting:
        lex.quotes = ""
        lex.escape = ""
    out = []
    for tok in lex:
        punct = tok != "" and all(c in lex.punctuation_chars for c in tok)
        if not quoting:
            tok = tok.strip("\"'")
        elif not posix and len(tok) >= 2 and tok[0] == tok[-1] and tok[0] in "\"'":
            tok = tok[1:-1]
        out.append((tok, punct))
    return out


def _is_git(tok: str) -> bool:
    name = re.split(r"[\\/]", tok)[-1].strip("`").lower()
    return name in ("git", "git.exe")


def _is_no_verify(arg: str) -> bool:
    # git accepts an abbreviated long option as long as it is unique:
    # `--no-veri` is already `--no-verify`, `--no-ver` is ambiguous with
    # `--no-verbose`.
    return len(arg) >= len("--no-veri") and "--no-verify".startswith(arg)


def _git_args(args: list[str]) -> tuple[str | None, set[int]]:
    """`(reason, indices of option values)` for the arguments of a `git`.

    The returned indices are text — a commit's message — and the caller does
    not analyse them again. It stops at the first `git` that is not an
    option's value: another command starts there, which the caller analyses on
    its own. A `git` value (`-m git`) closes nothing.
    """
    values: set[int] = set()
    sub = None
    global_value = False
    k = 0
    while k < len(args):
        arg = args[k]
        low = arg.lower()
        if "core.hookspath" in low:
            return f"git {arg}: core.hooksPath is not touched", values
        if sub is None:
            if global_value:
                global_value = False
            elif _is_git(arg):
                break
            elif arg in GLOBAL_WITH_VALUE:
                global_value = True
            elif not arg.startswith("-"):
                sub = low
            k += 1
            continue
        if arg == "--" or _is_git(arg):
            break
        if _is_no_verify(low):
            return f"git {sub} {arg}", values
        if sub == "commit":
            if arg in COMMIT_WITH_VALUE:
                values.add(k + 1)
                k += 2
                continue
            if arg.startswith("-") and not arg.startswith("--"):
                for pos, flag in enumerate(arg[1:]):
                    if flag == "n":
                        return f"git commit {arg}: -n is --no-verify", values
                    if flag in COMMIT_SHORT_WITH_VALUE:
                        if pos == len(arg) - 2:
                            values.add(k + 1)
                            k += 1
                        break
                    if flag in COMMIT_SHORT_OPTIONAL_VALUE:
                        break
        k += 1
    return None, values


def _say(text: str) -> None:
    # A reason that cannot be printed does not change the outcome: the exit
    # code is decided by the caller, and it must arrive even with stderr broken.
    try:
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
    except BaseException:
        pass


def main() -> None:
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        found = verdict(data)
        reason = (
            f"{NAME}: {found}. Git hooks are not skipped: fix what they report; "
            "if bypassing them is intended, the user does it."
            if found
            else None
        )
    except BaseException as exc:
        reason = f"{NAME}: unreadable input or internal error ({exc!r}), blocking"
    if reason:
        _say(reason)
    # os._exit and not sys.exit: a failed flush on exit would turn the code
    # into 120, that is into "let it through".
    os._exit(2 if reason else 0)


if __name__ == "__main__":
    main()
