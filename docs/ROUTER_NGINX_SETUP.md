# Router-Level Nginx Setup for MCLI Model Service

This guide is specifically for setups where nginx reverse proxy runs on your **router** (not on the same host as MCLI).

## Architecture

```
Internet
   ↓
Router (nginx with SSL)
   ↓ (internal network)
Host Server (192.168.8.100)
   ↓
MCLI Model Service (0.0.0.0:51234)
```

**Key Differences from Standard Setup:**
- Nginx runs on your router, not on the MCLI host server
- MCLI must bind to `0.0.0.0` or the internal network IP to be accessible from the router
- SSL termination happens at the router level
- Security relies on network-level restrictions

## Prerequisites

- Router with nginx capability (e.g., OPNsense, pfSense, custom router)
- Host server on internal network (e.g., 192.168.8.100)
- Domain pointing to your router's public IP
- SSL certificate on router (Let's Encrypt via ACME)

## Step 1: Identify Your Network Configuration

Find your host server's internal IP:

```bash
# On your host server (where MCLI runs)
hostname -I
# or
ip addr show

# Example output: 192.168.8.100
```

Note down:
- **Host IP**: 192.168.8.100 (your actual IP)
- **Port**: 51234 (MCLI default)
- **Router IP**: 192.168.8.1 (or your router's internal IP)

## Step 2: Start MCLI on Host Server

On your host server (192.168.8.100), start MCLI bound to all interfaces:

```bash
# Generate API key (do this once, save securely)
export MCLI_API_KEY=$(openssl rand -hex 32)
echo "API Key: $MCLI_API_KEY"
echo "export MCLI_API_KEY=$MCLI_API_KEY" >> ~/.bashrc

# Start MCLI bound to all interfaces (so router can reach it)
mcli model start \
  --host 0.0.0.0 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

**Important:** Using `0.0.0.0` makes the service accessible from your internal network. This is necessary for the router to proxy to it.

### Create Systemd Service (Recommended)

```bash
# Create service file
sudo nano /etc/systemd/system/mcli-model.service
```

Add this content (replace YOUR_USERNAME and YOUR_API_KEY):

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

## Step 3: Configure Firewall on Host Server

Since the service is bound to `0.0.0.0`, you need to restrict access to only your router:

```bash
# Allow access only from router IP
sudo ufw allow from 192.168.8.1 to any port 51234 proto tcp

# Deny all other access to this port
sudo ufw deny 51234/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

**This is critical for security!** Without this, any device on your internal network can access the service.

### Alternative: Use iptables

```bash
# Allow only from router
sudo iptables -A INPUT -p tcp -s 192.168.8.1 --dport 51234 -j ACCEPT

# Drop all other connections to this port
sudo iptables -A INPUT -p tcp --dport 51234 -j DROP

# Save rules
sudo iptables-save | sudo tee /etc/iptables/rules.v4
```

## Step 4: Configure Nginx on Router

On your router, add the nginx configuration. The exact method depends on your router:

### For OPNsense/pfSense with nginx plugin:

1. Go to Services → Nginx → Configuration
2. Add a new HTTP server
3. Use the configuration from `nginx/model.mcli.info.conf` but note:
   - Replace `127.0.0.1:51234` with `192.168.8.100:51234`
   - SSL certificates are managed by your router's ACME client

### For Custom Router with nginx:

Copy the configuration file:

```bash
# On your router (adjust paths as needed)
scp nginx/model.mcli.info.conf root@router:/etc/nginx/sites-available/

# Edit to use your host IP
ssh root@router
nano /etc/nginx/sites-available/model.mcli.info.conf
```

**Edit these lines:**
```nginx
# Change from:
proxy_pass http://127.0.0.1:51234;

# To (use your actual host IP):
proxy_pass http://192.168.8.100:51234;
```

**Do this for all proxy_pass directives in the file.**

Enable the site:

```bash
# On router
ln -s /etc/nginx/sites-available/model.mcli.info.conf /etc/nginx/sites-enabled/
nginx -t
systemctl reload nginx
```

## Step 5: SSL Certificate on Router

Configure SSL on your router using its ACME/Let's Encrypt client.

### For OPNsense:

1. Go to Services → Acme Client → Accounts
2. Add Let's Encrypt account
3. Go to Certificates
4. Add certificate for `model.mcli.info`
5. Choose HTTP-01 or DNS-01 challenge
6. Issue certificate
7. In nginx config, reference the certificate

### For pfSense with ACME package:

1. System → Package Manager → Install ACME
2. Services → Acme → Accounts (add Let's Encrypt)
3. Services → Acme → Certificates
4. Add certificate for `model.mcli.info`
5. Issue and install

### For Custom Router:

```bash
# Install certbot
apt-get install certbot

# Obtain certificate (HTTP challenge)
certbot certonly --standalone \
  -d model.mcli.info \
  --preferred-challenges http \
  --email your@email.com

# Certificate will be at:
# /etc/letsencrypt/live/model.mcli.info/fullchain.pem
# /etc/letsencrypt/live/model.mcli.info/privkey.pem
```

## Step 6: Test the Setup

### Test from Host Server (Internal)

```bash
# From the host server (192.168.8.100)
curl http://192.168.8.100:51234/health
```

Expected: `{"status": "healthy", "model": "prajjwal1/bert-tiny"}`

### Test from Router (Internal)

```bash
# From router
curl http://192.168.8.100:51234/health
```

Should also work if firewall rules are correct.

### Test from Internet (External)

```bash
# From any external machine
curl https://model.mcli.info/health
```

Expected: `{"status": "healthy", "model": "prajjwal1/bert-tiny"}`

### Test with Authentication

```bash
# Test models endpoint
curl https://model.mcli.info/v1/models \
  -H "Authorization: Bearer $MCLI_API_KEY"

# Test chat completion
curl https://model.mcli.info/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $MCLI_API_KEY" \
  -d '{
    "model": "prajjwal1/bert-tiny",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Step 7: Use with Aider

On your development machine:

```bash
# Set environment variables
export OPENAI_API_KEY="your-mcli-api-key"
export OPENAI_API_BASE="https://model.mcli.info/v1"

# Use with aider
aider --model prajjwal1/bert-tiny
```

## Security Considerations for Router-Level Setup

### Network-Level Security

1. **Firewall on Host Server** (CRITICAL)
   - Only allow router IP to access port 51234
   - Block all other internal network devices
   - Monitor firewall logs

2. **Router Firewall Rules**
   - Only forward 80/443 to the proxy
   - Don't expose port 51234 directly to internet
   - Consider IP whitelisting at router level

3. **Internal Network Isolation**
   - Consider VLANs to isolate the host server
   - Use separate network for services vs. user devices
   - Monitor internal network traffic

### Application-Level Security

1. **API Key Management**
   - Use strong random keys
   - Rotate keys regularly
   - Different keys per environment/user
   - Monitor key usage

2. **Rate Limiting**
   - Configure at nginx level (router)
   - Monitor for abuse
   - Consider per-IP and per-key limits

3. **Logging and Monitoring**
   - Host server logs: `journalctl -u mcli-model -f`
   - Router nginx logs: check your router's log location
   - Monitor for unusual patterns

## Troubleshooting Router-Level Setup

### Service not accessible from router

```bash
# On host server, check if service is listening
sudo netstat -tlnp | grep 51234

# Should show: 0.0.0.0:51234 (not 127.0.0.1:51234)

# Test from router
curl http://192.168.8.100:51234/health

# Check firewall
sudo ufw status
sudo iptables -L -n | grep 51234
```

### Router can't reach host

```bash
# From router, ping host
ping 192.168.8.100

# From router, test port
telnet 192.168.8.100 51234
# or
nc -zv 192.168.8.100 51234

# Check host firewall rules
sudo ufw status verbose
```

### SSL certificate issues on router

- Verify domain DNS points to router's public IP
- Check router's ACME client logs
- Ensure ports 80/443 are forwarded to router
- Try manual certificate renewal

### 502 Bad Gateway from nginx

```bash
# Check nginx error logs on router
tail -f /var/log/nginx/error.log

# Common causes:
# 1. MCLI service not running on host
sudo systemctl status mcli-model

# 2. Wrong IP in nginx config
# Verify nginx config has correct host IP (192.168.8.100)

# 3. Firewall blocking
sudo ufw status

# 4. Service crashed
journalctl -u mcli-model -n 50
```

### Can access internally but not externally

1. Verify DNS: `dig model.mcli.info` should show your public IP
2. Check router port forwarding: 80/443 → router nginx
3. Check router's public firewall: allow 80/443 inbound
4. Verify SSL certificate is valid: `openssl s_client -connect model.mcli.info:443`

## Network Diagram

```
┌─────────────────────────────────────────────────────┐
│                    Internet                          │
└───────────────────────┬─────────────────────────────┘
                        │
                        │ HTTPS (443)
                        ↓
        ┌───────────────────────────────┐
        │  Router (Public IP)           │
        │  - Nginx Reverse Proxy        │
        │  - SSL Termination            │
        │  - Rate Limiting              │
        │  - Firewall                   │
        └──────────┬────────────────────┘
                   │
                   │ HTTP (internal network)
                   │ 192.168.8.1 → 192.168.8.100:51234
                   ↓
        ┌───────────────────────────────┐
        │  Host Server (192.168.8.100)  │
        │  - Firewall (ufw/iptables)    │
        │    Allow only from 192.168.8.1│
        │  - MCLI Service (0.0.0.0:51234)│
        │    - OpenAI Adapter           │
        │    - API Key Auth             │
        │    - Model Manager            │
        └───────────────────────────────┘
```

## Configuration Summary

| Component | Location | Key Configuration |
|-----------|----------|------------------|
| MCLI Service | Host Server (192.168.8.100) | `--host 0.0.0.0 --port 51234` |
| Nginx Proxy | Router | `proxy_pass http://192.168.8.100:51234` |
| SSL Certificate | Router | Let's Encrypt via ACME |
| Firewall | Host Server | Allow only from router IP |
| API Keys | Host Server | Environment variable |
| DNS | External | A record → Router public IP |

## Monitoring Commands

### On Host Server

```bash
# Service status
sudo systemctl status mcli-model

# Live logs
journalctl -u mcli-model -f

# Resource usage
htop
ps aux | grep mcli

# Network connections
sudo netstat -an | grep 51234
```

### On Router

```bash
# Nginx status
systemctl status nginx

# Nginx logs
tail -f /var/log/nginx/model.mcli.info.access.log
tail -f /var/log/nginx/model.mcli.info.error.log

# Active connections
netstat -an | grep :443
```

## Advanced: Multiple Host Servers

If you want to load balance across multiple host servers:

```nginx
# On router nginx config
upstream mcli_backend {
    least_conn;
    server 192.168.8.100:51234;
    server 192.168.8.101:51234;
    server 192.168.8.102:51234;
}

location / {
    proxy_pass http://mcli_backend;
    # ... other proxy settings
}
```

Start MCLI on each host with the same configuration and API keys.

## Quick Reference Card

```bash
# On Host Server (192.168.8.100)
# Start service
mcli model start --host 0.0.0.0 --port 51234 --openai-compatible --api-key "$KEY"

# Check status
sudo systemctl status mcli-model

# View logs
journalctl -u mcli-model -f

# Test locally
curl http://192.168.8.100:51234/health

# On Router
# Test from router to host
curl http://192.168.8.100:51234/health

# Reload nginx
systemctl reload nginx

# Check nginx logs
tail -f /var/log/nginx/error.log

# From Development Machine
# Test external access
curl https://model.mcli.info/health

# Use with aider
export OPENAI_API_KEY="your-key"
export OPENAI_API_BASE="https://model.mcli.info/v1"
aider --model prajjwal1/bert-tiny
```

## Support

For issues specific to router-level setup:
- Verify network connectivity between router and host
- Check firewall rules on both router and host
- Ensure correct IP addresses in all configurations
- Monitor logs on both systems

See also:
- [PUBLIC_MODEL_SERVICE_SETUP.md](PUBLIC_MODEL_SERVICE_SETUP.md) - General setup guide
- [QUICK_START_AIDER.md](QUICK_START_AIDER.md) - Quick reference
- [OPENAI_ADAPTER_IMPLEMENTATION.md](OPENAI_ADAPTER_IMPLEMENTATION.md) - Technical details
