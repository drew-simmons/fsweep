from pathlib import Path


def test_ci_workflow_exists():
    ci_file = Path(".github/workflows/ci.yml")
    assert ci_file.is_file(), f"CI workflow file {ci_file} not found."


def test_ci_workflow_has_required_steps():
    ci_file = Path(".github/workflows/ci.yml")
    content = ci_file.read_text()
    assert "ruff check" in content
    assert "ty check" in content
    assert "uv lock --check" in content
    assert "astral-sh/setup-uv" in content
