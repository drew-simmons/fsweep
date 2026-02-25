# Features

`fsweep` is designed to be intelligent, fast, and safe.

## 🧹 What does it sweep?

`fsweep` knows exactly which corners to sweep. It targets common development
artifacts:

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

## 📊 Size Estimation

One of the most powerful features of `fsweep` is its ability to calculate
exactly how much space you'll recover before you commit to any action.

- **Fast Recursive Scan:** Uses a high-performance scan to calculate directory
  sizes.
- **Rich Output:** Displays results in a clear, formatted table.

## 📈 Benchmark + Indexing

- **Indexing**: `--use-index` caches directory size calculations in
  `<scan_path>/.fsweep-index.json` to speed up repeated scans.
- **Benchmarking**: Use `--no-index` to benchmark raw scan performance.

### Run Benchmarks

To run the opt-in benchmark suite (requires `pytest`):

```bash
FSWEEP_BENCHMARK=1 ./.venv/bin/python -m pytest tests/test_fsweep/test_benchmark.py -q
```

## 🚫 .fsweepignore

Skip an entire directory tree by placing an empty `.fsweepignore` file in its
root. This is useful for large sub-directories that you never want `fsweep` to
scan or touch.
