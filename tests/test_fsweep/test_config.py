"""Tests for fsweep config values."""

from typing import Optional, Set

import pytest

try:
    from fsweep.config import TARGET_FOLDERS
except ImportError:
    TARGET_FOLDERS: Optional[Set[str]] = None


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
        "target",
        "bin",
        "obj",
        ".gradle",
    }

    # Check if all expected artifacts are in TARGET_FOLDERS
    assert TARGET_FOLDERS is not None
    missing = expected_artifacts - TARGET_FOLDERS
    assert not missing, f"Missing expected artifacts in TARGET_FOLDERS: {missing}"
