"""Engine-focused tests, including symlink and cleanup behavior."""

import os
import shutil
import time
from pathlib import Path

import pytest

from fsweep.cli import FSweepEngine

ONE_MIB = 1024 * 1024
READ_WRITE_EXECUTE_PERMS = 0o755
NO_PERMS = 0o000
EXPECTED_TWO_ITEMS = 2
PERFORMANCE_THRESHOLD_SECONDS = 2.5
INDEX_CACHE_FILE_BYTES = 128


@pytest.fixture
def symlink_workspace(tmp_path: Path) -> Path:
    """Creates a workspace with symlinks to test size calculation.

    Structure:
    - real_folder/
        - large_file.txt (1MB)
    - junk_folder/ (targeted)
        - link_to_real -> ../real_folder
    """
    real_folder = tmp_path / "real_folder"
    real_folder.mkdir()
    large_file = real_folder / "large_file.txt"
    large_file.write_bytes(b"a" * ONE_MIB)  # 1MB

    junk_folder = tmp_path / "junk_folder"
    junk_folder.mkdir()

    # Create symlink: junk_folder/link_to_real points to real_folder
    # Note: On some systems or permissions this might fail.
    try:
        os.symlink(real_folder, junk_folder / "link_to_real")
    except OSError:
        pytest.skip("Symlinks not supported on this platform")

    return tmp_path


def test_get_size_ignores_symlinks(symlink_workspace: Path) -> None:
    """Verify that get_size does NOT follow symlinks to directories.

    preventing double counting or counting outside junk folder.
    """
    engine = FSweepEngine(symlink_workspace)
    junk_folder = symlink_workspace / "junk_folder"

    # The junk folder contains only a symlink.
    # If we follow it, size will be > 1MB.
    # If we ignore it (or just count the link itself), size should be negligible.

    size = engine.get_size(junk_folder)

    # Size should be small (size of symlink), definitely not 1MB
    assert size < ONE_MIB, f"Size {size} indicates symlink was followed!"


def test_get_size_symlink_to_file(symlink_workspace: Path) -> None:
    """Verify that get_size does not count the target size of a file symlink."""
    engine = FSweepEngine(symlink_workspace)
    real_folder = symlink_workspace / "real_folder"
    junk_folder = symlink_workspace / "junk_folder"

    # Create symlink to file: junk_folder/link_to_file -> real_folder/large_file.txt
    try:
        os.symlink(real_folder / "large_file.txt", junk_folder / "link_to_file")
    except OSError:
        pytest.skip("Symlinks not supported")

    size = engine.get_size(junk_folder)

    # Should be small (link size), not 1MB
    assert size < ONE_MIB, f"Size {size} indicates file symlink was followed!"


def test_get_size_handles_permission_error(tmp_path: Path) -> None:
    """Verify that get_size skips files/folders it cannot access."""
    engine = FSweepEngine(tmp_path)
    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()

    protected_file = restricted_dir / "secret.txt"
    protected_file.write_text("shhh")

    # Make it unreadable
    os.chmod(restricted_dir, NO_PERMS)

    try:
        # Should not raise PermissionError
        size = engine.get_size(tmp_path)
        assert size == 0
    finally:
        # Restore permissions so pytest can clean up
        os.chmod(restricted_dir, READ_WRITE_EXECUTE_PERMS)


def test_engine_cleanup_respects_dry_run(tmp_path: Path) -> None:
    """Verify that FSweepEngine.cleanup does not delete files when dry_run is True."""
    junk_dir = tmp_path / "node_modules"
    junk_dir.mkdir()
    (junk_dir / "file.txt").write_text("content")

    engine = FSweepEngine(tmp_path)
    engine.found_items = [junk_dir]

    # Run cleanup with dry_run=True
    stats, _ = engine.cleanup(dry_run=True)

    # Folder should still exist
    assert junk_dir.exists()
    assert stats.deleted == 0
    assert stats.skipped == 1
    assert stats.failed == 0


def test_engine_cleanup_deletes_when_not_dry_run(tmp_path: Path) -> None:
    """Verify that FSweepEngine.cleanup deletes files when dry_run is False."""
    junk_dir = tmp_path / "node_modules"
    junk_dir.mkdir()
    (junk_dir / "file.txt").write_text("content")

    engine = FSweepEngine(tmp_path)
    engine.found_items = [junk_dir]

    # Run cleanup with dry_run=False
    stats, _ = engine.cleanup(dry_run=False)

    # Folder should be gone
    assert not junk_dir.exists()
    assert stats.deleted == 1
    assert stats.skipped == 0
    assert stats.failed == 0


def test_engine_cleanup_handles_delete_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify cleanup continues and records failures when deletes error."""
    ok_dir = tmp_path / "node_modules"
    ok_dir.mkdir()
    (ok_dir / "file.txt").write_text("content")

    failing_dir = tmp_path / "venv"
    failing_dir.mkdir()
    (failing_dir / "file.txt").write_text("content")

    engine = FSweepEngine(tmp_path)
    engine.found_items = [ok_dir, failing_dir]

    original_rmtree = shutil.rmtree

    def fake_rmtree(path: Path) -> None:
        if Path(path) == failing_dir:
            raise PermissionError("blocked")
        original_rmtree(path)

    monkeypatch.setattr(shutil, "rmtree", fake_rmtree)

    stats, _ = engine.cleanup(dry_run=False)

    assert not ok_dir.exists()
    assert failing_dir.exists()
    assert stats.deleted == 1
    assert stats.skipped == 0
    assert stats.failed == 1


def test_scan_finds_nested_target_directories(tmp_path: Path) -> None:
    """Verify scan finds nested target directories exactly once each."""
    top_target = tmp_path / "project" / "node_modules"
    nested_target = top_target / "nested" / "venv"
    top_target.mkdir(parents=True)
    nested_target.mkdir(parents=True)

    engine = FSweepEngine(tmp_path)
    engine.scan()

    found = {item.relative_to(tmp_path) for item in engine.found_items}
    assert Path("project/node_modules") in found
    # Nested venv is inside a matched folder, so scan should prune and skip it.
    assert Path("project/node_modules/nested/venv") not in found


def test_scan_handles_symlink_loop(tmp_path: Path) -> None:
    """Verify scan does not recurse through symlink loops."""
    project = tmp_path / "project"
    project.mkdir()
    target = project / "node_modules"
    target.mkdir()

    loop_link = project / "loop"
    try:
        os.symlink(project, loop_link)
    except OSError:
        pytest.skip("Symlinks not supported on this platform")

    engine = FSweepEngine(tmp_path)
    engine.scan()

    assert target in engine.found_items


def test_scan_multi_project_duplicates(tmp_path: Path) -> None:
    """Verify same folder names in multiple projects are all discovered."""
    first = tmp_path / "project_a" / "node_modules"
    second = tmp_path / "project_b" / "node_modules"
    first.mkdir(parents=True)
    second.mkdir(parents=True)

    engine = FSweepEngine(tmp_path)
    engine.scan()

    assert first in engine.found_items
    assert second in engine.found_items
    assert len(engine.found_items) == EXPECTED_TWO_ITEMS


def test_scan_permission_restricted_target_folder(tmp_path: Path) -> None:
    """Verify scan does not crash when target folder permissions are restricted."""
    restricted = tmp_path / "project" / "node_modules"
    restricted.mkdir(parents=True)
    (restricted / "content.txt").write_text("x")
    os.chmod(restricted, NO_PERMS)

    try:
        engine = FSweepEngine(tmp_path)
        engine.scan()
        assert restricted in engine.found_items
        assert engine.item_sizes[restricted] == 0
    finally:
        os.chmod(restricted, READ_WRITE_EXECUTE_PERMS)


def test_scan_performance_sanity_non_blocking(tmp_path: Path) -> None:
    """Benchmark-style scan test gated by env var to avoid CI flakiness."""
    if os.getenv("FSWEEP_PERF_CHECK") != "1":
        pytest.skip("Set FSWEEP_PERF_CHECK=1 to run performance sanity check.")

    project_count = 200
    for idx in range(project_count):
        target = tmp_path / f"project_{idx}" / "node_modules"
        target.mkdir(parents=True)
        (target / "file.txt").write_bytes(b"x" * 512)

    start = time.perf_counter()
    engine = FSweepEngine(tmp_path)
    engine.scan()
    elapsed = time.perf_counter() - start

    assert len(engine.found_items) == project_count
    assert elapsed < PERFORMANCE_THRESHOLD_SECONDS


def test_scan_writes_index_file(tmp_path: Path) -> None:
    """Verify scan writes an index file when indexing is enabled."""
    target = tmp_path / "project" / "node_modules"
    target.mkdir(parents=True)
    (target / "file.txt").write_text("content")
    index_file = tmp_path / ".fsweep-index.json"

    engine = FSweepEngine(tmp_path)
    engine.scan(show_progress=False, use_index=True, index_path=index_file)

    assert index_file.exists()
    contents = index_file.read_text()
    assert '"schema_version": "1"' in contents
    assert str(target.resolve()) in contents


def test_scan_uses_index_cache_when_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify repeated scans can reuse indexed size values."""
    target = tmp_path / "project" / "node_modules"
    target.mkdir(parents=True)
    (target / "file.txt").write_bytes(b"x" * INDEX_CACHE_FILE_BYTES)
    index_file = tmp_path / ".fsweep-index.json"

    first_engine = FSweepEngine(tmp_path)
    first_engine.scan(show_progress=False, use_index=True, index_path=index_file)
    assert target in first_engine.found_items

    def fail_get_size(_: Path) -> int:
        raise AssertionError("get_size should not be called when index cache is valid")

    second_engine = FSweepEngine(tmp_path)
    monkeypatch.setattr(second_engine, "get_size", fail_get_size)
    second_engine.scan(show_progress=False, use_index=True, index_path=index_file)

    assert second_engine.item_sizes[target] == INDEX_CACHE_FILE_BYTES
