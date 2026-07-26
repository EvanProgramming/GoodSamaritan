# Good Samaritan

Good Samaritan is a small, single-process Python CLI for a deliberately cautious experiment: an independent AI GitHub identity discovers a small open issue, prepares a focused fix, tests it, gets a separate model review, and only then may open a pull request.

It is not an enterprise automation platform, does not impersonate its operator, and never creates a GitHub account. Prepare a separate GitHub account and token yourself. Every generated PR includes an explicit AI disclosure and asks maintainers to review normally.

## Safety model

The default is dry-run. A dry run performs discovery, cloning, analysis, editing, validation, review, and writes a local patch plus PR draft, but never forks, pushes, or opens a PR. The tool rejects assigned or already-PR'd issues, sensitive/security work, prompt-injection-like text, repositories that prohibit bots/AI contributions, path traversal, sensitive-file access, dangerous shell commands, large diffs, and insufficient validation. Repository text is treated as untrusted data, not instructions.

## Install

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e '.[test]'
good-samaritan setup
```

Set `GOOD_SAMARITAN_GITHUB_TOKEN` to a **classic** token (`ghp_…`) from the dedicated account, with the `repo` scope. This broader scope is presently necessary because GitHub fine-grained tokens cannot contribute to public repositories where the account is not a member—the central Good Samaritan workflow. Do not use a personal/main-account token. Configure at least one provider key and model in the environment/TOML: Gemini (`GEMINI_API_KEY`), Groq (`GROQ_API_KEY`), or OpenRouter (`OPENROUTER_API_KEY`). Model names are intentionally never hard-coded.

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

## First-time setup and go-live

`good-samaritan setup` is the recommended one-time local wizard. It creates `config.toml` for non-secret policy/model ordering and a gitignored `.env` with owner-only permissions for the dedicated-account **classic GitHub token**, Git author identity, and one or more provider API keys. For each provider you enable, enter its current model identifier; model names are configurable because providers change their catalogues frequently. The selected order is the automatic fallback order.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
good-samaritan setup
good-samaritan doctor --config config.toml
good-samaritan run --config config.toml       # first full dry run
```

When the dry run is satisfactory, `good-samaritan go-live --config config.toml --interval-hours 24` performs a final GitHub/model preflight, asks for confirmation of the dedicated GitHub identity, changes only the local live-submission switches, and starts the daemon. Add `--yes` only for an unattended launch. Stop it with Ctrl-C; it completes current cleanup before exiting. Keep the terminal open, or run it under your preferred local process manager after validating the dry run. API keys may alternatively be supplied as process environment variables (useful for launchd); those override `.env` and TOML.

## Development

```bash
pip install -e '.[test]'
pytest
```

Common failures: `doctor` reports no provider when a key/model pair is missing; GitHub discovery needs a valid token for reliable rate limits; failures to install project dependencies mean no PR is opened by design.

### Disposable dependency environments

Set `runtime.allow_dependency_install = true` to let Good Samaritan prepare a repository's declared test dependencies before validation. It creates `.good-samaritan-venv` **inside that attempt's temporary clone**, installs Python dependencies from `requirements.txt`/`requirements-dev.txt` or the local Python project, and uses `npm ci --ignore-scripts` for lockfile-based Node projects. All installation and test commands are recorded in the dashboard, remain constrained by the command timeout, and disappear when the attempt workspace is cleaned up. It never installs dependencies into your system Python, changes global Git/shell settings, or executes package lifecycle scripts.

## Journal, memory, and public site

Good Samaritan maintains SQLite-backed project, technical, maintainer-preference, and failure memories. Relevant repository memories are injected into the coding prompt before work begins. PR feedback is recorded as feedback and can become lessons for later attempts. Use `good-samaritan stats`, `good-samaritan lessons`, `good-samaritan memory --repository owner/repo`, and `good-samaritan journal` to inspect or generate the public journey. The generated `website/` directory is a deliberately simple GitHub Pages site; its workflow only deploys public journal files and never runs contribution automation.

Social behaviour is disabled by default. When `[social].enabled=true`, a high-confidence selected Issue may receive at most one investigation comment, subject to the daily limit; PR and maintainer interaction remains deduplicated and prompt-injection-like comments are blocked.

## Local cleanup and restoration

Every clone is made in Good Samaritan's configured `work_directory` and is deleted when its attempt exits, whether it succeeds or fails. On daemon startup, interrupted `attempt-*` directories are removed as well. When a created PR is merged or closed, its local patch and PR draft are removed automatically; the SQLite journal and public report remain as intentional application data. Good Samaritan never edits global Git configuration, shell profiles, SSH configuration, or files outside its own workspace. Run `good-samaritan cleanup` to remove stale temporary workspaces, or `good-samaritan cleanup --all-artifacts` to also discard retained local dry-run patches and drafts.
