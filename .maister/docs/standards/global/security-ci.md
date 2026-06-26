## Security & CI Gates

### Self-hosted, act-first CI
Per the act-first private-repo policy, core CI (`ci.yml`/`test.yml`) runs on self-hosted runners (`runs-on: [self-hosted, linux, x64]`) and is gated locally before push via `mcli ci preflight` (a green local `act` run is equivalent to a remote run). New workflows should follow the self-hosted + `workflow_dispatch` pattern; do not add billed hosted `push`/`pull_request` triggers to CI/lint/test jobs without cost approval. Confidence 82.

### Bandit blocks HIGH-severity findings
`security.yml` runs `bandit -r src/ --severity-level high` with a fixed CLI false-positive skip list; bandit also runs at commit time. Confidence 88.

### Secret scanning with TruffleHog (verified only)
`security.yml` runs TruffleHog on the diff with `--only-verified` on push/PR. Confidence 85.

### CodeQL security-and-quality analysis
CodeQL analyzes Python on push/PR to main and weekly (Sun cron) using the `+security-and-quality` suite, uploading to GitHub Security. Confidence 85.

### Dependency review fails on moderate+
PRs run `actions/dependency-review-action` with `fail-on-severity: moderate`; Trivy filesystem scan and a Safety check also run (largely advisory). Confidence 85.

### Never commit secrets — use environment variables
Store config/secrets in environment variables and `.env` files (gitignored); never commit API keys. Keys like `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SUPABASE_*` are sourced from `.env`. Confidence 88.
