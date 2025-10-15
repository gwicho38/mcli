# Architecture Comparison: Standard vs Router-Level Nginx

This document compares the two deployment architectures for MCLI model service.

## Standard Setup (Nginx on Same Host)

### Architecture Diagram

```
┌─────────────────────┐
│     Internet        │
└──────────┬──────────┘
           │ HTTPS (443)
           ↓
┌────────────────────────────────┐
│  Single Host Server            │
│                                │
│  ┌──────────────────────────┐ │
│  │  Nginx (Port 443)        │ │
│  │  - SSL Termination       │ │
│  │  - Reverse Proxy         │ │
│  │  - Rate Limiting         │ │
│  └──────────┬───────────────┘ │
│             │ HTTP (localhost) │
│             ↓                  │
│  ┌──────────────────────────┐ │
│  │  MCLI Service            │ │
│  │  (127.0.0.1:51234)       │ │
│  │  - OpenAI Adapter        │ │
│  │  - API Key Auth          │ │
│  │  - Model Manager         │ │
│  └──────────────────────────┘ │
└────────────────────────────────┘
```

### Configuration

**MCLI Service:**
```bash
mcli model start \
  --host 127.0.0.1 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

**Nginx Config:**
```nginx
location / {
    proxy_pass http://127.0.0.1:51234;
    # ...
}
```

**Firewall:**
```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Pros
- ✅ Simpler setup
- ✅ Everything on one machine
- ✅ Easier to debug
- ✅ No network exposure on internal network
- ✅ Lower latency (no network hops)

### Cons
- ❌ Single point of failure
- ❌ Can't easily load balance
- ❌ All SSL processing on one machine
- ❌ Can't reuse existing router infrastructure

### Best For
- Small deployments
- Development/testing
- Single-server setups
- When you have full control of the host

---

## Router-Level Setup (Nginx on Router)

### Architecture Diagram

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
│  │  - Rate Limiting                    │  │
│  │  - Firewall Rules                   │  │
│  └──────────────┬──────────────────────┘  │
└─────────────────┼─────────────────────────┘
                  │ HTTP (internal network)
                  │ 192.168.8.1 → 192.168.8.100:51234
                  ↓
┌────────────────────────────────────────────┐
│  Host Server (192.168.8.100)              │
│  ┌──────────────────────────────────────┐ │
│  │  Firewall (ufw/iptables)             │ │
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

### Configuration

**MCLI Service (on host 192.168.8.100):**
```bash
mcli model start \
  --host 0.0.0.0 \
  --port 51234 \
  --openai-compatible \
  --api-key "$MCLI_API_KEY"
```

**Nginx Config (on router):**
```nginx
location / {
    proxy_pass http://192.168.8.100:51234;
    # ...
}
```

**Firewall (on host):**
```bash
# CRITICAL: Only allow router
sudo ufw allow from 192.168.8.1 to any port 51234 proto tcp
sudo ufw deny 51234/tcp
sudo ufw enable
```

### Pros
- ✅ Centralized SSL management
- ✅ Can serve multiple services
- ✅ Reuse existing router infrastructure
- ✅ Easy to add multiple backend hosts
- ✅ Router handles all external security
- ✅ Can isolate services with VLANs

### Cons
- ❌ More complex setup
- ❌ Network latency (additional hop)
- ❌ Must configure firewall on host
- ❌ Service exposed on internal network (with restrictions)
- ❌ More points of failure
- ❌ Harder to debug

### Best For
- Existing router-based infrastructure
- Multiple services behind one proxy
- Network-segregated environments
- When you want centralized SSL management
- Load balancing across multiple hosts

---

## Feature Comparison Table

| Feature | Standard Setup | Router-Level Setup |
|---------|---------------|-------------------|
| **Setup Complexity** | Simple | Moderate |
| **Components** | 1 (host) | 2 (router + host) |
| **SSL Management** | On host | On router |
| **MCLI Bind Address** | 127.0.0.1 | 0.0.0.0 |
| **Nginx Location** | Same host | Router |
| **Firewall Rules** | Allow 80/443 | Restrict 51234 to router only |
| **Network Exposure** | None (localhost) | Internal network (restricted) |
| **Latency** | Lowest | +1 network hop |
| **Load Balancing** | Harder | Easier |
| **Debugging** | Easier | Harder |
| **Security Layers** | 2 (Nginx + API key) | 3 (Router FW + Host FW + API key) |
| **SSL Certificates** | On host (certbot) | On router (ACME) |
| **Suitable For** | Single server | Multiple services |

---

## Security Comparison

### Standard Setup Security Layers

1. **External Firewall**: Only 80/443 open to internet
2. **Nginx**: Reverse proxy, rate limiting, SSL
3. **Localhost Binding**: Service not accessible from network
4. **API Key**: Application-level authentication

**Threat Model:**
- ✅ Protected from external network attacks
- ✅ Protected from internal network (localhost only)
- ✅ SSL/TLS encryption
- ✅ Rate limiting
- ❌ Single machine compromise = full compromise

### Router-Level Security Layers

1. **Router Firewall**: Only 80/443 forwarded to nginx
2. **Nginx on Router**: Reverse proxy, rate limiting, SSL
3. **Internal Network**: Unencrypted but isolated
4. **Host Firewall**: Only accepts connections from router
5. **API Key**: Application-level authentication

**Threat Model:**
- ✅ Protected from external network attacks
- ✅ Protected from internal network (firewall)
- ✅ SSL/TLS encryption (to router)
- ✅ Rate limiting at router
- ✅ Network segmentation possible
- ⚠️ Internal traffic unencrypted (between router and host)
- ⚠️ Must secure router and host separately

---

## Performance Comparison

### Standard Setup

**Latency:**
```
Client → Router → Host (Nginx) → Host (MCLI)
  ^        ^         ^              ^
  30ms     <1ms     <1ms          50-200ms
```
Total: ~80-230ms

**Throughput:**
- Limited by single host resources
- No network bottleneck (localhost)
- CPU-bound on model inference

### Router-Level Setup

**Latency:**
```
Client → Router (Nginx) → Host (MCLI)
  ^        ^                ^
  30ms     1-5ms          50-200ms
```
Total: ~81-235ms

**Throughput:**
- Limited by internal network bandwidth (usually gigabit)
- Can distribute across multiple hosts
- Nginx on router can become bottleneck

**Difference:** ~1-5ms additional latency for internal network hop

---

## Configuration Examples

### Standard Setup Quick Start

```bash
# On single host
# 1. Generate API key
export MCLI_API_KEY=$(openssl rand -hex 32)

# 2. Install nginx
sudo apt-get install nginx certbot python3-certbot-nginx

# 3. Start MCLI
mcli model start --host 127.0.0.1 --openai-compatible --api-key "$KEY"

# 4. Configure nginx (see PUBLIC_MODEL_SERVICE_SETUP.md)

# 5. Get SSL certificate
sudo certbot --nginx -d model.mcli.info

# 6. Configure firewall
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### Router-Level Quick Start

```bash
# On host server (192.168.8.100)
# 1. Generate API key
export MCLI_API_KEY=$(openssl rand -hex 32)

# 2. Start MCLI
mcli model start --host 0.0.0.0 --openai-compatible --api-key "$KEY"

# 3. Configure firewall (CRITICAL!)
sudo ufw allow from 192.168.8.1 to any port 51234 proto tcp
sudo ufw deny 51234/tcp
sudo ufw enable

# On router
# 4. Configure nginx to proxy to 192.168.8.100:51234
# 5. Configure SSL on router (via router's ACME/Let's Encrypt)
# 6. Configure router firewall to allow 80/443

# See ROUTER_NGINX_SETUP.md for details
```

---

## Troubleshooting by Architecture

### Standard Setup Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| 502 Bad Gateway | MCLI not running | `systemctl status mcli-model` |
| SSL errors | Certificate issue | `certbot renew` |
| Connection refused | Firewall blocking | `ufw status` |
| Can't access externally | DNS or port forwarding | Check DNS, router settings |

### Router-Level Issues

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| 502 Bad Gateway | Host unreachable | Ping 192.168.8.100 from router |
| Connection timeout | Firewall on host | Check ufw rules on host |
| Works internally, not externally | Router SSL/port issue | Check router nginx config |
| SSL errors | Router certificate | Check router ACME setup |
| Slow performance | Network latency | Check internal network speed |

---

## Migration Between Architectures

### From Standard to Router-Level

1. **Update MCLI service:**
   ```bash
   # Change from
   --host 127.0.0.1
   # To
   --host 0.0.0.0
   ```

2. **Add firewall rules:**
   ```bash
   sudo ufw allow from 192.168.8.1 to any port 51234 proto tcp
   sudo ufw deny 51234/tcp
   ```

3. **Move nginx config to router**

4. **Update nginx config:**
   - Change `127.0.0.1:51234` to `192.168.8.100:51234`

5. **Move SSL certificates to router**

### From Router-Level to Standard

1. **Update MCLI service:**
   ```bash
   # Change from
   --host 0.0.0.0
   # To
   --host 127.0.0.1
   ```

2. **Remove firewall restrictions:**
   ```bash
   sudo ufw delete allow from 192.168.8.1 to any port 51234 proto tcp
   sudo ufw allow 80/tcp
   sudo ufw allow 443/tcp
   ```

3. **Install nginx on host**

4. **Update nginx config:**
   - Change `192.168.8.100:51234` to `127.0.0.1:51234`

5. **Move SSL certificates to host**

---

## Recommendation

### Choose Standard Setup If:
- You have a single dedicated server
- You want simplicity
- You're testing/developing
- You don't have an advanced router
- You want the lowest latency

### Choose Router-Level Setup If:
- You already have nginx on your router
- You serve multiple services
- You want to add more hosts later
- Your router is powerful (OPNsense/pfSense)
- You want centralized SSL management
- You want network segmentation (VLANs)

---

## Documentation References

- **Standard Setup**: [PUBLIC_MODEL_SERVICE_SETUP.md](PUBLIC_MODEL_SERVICE_SETUP.md)
- **Router-Level Setup**: [ROUTER_NGINX_SETUP.md](ROUTER_NGINX_SETUP.md)
- **Quick Start**: [QUICK_START_AIDER.md](QUICK_START_AIDER.md)
- **Implementation**: [OPENAI_ADAPTER_IMPLEMENTATION.md](../OPENAI_ADAPTER_IMPLEMENTATION.md)

---

## Summary

Both architectures are fully supported and production-ready. The choice depends on your infrastructure and requirements:

- **Standard** = Simpler, lower latency, single machine
- **Router-Level** = More flexible, centralized, scalable

The automated setup script (`scripts/setup_public_model_service.sh`) supports both architectures and will guide you through the appropriate configuration.
