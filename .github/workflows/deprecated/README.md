# Deprecated Workflows

This directory contains GitHub Actions workflows that have been deprecated and disabled.

## ml-pipeline.yml.disabled

**Deprecated**: 2025-11-21
**Reason**: ML system testing requires complex infrastructure (PostgreSQL, Redis, Alembic migrations, Docker Hub credentials) that is not essential for core MCLI functionality. The main CI pipeline (`ci.yml`) provides adequate test coverage for the framework.

**What it tested**:
- ML-specific linting and type checking
- ML module unit tests across Python 3.10-3.12
- Integration tests with PostgreSQL and Redis
- Security scanning (Bandit)
- Docker image builds
- Staging/production deployments

**Why disabled**:
- Failing due to missing Alembic configuration (`script_location` key)
- Missing MyPy type stubs (types-PyYAML, types-requests)
- Docker Hub authentication not configured
- Deployment targets don't exist
- Adds complexity without critical coverage

**If you need ML-specific testing**:
- Run tests locally: `pytest tests/ -k ml -v`
- Use main CI pipeline which covers core functionality
- Re-enable and fix this workflow if ML features become critical path
