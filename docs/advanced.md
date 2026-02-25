# Advanced Features

`fsweep` is designed for power users and automation.

## 📤 JSON Output Contract

Use `--output json` for scripts and automation.

```bash
uv run fsweep --output json
```

The JSON output includes:

- `schema_version`: currently `"1"`
- `summary`: totals, counts, and effective action
- `items[]`: per-folder path, size, action, status, and optional error

Errors also use a standard JSON structure with `error` and `exit_code`.

## 📈 Markdown Reports

Generate a markdown report for your scan and cleanup results:

```bash
uv run fsweep --report report.md
```

This is useful for documenting your disk cleanup activity or sharing results
with a team.

## 🔧 System Command

The `fsweep system` command gives tips for cleaning global tool caches (like
Docker or uv). These caches are often large and can be cleaned safely with the
recommended commands.

```bash
uv run fsweep system
```

## Exit Codes

`fsweep` uses standard exit codes to indicate the outcome of an operation:

- `0`: Successful run (including dry-run).
- `1`: Safety check failure or invalid command.
- `2`: One or more deletions failed (unless `--best-effort` is used).
