# Quick Start: Self-Hosted Runner for PyPI Publishing

## TL;DR - Get Publishing in 5 Minutes

### On Your Server (lefvpc@192.168.8.239)

```bash
# 1. Download and run setup script
ssh lefvpc@192.168.8.239
curl -O https://raw.githubusercontent.com/gwicho38/mcli/main/setup-self-hosted-runner.sh
bash setup-self-hosted-runner.sh
```

### On Your Local Machine

```bash
# 2. Get registration token
gh api repos/gwicho38/mcli/actions/runners/registration-token --jq .token
# Copy the token output (looks like: AABCD...XYZ)
```

### Back on Your Server

```bash
# 3. Configure runner (paste token from step 2)
cd ~/actions-runner
./config.sh \
  --url https://github.com/gwicho38/mcli \
  --token <PASTE_TOKEN_HERE> \
  --name lefvpc-runner \
  --labels self-hosted,linux,x64 \
  --work _work

# 4. Install as service
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status

# 5. Install dependencies
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"

# Optional: Install multiple Python versions
curl https://pyenv.run | bash
echo 'export PATH="$HOME/.pyenv/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc
pyenv install 3.9.18 3.10.13 3.11.7 3.12.1
```

### Verify It's Working

```bash
# From your local machine
gh api repos/gwicho38/mcli/actions/runners --jq '.runners[] | {name: .name, status: .status}'
# Should show: "name": "lefvpc-runner", "status": "online"
```

## Publish to PyPI Now

```bash
# Trigger self-hosted workflow to publish
gh workflow run publish-self-hosted.yml -f publish_target=production-pypi

# Watch it run
gh run watch
```

## What This Does

1. **Bypasses GitHub Actions Quota** - Uses your own server's compute
2. **Publishes to PyPI** - Same as cloud workflow, but on your hardware
3. **Runs Tests** - Python 3.9-3.12 on your server
4. **Builds Package** - Creates wheel and source distributions
5. **Uploads to PyPI** - Using your PYPI_API_TOKEN secret

## Workflow Triggers

| Trigger | What Happens |
|---------|--------------|
| `git push origin main` | Builds & publishes to PyPI automatically |
| `git push origin dev` | Builds & publishes to Test PyPI |
| `git push origin v7.0.0` (tag) | Publishes + creates GitHub release |
| Manual trigger | Choose test-pypi, production-pypi, or both |

## Manual Trigger Options

```bash
# Publish to Test PyPI
gh workflow run publish-self-hosted.yml -f publish_target=test-pypi

# Publish to Production PyPI
gh workflow run publish-self-hosted.yml -f publish_target=production-pypi

# Publish to both
gh workflow run publish-self-hosted.yml -f publish_target=both
```

## Troubleshooting

### Runner not showing up?
```bash
ssh lefvpc@192.168.8.239
cd ~/actions-runner
./run.sh  # Run in foreground to see logs
```

### Service not starting?
```bash
sudo ./svc.sh status
sudo ./svc.sh stop
sudo ./svc.sh start
journalctl -u actions.runner.* -f
```

### Workflow failing?
```bash
# Check workflow runs
gh run list --workflow=publish-self-hosted.yml

# View failed run
gh run view <run-id> --log-failed
```

## Cost Savings

| Scenario | GitHub-Hosted | Self-Hosted |
|----------|---------------|-------------|
| Build time (est.) | 5 minutes | 5 minutes |
| Cost per build | $0.008/min × 5 = $0.04 | $0 (electricity) |
| Monthly builds (100) | $4.00 or quota | $0 |
| **Annual savings** | **~$48/year** | **Free** |

Plus: **Unlimited builds**, no quota restrictions!

## Next Steps

1. ✅ Set up runner (steps above)
2. ✅ Test with: `gh workflow run publish-self-hosted.yml`
3. ✅ Publish v7.0.0: `git push origin v7.0.0`
4. ✅ Install from PyPI: `pip install mcli`
5. ✅ Test self-update: `mcli self update`

## Full Documentation

- [Complete Setup Guide](.github/SELF_HOSTED_RUNNER_SETUP.md)
- [GitHub Actions Docs](https://docs.github.com/en/actions/hosting-your-own-runners)
- [PyPI Publishing Guide](.github/SECRETS_SETUP.md)

---

**Ready to publish?** Run: `gh workflow run publish-self-hosted.yml -f publish_target=production-pypi` 🚀
