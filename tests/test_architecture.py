"""Executable checks for the package boundaries in ``docs/architecture.md``."""

from __future__ import annotations

import ast
from pathlib import Path


PACKAGE = Path(__file__).parents[1] / "red_store"
TRANSFORMATIONS = {
    "message_parser",
    "incident_extractor",
}
STORES = {
    "message_store",
    "reference_store",
    "incident_store",
    "processing_issue_store",
}


def _module_tree(module_name: str) -> ast.Module:
    return ast.parse(
        (PACKAGE / f"{module_name}.py").read_text(encoding="utf-8")
    )


def _red_store_imports(module_name: str) -> set[str]:
    imported_modules: set[str] = set()
    for node in ast.walk(_module_tree(module_name)):
        if isinstance(node, ast.ImportFrom) and node.module == "red_store":
            imported_modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Import) and any(
            alias.name.startswith("red_store.") for alias in node.names
        ):
            imported_modules.update(
                alias.name.removeprefix("red_store.") for alias in node.names
            )
    return imported_modules


def test_runtime_package_is_flat() -> None:
    """Runtime Python modules live at the package root, not lifecycle levels."""

    nested_modules = [
        path
        for path in PACKAGE.rglob("*.py")
        if path.parent != PACKAGE
    ]

    assert nested_modules == []


def test_transformations_depend_on_no_runtime_io_layer() -> None:
    """Pure transformations may share model records, but never reach stores or I/O."""

    allowed_dependencies = {
        "message_parser": {"model"},
        "incident_extractor": {"model"},
    }
    forbidden_standard_modules = {"pathlib", "sqlite3"}

    for module_name in TRANSFORMATIONS:
        assert _red_store_imports(module_name) <= allowed_dependencies[module_name]
        imported_roots = {
            node.names[0].name.partition(".")[0]
            for node in ast.walk(_module_tree(module_name))
            if isinstance(node, ast.Import)
        }
        assert imported_roots.isdisjoint(forbidden_standard_modules)


def test_stores_depend_on_no_transformation_or_workflow_module() -> None:
    """SQL adapters may use model records, never parsing or orchestration."""

    for module_name in STORES:
        assert _red_store_imports(module_name) <= {"model"}


def test_only_store_and_infrastructure_modules_contain_sql_calls() -> None:
    """The use-case service coordinates store calls instead of owning SQL."""

    modules_without_sql = TRANSFORMATIONS | {"ingest_service", "cli", "model"}
    for module_name in modules_without_sql:
        call_attributes = {
            node.func.attr
            for node in ast.walk(_module_tree(module_name))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
        }
        assert call_attributes.isdisjoint({"execute", "executemany", "executescript"})
