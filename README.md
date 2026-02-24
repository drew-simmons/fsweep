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

## 📖 Usage

Keep your workspace spotless with a single command:

```bash
uv run fsweep --path /path/to/projects
```

Safe destructive run flow:

```bash
# Step 1: default dry-run (non-destructive)
uv run fsweep --path /path/to/projects

# Step 2: destructive run with explicit confirmation flags
uv run fsweep --path /path/to/projects --delete --yes-delete
```

### Options

| Option | Shorthand | Description | Default |
| :----- | :-------- | :---------- | :------ |
| `--path` | | The directory to scan for cleanup. | `~/developer/archive` |
| `--force` | `-f` | Mop up everything without asking for confirmation. | `False` |
| `--dry-run` / `--delete` | `-d` | Simulate cleanup (default) or enable destructive mode. | `True` |
| `--yes-delete` | | Required for destructive runs. | `False` |
| `--best-effort` | | Continue and exit successfully even if deletes fail. | `False` |
| `--max-delete-count` | | Max folders allowed in one destructive run. | `50` |
| `--no-delete-limit` | | Override `--max-delete-count`. | `False` |

### 🧹 What does it sweep?

`fsweep` knows exactly which corners to sweep. It currently targets:

- **JavaScript/TypeScript:** `node_modules`, `.next`, `.nuxt`, `.svelte-kit`,
  `.astro`, `.turbo`, `.parcel-cache`, `.vite`
- **Python:** `venv`, `.venv`, `__pycache__`, `.pytest_cache`, `.tox`, `.nox`,
  `.mypy_cache`, `.ruff_cache`, `.ipynb_checkpoints`
- **Build/Test Artifacts:** `build`, `dist`, `out`, `coverage`, `htmlcov`,
  `.nyc_output`, `.cache`
- **JVM/.NET/Rust:** `.gradle`, `target`, `bin`, `obj`
- **Infrastructure-as-Code:** `.terraform`, `.terragrunt-cache`

## 🚀 Key Features

- **🔍 Intelligent Scanning:** Recursively hunts down common "junk" folders
  across your projects.
- **💰 Size Estimation:** Calculates exactly how much space you'll recover
  before you commit.
- **📊 Rich Terminal UI:** Presents findings in beautiful, easy-to-read tables
  thanks to [Rich](https://github.com/Textualize/rich).
- **🛡️ Safety First:** Includes a robust `--dry-run` mode and confirmation
  prompts to ensure your precious source code stays safe.
- **💨 Built for Speed:** Leverages Python 3.13 and modern async-style progress
  feedback.

## 🧪 Development

Ready to help improve the `fsweep`? Here's how to keep the codebase as clean as
your workspace.

```bash
git clone https://github.com/drew-simmons/fsweep.git
cd fsweep

uv sync
```

## 🛠️ Tech Stack

- **Python 3.13+**
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
