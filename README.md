# 🧹 fsweep

`fsweep` is your friendly neighborhood workspace cleanup tool! It's designed to
help developers mop up bulky development artifacts and sweep away
disk-space-hogging junk with ease.

Whether it's a mountain of `node_modules`, a forgotten `venv`, or stale build
caches, `fsweep` identifies the mess and helps you reclaim your disk space in
seconds.

## 📦 Installation

`fsweep` is best managed with `uv`. If you don't have it yet, get it from
[astral.sh/uv](https://astral.sh/uv).

```bash
uv tool install fsweep
```

## ⚡ Quickstart (30 seconds)

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

### Options

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

## ⚙️ Config File (`fsweep.toml`)

`fsweep` loads config in this order (later wins):

1. `~/.config/fsweep/fsweep.toml`
2. `<scan_path>/fsweep.toml`
3. `--config /path/to/fsweep.toml`
4. CLI flags

Example:

```toml
[fsweep]
target_folders = ["node_modules", "venv", "vendor_cache"]
exclude_patterns = ["**/.git/**", "**/keep/**"]
protected_paths = ["important", "../do-not-touch"]
max_delete_count = 75
no_delete_limit = false
```

`protected_paths` are resolved relative to the config file that defines them.
If you want to include generic names such as `build`, `dist`, `out`, `bin`, or
`obj`, add them explicitly with `target_folders`.

## 📤 JSON Output Contract

Use `--output json` for scripts/automation.

- `schema_version`: currently `"1"`
- `summary`: totals, counts, and effective action
- `items[]`: per-folder path, size, action, status, and optional error
- error responses also use JSON with `error` and `exit_code`

## ⚖️ Dry-run Parity Guarantee

`fsweep` now includes a dry-run parity test that guarantees the matched set in
dry-run and destructive mode is identical for equivalent flags and path.

## 📈 Benchmark + Indexing

- `--use-index` caches directory size calculations in
  `<scan_path>/.fsweep-index.json` to speed repeated scans.
- Use `--no-index` to benchmark raw scan performance.
- Opt-in benchmark suite:

<!-- rumdl-disable MD013 -->

```bash
FSWEEP_BENCHMARK=1 ./.venv/bin/python -m pytest tests/test_fsweep/test_benchmark.py -q
```

<!-- rumdl-disable MD013 -->

### 🧹 What does it sweep?

`fsweep` knows exactly which corners to sweep. It currently targets:

- **JavaScript/TypeScript:** `.astro`, `.eslintcache`, `.next`, `.nuxt`,
  `.parcel-cache`, `.pnpm-store`, `.svelte-kit`, `.turbo`, `.vercel`, `.vite`,
  `.wrangler`, `node_modules`
- **Python:** `.ipynb_checkpoints`, `.mypy_cache`, `.nox`, `.pytest_cache`,
  `.ruff_cache`, `.rumdl_cache`, `.tox`, `.uv-cache`, `.venv`, `__pycache__`,
  `venv`
- **Build/Test Artifacts:** `.cache`, `.nyc_output`, `coverage`, `htmlcov`
- **JVM/.NET/Rust:** `.gradle`
- **Infrastructure-as-Code:** `.aws-sam`, `.serverless`, `.terraform`,
  `.terragrunt-cache`

## 🚀 Key Features

- **🔍 Intelligent Scanning:** Recursively hunts down common "junk" folders
  across your projects.
- **💰 Size Estimation:** Calculates exactly how much space you'll recover
  before you commit.
- **📊 Rich Terminal UI:** Presents findings in beautiful, easy-to-read tables
  thanks to [Rich](https://github.com/Textualize/rich).
- **🛡️ Safety First:** Includes a robust `--dry-run` mode and confirmation
  prompts to ensure your precious source code stays safe.
- **💨 Reach + Speed:** Supports Python 3.10+ and keeps scan/deletion fast.
- **🚫 .fsweepignore:** Skip an entire directory tree by placing an empty
  `.fsweepignore` file in its root.
- **🔧 System Command:** Run `fsweep system` to get tips for cleaning global
  tool caches (like Docker or uv).

## 🧪 Development

Ready to help improve the `fsweep`? Here's how to keep the codebase as clean as
your workspace.

```bash
git clone https://github.com/drew-simmons/fsweep.git
cd fsweep

uv sync
```

## 🛠️ Tech Stack

- **Python 3.10+**
- **[Typer](https://typer.tiangolo.com/):** For a clean and intuitive CLI
  experience.
- **[Rich](https://rich.readthedocs.io/):** For beautiful terminal output, tables,
  and progress indicators.
- **[uv](https://github.com/astral-sh/uv):** For lightning-fast dependency
  management.

### Running Tests

```bash
uv run pytest
```

### Exit Codes

- `0`: successful run (or dry-run simulation complete)
- `1`: safety check failure or invalid invocation
- `2`: one or more deletions failed (unless `--best-effort` is set)

### Linting & Formatting

We use [Ruff](https://github.com/astral-sh/ruff) to keep things tidy:

```bash
uv run ruff check .
uv run ruff format .
uv run rumdl fmt .
```

### Type Checking

Keep the types in check with `ty`:

```bash
uv run ty check .
```

> [!TIP]
> `uv run prek -a` runs all the above linting and formatting.

## 🔐 Safety Model

- Default mode is non-destructive (`--dry-run`).
- Destructive mode requires `--delete --yes-delete`.
- Optional `--trash` mode is destructive but recoverable.
- `fsweep` refuses to sweep `/` and your home directory root.
- Destructive runs are capped by `--max-delete-count` unless overridden.

## 📋 Release Checklist

Before tagging a release (`v*`), verify:

```bash
uv run pytest
uv run ruff check .
uv run ty check .
uv build
uv run --isolated --no-project --with dist/*.whl fsweep --help
uv run --isolated --no-project --with dist/*.whl python -m fsweep --help
uv run --isolated --no-project --with dist/*.tar.gz fsweep --help
uv run --isolated --no-project --with dist/*.tar.gz python -m fsweep --help
```
