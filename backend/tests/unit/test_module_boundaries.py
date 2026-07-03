"""Mechanical checks for the build rules the layout encodes (CLAUDE.md,
Backend Build Rules 1 & 3): domain/ is a pure shared kernel, and engine
modules never import each other except Valuation's pure math."""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"

ENGINES = {"knowledge", "valuation", "simulation", "optimization", "ai_reasoning"}
# The two sanctioned intra-stage exceptions (blueprint §3.1): Optimization and
# Simulation may call Valuation's pure functions.
ALLOWED_ENGINE_IMPORTS = {
    "optimization": {"valuation"},
    "simulation": {"valuation"},
}


def _app_imports(path: Path) -> set[str]:
    """Top-level `app.<pkg>` packages imported by a module."""
    tree = ast.parse(path.read_text())
    packages: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            packages.add(node.module.split(".")[1])
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("app."):
                    packages.add(alias.name.split(".")[1])
    return packages


def test_domain_imports_nothing_from_app() -> None:
    for module in (APP_DIR / "domain").glob("*.py"):
        illegal = _app_imports(module) - {"domain"}
        assert not illegal, f"domain/{module.name} must stay pure but imports {illegal}"


def test_engines_do_not_import_each_other() -> None:
    for engine in ENGINES:
        allowed = {engine, "domain", "config"} | ALLOWED_ENGINE_IMPORTS.get(engine, set())
        for module in (APP_DIR / engine).rglob("*.py"):
            illegal = _app_imports(module) - allowed
            assert not illegal, f"{engine}/{module.name} imports {illegal} across engine boundary"


def test_only_ai_reasoning_may_reference_llm_clients() -> None:
    llm_markers = ("pydantic_ai", "openai", "google.genai", "anthropic")
    for module in APP_DIR.rglob("*.py"):
        if "ai_reasoning" in module.parts:
            continue
        tree = ast.parse(module.read_text())
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.ImportFrom) and node.module:
                names.append(node.module)
                # `from google import genai` must resolve to google.genai,
                # not slip through as bare `google`.
                names.extend(f"{node.module}.{alias.name}" for alias in node.names)
            elif isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            for name in names:
                assert not name.startswith(llm_markers), (
                    f"{module.relative_to(APP_DIR)} imports LLM client '{name}' — "
                    "only ai_reasoning/ may touch an LLM (build rule 3)"
                )
