# Good Samaritan

Good Samaritan is a small, single-process Python CLI for a deliberately cautious experiment: an independent AI GitHub identity discovers a small open issue, prepares a focused fix, tests it, gets a separate model review, and only then may open a pull request.

It is not an enterprise automation platform, does not impersonate its operator, and never creates a GitHub account. Prepare a separate GitHub account and token yourself. Every generated PR includes an explicit AI disclosure and asks maintainers to review normally.

## Safety model

The default is dry-run. A dry run performs discovery, cloning, analysis, editing, validation, review, and writes a local patch plus PR draft, but never forks, pushes, or opens a PR. The tool rejects assigned or already-PR'd issues, sensitive/security work, prompt-injection-like text, repositories that prohibit bots/AI contributions, path traversal, sensitive-file access, dangerous shell commands, large diffs, and insufficient validation. Repository text is treated as untrusted data, not instructions.

## Install

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
cp .env.example .env
cp config.example.toml config.toml
```

Set `GOOD_SAMARITAN_GITHUB_TOKEN` for the dedicated account. A classic token needs `repo` for private-repository access or fork/PR writes; public-only operation can use a fine-grained token with repository contents and pull-requests read/write permissions. Configure at least one provider key and model in the environment/TOML: Gemini (`GEMINI_API_KEY`), Groq (`GROQ_API_KEY`), or OpenRouter (`OPENROUTER_API_KEY`). Model names are intentionally never hard-coded.

## Commands

```bash
good-samaritan doctor --config config.toml
good-samaritan discover --config config.toml
good-samaritan run --config config.toml              # always dry run by default
good-samaritan history --config config.toml
good-samaritan show 1 --config config.toml
```

For a real submission, set `runtime.dry_run = false`, `runtime.allow_submit = true`, configure the dedicated account name/email, then use `good-samaritan run --submit`. This is intentionally a two-part opt-in. `good-samaritan daemon` runs the same bounded one-issue attempt on the configured interval and exits cleanly on SIGINT/SIGTERM.

## Workflow and records

Discovery searches active non-fork, non-archived repositories with GitHub Search, evaluates labeled open issues using transparent local scoring, then consults the configured model. The selected repository is shallow-cloned to a temporary directory; bounded tools may inspect/edit only inside it. Relevant tests are detected conservatively, results are persisted to SQLite, and the patch/PR draft is retained in the configured work directory. Attempt states progress from `DISCOVERED` through analysis, editing, testing and reviewing to `READY`/`PR_CREATED`, or a safe failure.

Provider failures, rate limits, and temporary errors cause cooldown and automatic provider fallback. If none are usable, the run stops safely without retries or remote changes. API keys are never put in prompts or log output.

## Development

```bash
pip install -e '.[test]'
pytest
```

Common failures: `doctor` reports no provider when a key/model pair is missing; GitHub discovery needs a valid token for reliable rate limits; failures to install project dependencies mean no PR is opened by design. This tool does not run arbitrary project install scripts.
