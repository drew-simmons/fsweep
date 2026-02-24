"""Tests for fsweep CLI behavior and engine basics."""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from fsweep.cli import FSweepEngine, app
from fsweep.config import TARGET_FOLDERS

runner = CliRunner()
ONE_KIB = 1024
EXPECTED_FOUND_ITEMS = 2


@pytest.fixture
def mock_workspace(tmp_path: Path) -> Path:
    """Creates a fake directory structure for testing.

    - project_a/node_modules (should find)
    - project_b/venv (should find)
    - project_c/src (should NOT find)
    """
    # Create junk folders
    (tmp_path / "project_a" / "node_modules").mkdir(parents=True)
    (tmp_path / "project_b" / "venv").mkdir(parents=True)

    # Add a dummy file to test size calculation (1KB)
    dummy_file = tmp_path / "project_a" / "node_modules" / "test.txt"
    dummy_file.write_bytes(b"a" * ONE_KIB)

    # Create a legitimate folder that should be ignored
    (tmp_path / "project_c" / "src").mkdir(parents=True)

    return tmp_path


def test_fsweep_finds_targeted_folders(mock_workspace: Path) -> None:
    """Verify that the engine only finds folders in TARGET_FOLDERS."""
    engine = FSweepEngine(mock_workspace)
    engine.scan()

    found_names = {item.name for item in engine.found_items}

    assert "node_modules" in found_names
    assert "venv" in found_names
    assert "src" not in found_names
    assert len(engine.found_items) == EXPECTED_FOUND_ITEMS


def test_fsweep_calculates_size(mock_workspace: Path) -> None:
    """Verify size calculation accurately reports bytes."""
    engine = FSweepEngine(mock_workspace)
    engine.scan()

    # We added 1 KiB to project_a/node_modules.
    assert engine.total_bytes >= ONE_KIB


def test_format_size_conversion() -> None:
    """Verify the human-readable string formatting."""
    engine = FSweepEngine(Path("."))

    assert engine.format_size(500) == "500.00 B"
    assert engine.format_size(ONE_KIB * ONE_KIB) == "1.00 MB"
    assert engine.format_size(ONE_KIB**3) == "1.00 GB"


@pytest.mark.parametrize("folder_name", list(TARGET_FOLDERS)[:3])
def test_target_folders_discovery(tmp_path: Path, folder_name: str) -> None:
    """Parametrized test to ensure various target types are discovered."""
    junk_dir = tmp_path / "subdir" / folder_name
    junk_dir.mkdir(parents=True)

    engine = FSweepEngine(tmp_path)
    engine.scan()

    assert any(item.name == folder_name for item in engine.found_items)


def test_cli_dry_run(mock_workspace: Path) -> None:
    """Verify that --dry-run flag is accepted and simulation is reported."""
    result = runner.invoke(app, ["--path", str(mock_workspace), "--dry-run"])
    assert result.exit_code == 0
    assert "DRY-RUN MODE" in result.stdout
    assert "Would have recovered" in result.stdout

    # Verify files were NOT deleted
    assert (mock_workspace / "project_a" / "node_modules").exists()
