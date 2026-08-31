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
| `mcli ci preflight [--event EVENT] [--lock-timeout SECONDS]` | Run `act` as the PR gate. See exit codes below. `act` runs are serialised machine-wide. |
| `mcli ci pr` | Run `preflight`; on pass, `gh pr create --fill --base main`. On the runner-fallback path, push and open the PR. |
| `mcli ci doctor` | Report `act` / Docker / online-runner status for the current repo. |
| `mcli ci install-hook` | Install an opt-in `.git/hooks/pre-push` that runs `mcli ci preflight`. |

## `preflight` exit-code contract

| Exit | Meaning |
|------|---------|
| `0` | `act` ran and passed — OK to open the PR. |
| `1` | `act` ran and a job failed — fix before opening the PR. |
| `2` | `act` could not run here (no Docker / no `act` / image pull failed / the machine-wide act lock never came free) **and** no online self-hosted runner exists — cannot validate. |
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

## One act run at a time (machine-wide lock)

Every repo with the pre-push hook installed runs `mcli ci preflight` on push, and
every `act` run drives the *same* container runtime (one podman/docker VM with a
fixed CPU/memory budget). Several pushes at once therefore starve the host —
which is how a running Android emulator was made to ANR.

`preflight` takes a machine-wide `fcntl.flock` on `~/.mcli/locks/ci-act.lock`
before starting `act`, so concurrent invocations queue instead of piling on:

```
repo A: mcli ci preflight ── holds lock ── act runs ──┐
repo B: mcli ci preflight ── waits ───────────────────┴─ act runs
```

- **Timeout** — waiting is bounded, 600s by default. Change it per-invocation with
  `--lock-timeout SECONDS` or machine-wide with `MCLI_CI_LOCK_TIMEOUT`.
- **On expiry** the gate does *not* block the push and does *not* start a second
  concurrent container run: it reports the existing "cannot validate" state
  (exit `2`, or `3` where a runner can validate instead), loudly.
- **No stale locks.** `flock` belongs to the open file descriptor, so the kernel
  releases it when the holder exits — including on exception and on `SIGKILL`.
  The `pid=… repo=…` line written into the lockfile only feeds the "waiting for…"
  message; it is never consulted for correctness.
- **Fails open.** If the lockfile cannot be created or opened at all, `preflight`
  warns and runs `act` unserialised rather than raising — an exception there
  would exit `1` and block the push in every repo.
- **What is not locked**: the `make ci-native` gate (host-local, no container
  runtime — serialising it behind heavyweight act runs would only push fast,
  valid gates into the timeout) and the capability probe (so a dead Docker is
  reported immediately rather than after a 600s wait).
- Override the lockfile location with `MCLI_CI_LOCK_PATH` (mainly for tests).

## Secrets for `act`

If a `.secrets` file exists in the repo root, `preflight` passes it to `act`
(`--secret-file .secrets`). Keep `.secrets` out of git (add it to `.gitignore`);
the repository `.env` is never loaded implicitly. This keeps application
configuration out of local CI containers and avoids dotenv parsing failures for
valid multiline values such as JSON credentials or certificates.
Populate `.secrets` from your secrets manager.

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
