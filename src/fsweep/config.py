from typing import Set

TARGET_FOLDERS: Set[str] = {
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
    ".next",
    ".docusaurus",
    # New additions
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    "target",  # Rust/Java
    "bin",  # C#
    "obj",  # C#
    ".gradle",  # Java/Kotlin
}
