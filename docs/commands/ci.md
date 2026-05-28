# `mcli ci` — act-first CI

Make local [`act`](https://github.com/nektos/act) the primary pull-request gate and
stop billed GitHub-hosted Actions minutes on private repositories. Hosted workflows
are kept (still runnable via `workflow_dispatch`) but no longer auto-fire on
`push`/`pull_request`; a dormant self-hosted fallback workflow is added that activates
only where a self-hosted runner is online.

## Commands

| Command | What it does |
|---------|--------------|
| `mcli ci migrate [--dry-run]` | Strip `push`/`pull_request` triggers from this repo's GitHub-hosted workflows and add a `self-hosted-ci.yml` fallback. Idempotent. `--dry-run` shows the plan without writing. |
| `mcli ci preflight [--event EVENT]` | Run `act` as the PR gate. See exit codes below. |
| `mcli ci pr` | Run `preflight`; on pass, `gh pr create --fill --base main`. On the runner-fallback path, push and open the PR. |
| `mcli ci doctor` | Report `act` / Docker / online-runner status for the current repo. |
| `mcli ci install-hook` | Install an opt-in `.git/hooks/pre-push` that runs `mcli ci preflight`. |

## `preflight` exit-code contract

| Exit | Meaning |
|------|---------|
| `0` | `act` ran and passed — OK to open the PR. |
| `1` | `act` ran and a job failed — fix before opening the PR. |
| `2` | `act` could not run here (no Docker / no `act` / image pull failed) **and** no online self-hosted runner exists — cannot validate. |
| `3` | `act` could not run here, but an online self-hosted runner exists — push and let the runner validate. |

"Could not run" is distinguished from "ran and failed" by a capability probe
(Docker daemon up + `act -l` succeeds) before any job is executed.

## How the gate works

```
git push  (or: mcli ci pr)
   └─ mcli ci preflight
        ├─ act passed ............................ open PR              ($0)
        ├─ act failed ............................ blocked, fix it
        └─ act unreachable
             ├─ repo has an online runner ........ push; runner validates
             └─ no runner ........................ cannot validate
```

## Secrets for `act`

If a `.secrets` file exists in the repo root, `preflight` passes it to `act`
(`--secret-file .secrets`). Keep `.secrets` out of git (add it to `.gitignore`);
populate it from your secrets manager.

## Migration notes

- Migration is idempotent: a marker comment (`# mcli-ci: hosted-triggers-stripped`)
  makes re-runs no-ops.
- `on:` is workflow-level. A workflow that mixes hosted and self-hosted jobs loses
  the self-hosted job's auto-trigger too; the separate `self-hosted-ci.yml` covers
  the runner path when a runner exists.
- The fallback `self-hosted-ci.yml` gets a `pull_request` trigger only if the repo
  already has an online self-hosted runner at migrate time; otherwise it is
  `workflow_dispatch`-only (dormant) until you register one.
- Re-enabling hosted CI: the original workflows still exist — run them manually via
  `workflow_dispatch`, or restore the stripped triggers.
