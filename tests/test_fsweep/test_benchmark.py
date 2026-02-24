"""Benchmark-style checks for scan/index behavior.

These checks are opt-in and skipped in normal CI runs.
"""

import os
import time
from pathlib import Path

import pytest

from fsweep.cli import FSweepEngine

BENCH_PROJECT_COUNT = 300
BENCH_FILE_BYTES = 2048


def _seed_workspace(tmp_path: Path, *, project_count: int) -> None:
    for idx in range(project_count):
        target = tmp_path / f"project_{idx}" / "node_modules"
        target.mkdir(parents=True)
        (target / "file.txt").write_bytes(b"x" * BENCH_FILE_BYTES)


def test_benchmark_scan_threshold(tmp_path: Path) -> None:
    """Verify scan benchmark threshold when explicitly enabled."""
    if os.getenv("FSWEEP_BENCHMARK") != "1":
        pytest.skip("Set FSWEEP_BENCHMARK=1 to run benchmark checks.")

    threshold_seconds = float(os.getenv("FSWEEP_BENCH_THRESHOLD_SECONDS", "4.0"))
    _seed_workspace(tmp_path, project_count=BENCH_PROJECT_COUNT)

    start = time.perf_counter()
    engine = FSweepEngine(tmp_path)
    engine.scan(show_progress=False, use_index=False)
    elapsed = time.perf_counter() - start

    assert len(engine.found_items) == BENCH_PROJECT_COUNT
    assert elapsed < threshold_seconds


def test_benchmark_indexed_scan_not_slower(tmp_path: Path) -> None:
    """Verify repeated indexed scan is not slower than non-indexed baseline."""
    if os.getenv("FSWEEP_BENCHMARK") != "1":
        pytest.skip("Set FSWEEP_BENCHMARK=1 to run benchmark checks.")

    _seed_workspace(tmp_path, project_count=BENCH_PROJECT_COUNT)
    index_file = tmp_path / ".fsweep-index.json"

    baseline_start = time.perf_counter()
    baseline_engine = FSweepEngine(tmp_path)
    baseline_engine.scan(show_progress=False, use_index=False)
    baseline_elapsed = time.perf_counter() - baseline_start

    first_index_start = time.perf_counter()
    indexed_engine_first = FSweepEngine(tmp_path)
    indexed_engine_first.scan(
        show_progress=False,
        use_index=True,
        index_path=index_file,
    )
    _ = time.perf_counter() - first_index_start

    second_index_start = time.perf_counter()
    indexed_engine_second = FSweepEngine(tmp_path)
    indexed_engine_second.scan(
        show_progress=False,
        use_index=True,
        index_path=index_file,
    )
    indexed_elapsed = time.perf_counter() - second_index_start

    assert len(indexed_engine_second.found_items) == BENCH_PROJECT_COUNT
    assert indexed_elapsed <= baseline_elapsed
