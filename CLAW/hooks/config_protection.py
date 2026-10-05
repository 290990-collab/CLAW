"""PreToolUse hook: the configuration of a linter that already exists is not edited.

An agent that cannot make a check pass tends to weaken the rule instead of
fixing the code. Creating a new configuration stays allowed: there is nothing
to weaken.

Closed hook: unreadable input, missing field, any error → exit 2. A check that
gives way silently on odd input is a check switched off without anyone
knowing.

Exit: 0 lets it through, 2 blocks with the reason on stderr.
"""

from __future__ import annotations

import json
import os
import sys

NAME = "config_protection"

# Lowercase: the comparison is on the lowercased name, because on a file system
# that does not distinguish case `.ESLINTRC.JSON` is the same file.
PROTECTED = frozenset(
    {
        ".eslintrc",
        ".eslintrc.js",
        ".eslintrc.cjs",
        ".eslintrc.json",
        ".eslintrc.yml",
        ".eslintrc.yaml",
        "eslint.config.js",
        "eslint.config.mjs",
        "eslint.config.cjs",
        "eslint.config.ts",
        "eslint.config.mts",
        "eslint.config.cts",
        ".prettierrc",
        ".prettierrc.js",
        ".prettierrc.cjs",
        ".prettierrc.json",
        ".prettierrc.yml",
        ".prettierrc.yaml",
        "prettier.config.js",
        "prettier.config.cjs",
        "prettier.config.mjs",
        "biome.json",
        "biome.jsonc",
        ".ruff.toml",
        "ruff.toml",
        ".shellcheckrc",
        ".stylelintrc",
        ".stylelintrc.json",
        ".stylelintrc.yml",
        ".markdownlint.json",
        ".markdownlint.yaml",
        ".markdownlintrc",
        ".flake8",
        ".pylintrc",
        "pylintrc",
        "mypy.ini",
        ".mypy.ini",
    }
)


def verdict(data: object) -> str | None:
    """The reason for the block, or `None` if the operation passes.

    `pyproject.toml` is left out on purpose: it also carries metadata and
    dependencies, and blocking it would stop legitimate changes.
    """
    if not isinstance(data, dict) or not isinstance(data.get("tool_input"), dict):
        raise ValueError("tool_input missing or not an object")
    path = data["tool_input"].get("file_path")
    if not isinstance(path, str) or not path:
        raise ValueError("file_path missing or not a string")
    name = path.replace("\\", "/").rsplit("/", 1)[-1].lower()
    if name not in PROTECTED:
        return None
    if not os.path.isabs(path):
        cwd = data.get("cwd")
        if not isinstance(cwd, str) or not cwd:
            raise ValueError("relative file_path and cwd missing")
        path = os.path.join(cwd, path)
    try:
        # lstat and not exists: a broken link is still a configuration that is
        # present, and any error other than "not there" treats it as present.
        os.lstat(path)
    except FileNotFoundError:
        return None
    return (
        f"{NAME}: {name} already exists and is the configuration of a linter or "
        "a formatter. Fix the code so it follows the rule instead of weakening "
        "it; if the configuration change is intended, ask the user for it."
    )


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
        reason = verdict(data)
    except BaseException as exc:
        reason = f"{NAME}: unreadable input or internal error ({exc!r}), blocking"
    if reason:
        _say(reason)
    # os._exit and not sys.exit: a failed flush on exit would turn the code
    # into 120, that is into "let it through".
    os._exit(2 if reason else 0)


if __name__ == "__main__":
    main()
