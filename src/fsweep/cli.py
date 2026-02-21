import shutil
import typer
from pathlib import Path
from typing import List, Optional, Callable
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import print as rprint
from fsweep.config import TARGET_FOLDERS

# --- Configuration ---
app = typer.Typer(help="🚀 Advanced Workspace Cleanup Tool for Developers")
console = Console()


class FSweepEngine:
    """The core engine for scanning and cleaning developer workspace artifacts."""

    def __init__(self, target_path: Path):
        """Initializes the engine with the path to scan.

        Args:
            target_path: The directory path where the scan will begin.
        """
        self.target_path = target_path
        self.found_items: List[Path] = []
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
                    # This ensures we only count the size of the link itself, not the target.
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
            for path in self.target_path.rglob("*"):
                if path.is_dir() and path.name in TARGET_FOLDERS:
                    size = self.get_size(path)
                    self.found_items.append(path)
                    self.total_bytes += size

    def format_size(self, size_bytes: int) -> str:
        """Formats a size in bytes into a human-readable string (e.g., MB, GB).

        Args:
            size_bytes: The number of bytes to format.

        Returns:
            A string representing the size with an appropriate unit.
        """
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def cleanup(
        self, dry_run: bool = False, callback: Optional[Callable[[Path], None]] = None
    ) -> None:
        """Deletes the found junk items.

        Args:
            dry_run: If True, only simulates deletion.
            callback: An optional function called with each deleted Path for progress reporting.
        """
        for item in self.found_items:
            if not dry_run:
                shutil.rmtree(item)
            if callback:
                callback(item)


@app.command()
def clean(
    path: Path = typer.Option(
        Path.home() / "developer/archive", help="The directory to scan for cleanup"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Delete files without confirmation"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Simulate cleanup without deleting files"
    ),
):
    """
    Scan and clean developer bloat (node_modules, venv, etc.)
    """
    banner_style = "yellow" if dry_run else "blue"
    banner_text = (
        "[bold yellow]DRY-RUN MODE[/bold yellow] 🔍"
        if dry_run
        else "[bold blue]Developer Workspace FSweep[/bold blue] 🧹"
    )

    rprint(Panel.fit(banner_text, border_style=banner_style))

    if not path.exists():
        rprint(f"[bold red]Error:[/bold red] Path {path} does not exist.")
        raise typer.Exit(1)

    engine = FSweepEngine(path)
    engine.scan()

    if not engine.found_items:
        rprint("[bold green]✨ Everything is clean! No junk found.[/bold green]")
        return

    # Display Results Table
    table = Table(title=f"Results for {path.name}", title_style="bold magenta")
    table.add_column("Directory Relative Path", style="cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Size", justify="right", style="green")

    for item in engine.found_items:
        table.add_row(
            str(item.relative_to(path.parent)),
            item.name,
            engine.format_size(engine.get_size(item)),
        )

    console.print(table)

    summary_label = (
        "Total Potential Savings:"
        if not dry_run
        else "Total Estimated Savings (Simulation):"
    )
    rprint(
        f"\n[bold]{summary_label}[/bold] [green]{engine.format_size(engine.total_bytes)}[/green]\n"
    )

    # Confirmation Logic (Skipped in dry-run)
    if not dry_run and not force:
        confirm = typer.confirm("Do you want to delete these folders?", default=False)
        if not confirm:
            rprint("[yellow]Aborted. No files were harmed.[/yellow]")
            return

    # Execution Phase
    action_text = "[yellow]Simulating..." if dry_run else "[red]Deleting..."
    with Progress() as progress:
        task = progress.add_task(action_text, total=len(engine.found_items))
        engine.cleanup(
            dry_run=dry_run, callback=lambda _: progress.update(task, advance=1)
        )

    success_msg = f"\n[bold green]✅ Successfully recovered {engine.format_size(engine.total_bytes)}![/bold green]"
    dry_run_msg = f"\n[bold yellow]✨ Dry-run complete. Would have recovered {engine.format_size(engine.total_bytes)}.[/bold yellow]"
    rprint(dry_run_msg if dry_run else success_msg)


if __name__ == "__main__":
    app()
