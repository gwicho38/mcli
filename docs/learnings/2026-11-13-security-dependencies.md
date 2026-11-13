# Dependency security and default-wheel encryption

Issue: #251. Integration release: 8.0.71, not yet published.

The project development environment reproduced 156 active Safety advisories
across 19 packages, with zero ignores. Matching tuples on main establish that
the shell exit-status fix did not introduce them; baseline provenance does not
waive the security gate.

The repair raises the affected runtime and development floors and uses named
UV upgrades. FastAPI 0.133.0 permits the fixed Starlette 1.3.1. Black 26.3.1
requires the development upper bound to move to 27; its formatting-only changes
are included. Cryptography 50 and virtualenv 21 cross major versions, so package
metadata alone is insufficient evidence of supported behavior.

The default wheel also omitted `cryptography`, despite storage and secrets
modules importing it. A fresh default-wheel installation reproduced
`ModuleNotFoundError: No module named 'cryptography'`. The regression builds the
wheel, installs it with runtime dependencies only into an isolated UV environment,
and verifies a binary encryption round trip and the installed API health route.
The test asserts that pytest is absent from that runtime environment. Declaring
cryptography as a runtime dependency makes the regression pass.

**Before**

```mermaid
flowchart LR
    A[Development extras] --> B[Cryptography present incidentally]
    C[Default wheel] --> D[Storage import fails]
    E[Permitted old dependency floors] --> F[156 active audit findings]
```

**After**

```mermaid
flowchart LR
    A[Runtime dependency declaration] --> B[Default wheel encryption works]
    C[Reviewed security floors and named upgrades] --> D[Zero active audit findings]
```

After frozen development installation, Safety reports 184 packages, zero active
advisories and zero ignored advisories. No policy exceptions were added. The
configured HIGH-severity Bandit filter is separate from the unfiltered report;
this dependency repair does not eliminate pre-existing raw source findings.
Coverage configuration and the documented 50 percent threshold remain separate
integration requirements (#252 and #178).

## Dependency versions

| Package | Before | After |
|---|---|---|
| aiohttp | 3.13.3 | 3.14.3 |
| anyio | 4.12.1 | 4.14.2 |
| authlib | 1.6.6 | 1.6.12 |
| black | 25.12.0 | 26.3.1 |
| cryptography | 46.0.4 | 50.0.0 |
| fastapi | 0.128.0 | 0.133.0 |
| gitpython | 3.1.46 | 3.1.62 |
| idna | 3.11 | 3.15 |
| multidict | 6.7.1 | 6.9.1 |
| nltk | 3.9.2 | 3.10.4 |
| pydantic-settings | 2.12.0 | 2.14.2 |
| pygments | 2.19.2 | 2.20.0 |
| pyjwt | 2.10.1 | 2.15.0 |
| pytest | 9.0.2 | 9.0.3 |
| python-dotenv | 1.2.1 | 1.2.2 |
| requests | 2.32.5 | 2.33.0 |
| soupsieve | 2.8.3 | 2.9 |
| starlette | 0.50.0 | 1.3.1 |
| urllib3 | 2.6.3 | 2.8.0 |
| virtualenv | 20.36.1 | 21.7.13 |

Resolution also updates filelock and pathspec and adds python-discovery and
defusedxml to satisfy the updated tools. Other existing versions stay locked.

## Publisher evidence

All target releases have published files and Python requirements compatible with
3.10 in their PyPI JSON metadata. Maintainer advisories and release notes explain
the security boundaries; the fresh audit verifies the combined installed set.

- [Black advisory, fixed in 26.3.1](https://github.com/psf/black/security/advisories/GHSA-3936-cmfr-pm3m)
- [Starlette form-limit advisory, fixed in 1.3.1](https://github.com/Kludex/starlette/security/advisories/GHSA-82w8-qh3p-5jfq)
- [FastAPI 0.133.0 dependency declarations](https://github.com/fastapi/fastapi/blob/0.133.0/pyproject.toml)
- [Cryptography changelog](https://github.com/pyca/cryptography/blob/main/CHANGELOG.rst)
- [Virtualenv activation advisory](https://github.com/pypa/virtualenv/security/advisories/GHSA-p58f-9548-mpm2)
- [Pydantic Settings 2.14.2 security release](https://github.com/pydantic/pydantic-settings/releases/tag/v2.14.2)
- [Pytest 9.0.3 security fix](https://github.com/pytest-dev/pytest/releases/tag/9.0.3)
- [Pygments changelog](https://github.com/pygments/pygments/blob/master/CHANGES)

## Validation

- Baseline Safety: 182 packages, 156 active findings, zero ignored; exit 64.
- Repaired Safety: Python 3.11, 184 packages; Python 3.10, 188 packages. Both
  report zero active findings, zero ignored, exit 0.
- Full functional suite: 1,810 passed, 267 skipped, 12 warnings, exit 0.
- Focused encryption, daemon API, API utilities and shell-loader suite: 44 passed
  on Python 3.10 and 3.11. The final wheel regression with API health validation
  also passed separately on both interpreters.
- Frozen install, lock check, Black, isort, flake8, mypy (217 source files), wheel
  and sdist builds, and configured HIGH-severity Bandit: exit 0.
- The 18 existing Python files changed by Black have identical parsed ASTs before
  and after formatting. No source behavior was changed by the formatter.
- Virtualenv 21.7.13 creates a working isolated Python interpreter.

Starlette warns that its HTTPX TestClient adapter is deprecated. The adapter
still passes the exercised routes; no HTTP client migration is included here.
These checks do not satisfy the separate coverage gate or authorize publication.
