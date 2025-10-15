# MCLI Model Service - Complete Setup Guide

## Overview

MCLI now supports running as a publicly accessible, OpenAI-compatible model service that works seamlessly with tools like **aider**. This implementation provides API key authentication, SSL/TLS encryption, and production-ready deployment options.

## Architecture

```
Internet → Router (nginx + SSL) → Host Server (MCLI) → AI Models
          (192.168.8.1)           (192.168.8.100)
```

**Key Features:**
- ✅ OpenAI-compatible API endpoints (`/v1/models`, `/v1/chat/completions`)
- ✅ API key authentication (Bearer token)
- ✅ SSL/TLS encryption (via nginx reverse proxy)
- ✅ Rate limiting support
- ✅ Streaming responses
- ✅ Health check endpoint
- ✅ Production-ready systemd integration

## Quick Start

### Local Development (Simplest)

```bash
# Generate API key
export MCLI_API_KEY=$(openssl rand -hex 32)
echo "Your API Key: $MCLI_API_KEY"

# Start model service
mcli model start \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# In another terminal, use with aider
export OPENAI_API_KEY="$MCLI_API_KEY"
export OPENAI_API_BASE="http://localhost:51234/v1"
aider --model prajjwal1/bert-tiny
```

### Production Deployment (Router-Level Nginx)

For your network setup with nginx on router:

**Step 1: On Host Server (192.168.8.100)**

```bash
# Generate API key
export MCLI_API_KEY=$(openssl rand -hex 32)
echo "Save this: $MCLI_API_KEY" | tee ~/mcli-api-key.txt

# Start MCLI (accessible from router)
mcli model start \
  --host 0.0.0.0 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# Configure firewall (ONLY allow router)
sudo ufw allow from 192.168.8.1 to any port 51234 proto tcp
sudo ufw deny 51234/tcp
sudo ufw enable
```

**Step 2: On Router (192.168.8.1)**

```bash
# Find your SSL certificate location
ssh root@192.168.8.1
grep -r "ssl_certificate" /etc/nginx/sites-enabled/ | head -3

# Copy minimal nginx config
# From your host:
scp nginx/model.mcli.info-minimal.conf root@192.168.8.1:/tmp/

# On router, edit SSL paths to match your setup
nano /tmp/model.mcli.info-minimal.conf

# Update these lines:
# ssl_certificate /etc/nginx/ssl/YOUR_CERT.crt;
# ssl_certificate_key /etc/nginx/ssl/YOUR_CERT.key;

# Move to nginx directory
mv /tmp/model.mcli.info-minimal.conf /etc/nginx/conf.d/model.mcli.info.conf

# Test and reload
nginx -t && /etc/init.d/nginx reload
```

**Step 3: Test and Use**

```bash
# Test health endpoint
curl https://model.mcli.info/health

# Use with aider
export OPENAI_API_KEY="your-mcli-api-key"
export OPENAI_API_BASE="https://model.mcli.info/v1"
aider --model prajjwal1/bert-tiny
```

## Documentation Structure

### Quick Reference
- **[QUICK_START_AIDER.md](QUICK_START_AIDER.md)** - Quick commands and common tasks
- **README_MODEL_SERVICE.md** - This file (overview and quick start)

### Deployment Guides
- **[ROUTER_NGINX_SETUP.md](ROUTER_NGINX_SETUP.md)** - Complete router-level nginx setup
- **[ROUTER_SSL_SETUP.md](ROUTER_SSL_SETUP.md)** - Integrating with existing SSL certificates
- **[PUBLIC_MODEL_SERVICE_SETUP.md](PUBLIC_MODEL_SERVICE_SETUP.md)** - Standard setup (nginx on same host)

### Technical Documentation
- **[OPENAI_ADAPTER_IMPLEMENTATION.md](../OPENAI_ADAPTER_IMPLEMENTATION.md)** - Technical implementation details
- **[ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md)** - Standard vs router-level comparison

### Configuration Files
- **[nginx/model.mcli.info.conf](../nginx/model.mcli.info.conf)** - Full nginx config
- **[nginx/model.mcli.info-minimal.conf](../nginx/model.mcli.info-minimal.conf)** - Minimal config for existing SSL
- **[scripts/setup_public_model_service.sh](../scripts/setup_public_model_service.sh)** - Automated setup script

## Network Setup (Your Environment)

### Your Network Topology

```
┌─────────────────────────────────────────┐
│            Internet                      │
└───────────────────┬─────────────────────┘
                    │ HTTPS (443)
                    ↓
┌───────────────────────────────────────────┐
│  Router (192.168.8.1)                     │
│  ┌─────────────────────────────────────┐  │
│  │  Nginx (Port 443)                   │  │
│  │  - SSL Termination                  │  │
│  │  - Reverse Proxy                    │  │
│  │  - Security Headers                 │  │
│  └──────────────┬──────────────────────┘  │
└─────────────────┼─────────────────────────┘
                  │ HTTP (internal network)
                  │ 192.168.8.1 → 192.168.8.100:51234
                  ↓
┌────────────────────────────────────────────┐
│  Host Server (192.168.8.100)              │
│  ┌──────────────────────────────────────┐ │
│  │  Firewall (ufw)                      │ │
│  │  - Allow ONLY from 192.168.8.1:51234│ │
│  │  - Deny all other access             │ │
│  └──────────────┬───────────────────────┘ │
│                 ↓                          │
│  ┌──────────────────────────────────────┐ │
│  │  MCLI Service (0.0.0.0:51234)        │ │
│  │  - OpenAI Adapter                    │ │
│  │  - API Key Auth                      │ │
│  │  - Model Manager                     │ │
│  └──────────────────────────────────────┘ │
└────────────────────────────────────────────┘
```

### Key Network Details

| Component | Location | Configuration |
|-----------|----------|---------------|
| **Router** | 192.168.8.1 | Nginx with SSL, proxy to 192.168.8.100:51234 |
| **Host Server** | 192.168.8.100 | MCLI service on 0.0.0.0:51234 |
| **Firewall** | Host Server | Allow only 192.168.8.1, deny all others |
| **SSL** | Router | Existing certificates in /etc/nginx/ssl/ |
| **API Key** | Both | Generated on host, validated by MCLI |

## Available Commands

### Start Server

```bash
# Local development (localhost only)
mcli model start \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# Production (router-level nginx)
mcli model start \
  --host 0.0.0.0 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

### List Models

```bash
# List available models
mcli model list

# List with details
mcli model list -l
```

### Check Status

```bash
# Check service status
mcli model status

# If using systemd
sudo systemctl status mcli-model

# View logs
sudo journalctl -u mcli-model -f
```

### Stop Server

```bash
# If running in foreground: Ctrl+C

# If running as systemd service
sudo systemctl stop mcli-model

# Or find and kill process
mcli model stop
```

## Available Models

| Model | Parameters | Size | Speed | Use Case |
|-------|-----------|------|-------|----------|
| prajjwal1/bert-tiny | 4.4M | 18 MB | Fastest | Quick responses |
| sshleifer/tiny-distilbert | 22M | 88 MB | Very Fast | Classification |
| microsoft/DialoGPT-tiny | 33M | 132 MB | Fast | Conversation |
| distilbert-base | 66M | 260 MB | Moderate | General purpose |
| microsoft/DialoGPT-small | 117M | 470 MB | Moderate | Better conversation |

## API Endpoints

### Health Check (No Auth)

```bash
GET /health
```

**Example:**
```bash
curl https://model.mcli.info/health
```

**Response:**
```json
{"status": "healthy", "model": "prajjwal1/bert-tiny"}
```

### List Models

```bash
GET /v1/models
Authorization: Bearer YOUR_API_KEY
```

**Example:**
```bash
curl https://model.mcli.info/v1/models \
  -H "Authorization: Bearer $MCLI_API_KEY"
```

**Response:**
```json
{
  "object": "list",
  "data": [
    {
      "id": "prajjwal1/bert-tiny",
      "object": "model",
      "created": 1234567890,
      "owned_by": "mcli"
    }
  ]
}
```

### Chat Completions

```bash
POST /v1/chat/completions
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

**Example:**
```bash
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

**Response:**
```json
{
  "id": "chatcmpl-xxx",
  "object": "chat.completion",
  "created": 1234567890,
  "model": "prajjwal1/bert-tiny",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Response text..."
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 10,
    "completion_tokens": 20,
    "total_tokens": 30
  }
}
```

## Using with Aider

### Local Development

```bash
export OPENAI_API_KEY="your-mcli-api-key"
export OPENAI_API_BASE="http://localhost:51234/v1"
aider --model prajjwal1/bert-tiny
```

### Production

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

Then reload: `source ~/.bashrc`

## Security

### Security Layers

1. **API Key Authentication** - Bearer token required for all API endpoints
2. **SSL/TLS Encryption** - HTTPS via nginx on router
3. **Firewall Restrictions** - Host only accepts connections from router
4. **Network Isolation** - Service bound to specific interface
5. **Rate Limiting** - Prevents abuse (if nginx module available)

### Best Practices

1. **Generate Strong API Keys:**
   ```bash
   openssl rand -hex 32
   ```

2. **Rotate Keys Regularly:**
   - Monthly for development
   - Quarterly for production

3. **Monitor Access:**
   ```bash
   # On host
   sudo journalctl -u mcli-model -f

   # On router
   tail -f /var/log/nginx/model.mcli.info.access.log
   ```

4. **Firewall Configuration:**
   ```bash
   # Critical: Only allow router
   sudo ufw allow from 192.168.8.1 to any port 51234 proto tcp
   sudo ufw deny 51234/tcp
   sudo ufw enable
   ```

5. **Use HTTPS Only:**
   - Never expose HTTP directly to internet
   - SSL termination at router level
   - Internal traffic can be HTTP (on trusted network)

## Troubleshooting

### Service Not Starting

```bash
# Check if port is in use
sudo lsof -i :51234

# Check service logs
sudo journalctl -u mcli-model -n 50

# Check if model is downloaded
mcli model list -d
```

### Can't Connect from Router

```bash
# On host, verify service is listening on 0.0.0.0
sudo netstat -tlnp | grep 51234

# Should show: 0.0.0.0:51234 (not 127.0.0.1)

# Check firewall rules
sudo ufw status verbose

# Test from router
ssh root@192.168.8.1 "curl http://192.168.8.100:51234/health"
```

### SSL Certificate Errors

```bash
# On router, find certificate location
grep -r "ssl_certificate" /etc/nginx/sites-enabled/

# Verify certificate exists
ls -la /etc/nginx/ssl/

# Test nginx config
nginx -t

# Check certificate validity
openssl x509 -in /path/to/cert.crt -text -noout
```

### API Key Not Working

```bash
# Verify API key is set
echo $MCLI_API_KEY

# Test with explicit key
curl https://model.mcli.info/v1/models \
  -H "Authorization: Bearer YOUR_ACTUAL_KEY"

# Check service logs for auth errors
sudo journalctl -u mcli-model | grep -i auth
```

### 502 Bad Gateway

```bash
# Check if MCLI service is running
sudo systemctl status mcli-model

# Check if host is reachable from router
ssh root@192.168.8.1 "ping -c 3 192.168.8.100"

# Verify nginx is proxying to correct IP:port
ssh root@192.168.8.1 "grep proxy_pass /etc/nginx/conf.d/model.mcli.info.conf"

# Should show: http://192.168.8.100:51234
```

## Systemd Service Setup

Create `/etc/systemd/system/mcli-model.service`:

```ini
[Unit]
Description=MCLI Model Service (OpenAI Compatible)
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME
Environment="MCLI_API_KEY=YOUR_API_KEY_HERE"
Environment="PATH=/home/YOUR_USERNAME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/YOUR_USERNAME/.local/bin/mcli model start --host 0.0.0.0 --port 51234 --openai-compatible --api-key "$MCLI_API_KEY"
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcli-model
sudo systemctl start mcli-model
sudo systemctl status mcli-model
```

## Performance Considerations

### Resource Usage

- **RAM:** 500MB - 2GB (depending on model)
- **CPU:** 1-2 cores recommended
- **Disk:** 100MB - 1GB per model
- **Network:** Minimal after model download

### Latency

- **Local:** ~50-200ms (model inference)
- **Router-level:** +1-5ms (network hop)
- **External:** +30-100ms (internet latency)

### Optimization Tips

1. **Use Smaller Models:**
   - `prajjwal1/bert-tiny` for fastest responses
   - Trade-off: accuracy vs speed

2. **Enable GPU (if available):**
   ```bash
   mcli model start --device cuda --openai-compatible
   ```

3. **Monitor Resource Usage:**
   ```bash
   htop
   sudo iotop
   ```

## Implementation Details

### Files Created

- `src/mcli/workflow/model_service/openai_adapter.py` - OpenAI API adapter
- `nginx/model.mcli.info.conf` - Full nginx configuration
- `nginx/model.mcli.info-minimal.conf` - Minimal nginx config
- `scripts/setup_public_model_service.sh` - Automated setup
- `tests/test_openai_adapter.py` - Test suite
- Multiple documentation files (this directory)

### Files Modified

- `src/mcli/app/model_cmd.py` - Added `--host`, `--openai-compatible`, `--api-key` options

### Key Features Implemented

- ✅ OpenAI-compatible `/v1/models` endpoint
- ✅ OpenAI-compatible `/v1/chat/completions` endpoint
- ✅ API key authentication with Bearer tokens
- ✅ Multiple API key support
- ✅ Streaming response support (basic)
- ✅ Request/response validation (Pydantic)
- ✅ Health check endpoint (no auth)
- ✅ CORS support
- ✅ Security headers
- ✅ Comprehensive error handling

## Version History

- **v7.5.0+** - OpenAI adapter implementation
  - Added OpenAI-compatible API endpoints
  - Added API key authentication
  - Added router-level nginx support
  - Comprehensive documentation

## Support and Resources

### Documentation
- This directory contains complete setup guides
- See individual files for specific scenarios

### Testing
```bash
# Run tests
pytest tests/test_openai_adapter.py -v

# With coverage
pytest tests/test_openai_adapter.py --cov
```

### Getting Help
- GitHub Issues: https://github.com/lefv/mcli/issues
- Project README: https://github.com/lefv/mcli

## License

Part of the MCLI project. See LICENSE for details.

---

**Quick Links:**
- [Quick Start Guide](QUICK_START_AIDER.md)
- [Router Setup](ROUTER_NGINX_SETUP.md)
- [SSL Setup](ROUTER_SSL_SETUP.md)
- [Architecture Comparison](ARCHITECTURE_COMPARISON.md)
- [Implementation Details](../OPENAI_ADAPTER_IMPLEMENTATION.md)
