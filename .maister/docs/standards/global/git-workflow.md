## Git & Release Workflow

### Use conventional commit messages and PR titles
Commits and PR titles follow `type(scope): description` with types feat/fix/docs/style/refactor/test/chore (e.g. `fix(ci): preflight runs ci.yml primary`, `feat(sync): mcli sync key`). Confidence 90.

### Bump the version in pyproject.toml within the fix/feature PR
Bump the `version` field in `pyproject.toml` (patch for fixes) in the same PR as the change — observed consistently across recent merged PRs. This is step 1 of the release process. Confidence 80.

### Ship a regression test with each bug fix
Bug-fix PRs include a regression test reproducing the issue (TDD-style), especially for security fixes (RCE/path-traversal guards). Confidence 70.

### Write release notes per version
Each release has notes at `docs/releases/X.Y.Z.md` following the established format; tag as `vX.Y.Z`. Confidence 85.

### Pass PR quality gates before submitting
Develop on `feature/*` (or `fix/*`, `docs/*`, `chore/*`) off `main`. Before a PR run `make lint`, `make test-cov`, `make security-check`, and update docs for new features. PRs must pass tests, lint, security, and maintain coverage. Confidence 85.

### Never declare work complete until CI passes
CI must be green on GitHub before work is considered done — check `gh run list` before starting, monitor after pushing, fix failures immediately. Confidence 88.

### Concurrent agents use isolated git worktrees
When multiple agents/sessions may touch the repo simultaneously, each works in its own `git worktree` (never a shared checkout) to avoid commit commingling. Confidence 84.
