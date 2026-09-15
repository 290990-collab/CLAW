"""Structural parity between the two editions.

The editions are independent in use and identical in development: they must
differ by language only. Nothing in the repository enforced that, and a silent
divergence is the defect that costs most to find late, because it accumulates.

This check lives outside both editions on purpose. Each edition is copied out
on its own, so a test inside one that reached for the other would break the
moment the product is used as intended -- and adding it to both would break
the "same number of tests" property it is meant to defend.

Compared: what is structure. Never prose: the translation is the one difference
that is allowed, and a check that demanded equal text would forbid it.

Run: python .github/parity.py
"""

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IT = ROOT / "CLAW-it"
EN = ROOT / "CLAW-eng"

# Frontmatter keys an agent card may carry. `description` is read by Claude
# Code in the user's own language, so it is the one key allowed to differ.
AGENT_KEYS = ("name", "description", "model", "tools", "color", "effort")
AGENT_TRANSLATED = {"description"}

# Profile fields written for a human to read, hence translated. Everything
# else -- roster, guides, cycles, permissions -- is contract and must match.
PROFILE_TRANSLATED = {"description", "critical_surface"}

# Declared exception: these constants are localized contracts and their values
# are expected to differ. Their names must still exist on both sides, which is
# what the module API check covers.
LOCALIZED_CONSTANTS = {"METHOD_HEADING", "DOMAIN_HEADING", "PLACEHOLDER_RE"}


def files(root: Path) -> set[str]:
    out = set()
    for p in root.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts:
            continue
        rel = p.relative_to(root).as_posix()
        # Connected skill packages belong to other authors and never reach git:
        # they are local material, and one edition having them is not a
        # divergence. Only the framework's own skills are published.
        if rel.startswith("skills/") and not rel.startswith("skills/framework-"):
            continue
        out.add(rel)
    return out


def check_inventory() -> list[str]:
    a, b = files(IT), files(EN)
    return [f"only in it: {p}" for p in sorted(a - b)] + [
        f"only in eng: {p}" for p in sorted(b - a)
    ]


def api(path: Path) -> tuple[list[str], list[str], dict[str, object]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    functions = [
        n.name
        for n in tree.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    classes = [n.name for n in tree.body if isinstance(n, ast.ClassDef)]
    constants: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id.isupper():
                try:
                    value = ast.literal_eval(node.value)
                except ValueError:
                    value = None
                # Only numbers are compared: a budget or a price that drifts
                # between editions is a real divergence, a translated string
                # is not.
                constants[target.id] = (
                    value if isinstance(value, (int, float)) else None
                )
    return functions, classes, constants


def check_modules() -> list[str]:
    out = []
    for module in sorted(p.name for p in (IT / "tools" / "fwbuild").glob("*.py")):
        fi, ci, ki = api(IT / "tools" / "fwbuild" / module)
        fe, ce, ke = api(EN / "tools" / "fwbuild" / module)
        if fi != fe:
            out.append(f"{module}: functions differ -> {sorted(set(fi) ^ set(fe))}")
        if ci != ce:
            out.append(f"{module}: classes differ -> {sorted(set(ci) ^ set(ce))}")
        if set(ki) != set(ke):
            out.append(f"{module}: constants differ -> {sorted(set(ki) ^ set(ke))}")
        for name in sorted(set(ki) & set(ke) - LOCALIZED_CONSTANTS):
            if ki[name] is not None and ki[name] != ke[name]:
                out.append(f"{module}: {name} = {ki[name]} in it, {ke[name]} in eng")
    return out


def findings(root: Path) -> set[tuple[str, str]]:
    text = (root / "tools" / "fwbuild" / "doctor.py").read_text(encoding="utf-8")
    return set(re.findall(r'Finding\(\s*"([A-Z_]+)"\s*,\s*"(ERROR|WARN|NOTE)"', text))


def check_doctor_codes() -> list[str]:
    a, b = findings(IT), findings(EN)
    return [f"code/severity only in {'it' if p in a else 'eng'}: {p}" for p in sorted(a ^ b)]


def check_tests() -> list[str]:
    out = []
    for path in sorted((IT / "tools" / "tests").glob("test_*.py")):
        twin = EN / "tools" / "tests" / path.name
        if not twin.exists():
            out.append(f"{path.name}: missing in eng")
            continue
        a = re.findall(r"def (test_\w+)", path.read_text(encoding="utf-8"))
        b = re.findall(r"def (test_\w+)", twin.read_text(encoding="utf-8"))
        if a != b:
            out.append(f"{path.name}: test names differ -> {sorted(set(a) ^ set(b))}")
    return out


def frontmatter(path: Path) -> dict[str, str]:
    block = path.read_text(encoding="utf-8").split("---", 2)[1]
    keys = "|".join(AGENT_KEYS)
    out: dict[str, str] = {}
    current = None
    for line in block.splitlines():
        match = re.match(rf"^({keys}):\s*(.*)$", line)
        if match:
            current = match.group(1)
            out[current] = match.group(2)
        elif current:
            out[current] += " " + line.strip()
    return out


def check_agents() -> list[str]:
    out = []
    for path in sorted((IT / "agents").glob("*.md")):
        fi, fe = frontmatter(path), frontmatter(EN / "agents" / path.name)
        if set(fi) != set(fe):
            out.append(f"{path.name}: keys differ -> {sorted(set(fi) ^ set(fe))}")
        for key in sorted(set(fi) & set(fe) - AGENT_TRANSLATED):
            if fi[key] != fe[key]:
                out.append(f"{path.name}: {key} = {fi[key]!r} in it, {fe[key]!r} in eng")
    return out


def check_profiles() -> list[str]:
    out = []
    for path in sorted((IT / "profiles").glob("*.toml")):
        a = tomllib.loads(path.read_text(encoding="utf-8"))
        b = tomllib.loads((EN / "profiles" / path.name).read_text(encoding="utf-8"))
        if set(a) != set(b):
            out.append(f"{path.name}: keys differ -> {sorted(set(a) ^ set(b))}")
        for key in sorted(set(a) & set(b) - PROFILE_TRANSLATED):
            if a[key] != b[key]:
                out.append(f"{path.name}: {key} differs")
    return out


def check_version() -> list[str]:
    a = (IT / "VERSION").read_text(encoding="utf-8").strip()
    b = (EN / "VERSION").read_text(encoding="utf-8").strip()
    return [] if a == b else [f"VERSION: {a} in it, {b} in eng"]


CHECKS = (
    ("file inventory", check_inventory),
    ("fwbuild module API", check_modules),
    ("doctor codes and severities", check_doctor_codes),
    ("test names", check_tests),
    ("agent frontmatter", check_agents),
    ("profiles", check_profiles),
    ("VERSION", check_version),
)


def main() -> int:
    failed = 0
    for label, check in CHECKS:
        divergences = check()
        if divergences:
            failed += 1
            print(f"FAIL  {label}")
            for line in divergences:
                print(f"        {line}")
        else:
            print(f"ok    {label}")
    if failed:
        print(f"\n{failed} check(s) failed: the editions have drifted apart.")
        print("They must differ by language only -- fix the twin, do not relax the check.")
        return 1
    print("\nThe two editions are structurally identical.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
