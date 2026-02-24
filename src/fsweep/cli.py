"""Command-line interface and cleanup engine for fsweep."""

import os
import shutil
from pathlib import Path
from typing import Callable, Dict, List, Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from fsweep.config import TARGET_FOLDERS

# --- Configuration ---
app = typer.Typer(help="🚀 Advanced Workspace Cleanup Tool for Developers")
console = Console()
BYTE_UNIT_BASE = 1024
DEFAULT_MAX_DELETE_COUNT = 50


class CleanupStats:
    """Represents the outcome of a cleanup operation."""

    def __init__(self) -> None:
        """Initialize counters for cleanup results."""
        self.deleted = 0
        self.skipped = 0
        self.failed = 0


class FSweepEngine:
    """The core engine for scanning and cleaning developer workspace artifacts."""

    def __init__(self, target_path: Path) -> None:
        """Initializes the engine with the path to scan.

        Args:
            target_path: The directory path where the scan will begin.
        """
        self.target_path = target_path
        self.found_items: List[Path] = []
        self.item_sizes: Dict[Path, int] = {}
        self.total_bytes: int = 0

    def get_size(self, path: Path) -> int:
        """Calculates the total size of a folder recursively, ignoring symlinks.

        Args:
            path: The path of the folder to measure.

        Returns:
            The total size in bytes.
        """
        total = 0
        try:
            # rglob('*') iterates over all files and directories recursively.
            # By default, it does NOT follow symlinks to directories.
            for f in path.rglob("*"):
                try:
                    # We use lstat() for symlinks to avoid following them to the target.
                    # This ensures we only count the size of the link itself,
                    # not the target.
                    if f.is_symlink():
                        total += f.lstat().st_size
                    elif f.is_file():
                        total += f.stat().st_size
                except (PermissionError, OSError):
                    # Skip files we can't access
                    continue
        except (PermissionError, OSError):
            # Skip directories we can't access
            pass
        return total

    def scan(self) -> None:
        """Recursively scans the target path for folders matching TARGET_FOLDERS."""
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Scanning for junk...", total=None)
            for current_root, dirs, _ in os.walk(
                self.target_path, topdown=True, followlinks=False
            ):
                matched_dirs = [name for name in dirs if name in TARGET_FOLDERS]
                for name in matched_dirs:
                    path = Path(current_root) / name
                    size = self.get_size(path)
                    self.found_items.append(path)
                    self.item_sizes[path] = size
                    self.total_bytes += size
                dirs[:] = [name for name in dirs if name not in TARGET_FOLDERS]

    def format_size(self, size_bytes: int) -> str:
        """Formats a size in bytes into a human-readable string (e.g., MB, GB).

        Args:
            size_bytes: The number of bytes to format.

        Returns:
            A string representing the size with an appropriate unit.
        """
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < BYTE_UNIT_BASE:
                return f"{size:.2f} {unit}"
            size /= BYTE_UNIT_BASE
        return f"{size:.2f} TB"

    def cleanup(
        self,
        dry_run: bool = False,
        callback: Optional[Callable[[Path], None]] = None,
    ) -> CleanupStats:
        """Deletes the found junk items.

        Args:
            dry_run: If True, only simulates deletion.
            callback: An optional function called with each deleted Path for
                progress reporting.

        Returns:
            A summary of deleted, skipped, and failed items.
        """
        stats = CleanupStats()
        for item in self.found_items:
            if dry_run:
                stats.skipped += 1
                if callback:
                    callback(item)
                continue
            try:
                shutil.rmtree(item)
                stats.deleted += 1
            except FileNotFoundError:
                stats.skipped += 1
            except (PermissionError, OSError):
                stats.failed += 1
            if callback:
                callback(item)
        return stats


@app.command()
def clean(  # noqa: PLR0913, PLR0915
    path: Path = typer.Option(
        Path.home() / "developer/archive",
        metavar="DIRECTORY",
        show_default="~/developer/archive",
        help="Workspace directory to scan.",
        rich_help_panel="Scan",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Skip interactive delete confirmation.",
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
    max_delete_count: int = typer.Option(
        DEFAULT_MAX_DELETE_COUNT,
        "--max-delete-count",
        min=1,
        help="Maximum number of directories allowed in one destructive run.",
        rich_help_panel="Safety",
    ),
    no_delete_limit: bool = typer.Option(
        False,
        "--no-delete-limit",
        help="Disable --max-delete-count protection.",
        rich_help_panel="Safety",
    ),
) -> None:
    """Scan and clean developer bloat (node_modules, venv, etc.)."""
    effective_dry_run = dry_run and not no_dry_run

    banner_style = "yellow" if effective_dry_run else "blue"
    banner_text = (
        "[bold yellow]DRY-RUN MODE[/bold yellow] 🔍"
        if effective_dry_run
        else "[bold blue]Developer Workspace FSweep[/bold blue] 🧹"
    )

    rprint(Panel.fit(banner_text, border_style=banner_style))

    if not path.exists():
        rprint(f"[bold red]Error:[/bold red] Path {path} does not exist.")
        raise typer.Exit(1)

    resolved_path = path.resolve()
    if resolved_path == Path("/"):
        rprint("[bold red]Error:[/bold red] Refusing to sweep filesystem root ('/').")
        raise typer.Exit(1)
    if resolved_path == Path.home().resolve():
        rprint(
            "[bold red]Error:[/bold red] Refusing to sweep your home directory root."
        )
        raise typer.Exit(1)

    if not effective_dry_run and not yes_delete:
        rprint(
            "[bold red]Error:[/bold red] Destructive mode requires "
            "[bold]--yes-delete[/bold]."
        )
        raise typer.Exit(1)

    engine = FSweepEngine(path)
    engine.scan()

    if not engine.found_items:
        rprint("[bold green]✨ Everything is clean! No junk found.[/bold green]")
        return

    if (
        not effective_dry_run
        and not no_delete_limit
        and len(engine.found_items) > max_delete_count
    ):
        rprint(
            "[bold red]Error:[/bold red] Refusing to delete "
            f"{len(engine.found_items)} folders because it exceeds "
            f"--max-delete-count={max_delete_count}. "
            "Use --no-delete-limit to override."
        )
        raise typer.Exit(1)

    # Display Results Table
    table = Table(title=f"Results for {path.name}", title_style="bold magenta")
    table.add_column("Directory Relative Path", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Size", justify="right", style="green")

    for item in engine.found_items:
        table.add_row(
            str(item.relative_to(path.parent)),
            item.name,
            engine.format_size(engine.item_sizes[item]),
        )

    console.print(table)

    summary_label = (
        "Total Potential Savings:"
        if not dry_run
        else "Total Estimated Savings (Simulation):"
    )
    rprint(
        (
            f"\n[bold]{summary_label}[/bold] "
            f"[green]{engine.format_size(engine.total_bytes)}[/green]\n"
        )
    )

    # Confirmation Logic (Skipped in dry-run)
    if not effective_dry_run and not force:
        confirm = typer.confirm("Do you want to delete these folders?", default=False)
        if not confirm:
            rprint("[yellow]Aborted. No files were harmed.[/yellow]")
            return

    # Execution Phase
    action_text = "[yellow]Simulating..." if effective_dry_run else "[red]Deleting..."
    with Progress() as progress:
        task = progress.add_task(action_text, total=len(engine.found_items))
        stats = engine.cleanup(
            dry_run=effective_dry_run,
            callback=lambda _: progress.update(task, advance=1),
        )

    recovered_size = engine.format_size(engine.total_bytes)
    if effective_dry_run:
        rprint(
            f"\n[bold yellow]✨ Dry-run complete. "
            f"Would have recovered {recovered_size}.[/bold yellow]"
        )
    else:
        rprint(f"\n[bold green]✅ Recovered up to {recovered_size}.[/bold green]")

    summary_table = Table(title="Cleanup Summary", title_style="bold cyan")
    summary_table.add_column("Deleted", justify="right", style="green")
    summary_table.add_column("Skipped", justify="right", style="yellow")
    summary_table.add_column("Failed", justify="right", style="red")
    summary_table.add_row(str(stats.deleted), str(stats.skipped), str(stats.failed))
    console.print(summary_table)

    if stats.failed > 0 and not best_effort:
        rprint(
            "[bold red]Error:[/bold red] One or more directories failed to delete. "
            "Use --best-effort to ignore failures."
        )
        raise typer.Exit(2)


if __name__ == "__main__":
    app()
