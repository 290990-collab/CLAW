"""PreToolUse hook: the first touch of a file asks for the facts before the edit.

The first Edit, Write or MultiEdit on a project file is denied with the list of
facts to gather — who imports the file, what public surface changes — and the
second attempt on the same file passes. Asking "are you sure?" always gets a
yes; asking who imports the file forces a search for it.

Open hook: it is a habit, not a defence. An internal error lets the edit
through with a warning on stderr instead of blocking the work, and the only
block is the first touch, recorded before denying it: without the record the
second attempt would be denied again, forever.

Turned off with `FRAMEWORK_GATEGUARD=off` (or `0`, `false`).

Exit: 0 lets it through, 2 denies the first touch with the facts on stderr.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile

NAME = "gateguard"

OFF = frozenset({"off", "0", "false"})

# The framework's state files are updated at every step of the work: asking who
# imports them makes no sense.
STATE_FILES = ("TODO.md", "status.md", "roadmap.md")

STATE_DIR = "claw-gateguard"


def verdict(data: object) -> str | None:
    """The facts to present at the first touch, or `None` if the operation passes."""
    if os.environ.get("FRAMEWORK_GATEGUARD", "").strip().lower() in OFF:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("tool_input"), dict):
        raise ValueError("tool_input missing or not an object")
    file_path = data["tool_input"].get("file_path")
    if not isinstance(file_path, str) or not file_path:
        raise ValueError("file_path missing or not a string")
    session = data.get("session_id")
    if not isinstance(session, str) or not session:
        raise ValueError("session_id missing or not a string")
    cwd = data.get("cwd")
    root = os.environ.get("CLAUDE_PROJECT_DIR") or cwd
    if not isinstance(root, str) or not root:
        raise ValueError("neither CLAUDE_PROJECT_DIR nor cwd")
    root = os.path.normcase(os.path.abspath(root))
    base = cwd if isinstance(cwd, str) and cwd else root
    path = os.path.normcase(os.path.abspath(os.path.join(base, file_path)))
    if not _inside(path, root):
        return None
    if path in {os.path.normcase(os.path.join(root, "docs", n)) for n in STATE_FILES}:
        return None

    state = os.path.join(
        tempfile.gettempdir(),
        STATE_DIR,
        hashlib.sha256(session.encode("utf-8")).hexdigest()[:16] + ".json",
    )
    seen = _load(state)
    if path in seen:
        return None
    creating = data.get("tool_name") == "Write" and not os.path.exists(path)
    _store(state, seen + [path])
    return _creation_facts(file_path) if creating else _edit_facts(file_path)


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:
        # Different drives on Windows: the file is outside the project.
        return False


def _load(state: str) -> list[str]:
    if not os.path.exists(state):
        return []
    with open(state, encoding="utf-8") as f:
        seen = json.load(f)
    if not isinstance(seen, list) or not all(isinstance(p, str) for p in seen):
        raise ValueError(f"unreadable state: {state}")
    return seen


def _store(state: str, seen: list[str]) -> None:
    # os.replace: another hook of the same session reading at that moment finds
    # the old file or the new one, never one written halfway.
    folder = os.path.dirname(state)
    os.makedirs(folder, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=folder, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(seen, f)
        os.replace(tmp, state)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def _edit_facts(file_path: str) -> str:
    return (
        f"{NAME}: before editing {file_path} present these facts, then retry.\n"
        "1. Which files import or call this file: search for them, do not deduce them.\n"
        "2. Which public functions, classes or interfaces change with the edit.\n"
        "3. If the file reads or writes data, its format: fields, structure, "
        "dates, with synthetic values.\n"
        "4. The user's instruction that motivates the edit, quoted verbatim.\n"
        "The second attempt on the same file passes."
    )


def _creation_facts(file_path: str) -> str:
    return (
        f"{NAME}: before creating {file_path} present these facts, then retry.\n"
        "1. Which file, and at which line, will call the new file.\n"
        "2. That no existing file already does the same thing: search for it, do not deduce it.\n"
        "The second attempt on the same file passes."
    )


def _say(text: str) -> None:
    # A warning that cannot be printed does not change the outcome.
    try:
        sys.stderr.write(text + "\n")
        sys.stderr.flush()
    except BaseException:
        pass


def main() -> None:
    code = 0
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        data = json.loads(sys.stdin.buffer.read().decode("utf-8"))
        facts = verdict(data)
    except BaseException as exc:
        _say(f"{NAME}: internal error ({exc!r}), letting it through unchecked")
    else:
        if facts:
            _say(facts)
            code = 2
    os._exit(code)


if __name__ == "__main__":
    main()
