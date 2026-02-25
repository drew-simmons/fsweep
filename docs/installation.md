# Installation

`fsweep` is best managed with `uv`. If you don't have it yet, get it from
[astral.sh/uv](https://astral.sh/uv).

## Install with uv

To install `fsweep` globally as a tool, use the `uv tool install` command:

```bash
uv tool install fsweep
```

## Run with uv

Alternatively, you can run `fsweep` on-demand without installing it:

```bash
uv run fsweep
```

## Development Setup

If you want to contribute to `fsweep`, follow these steps to set up your
development environment:

1. **Clone the Repository**:

    ```bash
    git clone https://github.com/drew-simmons/fsweep.git
    cd fsweep
    ```

2. **Sync Dependencies**:

    ```bash
    uv sync
    ```

3. **Run Tests**:

    ```bash
    uv run pytest
    ```
