# Repository Guidelines

## Project Structure & Module Organization

Application code lives in `src/good_samaritan/`. Keep responsibilities separated by workflow concern: `cli.py` exposes Typer commands, `agent.py` coordinates an attempt, `github.py` and `router.py` handle external services, and `database.py`, `memory.py`, and `journal.py` persist local state. Safety-sensitive filesystem and command restrictions belong in `tools.py` and `workspace.py`.

Tests are in `tests/`, generally one `test_<area>.py` file per module or feature. `website/` contains the intentionally dependency-free GitHub Pages output. Use `config.example.toml` as the public configuration template; never add credentials or generated runtime data.

## Build, Test, and Development Commands

Use Python 3.12 and an isolated environment:

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'       # install the package and test dependencies
pytest                         # run the complete test suite
good-samaritan doctor --config config.toml  # validate local configuration
```

`good-samaritan run --config config.toml` is dry-run by default; do not use submission flags for routine development checks.

## Coding Style & Naming Conventions

Follow the surrounding Python style: type hints, `from __future__ import annotations`, standard-library imports first, and four-space indentation for new multiline code. Use `snake_case` for functions, variables, and modules; `PascalCase` for Pydantic models and other classes; and `UPPER_SNAKE_CASE` for constants. Prefer small, explicit functions and preserve the existing defensive error handling and redaction behavior. No formatter or linter is configured, so avoid unrelated reformatting.

## Testing Guidelines

Use pytest and name tests `test_<behavior>`. Keep tests offline and deterministic: use `tmp_path`, `monkeypatch`, and `httpx.MockTransport` rather than real GitHub or model-provider calls. Add regression coverage for changed safety gates, retry behavior, configuration precedence, and persisted state. Run `pytest` before proposing a change.

## Commit & Pull Request Guidelines

Recent commits use concise imperative subjects, e.g. `Retry transient GitHub API failures`. Keep each commit focused. PRs should explain the behavioral and safety impact, identify tests run, link the relevant issue, and include CLI output or screenshots when dashboard/website behavior changes. Never commit `.env`, tokens, database files, temporary workspaces, patches, or PR drafts.
