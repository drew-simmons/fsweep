"""Configuration values and fsweep.toml loading."""

import importlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

try:
    tomllib = importlib.import_module("tomllib")
except ModuleNotFoundError:  # pragma: no cover - Python 3.10 fallback
    tomllib = importlib.import_module("tomli")
TOMLDecodeError = getattr(tomllib, "TOMLDecodeError", ValueError)

DEFAULT_MAX_DELETE_COUNT = 50

DEFAULT_TARGET_FOLDERS: Set[str] = {
    "node_modules",
    ".next",
    ".nuxt",
    ".svelte-kit",
    ".astro",
    ".turbo",
    ".parcel-cache",
    ".vite",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".tox",
    ".nox",
    ".mypy_cache",
    ".ruff_cache",
    ".ipynb_checkpoints",
    "build",
    "dist",
    "out",
    "coverage",
    "htmlcov",
    ".nyc_output",
    ".cache",
    ".gradle",
    "target",
    "bin",
    "obj",
    ".terraform",
    ".terragrunt-cache",
}


@dataclass
class ConfigOverrides:
    """Partial config values loaded from a source."""

    target_folders: Set[str] = field(default_factory=set)
    exclude_patterns: List[str] = field(default_factory=list)
    protected_paths: List[Path] = field(default_factory=list)
    max_delete_count: Optional[int] = None
    no_delete_limit: Optional[bool] = None


@dataclass
class SweepConfig:
    """Effective configuration after merging all sources."""

    target_folders: Set[str] = field(
        default_factory=lambda: set(DEFAULT_TARGET_FOLDERS)
    )
    exclude_patterns: List[str] = field(default_factory=list)
    protected_paths: List[Path] = field(default_factory=list)
    max_delete_count: int = DEFAULT_MAX_DELETE_COUNT
    no_delete_limit: bool = False


def global_config_path() -> Path:
    """Return global config path."""
    return Path.home() / ".config" / "fsweep" / "fsweep.toml"


def local_config_path(scan_path: Path) -> Path:
    """Return local config path for a scan root."""
    return scan_path / "fsweep.toml"


def load_config_overrides(config_path: Path) -> ConfigOverrides:
    """Load config overrides from a TOML file."""
    try:
        data = tomllib.loads(config_path.read_text())
    except TOMLDecodeError as exc:
        raise ValueError(f"Invalid TOML in {config_path}: {exc}") from exc

    source = data.get("fsweep", data)
    if not isinstance(source, dict):
        raise ValueError(f"Config root must be a table in {config_path}")
    return _parse_config_source(config_path, source)


def merge_overrides(
    base: SweepConfig,
    overrides: ConfigOverrides,
) -> SweepConfig:
    """Merge config overrides into the current effective config."""
    if overrides.target_folders:
        base.target_folders.update(overrides.target_folders)
    if overrides.exclude_patterns:
        base.exclude_patterns = _merge_unique(
            base.exclude_patterns, overrides.exclude_patterns
        )
    if overrides.protected_paths:
        base.protected_paths = _merge_unique_paths(
            base.protected_paths, overrides.protected_paths
        )
    if overrides.max_delete_count is not None:
        base.max_delete_count = overrides.max_delete_count
    if overrides.no_delete_limit is not None:
        base.no_delete_limit = overrides.no_delete_limit
    return base


def _parse_config_source(config_path: Path, source: Dict[str, Any]) -> ConfigOverrides:
    overrides = ConfigOverrides()
    overrides.target_folders = set(
        _coerce_str_list(config_path, source, "target_folders")
    )
    overrides.exclude_patterns = _coerce_str_list(
        config_path, source, "exclude_patterns"
    )
    overrides.protected_paths = [
        (config_path.parent / raw_path).resolve()
        for raw_path in _coerce_str_list(config_path, source, "protected_paths")
    ]

    if "max_delete_count" in source:
        raw = source["max_delete_count"]
        if not isinstance(raw, int) or raw < 1:
            raise ValueError(
                f"max_delete_count must be an integer >= 1 in {config_path}"
            )
        overrides.max_delete_count = raw

    if "no_delete_limit" in source:
        raw = source["no_delete_limit"]
        if not isinstance(raw, bool):
            raise ValueError(f"no_delete_limit must be a boolean in {config_path}")
        overrides.no_delete_limit = raw

    return overrides


def _coerce_str_list(
    config_path: Path,
    source: Dict[str, Any],
    key: str,
) -> List[str]:
    raw = source.get(key, [])
    if raw is None:
        return []
    if not isinstance(raw, list) or not all(isinstance(item, str) for item in raw):
        raise ValueError(f"{key} must be an array of strings in {config_path}")
    return raw


def _merge_unique(left: List[str], right: List[str]) -> List[str]:
    merged = list(left)
    for item in right:
        if item not in merged:
            merged.append(item)
    return merged


def _merge_unique_paths(left: List[Path], right: List[Path]) -> List[Path]:
    merged = list(left)
    known = {path.resolve() for path in left}
    for path in right:
        resolved = path.resolve()
        if resolved not in known:
            known.add(resolved)
            merged.append(resolved)
    return merged


# Backward-compatible import used in existing tests.
TARGET_FOLDERS: Set[str] = DEFAULT_TARGET_FOLDERS
