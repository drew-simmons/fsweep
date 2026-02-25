# Contributing

Thanks for contributing to `fsweep`.

## Development setup

```bash
uv sync
```

## Run checks locally

```bash
uv run pytest
uv run ruff check .
uv run ty check .
```

Optional full pre-commit run:

```bash
uv run prek -a
```

## Pull request expectations

- Keep changes focused and scoped.
- Include tests for behavior changes when possible.
- Update `README.md` and `CHANGELOG.md` if user-visible behavior changes.
- Use clear PR descriptions and include verification steps.

## Release notes

- Add notable user-facing changes to the `Unreleased` section in `CHANGELOG.md`.
