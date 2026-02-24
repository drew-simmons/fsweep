"""Engine-focused tests, including symlink and cleanup behavior."""

import os
from pathlib import Path

import pytest

from fsweep.cli import FSweepEngine

ONE_MIB = 1024 * 1024
READ_WRITE_EXECUTE_PERMS = 0o755
NO_PERMS = 0o000


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
    engine.cleanup(dry_run=True)

    # Folder should still exist
    assert junk_dir.exists()


def test_engine_cleanup_deletes_when_not_dry_run(tmp_path: Path) -> None:
    """Verify that FSweepEngine.cleanup deletes files when dry_run is False."""
    junk_dir = tmp_path / "node_modules"
    junk_dir.mkdir()
    (junk_dir / "file.txt").write_text("content")

    engine = FSweepEngine(tmp_path)
    engine.found_items = [junk_dir]

    # Run cleanup with dry_run=False
    engine.cleanup(dry_run=False)

    # Folder should be gone
    assert not junk_dir.exists()
