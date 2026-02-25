# Configuration

`fsweep` loads configuration in this order (later wins):

1. `~/.config/fsweep/fsweep.toml` (Global config)
2. `<scan_path>/fsweep.toml` (Local config)
3. `--config /path/to/fsweep.toml` (Custom CLI config)
4. CLI flags (Direct overrides)

## Example `fsweep.toml`

```toml
[fsweep]
target_folders = ["node_modules", "venv", "vendor_cache"]
exclude_patterns = ["**/.git/**", "**/keep/**"]
protected_paths = ["important", "../do-not-touch"]
max_delete_count = 75
no_delete_limit = false
```

### Options Explained

- **`target_folders`**: Explicitly specify additional folder names to clean.
- **`exclude_patterns`**: Glob patterns to skip during scan.
- **`protected_paths`**: Paths that should never be scanned or deleted.
  Resolved relative to the config file defining them.
- **`max_delete_count`**: Maximum folder count allowed in a single
  destructive run (defaults to 50).
- **`no_delete_limit`**: Boolean to disable the safety limit on folder
  deletions.

## Protected Paths

`protected_paths` are absolute paths or paths relative to the directory where
the configuration file is located. If `fsweep` encounters a path that matches a
protected path or is within a protected path tree, it will skip it.
