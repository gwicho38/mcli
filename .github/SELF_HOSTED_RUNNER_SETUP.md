# Self-Hosted GitHub Actions Runner Setup

This guide will help you set up a self-hosted GitHub Actions runner on your local server to bypass GitHub Actions quota limits.

## Prerequisites

- Server: `lefvpc@192.168.8.239` (or any Linux/macOS machine)
- SSH access to the server
- Python 3.9+ installed
- Internet connectivity from the server to GitHub

## Step 1: Install GitHub Actions Runner on Your Server

### Connect to Your Server
```bash
ssh lefvpc@192.168.8.239
```

### Create Runner Directory
```bash
mkdir -p ~/actions-runner
cd ~/actions-runner
```

### Download and Extract GitHub Actions Runner

**For Linux (x64):**
```bash
curl -o actions-runner-linux-x64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.321.0.tar.gz
```

**For macOS (arm64):**
```bash
curl -o actions-runner-osx-arm64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-osx-arm64-2.321.0.tar.gz
tar xzf ./actions-runner-osx-arm64-2.321.0.tar.gz
```

### Get Runner Registration Token

From your local machine (where you have gh CLI):
```bash
# Get registration token
gh api repos/gwicho38/mcli/actions/runners/registration-token --jq .token
```

This will output a token like: `AABCD...XYZ`

### Configure the Runner

Back on your server (`lefvpc@192.168.8.239`):
```bash
cd ~/actions-runner

# Configure with the token from above
./config.sh --url https://github.com/gwicho38/mcli \
  --token <PASTE_TOKEN_HERE> \
  --name lefvpc-runner \
  --labels self-hosted,linux,x64 \
  --work _work
```

**Answer the prompts:**
- Enter the name of the runner group: `[Press Enter for Default]`
- Enter the name of runner: `lefvpc-runner`
- Enter any additional labels: `linux,x64` (or `macos,arm64`)
- Enter name of work folder: `_work`

## Step 2: Install Runner as a Service (Recommended)

This keeps the runner running even after logout:

### Linux (systemd):
```bash
cd ~/actions-runner
sudo ./svc.sh install
sudo ./svc.sh start
sudo ./svc.sh status
```

### macOS (launchd):
```bash
cd ~/actions-runner
./svc.sh install
./svc.sh start
./svc.sh status
```

## Step 3: Install Dependencies on the Server

### Install Python versions (using pyenv):
```bash
# Install pyenv
curl https://pyenv.run | bash

# Add to ~/.bashrc or ~/.zshrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# Install Python versions
pyenv install 3.9.18
pyenv install 3.10.13
pyenv install 3.11.7
pyenv install 3.12.1
```

### Install UV:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.cargo/bin:$PATH"
```

### Install Build Tools:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y build-essential libssl-dev libffi-dev python3-dev git

# macOS
xcode-select --install
brew install openssl readline
```

## Step 4: Verify Runner is Active

From your local machine:
```bash
gh api repos/gwicho38/mcli/actions/runners --jq '.runners[] | {name: .name, status: .status, labels: .labels[].name}'
```

You should see your `lefvpc-runner` with status `online`.

## Step 5: Test the Self-Hosted Workflow

### Option A: Manual Trigger
```bash
# Trigger the self-hosted workflow manually
gh workflow run publish-self-hosted.yml \
  --ref main \
  -f publish_target=test-pypi
```

### Option B: Push to Trigger
```bash
# The workflow will run automatically on push to main
git push origin main
```

### Monitor the Run:
```bash
gh run list --workflow=publish-self-hosted.yml --limit 5
gh run watch
```

## Step 6: Configure Firewall (if needed)

If your server is behind a firewall, ensure it can reach:
- `github.com` (443)
- `*.actions.githubusercontent.com` (443)
- `*.blob.core.windows.net` (443)

```bash
# Test connectivity
curl -v https://github.com
curl -v https://pipelines.actions.githubusercontent.com
```

## Troubleshooting

### Check Runner Status:
```bash
cd ~/actions-runner
./run.sh  # Run in foreground for debugging
```

### Check Runner Logs:
```bash
# Linux/macOS
journalctl -u actions.runner.gwicho38-mcli.lefvpc-runner.service -f

# Or check log files
tail -f ~/actions-runner/_diag/*.log
```

### Restart Runner:
```bash
cd ~/actions-runner
sudo ./svc.sh stop
sudo ./svc.sh start
```

### Remove Runner:
```bash
cd ~/actions-runner
sudo ./svc.sh stop
sudo ./svc.sh uninstall
./config.sh remove --token <TOKEN>
```

## Security Considerations

1. **Network Security**: Runner can access your local network
2. **Repository Access**: Runner has access to repository secrets
3. **User Permissions**: Run as non-root user when possible
4. **Firewall**: Consider restricting outbound connections
5. **Updates**: Keep runner software updated

## Workflow Selection Strategy

### Automatic Fallback:
The repository now has two workflows:
- `publish.yml` - Uses GitHub-hosted runners (subject to quota)
- `publish-self-hosted.yml` - Uses your self-hosted runner

**To switch to self-hosted:**
1. Disable `publish.yml` workflow in GitHub settings
2. Enable `publish-self-hosted.yml` workflow
3. Or manually trigger self-hosted workflow when needed

### Manual Control:
```bash
# Use self-hosted runner
gh workflow run publish-self-hosted.yml -f publish_target=production-pypi

# Or edit .github/workflows/publish.yml to use:
# runs-on: [self-hosted, linux]
```

## Maintenance

### Update Runner:
```bash
cd ~/actions-runner
sudo ./svc.sh stop
./config.sh remove --token <TOKEN>
# Download new version and reconfigure
sudo ./svc.sh install
sudo ./svc.sh start
```

### Monitor Disk Space:
```bash
# Clean up old workflow runs
cd ~/actions-runner/_work
du -sh *
rm -rf <old-run-directories>
```

## Cost Comparison

| Option | Cost | Pros | Cons |
|--------|------|------|------|
| GitHub-hosted | Free tier: 2000 min/month<br>Paid: $0.008/min | No setup, maintained by GitHub | Quota limits, slower for large builds |
| Self-hosted | Server electricity + internet | Unlimited builds, faster, no quota | Setup/maintenance, security responsibility |

## Next Steps

1. Set up the runner following steps above
2. Test with: `gh workflow run publish-self-hosted.yml`
3. Monitor first run: `gh run watch`
4. If successful, consider disabling GitHub-hosted workflow to save quota

---

**Quick Start Script** (run on your server):

```bash
#!/bin/bash
# Save as setup-runner.sh on lefvpc@192.168.8.239

set -e

echo "Setting up GitHub Actions Runner..."

# Create directory
mkdir -p ~/actions-runner
cd ~/actions-runner

# Download runner (Linux x64)
curl -o actions-runner-linux-x64-2.321.0.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf ./actions-runner-linux-x64-2.321.0.tar.gz

echo ""
echo "✅ Runner downloaded and extracted"
echo ""
echo "Next steps:"
echo "1. Get registration token: gh api repos/gwicho38/mcli/actions/runners/registration-token --jq .token"
echo "2. Run: ./config.sh --url https://github.com/gwicho38/mcli --token <TOKEN> --name lefvpc-runner"
echo "3. Run: sudo ./svc.sh install && sudo ./svc.sh start"
echo ""
```

Save and run:
```bash
ssh lefvpc@192.168.8.239
bash setup-runner.sh
```
