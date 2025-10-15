# Router SSL Setup for MCLI Model Service

This guide is for scenarios where you already have SSL certificates managed at the router level.

## Your Scenario

✅ You already have SSL working on your router
✅ Certificates exist in `/etc/nginx/` or similar
✅ You just need to add MCLI as a new service

## Common Router SSL Setups

### Option 1: Individual Certificates per Domain

```
/etc/nginx/ssl/
├── model.mcli.info.crt
├── model.mcli.info.key
├── other-service.mcli.info.crt
└── other-service.mcli.info.key
```

**Nginx Config:**
```nginx
ssl_certificate /etc/nginx/ssl/model.mcli.info.crt;
ssl_certificate_key /etc/nginx/ssl/model.mcli.info.key;
```

### Option 2: Wildcard Certificate

```
/etc/nginx/ssl/
├── wildcard.mcli.info.crt
└── wildcard.mcli.info.key
```

**Nginx Config:**
```nginx
ssl_certificate /etc/nginx/ssl/wildcard.mcli.info.crt;
ssl_certificate_key /etc/nginx/ssl/wildcard.mcli.info.key;
```

### Option 3: Centralized Certificate Directory

```
/etc/nginx/certificates/
├── mcli.info/
│   ├── fullchain.pem
│   └── privkey.pem
```

**Nginx Config:**
```nginx
ssl_certificate /etc/nginx/certificates/mcli.info/fullchain.pem;
ssl_certificate_key /etc/nginx/certificates/mcli.info/privkey.pem;
```

## Find Your SSL Certificate Location

On your router:

```bash
# Find SSL certificates
find /etc/nginx -name "*.crt" -o -name "*.pem" -o -name "*.key" | head -20

# Check existing nginx configs to see the pattern
grep -r "ssl_certificate" /etc/nginx/

# Common locations
ls -la /etc/nginx/ssl/
ls -la /etc/nginx/certificates/
ls -la /etc/letsencrypt/live/
```

## Setup Steps

### Step 1: Determine Your Certificate Location

```bash
# SSH to your router
ssh router

# Find where certificates are stored
grep -r "ssl_certificate" /etc/nginx/sites-enabled/ | head -5

# Example output might show:
# ssl_certificate /etc/nginx/ssl/example.com.crt;
```

### Step 2: Choose the Right Config File

We provide two nginx config files:

1. **nginx/model.mcli.info.conf** - Full config with HTTP redirect and ACME support
2. **nginx/model.mcli.info-minimal.conf** - Minimal config for existing SSL setups ✅ USE THIS

For your setup, use the **minimal config** and update the SSL paths.

### Step 3: Update SSL Certificate Paths

Edit the config to match your certificate location:

```bash
# Copy minimal config
cp nginx/model.mcli.info-minimal.conf /tmp/model.mcli.info.conf

# Edit SSL paths
nano /tmp/model.mcli.info.conf
```

**Update these lines:**
```nginx
# Change from:
ssl_certificate /etc/nginx/ssl/model.mcli.info.crt;
ssl_certificate_key /etc/nginx/ssl/model.mcli.info.key;

# To match your actual location, for example:
ssl_certificate /etc/nginx/certificates/model.mcli.info/fullchain.pem;
ssl_certificate_key /etc/nginx/certificates/model.mcli.info/privkey.pem;
```

### Step 4: Add Certificate for model.mcli.info

If you're using your router's ACME/Let's Encrypt client:

#### For OPNsense:
1. Services → Acme Client → Certificates
2. Add new certificate
3. Domain: `model.mcli.info`
4. Use existing account
5. Issue certificate

#### For pfSense:
1. Services → Acme → Certificates
2. Add new certificate
3. Domain Names: `model.mcli.info`
4. Issue

#### For Custom Router with Certbot:
```bash
# If using standalone
certbot certonly --standalone -d model.mcli.info

# If using webroot (more common with nginx)
certbot certonly --webroot -w /var/www/html -d model.mcli.info

# If using DNS challenge
certbot certonly --dns-cloudflare -d model.mcli.info
```

#### For Wildcard Certificate:

If you already have `*.mcli.info`, you don't need a new certificate! Just use the existing one:

```nginx
ssl_certificate /etc/nginx/ssl/wildcard.mcli.info.crt;
ssl_certificate_key /etc/nginx/ssl/wildcard.mcli.info.key;
```

### Step 5: Install and Enable Config

```bash
# On router
# Copy config
scp /tmp/model.mcli.info.conf router:/etc/nginx/sites-available/

# Enable
ssh router
cd /etc/nginx/sites-enabled
ln -s ../sites-available/model.mcli.info.conf .

# Test config
nginx -t

# If OK, reload
nginx -s reload
# or
systemctl reload nginx
```

### Step 6: Verify

```bash
# Test from router
curl -k https://localhost/health -H "Host: model.mcli.info"

# Test externally
curl https://model.mcli.info/health

# Check SSL certificate
openssl s_client -connect model.mcli.info:443 -servername model.mcli.info
```

## Rate Limiting Setup

Add to `/etc/nginx/nginx.conf` in the `http` block:

```nginx
http {
    # ... existing config ...

    # Rate limiting for API endpoints
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/m;

    # ... rest of config ...
}
```

Then reload nginx:
```bash
nginx -t && nginx -s reload
```

## Example Configurations

### Example 1: Using Existing Wildcard Certificate

```nginx
server {
    listen 443 ssl http2;
    server_name model.mcli.info;

    # Use existing wildcard certificate
    ssl_certificate /etc/nginx/ssl/wildcard.mcli.info.crt;
    ssl_certificate_key /etc/nginx/ssl/wildcard.mcli.info.key;

    location / {
        proxy_pass http://192.168.8.100:51234;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Example 2: Domain-Specific Certificate

```nginx
server {
    listen 443 ssl http2;
    server_name model.mcli.info;

    # Domain-specific certificate
    ssl_certificate /etc/nginx/certificates/model.mcli.info/fullchain.pem;
    ssl_certificate_key /etc/nginx/certificates/model.mcli.info/privkey.pem;

    location / {
        proxy_pass http://192.168.8.100:51234;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Troubleshooting

### SSL Certificate Errors

```bash
# Check certificate validity
openssl x509 -in /etc/nginx/ssl/model.mcli.info.crt -text -noout

# Check if certificate matches key
openssl x509 -noout -modulus -in /etc/nginx/ssl/model.mcli.info.crt | openssl md5
openssl rsa -noout -modulus -in /etc/nginx/ssl/model.mcli.info.key | openssl md5
# These should match

# Check certificate expiry
openssl x509 -in /etc/nginx/ssl/model.mcli.info.crt -noout -enddate
```

### Nginx Config Errors

```bash
# Test config
nginx -t

# Check for specific errors
nginx -T | grep -A 5 "model.mcli.info"

# Verify file permissions
ls -la /etc/nginx/ssl/model.mcli.info.*
# Should be readable by nginx user
```

### Certificate Not Found

```bash
# List all certificates
find /etc/nginx -name "*.crt" -o -name "*.pem"
find /etc/letsencrypt -name "*.pem" 2>/dev/null

# Check nginx error logs
tail -f /var/log/nginx/error.log
```

### Wrong Certificate Served

```bash
# Test which certificate is being served
echo | openssl s_client -connect model.mcli.info:443 -servername model.mcli.info 2>/dev/null | openssl x509 -noout -subject -issuer -dates

# Check server_name in nginx config
nginx -T | grep -B 5 "ssl_certificate.*model.mcli.info"
```

## Common Patterns

### Pattern 1: All Services Use One Wildcard

If you have `*.mcli.info` certificate:

```nginx
# All services can use the same certificate
ssl_certificate /etc/nginx/ssl/wildcard.mcli.info.crt;
ssl_certificate_key /etc/nginx/ssl/wildcard.mcli.info.key;
```

Just add `model.mcli.info` DNS record and use the wildcard cert.

### Pattern 2: Certificate Per Service

If you create a new certificate for each service:

```bash
# On router, request new certificate
certbot certonly --webroot -w /var/www/html -d model.mcli.info

# Use in nginx
ssl_certificate /etc/letsencrypt/live/model.mcli.info/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/model.mcli.info/privkey.pem;
```

### Pattern 3: Shared Certificate Directory

If your router manages certificates centrally:

```nginx
# Point to centralized location
ssl_certificate /etc/nginx/certificates/mcli.info/cert.pem;
ssl_certificate_key /etc/nginx/certificates/mcli.info/key.pem;
```

## Quick Reference

```bash
# Find current SSL setup
grep -r "ssl_certificate" /etc/nginx/sites-enabled/

# Copy minimal config
scp nginx/model.mcli.info-minimal.conf router:/etc/nginx/sites-available/model.mcli.info.conf

# Edit SSL paths to match your setup
ssh router
nano /etc/nginx/sites-available/model.mcli.info.conf

# Enable
ln -s /etc/nginx/sites-available/model.mcli.info.conf /etc/nginx/sites-enabled/

# Test and reload
nginx -t && nginx -s reload

# Verify
curl https://model.mcli.info/health
```

## Complete Example

Here's a complete working example assuming wildcard certificate at `/etc/nginx/ssl/`:

```nginx
server {
    listen 443 ssl http2;
    server_name model.mcli.info;

    # Wildcard certificate
    ssl_certificate /etc/nginx/ssl/wildcard.mcli.info.crt;
    ssl_certificate_key /etc/nginx/ssl/wildcard.mcli.info.key;

    # SSL settings
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Proxy to MCLI on host
    location / {
        proxy_pass http://192.168.8.100:51234;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
    }

    location /health {
        proxy_pass http://192.168.8.100:51234/health;
        access_log off;
    }
}

server {
    listen 80;
    server_name model.mcli.info;
    return 301 https://$server_name$request_uri;
}
```

Save this, enable it, reload nginx, done! 🚀

## Related Documentation

- [ROUTER_NGINX_SETUP.md](ROUTER_NGINX_SETUP.md) - Full router setup guide
- [ARCHITECTURE_COMPARISON.md](ARCHITECTURE_COMPARISON.md) - Architecture comparison
- [QUICK_START_AIDER.md](QUICK_START_AIDER.md) - Quick reference
