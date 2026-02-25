"""Tests for fsweep config values."""

import textwrap
from pathlib import Path
from typing import Optional, Set

import pytest

EXPECTED_MAX_DELETE_COUNT = 7
EXPECTED_OVERRIDE_MAX_DELETE_COUNT = 3


try:
    from fsweep.config import (
        TARGET_FOLDERS,
        ConfigOverrides,
        SweepConfig,
        load_config_overrides,
        merge_overrides,
    )
except ImportError:
    TARGET_FOLDERS: Optional[Set[str]] = None
    ConfigOverrides = None  # type: ignore[misc,assignment]
    SweepConfig = None  # type: ignore[misc,assignment]
    load_config_overrides = None  # type: ignore[misc,assignment]
    merge_overrides = None  # type: ignore[misc,assignment]


def test_config_exists() -> None:
    """Verify that the config module exists and exports TARGET_FOLDERS."""
    assert TARGET_FOLDERS is not None, (
        "fsweep.config module or TARGET_FOLDERS not found"
    )


def test_new_artifacts_in_config() -> None:
    """Verify that new artifacts are present in TARGET_FOLDERS."""
    if TARGET_FOLDERS is None:
        pytest.fail("TARGET_FOLDERS not available")

    expected_artifacts = {
        ".tox",
        ".mypy_cache",
        ".ruff_cache",
        ".uv-cache",
        ".rumdl_cache",
        ".gradle",
        ".aws-sam",
    }

    # Check if all expected artifacts are in TARGET_FOLDERS
    assert TARGET_FOLDERS is not None
    missing = expected_artifacts - TARGET_FOLDERS
    assert not missing, f"Missing expected artifacts in TARGET_FOLDERS: {missing}"


def test_ambiguous_folder_names_are_not_default_targets() -> None:
    """Verify ambiguous generic folder names are not scanned by default."""
    assert TARGET_FOLDERS is not None

    ambiguous_names = {"build", "dist", "out", "bin", "obj", "target"}
    assert TARGET_FOLDERS.isdisjoint(ambiguous_names)


def test_load_config_overrides_from_fsweep_table(tmp_path: Path) -> None:
    """Verify fsweep.toml values are parsed from [fsweep] table."""
    if load_config_overrides is None:
        pytest.fail("load_config_overrides not available")

    config_file = tmp_path / "fsweep.toml"
    config_file.write_text(
        textwrap.dedent(
            """
            [fsweep]
            target_folders = ["vendor_cache"]
            exclude_patterns = ["**/keep/**"]
            protected_paths = ["important"]
            max_delete_count = 7
            no_delete_limit = true
            """
        ).strip()
        + "\n"
    )
    loaded = load_config_overrides(config_file)
    assert "vendor_cache" in loaded.target_folders
    assert loaded.exclude_patterns == ["**/keep/**"]
    assert loaded.max_delete_count == EXPECTED_MAX_DELETE_COUNT
    assert loaded.no_delete_limit is True
    assert (tmp_path / "important").resolve() in loaded.protected_paths


def test_merge_overrides_applies_additive_lists_and_scalar_override() -> None:
    """Verify merge semantics for additive list fields and scalar fields."""
    if merge_overrides is None or SweepConfig is None or ConfigOverrides is None:
        pytest.fail("merge_overrides, SweepConfig, or ConfigOverrides not available")

    base = SweepConfig(
        target_folders={"node_modules"},
        exclude_patterns=["**/.git/**"],
        protected_paths=[Path("/tmp/protected")],
        max_delete_count=50,
        no_delete_limit=False,
    )
    merged = merge_overrides(
        base,
        ConfigOverrides(
            target_folders={"custom_cache"},
            exclude_patterns=["**/tmp/**"],
            protected_paths=[Path("/tmp/protected2")],
            max_delete_count=3,
            no_delete_limit=True,
        ),
    )
    assert "node_modules" in merged.target_folders
    assert "custom_cache" in merged.target_folders
    assert merged.exclude_patterns == ["**/.git/**", "**/tmp/**"]
    assert Path("/tmp/protected").resolve() in [
        path.resolve() for path in merged.protected_paths
    ]
    assert Path("/tmp/protected2").resolve() in [
        path.resolve() for path in merged.protected_paths
    ]
    assert merged.max_delete_count == EXPECTED_OVERRIDE_MAX_DELETE_COUNT
    assert merged.no_delete_limit is True
