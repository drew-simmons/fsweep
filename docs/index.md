# Welcome to fsweep

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
- **💨 Reach + Speed:** Supports Python 3.10+ and keeps scan/deletion fast.
- **🚫 .fsweepignore:** Skip an entire directory tree by placing an empty
  `.fsweepignore` file in its root.
- **🔧 System Command:** Run `fsweep system` to get tips for cleaning global
  tool caches (like Docker or uv).

## 🛠️ Tech Stack

- **Python 3.10+**
- **[Typer](https://typer.tiangolo.com/):** For a clean and intuitive CLI
  experience.
- **[Rich](https://rich.readthedocs.io/):** For beautiful terminal output, tables,
  and progress indicators.
- **[uv](https://github.com/astral-sh/uv):** For lightning-fast dependency
  management.
