"""Command-line interface and cleanup engine for fsweep."""

from __future__ import annotations

import fnmatch
import json
import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from fsweep.config import (
    DEFAULT_MAX_DELETE_COUNT as CONFIG_DEFAULT_MAX_DELETE_COUNT,
)
from fsweep.config import (
    ConfigOverrides,
    SweepConfig,
    global_config_path,
    load_config_overrides,
    local_config_path,
    merge_overrides,
)

app = typer.Typer(help="Advanced workspace cleanup tool for developers.")
console = Console()
BYTE_UNIT_BASE = 1024
SCHEMA_VERSION = "1"
INDEX_SCHEMA_VERSION = "1"
DEFAULT_MAX_DELETE_COUNT = CONFIG_DEFAULT_MAX_DELETE_COUNT


class OutputFormat(str, Enum):
    """Supported output formats."""

    TABLE = "table"
    JSON = "json"


@dataclass
class CleanupStats:
    """Represents the outcome of a cleanup operation."""

    deleted: int = 0
    trashed: int = 0
    skipped: int = 0
    failed: int = 0


@dataclass
class ItemResult:
    """Execution result for one matched folder."""

    path: Path
    status: str
    error: Optional[str] = None
    trash_destination: Optional[Path] = None


class FSweepEngine:
    """Core engine for scanning and cleaning workspace artifacts."""

    def __init__(self, target_path: Path, config: Optional[SweepConfig] = None) -> None:
        """Initialize the engine with a scan root and config."""
        self.target_path = target_path.resolve()
        self.config = config or SweepConfig()
        self.found_items: List[Path] = []
        self.item_sizes: Dict[Path, int] = {}
        self.total_bytes: int = 0

    def get_size(self, path: Path) -> int:
        """Calculate folder size recursively, without following symlinks."""
        total = 0
        try:
            for node in path.rglob("*"):
                try:
                    if node.is_symlink():
                        total += node.lstat().st_size
                    elif node.is_file():
                        total += node.stat().st_size
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass
        return total

    def scan(
        self,
        *,
        show_progress: bool = True,
        use_index: bool = True,
        index_path: Optional[Path] = None,
    ) -> None:
        """Scan for target folders while honoring excludes and protections."""
        self.found_items = []
        self.item_sizes = {}
        self.total_bytes = 0

        scan_index = _load_scan_index(index_path) if use_index else {}
        updated_index: Dict[str, Dict[str, int]] = {}

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            disable=not show_progress,
        ) as progress:
            progress.add_task(description="Scanning for junk...", total=None)
            for current_root, dirs, _ in os.walk(
                self.target_path, topdown=True, followlinks=False
            ):
                root_path = Path(current_root)

                # Skip entire tree if .fsweepignore is found
                try:
                    if (root_path / ".fsweepignore").exists():
                        dirs[:] = []
                        continue
                except (PermissionError, OSError):
                    pass

                walkable_dirs: List[str] = []

                for name in dirs:
                    candidate = root_path / name
                    if self._is_excluded(candidate) or self._is_protected(candidate):
                        continue
                    walkable_dirs.append(name)
                walkable_dirs.sort()

                matched_dirs = [
                    name for name in walkable_dirs if name in self.config.target_folders
                ]
                for name in matched_dirs:
                    path = root_path / name
                    size = self._size_with_index(
                        path,
                        scan_index,
                        updated_index,
                        use_index,
                    )
                    self.found_items.append(path)
                    self.item_sizes[path] = size
                    self.total_bytes += size

                dirs[:] = [name for name in walkable_dirs if name not in matched_dirs]

        if use_index:
            _write_scan_index(index_path=index_path, entries=updated_index)

    def format_size(self, size_bytes: int) -> str:
        """Format bytes to a readable string."""
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < BYTE_UNIT_BASE:
                return f"{size:.2f} {unit}"
            size /= BYTE_UNIT_BASE
        return f"{size:.2f} TB"

    def cleanup(
        self,
        items: Optional[Sequence[Path]] = None,
        *,
        dry_run: bool,
        trash: bool = False,
        callback: Optional[Callable[[Path], None]] = None,
    ) -> tuple[CleanupStats, List[ItemResult]]:
        """Delete or move matched folders to the fsweep trash directory."""
        stats = CleanupStats()
        results: List[ItemResult] = []
        trash_root = self._trash_root() if trash and not dry_run else None

        selected_items = list(items) if items is not None else list(self.found_items)
        for item in selected_items:
            if dry_run:
                stats.skipped += 1
                result = ItemResult(path=item, status="simulated")
            else:
                result = self._cleanup_one(item, trash=trash, trash_root=trash_root)
                if result.status == "deleted":
                    stats.deleted += 1
                elif result.status == "trashed":
                    stats.trashed += 1
                elif result.status == "skipped":
                    stats.skipped += 1
                else:
                    stats.failed += 1

            results.append(result)
            if callback:
                callback(item)

        return stats, results

    def _cleanup_one(
        self,
        item: Path,
        *,
        trash: bool,
        trash_root: Optional[Path],
    ) -> ItemResult:
        try:
            if trash:
                destination = self._move_to_trash(item, trash_root=trash_root)
                return ItemResult(
                    path=item, status="trashed", trash_destination=destination
                )

            shutil.rmtree(item)
            return ItemResult(path=item, status="deleted")
        except FileNotFoundError:
            return ItemResult(path=item, status="skipped")
        except (PermissionError, OSError) as exc:
            return ItemResult(path=item, status="failed", error=str(exc))

    def _trash_root(self) -> Path:
        timestamp = datetime.now(tz=timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        trash_root = Path.home() / ".fsweep_trash" / timestamp
        trash_root.mkdir(parents=True, exist_ok=True)
        return trash_root

    def _move_to_trash(self, item: Path, *, trash_root: Optional[Path]) -> Path:
        if trash_root is None:
            raise OSError("trash root not initialized")
        relative = item.relative_to(self.target_path)
        destination = trash_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination = self._unique_path(destination)
        shutil.move(str(item), str(destination))
        return destination

    def _unique_path(self, path: Path) -> Path:
        counter = 1
        while True:
            candidate = path.with_name(f"{path.name}-{counter}")
            if not candidate.exists():
                return candidate
            counter += 1

    def _is_excluded(self, path: Path) -> bool:
        rel = path.relative_to(self.target_path).as_posix()
        return any(
            fnmatch.fnmatch(rel, pattern) or fnmatch.fnmatch(path.name, pattern)
            for pattern in self.config.exclude_patterns
        )

    def _is_protected(self, path: Path) -> bool:
        try:
            candidate = path.resolve()
        except OSError:
            candidate = path.absolute()
        for protected in self.config.protected_paths:
            if candidate == protected or protected in candidate.parents:
                return True
        return False

    def _size_with_index(
        self,
        path: Path,
        scan_index: Dict[str, Dict[str, int]],
        updated_index: Dict[str, Dict[str, int]],
        use_index: bool,
    ) -> int:
        path_key = str(path.resolve())
        mtime_ns = _directory_mtime_ns(path)
        if use_index:
            cached_entry = scan_index.get(path_key)
            if (
                cached_entry is not None
                and cached_entry.get("mtime_ns") == mtime_ns
                and "size_bytes" in cached_entry
            ):
                size = int(cached_entry["size_bytes"])
                updated_index[path_key] = {"mtime_ns": mtime_ns, "size_bytes": size}
                return size

        size = self.get_size(path)
        if use_index:
            updated_index[path_key] = {"mtime_ns": mtime_ns, "size_bytes": size}
        return size


@app.command()
def clean(  # noqa: PLR0912, PLR0913, PLR0915
    path: Path = typer.Option(
        Path("."),
        metavar="DIRECTORY",
        show_default=".",
        help="Workspace directory to scan.",
        rich_help_panel="Scan",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip final confirmation prompt.",
        rich_help_panel="Execution",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--delete",
        "-d",
        help="Preview actions (default) or perform deletion.",
        rich_help_panel="Execution",
    ),
    no_dry_run: bool = typer.Option(
        False,
        "--no-dry-run",
        hidden=True,
    ),
    trash: bool = typer.Option(
        False,
        "--trash",
        help="Move directories to ~/.fsweep_trash instead of hard deletion.",
        rich_help_panel="Execution",
    ),
    interactive: bool = typer.Option(
        False,
        "--interactive",
        help="Select which matched folders to act on.",
        rich_help_panel="Execution",
    ),
    output: OutputFormat = typer.Option(
        OutputFormat.TABLE,
        "--output",
        case_sensitive=False,
        help="Output format: table or json.",
        rich_help_panel="Output",
    ),
    report: Optional[Path] = typer.Option(
        None,
        "--report",
        help="Write a markdown report to this file path.",
        rich_help_panel="Output",
    ),
    use_index: bool = typer.Option(
        True,
        "--use-index/--no-index",
        help="Use a local scan-size index cache to speed repeated scans.",
        rich_help_panel="Execution",
    ),
    index_file: Optional[Path] = typer.Option(
        None,
        "--index-file",
        help="Path to scan index JSON file (default: <scan_path>/.fsweep-index.json).",
        rich_help_panel="Execution",
    ),
    config: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Load config overrides from a TOML file.",
        rich_help_panel="Config",
    ),
    target_folder: List[str] = typer.Option(
        [],
        "--target-folder",
        help="Add target folder names (repeatable).",
        rich_help_panel="Config",
    ),
    exclude_pattern: List[str] = typer.Option(
        [],
        "--exclude-pattern",
        help="Exclude path/name glob patterns (repeatable).",
        rich_help_panel="Config",
    ),
    protected_path: List[Path] = typer.Option(
        [],
        "--protected-path",
        help="Protect paths from scan/deletion (repeatable).",
        rich_help_panel="Config",
    ),
    yes_delete: bool = typer.Option(
        False,
        "--yes-delete",
        help="Required for destructive runs.",
        rich_help_panel="Safety",
    ),
    best_effort: bool = typer.Option(
        False,
        "--best-effort",
        help="Return success even if some deletes fail.",
        rich_help_panel="Safety",
    ),
    max_delete_count: Optional[int] = typer.Option(
        None,
        "--max-delete-count",
        min=1,
        help="Maximum folders allowed in one destructive run.",
        rich_help_panel="Safety",
    ),
    no_delete_limit: bool = typer.Option(
        False,
        "--no-delete-limit",
        help="Disable --max-delete-count protection.",
        rich_help_panel="Safety",
    ),
) -> None:
    """Scan and clean workspace artifacts."""
    effective_dry_run = dry_run and not no_dry_run

    if output == OutputFormat.JSON and interactive:
        _exit_with_error(
            "`--interactive` is not supported with `--output json`.", output
        )

    resolved_path = path.resolve()
    if not resolved_path.exists():
        _exit_with_error(f"Path {path} does not exist.", output)
    if resolved_path == Path("/"):
        _exit_with_error("Refusing to sweep filesystem root ('/').", output)
    if resolved_path == Path.home().resolve():
        _exit_with_error("Refusing to sweep your home directory root.", output)

    effective_config = _build_effective_config(
        scan_path=resolved_path,
        config_path=config,
        cli_target_folders=target_folder,
        cli_exclude_patterns=exclude_pattern,
        cli_protected_paths=protected_path,
        cli_max_delete_count=max_delete_count,
        cli_no_delete_limit=no_delete_limit,
        output=output,
    )
    max_delete_count = effective_config.max_delete_count
    no_delete_limit = no_delete_limit or effective_config.no_delete_limit

    destructive_mode = not effective_dry_run
    if destructive_mode and not yes_delete:
        _exit_with_error("Destructive mode requires --yes-delete.", output)

    if output == OutputFormat.JSON and destructive_mode and not force:
        _exit_with_error(
            "Use `--force` with destructive runs when `--output json` is set.",
            output,
        )

    engine = FSweepEngine(resolved_path, effective_config)
    engine.scan(
        show_progress=output == OutputFormat.TABLE,
        use_index=use_index,
        index_path=index_file or (resolved_path / ".fsweep-index.json"),
    )
    selected_items = list(engine.found_items)
    selected_sizes = dict(engine.item_sizes)

    if interactive and selected_items:
        selected_items = _select_items_interactively(
            selected_items,
            selected_sizes,
            engine=engine,
            base_path=resolved_path,
        )
        selected_sizes = {item: selected_sizes[item] for item in selected_items}

    if not selected_items:
        if output == OutputFormat.TABLE:
            rprint("[bold green]Everything is clean. No junk found.[/bold green]")
        _emit_json(
            output,
            {
                "schema_version": SCHEMA_VERSION,
                "path": str(resolved_path),
                "dry_run": effective_dry_run,
                "action": "trash" if trash else "delete",
                "summary": {"deleted": 0, "trashed": 0, "skipped": 0, "failed": 0},
                "items": [],
            },
        )
        return

    if (
        destructive_mode
        and not no_delete_limit
        and len(selected_items) > max_delete_count
    ):
        _exit_with_error(
            (
                "Refusing to delete "
                f"{len(selected_items)} folders because it exceeds "
                f"--max-delete-count={max_delete_count}. "
                "Use --no-delete-limit to override."
            ),
            output,
        )

    if output == OutputFormat.TABLE:
        banner_style = "yellow" if effective_dry_run else "blue"
        banner_text = (
            "[bold yellow]DRY-RUN MODE[/bold yellow]"
            if effective_dry_run
            else "[bold blue]Developer Workspace FSweep[/bold blue]"
        )
        rprint(Panel.fit(banner_text, border_style=banner_style))
        _print_results_table(selected_items, selected_sizes, base_path=resolved_path)
        summary_label = (
            "Total Estimated Savings (Simulation):"
            if effective_dry_run
            else "Total Potential Savings:"
        )
        selected_total = sum(selected_sizes[item] for item in selected_items)
        rprint(
            f"\n[bold]{summary_label}[/bold] "
            f"[green]{engine.format_size(selected_total)}[/green]\n"
        )

    if destructive_mode and not force:
        prompt = (
            "Move these folders to ~/.fsweep_trash?"
            if trash
            else "Do you want to delete these folders?"
        )
        confirm = typer.confirm(prompt, default=False)
        if not confirm:
            if output == OutputFormat.TABLE:
                rprint("[yellow]Aborted. No files were changed.[/yellow]")
            return

    action_text = (
        "[yellow]Simulating..."
        if effective_dry_run
        else ("[magenta]Trashing..." if trash else "[red]Deleting...")
    )
    with Progress(disable=output == OutputFormat.JSON) as progress:
        task = progress.add_task(action_text, total=len(selected_items))
        stats, results = engine.cleanup(
            selected_items,
            dry_run=effective_dry_run,
            trash=trash,
            callback=lambda _: progress.update(task, advance=1),
        )

    if output == OutputFormat.TABLE:
        recovered_size = engine.format_size(sum(selected_sizes.values()))
        if effective_dry_run:
            rprint(
                f"\n[bold yellow]Dry-run complete. "
                f"Would have recovered {recovered_size}.[/bold yellow]"
            )
        elif trash:
            rprint(
                (
                    f"\n[bold green]Moved up to {recovered_size} "
                    "to ~/.fsweep_trash.[/bold green]"
                )
            )
        else:
            rprint(f"\n[bold green]Recovered up to {recovered_size}.[/bold green]")

        summary_table = Table(title="Cleanup Summary", title_style="bold cyan")
        summary_table.add_column("Deleted", justify="right", style="green")
        summary_table.add_column("Trashed", justify="right", style="magenta")
        summary_table.add_column("Skipped", justify="right", style="yellow")
        summary_table.add_column("Failed", justify="right", style="red")
        summary_table.add_row(
            str(stats.deleted),
            str(stats.trashed),
            str(stats.skipped),
            str(stats.failed),
        )
        console.print(summary_table)

    if report:
        _write_markdown_report(
            report_path=report,
            engine=engine,
            path=resolved_path,
            effective_dry_run=effective_dry_run,
            trash=trash,
            selected_items=selected_items,
            selected_sizes=selected_sizes,
            stats=stats,
            results=results,
        )

    _emit_json(
        output,
        _build_json_payload(
            engine=engine,
            scan_path=resolved_path,
            effective_dry_run=effective_dry_run,
            trash=trash,
            selected_items=selected_items,
            selected_sizes=selected_sizes,
            stats=stats,
            results=results,
        ),
    )

    if stats.failed > 0 and not best_effort:
        _exit_with_error(
            (
                "One or more directories failed to delete. "
                "Use --best-effort to ignore failures."
            ),
            output,
            exit_code=2,
        )


@app.command()
def system() -> None:
    """Show hints for cleaning global toolchain artifacts."""
    rprint(Panel("[bold blue]System-wide Cleanup Recommendations[/bold blue]"))

    table = Table(box=None, padding=(0, 2))
    table.add_column("Tool", style="bold cyan")
    table.add_column("Cleanup Command", style="yellow")
    table.add_column("Description", style="dim")

    recommendations = [
        ("Docker", "docker system prune", "Removes unused data (images, caches)"),
        ("uv", "uv cache prune", "Removes outdated wheel/source caches"),
        ("pnpm", "pnpm store prune", "Removes unreferenced packages from store"),
        ("npm", "npm cache clean --force", "Clears the global npm cache"),
        (
            "Cargo",
            "cargo install cargo-sweep && cargo sweep -v",
            "Cleans Rust build artifacts",
        ),
        ("Brew", "brew cleanup", "Removes old versions of installed formulae"),
    ]

    for tool, cmd, desc in recommendations:
        table.add_row(tool, cmd, desc)

    rprint(table)
    rprint(
        "\n[dim]Note: Run these with caution as they affect your whole system.[/dim]"
    )


def _build_effective_config(  # noqa: PLR0913
    *,
    scan_path: Path,
    config_path: Optional[Path],
    cli_target_folders: Sequence[str],
    cli_exclude_patterns: Sequence[str],
    cli_protected_paths: Sequence[Path],
    cli_max_delete_count: Optional[int],
    cli_no_delete_limit: bool,
    output: OutputFormat,
) -> SweepConfig:
    effective_config = SweepConfig()
    config_sources = [global_config_path(), local_config_path(scan_path)]
    if config_path:
        config_sources.append(config_path.resolve())

    for source in config_sources:
        if not source.exists():
            continue
        try:
            loaded = load_config_overrides(source)
        except ValueError as exc:
            _exit_with_error(str(exc), output)
        effective_config = merge_overrides(effective_config, loaded)

    cli_overrides = ConfigOverrides(
        target_folders=set(cli_target_folders),
        exclude_patterns=list(cli_exclude_patterns),
        protected_paths=[path.resolve() for path in cli_protected_paths],
        max_delete_count=cli_max_delete_count,
        no_delete_limit=True if cli_no_delete_limit else None,
    )
    return merge_overrides(effective_config, cli_overrides)


def _print_results_table(
    selected_items: Sequence[Path],
    selected_sizes: Dict[Path, int],
    *,
    base_path: Path,
) -> None:
    table = Table(title=f"Results for {base_path.name}", title_style="bold magenta")
    table.add_column("#", style="white", justify="right")
    table.add_column("Directory Relative Path", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Size", justify="right", style="green")
    for idx, item in enumerate(selected_items, start=1):
        table.add_row(
            str(idx),
            str(item.relative_to(base_path)),
            item.name,
            _format_size(selected_sizes[item]),
        )
    console.print(table)


def _select_items_interactively(
    items: Sequence[Path],
    item_sizes: Dict[Path, int],
    *,
    engine: FSweepEngine,
    base_path: Path,
) -> List[Path]:
    table = Table(title="Interactive Selection", title_style="bold cyan")
    table.add_column("#", justify="right")
    table.add_column("Directory Relative Path")
    table.add_column("Size", justify="right")
    for idx, item in enumerate(items, start=1):
        table.add_row(
            str(idx),
            str(item.relative_to(base_path)),
            engine.format_size(item_sizes[item]),
        )
    console.print(table)

    selection = typer.prompt(
        "Select folders ([all], none, or comma-separated indexes)",
        default="all",
    ).strip()
    if selection.lower() in {"none", "n"}:
        return []
    if selection.lower() in {"all", "a"}:
        return list(items)

    selected_indexes: List[int] = []
    for raw_token in selection.split(","):
        cleaned_token = raw_token.strip()
        if not cleaned_token:
            continue
        if not cleaned_token.isdigit():
            raise typer.BadParameter(
                (
                    "Interactive selection must be 'all', 'none', "
                    "or comma-separated integers."
                )
            )
        selected_indexes.append(int(cleaned_token))

    selected_items: List[Path] = []
    for index in selected_indexes:
        if index < 1 or index > len(items):
            raise typer.BadParameter(f"Interactive index out of range: {index}")
        candidate = items[index - 1]
        if candidate not in selected_items:
            selected_items.append(candidate)
    return selected_items


def _build_json_payload(  # noqa: PLR0913
    *,
    engine: FSweepEngine,
    scan_path: Path,
    effective_dry_run: bool,
    trash: bool,
    selected_items: Sequence[Path],
    selected_sizes: Dict[Path, int],
    stats: CleanupStats,
    results: Sequence[ItemResult],
) -> Dict[str, object]:
    result_map = {result.path: result for result in results}
    action = "trash" if trash else "delete"
    items_payload: List[Dict[str, object]] = []
    for item in selected_items:
        result = result_map[item]
        items_payload.append(
            {
                "path": str(item),
                "relative_path": str(item.relative_to(scan_path)),
                "type": item.name,
                "size_bytes": selected_sizes[item],
                "size_human": engine.format_size(selected_sizes[item]),
                "action": "simulate" if effective_dry_run else action,
                "status": result.status,
                "error": result.error,
                "trash_destination": (
                    str(result.trash_destination) if result.trash_destination else None
                ),
            }
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "path": str(scan_path),
        "dry_run": effective_dry_run,
        "action": action,
        "summary": {
            "matched_count": len(selected_items),
            "total_bytes": sum(selected_sizes.values()),
            "total_human": engine.format_size(sum(selected_sizes.values())),
            "deleted": stats.deleted,
            "trashed": stats.trashed,
            "skipped": stats.skipped,
            "failed": stats.failed,
        },
        "items": items_payload,
    }


def _write_markdown_report(  # noqa: PLR0913
    *,
    report_path: Path,
    engine: FSweepEngine,
    path: Path,
    effective_dry_run: bool,
    trash: bool,
    selected_items: Sequence[Path],
    selected_sizes: Dict[Path, int],
    stats: CleanupStats,
    results: Sequence[ItemResult],
) -> None:
    action = "trash" if trash else "delete"
    lines: List[str] = []
    lines.append("# fsweep report")
    lines.append("")
    lines.append(f"- generated_at_utc: {datetime.now(tz=timezone.utc).isoformat()}")
    lines.append(f"- path: `{path}`")
    lines.append(f"- dry_run: `{effective_dry_run}`")
    lines.append(f"- action: `{action}`")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- matched_count: {len(selected_items)}")
    lines.append(f"- total_human: {engine.format_size(sum(selected_sizes.values()))}")
    lines.append(f"- deleted: {stats.deleted}")
    lines.append(f"- trashed: {stats.trashed}")
    lines.append(f"- skipped: {stats.skipped}")
    lines.append(f"- failed: {stats.failed}")
    lines.append("")
    lines.append("## Items")
    lines.append("")
    lines.append("| path | size | status | error |")
    lines.append("| :--- | ---: | :----- | :---- |")
    result_map = {result.path: result for result in results}
    for item in selected_items:
        result = result_map[item]
        error = result.error or ""
        lines.append(
            (
                f"| `{item}` | {engine.format_size(selected_sizes[item])} | "
                f"{result.status} | {error} |"
            )
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n")


def _load_scan_index(index_path: Optional[Path]) -> Dict[str, Dict[str, int]]:
    if index_path is None or not index_path.exists():
        return {}
    try:
        raw = json.loads(index_path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    if raw.get("schema_version") != INDEX_SCHEMA_VERSION:
        return {}
    entries = raw.get("entries", {})
    if not isinstance(entries, dict):
        return {}

    parsed: Dict[str, Dict[str, int]] = {}
    for path_key, entry in entries.items():
        if not isinstance(path_key, str) or not isinstance(entry, dict):
            continue
        mtime_ns = entry.get("mtime_ns")
        size_bytes = entry.get("size_bytes")
        if isinstance(mtime_ns, int) and isinstance(size_bytes, int):
            parsed[path_key] = {"mtime_ns": mtime_ns, "size_bytes": size_bytes}
    return parsed


def _write_scan_index(
    *,
    index_path: Optional[Path],
    entries: Dict[str, Dict[str, int]],
) -> None:
    if index_path is None:
        return
    payload = {"schema_version": INDEX_SCHEMA_VERSION, "entries": entries}
    try:
        index_path.parent.mkdir(parents=True, exist_ok=True)
        index_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    except OSError:
        return


def _directory_mtime_ns(path: Path) -> int:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return 0


def _emit_json(output: OutputFormat, payload: Dict[str, object]) -> None:
    if output == OutputFormat.JSON:
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))


def _format_size(size_bytes: int) -> str:
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < BYTE_UNIT_BASE:
            return f"{size:.2f} {unit}"
        size /= BYTE_UNIT_BASE
    return f"{size:.2f} TB"


def _exit_with_error(
    message: str,
    output: OutputFormat,
    exit_code: int = 1,
) -> None:
    if output == OutputFormat.JSON:
        typer.echo(
            json.dumps(
                {
                    "schema_version": SCHEMA_VERSION,
                    "error": message,
                    "exit_code": exit_code,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        rprint(f"[bold red]Error:[/bold red] {message}")
    raise typer.Exit(exit_code)


if __name__ == "__main__":
    app()
