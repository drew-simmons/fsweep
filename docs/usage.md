# Usage

`fsweep` provides a simple but powerful interface for scanning and cleaning
your development environment.

## Quickstart (30 seconds)

Safe first run (dry-run, current directory):

```bash
uv run fsweep
```

Machine-readable dry-run:

```bash
uv run fsweep --output json
```

Destructive run with hard-delete:

```bash
uv run fsweep --delete --yes-delete
```

Destructive run with recoverable trash mode:

```bash
uv run fsweep --delete --trash --yes-delete
```

The default scan path is your current working directory (`.`).

## Commands

### `fsweep` (or `fsweep clean`)

The main command for scanning and cleaning artifacts.

| Option | Shorthand | Description | Default |
| :----- | :-------- | :---------- | :------ |
| `--path` | | The directory to scan for cleanup. | `.` |
| `--force` | `-f` | Skip final destructive confirmation prompt. | `False` |
| `--dry-run` / `--delete` | `-d` | Simulate cleanup (default) or enable destructive mode. | `True` |
| `--trash` | | Move matched folders to `~/.fsweep_trash` instead of hard delete. | `False` |
| `--interactive` | | Select matched folders before execution. | `False` |
| `--use-index` / `--no-index` | | Enable/disable scan size cache index. | `True` |
| `--index-file` | | Path to scan index JSON file. | `<scan_path>/.fsweep-index.json` |
| `--output` | | Output format: `table` or `json`. | `table` |
| `--report` | | Write a markdown run report to a file. | unset |
| `--config` | | Load a TOML config file. | unset |
| `--target-folder` | | Add custom target folder names (repeatable). | `[]` |
| `--exclude-pattern` | | Exclude glob patterns from scan (repeatable). | `[]` |
| `--protected-path` | | Protect paths from scan/deletion (repeatable). | `[]` |
| `--yes-delete` | | Required for destructive runs. | `False` |
| `--best-effort` | | Continue and exit successfully even if deletes fail. | `False` |
| `--max-delete-count` | | Max folders allowed in one destructive run. | `50` |
| `--no-delete-limit` | | Override `--max-delete-count`. | `False` |

### `fsweep system`

Shows helpful hints for cleaning global toolchain artifacts (like Docker, uv,
and more).

## Interactive Mode

Use the `--interactive` flag to pick which folders to delete from the scan
results:

```bash
uv run fsweep --interactive
```

`fsweep` will present a numbered list of found items, and you can enter "all",
"none", or a comma-separated list of indexes (e.g., "1, 3, 5") to select them
for cleanup.
