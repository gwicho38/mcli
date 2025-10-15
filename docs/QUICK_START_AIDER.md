# Quick Start: Using MCLI with Aider

This is a quick reference guide for setting up and using MCLI as a model service for aider.

## For Local Development (No Public Access)

If you just want to test locally without public access:

```bash
# Generate an API key
export MCLI_API_KEY=$(openssl rand -hex 32)
echo "Your API Key: $MCLI_API_KEY"

# Start the model service
mcli model start \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# In another terminal, configure aider
export OPENAI_API_KEY="$MCLI_API_KEY"
export OPENAI_API_BASE="http://localhost:51234/v1"

# Use aider
aider --model prajjwal1/bert-tiny
```

## For Public Access (Production)

For production deployment with public access via nginx:

### Quick Setup

```bash
# Run the automated setup script
cd /path/to/mcli
./scripts/setup_public_model_service.sh
```

The script will ask:
- Where is your nginx (on this host or on router)?
- Domain name (e.g., model.mcli.info)
- Email for SSL certificate
- Model selection

The script will generate:
- API key
- Systemd service configuration
- Nginx configuration
- SSL certificate instructions
- Firewall configuration

### Manual Setup

**For standard setup (nginx on same host):**
See [PUBLIC_MODEL_SERVICE_SETUP.md](PUBLIC_MODEL_SERVICE_SETUP.md) for detailed manual setup instructions.

**For router-level nginx:**
See [ROUTER_NGINX_SETUP.md](ROUTER_NGINX_SETUP.md) for router-specific configuration.

## Testing Your Setup

### Test Health Endpoint

```bash
# Local
curl http://localhost:51234/health

# Public
curl https://model.mcli.info/health
```

### Test Models Endpoint

```bash
# Local
curl http://localhost:51234/v1/models \
  -H "Authorization: Bearer $MCLI_API_KEY"

# Public
curl https://model.mcli.info/v1/models \
  -H "Authorization: Bearer $MCLI_API_KEY"
```

### Test Chat Completion

```bash
# Local
curl http://localhost:51234/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCLI_API_KEY" \
  -d '{
    "model": "prajjwal1/bert-tiny",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'

# Public
curl https://model.mcli.info/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCLI_API_KEY" \
  -d '{
    "model": "prajjwal1/bert-tiny",
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

## Using with Aider

### Local Development

```bash
export OPENAI_API_KEY="your-mcli-api-key"
export OPENAI_API_BASE="http://localhost:51234/v1"
aider --model prajjwal1/bert-tiny
```

### Production (Public Domain)

```bash
export OPENAI_API_KEY="your-mcli-api-key"
export OPENAI_API_BASE="https://model.mcli.info/v1"
aider --model prajjwal1/bert-tiny
```

### Add to Shell Profile

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# MCLI Model Service
export OPENAI_API_KEY="your-mcli-api-key-here"
export OPENAI_API_BASE="https://model.mcli.info/v1"
```

Then reload:
```bash
source ~/.bashrc  # or ~/.zshrc
```

## Available Models

List available models:

```bash
mcli model list
```

Common lightweight models:
- `prajjwal1/bert-tiny` - Ultra-lightweight (4.4M params)
- `sshleifer/tiny-distilbert-base-uncased` - Tiny DistilBERT (22M params)
- `microsoft/DialoGPT-tiny` - Conversational (33M params)
- `distilbert-base-uncased` - DistilBERT (66M params)
- `microsoft/DialoGPT-small` - Conversational (117M params)

## Command Reference

### Start Server

```bash
# Basic (localhost only, no OpenAI compatibility)
mcli model start

# With specific model
mcli model start --model prajjwal1/bert-tiny

# Local development with OpenAI compatibility (recommended)
mcli model start \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# Router-level nginx (bind to all interfaces)
mcli model start \
  --host 0.0.0.0 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# Note: Use 0.0.0.0 only if nginx is on a different machine (e.g., router)
# Always configure firewall to restrict access when using 0.0.0.0
```

### Check Status

```bash
# Check if server is running
mcli model status

# View logs (if using systemd)
sudo journalctl -u mcli-model -f
```

### Stop Server

```bash
# If running in foreground: Ctrl+C

# If running as systemd service:
sudo systemctl stop mcli-model

# Or find and kill process:
mcli model stop
```

## Troubleshooting

### "Connection refused" when using aider

1. Check if the service is running:
   ```bash
   curl http://localhost:51234/health
   ```

2. Verify the API key is correct:
   ```bash
   echo $MCLI_API_KEY
   ```

3. Check service logs:
   ```bash
   # If running in terminal, check output
   # If running as systemd:
   sudo journalctl -u mcli-model -n 50
   ```

### "Invalid API key" error

Make sure you're using the correct API key:
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Should match the key you used to start the server
```

### "Model not found" error

Download the model first:
```bash
mcli model download prajjwal1/bert-tiny
```

Or start with `--auto-download`:
```bash
mcli model start --auto-download
```

### Port already in use

```bash
# Find process using the port
sudo lsof -i :51234

# Kill it if needed
sudo kill -9 <PID>

# Or use a different port
mcli model start --port 51235
```

## Security Notes

### For Local Development
- Use `127.0.0.1` instead of `0.0.0.0`
- API key is still recommended but optional

### For Production
- **Always** use an API key
- Bind to `127.0.0.1` and use nginx reverse proxy
- Use SSL/TLS (Let's Encrypt)
- Enable rate limiting in nginx
- Monitor access logs
- Rotate API keys periodically

## Performance Tips

1. **Use GPU if available:**
   ```bash
   mcli model start --device cuda --openai-compatible --api-key "$KEY"
   ```

2. **Use smaller models for faster responses:**
   - `prajjwal1/bert-tiny` is the fastest
   - `microsoft/DialoGPT-tiny` for conversation

3. **Monitor resource usage:**
   ```bash
   htop
   ```

## Support

- Documentation: [PUBLIC_MODEL_SERVICE_SETUP.md](PUBLIC_MODEL_SERVICE_SETUP.md)
- GitHub Issues: https://github.com/lefv/mcli/issues
- Project README: https://github.com/lefv/mcli

## License

Part of the MCLI project. See LICENSE for details.
