"""Configuration values for fsweep."""

from typing import Set

TARGET_FOLDERS: Set[str] = {
    # JavaScript / TypeScript
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".astro",
    ".turbo",
    ".parcel-cache",
    ".vite",
    # Python
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
    # Build artifacts (cross-language)
    "build",
    "dist",
    "out",
    "coverage",
    "htmlcov",
    ".nyc_output",
    ".cache",
    # JVM / .NET / Rust
    ".gradle",
    "target",
    "bin",
    "obj",
    # Infrastructure-as-Code
    ".terraform",
    ".terragrunt-cache",
}
