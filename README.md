# 🧹 fsweep

`fsweep` is your friendly neighborhood workspace cleanup tool! It's designed to
help developers mop up bulky development artifacts and sweep away
disk-space-hogging junk with ease.

Whether it's a mountain of `node_modules`, a forgotten `venv`, or stale build
caches, `fsweep` identifies the mess and helps you reclaim your disk space in
seconds.

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

## 🛠️ Tech Stack

- **Python 3.13+**
- **[Typer](https://typer.tiangolo.com/):** For a clean and intuitive CLI
  experience.
- **[Rich](https://rich.readthedocs.io/):** For beautiful terminal output, tables,
  and progress indicators.
- **[uv](https://github.com/astral-sh/uv):** For lightning-fast dependency
  management.

## 📦 Installation

`fsweep` is best managed with `uv`. If you don't have it yet, get it from
[astral.sh/uv](https://astral.sh/uv).

```bash
# Clone the repository
git clone https://github.com/yourusername/fsweep.git
cd fsweep

# Synchronize dependencies and set up the environment
uv sync
```

## 📖 Usage

Keep your workspace spotless with a single command:

```bash
uv run fsweep clean --path /path/to/projects
```

### Options

| Option | Shorthand | Description | Default |
| :--- | :--- | :--- | :--- |
| `--path` | | The directory to scan for cleanup. | `~/developer/archive` |
| `--force` | `-f` | Mop up everything without asking for confirmation. | `False` |
| `--dry-run` | `-d` | Just a scout mission—simulates cleanup without deleting. | `False` |

### 🧹 What does it sweep?

`fsweep` knows exactly which corners to sweep. It currently targets:

- **Python:** `venv`, `.venv`, `__pycache__`, `.pytest_cache`, `.tox`,
  `.mypy_cache`, `.ruff_cache`
- **Node.js:** `node_modules`, `.next`, `.docusaurus`
- **Rust:** `target`
- **Java/Kotlin/C#:** `bin`, `obj`, `build`, `dist`, `.gradle`

## 🧪 Development

Ready to help improve the `fsweep`? Here's how to keep the codebase as clean as
your workspace.

### Running Tests

```bash
uv run pytest
```

### Linting & Formatting

We use [Ruff](https://github.com/astral-sh/ruff) to keep things tidy:

```bash
uv run ruff check .
uv run ruff format .
```

### Type Checking

Keep the types in check with `ty`:

```bash
uv run ty
```
