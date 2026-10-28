"""Guards that keep the design honest: the dependency rule, and OCR only through MinerU.

Layers, inner to outer: domain → application → adapters → entry points (cli, wiring, config).
Adapted from OJK-Register-Connector/tests/test_architecture.py.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "reports"

ALLOWED_INTERNAL = {
    "domain": {"domain"},
    "application": {"domain", "application"},
    "adapters": {"domain", "application", "adapters"},
}
THIRD_PARTY_ALLOWED_IN = {"adapters"}  # and the entry points

# The project owner's rule (Metamorph-Knowledge-Platform/docs/engineering-principles.md): OCR is MinerU's alone.
OTHER_OCR = {"pytesseract", "tesserocr", "easyocr", "paddleocr", "ocrmypdf", "get_textpage_ocr", "textract"}


def _layer(path: Path) -> str | None:
    first = path.relative_to(PACKAGE).parts[0]
    return first if first in ALLOWED_INTERNAL else None


def _imports(path: Path) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _violations() -> list[str]:
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        layer = _layer(path)
        if layer is None:
            continue
        for name in _imports(path):
            top = name.split(".")[0]
            if top == "reports":
                inner = name.split(".")[1] if "." in name else ""
                if inner not in ALLOWED_INTERNAL[layer]:
                    found.append(f"{path.relative_to(ROOT)} imports {name}")
            elif top not in sys.stdlib_module_names and layer not in THIRD_PARTY_ALLOWED_IN:
                found.append(f"{path.relative_to(ROOT)} imports third-party {name}")
    return found


def test_dependencies_point_inward_only() -> None:
    assert _violations() == []


def test_no_ocr_engine_but_mineru() -> None:
    names_used = {
        f"{path.relative_to(ROOT)}: {name}"
        for path in PACKAGE.rglob("*.py")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
        for name in _names(node)
        if name in OTHER_OCR
    }
    assert names_used == set()


def _names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name.split(".")[0] for alias in node.names]
    if isinstance(node, ast.ImportFrom) and node.module:
        return [node.module.split(".")[0]]
    if isinstance(node, ast.Attribute):
        return [node.attr]
    return []
