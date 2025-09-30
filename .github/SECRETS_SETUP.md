# GitHub Secrets Setup for mcli

This document describes the required GitHub secrets for CI/CD and PyPI publishing.

## Required Secrets

### PyPI Publishing

#### Option 1: Trusted Publishing (Recommended)
PyPI now supports trusted publishing via OIDC, which doesn't require storing tokens.

**Setup:**
1. Go to https://pypi.org/manage/account/publishing/
2. Add a new publisher with:
   - **PyPI Project Name**: `mcli`
   - **Owner**: `gwicho38`
   - **Repository name**: `mcli`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi` (optional but recommended)

This is the **most secure** method and doesn't require managing tokens.

#### Option 2: API Token (Fallback)
If trusted publishing isn't set up, use an API token:

1. Go to https://pypi.org/manage/account/token/
2. Create a new API token with scope: `upload packages`
3. Add to GitHub secrets as: `PYPI_API_TOKEN`

```bash
# Set via gh CLI
gh secret set PYPI_API_TOKEN --body "pypi-AgE..."
```

### Test PyPI (Optional)
For testing releases before publishing to production PyPI:

1. Go to https://test.pypi.org/manage/account/token/
2. Create token and add as: `TEST_PYPI_API_TOKEN`

```bash
gh secret set TEST_PYPI_API_TOKEN --body "pypi-AgE..."
```

## Current Secrets Status

Check configured secrets:
```bash
gh secret list
```

## Security Best Practices

1. **Never** commit secrets to the repository
2. **Always** use GitHub secrets for CI/CD
3. **Rotate** tokens regularly (every 90 days)
4. **Use** trusted publishing when possible (no tokens needed)
5. **Limit** token scope to minimum required permissions
6. **Enable** 2FA on PyPI account

## Additional Secrets (for development)

These are NOT stored in GitHub secrets (use local .env files):

- `OPENAI_API_KEY` - For AI features (local development)
- `ANTHROPIC_API_KEY` - For Claude integration (local development)
- `SUPABASE_URL` / `SUPABASE_ANON_KEY` - For database (local development)

## Rotating Exposed Secrets

⚠️ **IMPORTANT**: The following secrets were found exposed and MUST be rotated:

1. **OpenAI API Key** - Go to https://platform.openai.com/api-keys
2. **GitHub Token** - Go to https://github.com/settings/tokens
3. **JIRA Tokens** - Go to your JIRA account settings
4. **Supabase Keys** - Go to https://app.supabase.com/project/*/settings/api

After rotating, update your local `.env.backup` files and any external services using these credentials.
