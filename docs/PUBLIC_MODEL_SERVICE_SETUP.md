# Public Model Service Setup Guide

This guide explains how to set up MCLI as a publicly accessible model service with OpenAI-compatible API endpoints, suitable for use with tools like aider.

## Architecture Overview

```
Internet → Nginx (SSL/TLS) → MCLI Model Service (localhost:51234) → AI Models
          (model.mcli.info)     (OpenAI-compatible API with API key auth)
```

## Prerequisites

- A Linux server with public IP address
- Domain name pointing to your server (e.g., model.mcli.info)
- Nginx installed
- Python 3.9+ with MCLI installed
- Certbot for Let's Encrypt SSL certificates

## Step 1: Install Dependencies

```bash
# Install nginx
sudo apt-get update
sudo apt-get install nginx certbot python3-certbot-nginx

# Install MCLI with required dependencies
pip install mcli-framework fastapi uvicorn

# Or if you're developing locally:
cd /path/to/mcli
make install
```

## Step 2: Configure DNS

Point your domain to your server's IP address:

```
A record: model.mcli.info → your.server.ip.address
```

Verify DNS propagation:
```bash
dig model.mcli.info
```

## Step 3: Generate API Key

Generate a secure API key for authentication:

```bash
# Generate a random API key
export MCLI_API_KEY=$(openssl rand -hex 32)
echo "Your API Key: $MCLI_API_KEY"

# Save it securely
echo "MCLI_API_KEY=$MCLI_API_KEY" >> ~/.bashrc
```

## Step 4: Start MCLI Model Service

Start the model service with OpenAI compatibility and authentication:

```bash
# Start with automatic model selection
mcli model start \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"

# Or specify a specific model
mcli model start \
  --model "prajjwal1/bert-tiny" \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

**Important Notes:**
- Use `127.0.0.1` (not `0.0.0.0`) to ensure the service is only accessible via nginx
- The service will auto-download the model if not present
- Keep the API key secure and never commit it to version control

## Step 5: Create Systemd Service (Recommended)

Create a systemd service to manage the model service:

```bash
sudo nano /etc/systemd/system/mcli-model.service
```

Add the following content:

```ini
[Unit]
Description=MCLI Model Service (OpenAI Compatible)
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/home/YOUR_USERNAME
Environment="MCLI_API_KEY=YOUR_API_KEY_HERE"
ExecStart=/home/YOUR_USERNAME/.local/bin/mcli model start --host 127.0.0.1 --port 51234 --openai-compatible --api-key "$MCLI_API_KEY"
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcli-model
sudo systemctl start mcli-model

# Check status
sudo systemctl status mcli-model

# View logs
sudo journalctl -u mcli-model -f
```

## Step 6: Configure Nginx

### 6.1: Setup Rate Limiting

Add rate limiting to nginx main config:

```bash
sudo nano /etc/nginx/nginx.conf
```

Add inside the `http` block:

```nginx
# Rate limiting for API
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/m;
```

### 6.2: Copy Configuration File

```bash
# Copy the nginx configuration
sudo cp nginx/model.mcli.info.conf /etc/nginx/sites-available/model.mcli.info

# Create symlink
sudo ln -s /etc/nginx/sites-available/model.mcli.info /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t
```

## Step 7: Obtain SSL Certificate

Use Let's Encrypt to get a free SSL certificate:

```bash
# Create directory for ACME challenge
sudo mkdir -p /var/www/certbot

# Reload nginx
sudo systemctl reload nginx

# Obtain certificate
sudo certbot certonly --webroot -w /var/www/certbot \
  -d model.mcli.info \
  --email your@email.com \
  --agree-tos \
  --no-eff-email

# Reload nginx with SSL
sudo systemctl reload nginx
```

### Setup Auto-renewal

Certbot automatically adds a cron job. Test renewal:

```bash
sudo certbot renew --dry-run
```

## Step 8: Start Nginx

```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

## Step 9: Test the Setup

### Test Health Endpoint

```bash
curl https://model.mcli.info/health
```

Expected response:
```json
{"status": "healthy", "model": "prajjwal1/bert-tiny"}
```

### Test Models Endpoint (with auth)

```bash
curl https://model.mcli.info/v1/models \
  -H "Authorization: Bearer $MCLI_API_KEY"
```

### Test Chat Completion (with auth)

```bash
curl https://model.mcli.info/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCLI_API_KEY" \
  -d '{
    "model": "prajjwal1/bert-tiny",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ]
  }'
```

## Step 10: Configure Aider

Now you can use the model service with aider:

### On Your Development Machine

```bash
# Set environment variables
export OPENAI_API_KEY="YOUR_MCLI_API_KEY"
export OPENAI_API_BASE="https://model.mcli.info/v1"

# Use with aider
aider --model prajjwal1/bert-tiny

# Or specify directly
aider --model prajjwal1/bert-tiny \
  --openai-api-key "$OPENAI_API_KEY" \
  --openai-api-base "https://model.mcli.info/v1"
```

### Add to Your Shell Profile

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# MCLI Model Service
export OPENAI_API_KEY="your_mcli_api_key_here"
export OPENAI_API_BASE="https://model.mcli.info/v1"
```

## Security Best Practices

1. **API Key Management**
   - Use strong, randomly generated API keys
   - Rotate keys periodically
   - Never commit keys to version control
   - Use environment variables or secret management systems

2. **Network Security**
   - Bind the model service to `127.0.0.1` only
   - Use nginx as the only public-facing interface
   - Enable rate limiting in nginx
   - Consider IP whitelisting for additional security

3. **Firewall Configuration**
   ```bash
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   sudo ufw enable
   ```

4. **Monitoring**
   - Monitor nginx access logs: `/var/log/nginx/model.mcli.info.access.log`
   - Monitor nginx error logs: `/var/log/nginx/model.mcli.info.error.log`
   - Monitor systemd service: `journalctl -u mcli-model -f`

5. **SSL/TLS**
   - Keep certificates up to date (certbot auto-renews)
   - Use strong cipher suites (already configured)
   - Enable HSTS (already configured)

## Advanced Configuration

### Multiple API Keys

To support multiple API keys, modify the start command:

```python
# In your startup script
from mcli.workflow.model_service.openai_adapter import create_openai_adapter

adapter = create_openai_adapter(server, require_auth=True)
adapter.api_key_manager.add_key("key1", name="user1")
adapter.api_key_manager.add_key("key2", name="user2")
```

### Custom Models

To use different models:

```bash
# List available models
mcli model list

# Start with a specific model
mcli model start \
  --model "microsoft/DialoGPT-small" \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

### Load Balancing

For high-traffic scenarios, you can run multiple model service instances:

```nginx
# In nginx config
upstream mcli_backend {
    least_conn;
    server 127.0.0.1:51234;
    server 127.0.0.1:51235;
    server 127.0.0.1:51236;
}

location / {
    proxy_pass http://mcli_backend;
    # ... other proxy settings
}
```

Start multiple instances:
```bash
mcli model start --port 51234 --openai-compatible --api-key "$KEY1"
mcli model start --port 51235 --openai-compatible --api-key "$KEY2"
mcli model start --port 51236 --openai-compatible --api-key "$KEY3"
```

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status mcli-model

# Check logs
sudo journalctl -u mcli-model -n 50 --no-pager

# Check if port is in use
sudo lsof -i :51234
```

### Nginx Errors

```bash
# Test nginx config
sudo nginx -t

# Check error logs
sudo tail -f /var/log/nginx/error.log
```

### Certificate Issues

```bash
# Check certificate
sudo certbot certificates

# Force renewal
sudo certbot renew --force-renewal
```

### Connection Refused

1. Verify service is running: `sudo systemctl status mcli-model`
2. Check nginx is running: `sudo systemctl status nginx`
3. Verify firewall: `sudo ufw status`
4. Check DNS: `dig model.mcli.info`

### API Key Not Working

```bash
# Test without nginx
curl http://127.0.0.1:51234/v1/models \
  -H "Authorization: Bearer $MCLI_API_KEY"

# Check nginx logs for auth errors
sudo tail -f /var/log/nginx/model.mcli.info.error.log
```

## Performance Tuning

### Nginx Workers

```nginx
# /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
```

### Model Service

```bash
# Use GPU if available
mcli model start \
  --device cuda \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

### System Resources

Monitor resource usage:
```bash
# CPU and memory
htop

# Disk I/O
iotop

# Network
iftop
```

## Monitoring and Metrics

### Setup Basic Monitoring

Create a monitoring script:

```bash
#!/bin/bash
# monitor.sh

while true; do
    echo "=== $(date) ==="
    echo "Service Status:"
    systemctl is-active mcli-model

    echo "Request Count (last 5 min):"
    journalctl -u mcli-model --since "5 minutes ago" | grep -c "POST /v1/chat/completions"

    echo "Memory Usage:"
    ps aux | grep "mcli model start" | grep -v grep | awk '{print $4}'

    echo ""
    sleep 300
done
```

### Log Rotation

Ensure logs don't fill up disk:

```bash
# /etc/logrotate.d/nginx
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data adm
    sharedscripts
    postrotate
        [ -f /var/run/nginx.pid ] && kill -USR1 `cat /var/run/nginx.pid`
    endscript
}
```

## Support

For issues or questions:
- GitHub Issues: https://github.com/lefv/mcli/issues
- Documentation: https://github.com/lefv/mcli
- Email: your-email@domain.com

## License

This setup guide is part of the MCLI project. See LICENSE for details.
