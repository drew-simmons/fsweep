"""Tests for fsweep CLI behavior and engine basics."""

import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from typer.testing import CliRunner

from fsweep.cli import DEFAULT_MAX_DELETE_COUNT, FSweepEngine, app
from fsweep.config import TARGET_FOLDERS

runner = CliRunner()
ONE_KIB = 1024
EXPECTED_FOUND_ITEMS = 2
DELETE_FAILURE_EXIT_CODE = 2


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
    result = runner.invoke(app, ["--path", str(mock_workspace)])
    assert result.exit_code == 0
    assert "DRY-RUN MODE" in result.stdout
    assert "Would have recovered" in result.stdout
    assert "Cleanup Summary" in result.stdout

    # Verify files were NOT deleted
    assert (mock_workspace / "project_a" / "node_modules").exists()


def test_cli_rejects_destructive_run_without_yes_delete(mock_workspace: Path) -> None:
    """Verify destructive mode requires --yes-delete."""
    result = runner.invoke(app, ["--path", str(mock_workspace), "--delete"])
    assert result.exit_code == 1
    assert "requires --yes-delete" in result.stdout


def test_cli_destructive_run_with_confirmation(mock_workspace: Path) -> None:
    """Verify interactive destructive mode still asks for confirmation."""
    result = runner.invoke(
        app,
        ["--path", str(mock_workspace), "--delete", "--yes-delete"],
        input="y\n",
    )
    assert result.exit_code == 0
    assert "Do you want to delete these folders?" in result.stdout
    assert "Cleanup Summary" in result.stdout
    assert not (mock_workspace / "project_a" / "node_modules").exists()


def test_cli_refuses_root_path() -> None:
    """Verify sweeping root path is rejected."""
    result = runner.invoke(app, ["--path", "/", "--delete", "--yes-delete"])
    assert result.exit_code == 1
    assert "Refusing to sweep filesystem root" in result.stdout


def test_cli_refuses_home_root_path() -> None:
    """Verify sweeping home root path is rejected."""
    result = runner.invoke(
        app,
        ["--path", str(Path.home()), "--delete", "--yes-delete"],
    )
    assert result.exit_code == 1
    assert "Refusing to sweep your home directory root" in result.stdout


def test_cli_applies_max_delete_count_limit(tmp_path: Path) -> None:
    """Verify max-delete-count blocks large destructive runs."""
    for idx in range(DEFAULT_MAX_DELETE_COUNT + 1):
        (tmp_path / f"project_{idx}" / "node_modules").mkdir(parents=True)

    result = runner.invoke(
        app,
        ["--path", str(tmp_path), "--delete", "--yes-delete", "--force"],
    )
    assert result.exit_code == 1
    assert "exceeds --max-delete-count" in result.stdout


def test_cli_no_delete_limit_allows_large_run(tmp_path: Path) -> None:
    """Verify no-delete-limit overrides max-delete-count."""
    for idx in range(DEFAULT_MAX_DELETE_COUNT + 1):
        (tmp_path / f"project_{idx}" / "node_modules").mkdir(parents=True)

    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--delete",
            "--yes-delete",
            "--force",
            "--no-delete-limit",
        ],
    )
    assert result.exit_code == 0


def test_python_module_entrypoint_help() -> None:
    """Verify `python -m fsweep --help` exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "fsweep", "--help"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Usage:" in result.stdout


def test_cli_exits_non_zero_on_delete_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify destructive run exits non-zero when a delete fails."""
    target = tmp_path / "project" / "node_modules"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("content")

    def fake_rmtree(_: Path) -> None:
        raise PermissionError("blocked")

    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    result = runner.invoke(
        app,
        ["--path", str(tmp_path), "--delete", "--yes-delete", "--force"],
    )
    assert result.exit_code == DELETE_FAILURE_EXIT_CODE
    assert "failed to delete" in result.stdout


def test_cli_best_effort_allows_delete_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify --best-effort returns success when delete failures occur."""
    target = tmp_path / "project" / "node_modules"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("content")

    def fake_rmtree(_: Path) -> None:
        raise PermissionError("blocked")

    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--delete",
            "--yes-delete",
            "--force",
            "--best-effort",
        ],
    )
    assert result.exit_code == 0
    assert "Cleanup Summary" in result.stdout


def test_cli_json_output_is_machine_readable(mock_workspace: Path) -> None:
    """Verify --output json returns stable JSON payload."""
    result = runner.invoke(app, ["--path", str(mock_workspace), "--output", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1"
    assert payload["dry_run"] is True
    assert payload["summary"]["matched_count"] == EXPECTED_FOUND_ITEMS
    assert len(payload["items"]) == EXPECTED_FOUND_ITEMS


def test_cli_trash_moves_directories(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify --trash moves matched directories to fsweep trash path."""
    target = tmp_path / "project" / "node_modules"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("content")

    trash_root = tmp_path / ".fsweep_trash" / "test-run"

    def fake_trash_root(_: FSweepEngine) -> Path:
        trash_root.mkdir(parents=True, exist_ok=True)
        return trash_root

    monkeypatch.setattr(FSweepEngine, "_trash_root", fake_trash_root)

    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--delete",
            "--trash",
            "--yes-delete",
            "--force",
        ],
    )
    assert result.exit_code == 0
    assert not target.exists()
    assert (trash_root / "project" / "node_modules" / "file.txt").exists()


def test_cli_interactive_selection_deletes_only_selected(tmp_path: Path) -> None:
    """Verify --interactive can limit deletion to a selected index set."""
    first = tmp_path / "project_a" / "node_modules"
    second = tmp_path / "project_b" / "venv"
    first.mkdir(parents=True)
    second.mkdir(parents=True)

    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--delete",
            "--yes-delete",
            "--interactive",
            "--force",
        ],
        input="1\n",
    )
    assert result.exit_code == 0
    assert not first.exists()
    assert second.exists()


def test_cli_protected_path_is_excluded_from_results(tmp_path: Path) -> None:
    """Verify protected paths are not scanned or acted on."""
    protected_target = tmp_path / "project_a" / "node_modules"
    unprotected_target = tmp_path / "project_b" / "venv"
    protected_target.mkdir(parents=True)
    unprotected_target.mkdir(parents=True)

    result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--output",
            "json",
            "--protected-path",
            str(tmp_path / "project_a"),
        ],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    item_paths = {item["relative_path"] for item in payload["items"]}
    assert "project_a/node_modules" not in item_paths
    assert "project_b/venv" in item_paths


def test_cli_default_path_is_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify default --path uses current working directory."""
    target = tmp_path / "node_modules"
    target.mkdir()
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, ["--output", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["path"] == str(tmp_path.resolve())


def test_cli_config_precedence_cli_overrides(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify precedence order: CLI > explicit config > local config > global config."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    global_config = tmp_path / "global.toml"
    explicit_config = tmp_path / "explicit.toml"
    local_config = workspace / "fsweep.toml"

    global_config.write_text(
        textwrap.dedent(
            """
            [fsweep]
            target_folders = ["cache_global"]
            max_delete_count = 10
            """
        ).strip()
        + "\n"
    )
    local_config.write_text(
        textwrap.dedent(
            """
            [fsweep]
            target_folders = ["cache_local"]
            max_delete_count = 9
            """
        ).strip()
        + "\n"
    )
    explicit_config.write_text(
        textwrap.dedent(
            """
            [fsweep]
            target_folders = ["cache_explicit"]
            max_delete_count = 8
            """
        ).strip()
        + "\n"
    )

    for name in ["cache_global", "cache_local", "cache_explicit"]:
        (workspace / "project" / name).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr("fsweep.cli.global_config_path", lambda: global_config)

    result = runner.invoke(
        app,
        [
            "--path",
            str(workspace),
            "--config",
            str(explicit_config),
            "--delete",
            "--yes-delete",
            "--force",
            "--max-delete-count",
            "1",
            "--output",
            "json",
        ],
    )
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert "--max-delete-count=1" in payload["error"]


def test_cli_dry_run_parity_with_destructive_set(tmp_path: Path) -> None:
    """Verify dry-run and destructive run target the same matched paths."""
    first = tmp_path / "project_a" / "node_modules"
    second = tmp_path / "project_b" / "venv"
    first.mkdir(parents=True)
    second.mkdir(parents=True)

    dry_run_result = runner.invoke(app, ["--path", str(tmp_path), "--output", "json"])
    assert dry_run_result.exit_code == 0
    dry_payload = json.loads(dry_run_result.stdout)
    dry_set = {item["relative_path"] for item in dry_payload["items"]}

    delete_result = runner.invoke(
        app,
        [
            "--path",
            str(tmp_path),
            "--delete",
            "--yes-delete",
            "--force",
            "--output",
            "json",
        ],
    )
    assert delete_result.exit_code == 0
    delete_payload = json.loads(delete_result.stdout)
    delete_set = {item["relative_path"] for item in delete_payload["items"]}

    assert delete_set == dry_set
