#!/bin/bash
# Quick setup script for MCLI Public Model Service
# This script helps automate the setup of MCLI as a public model service

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}MCLI Public Model Service Setup${NC}"
echo -e "${GREEN}========================================${NC}\n"

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root${NC}"
   echo "Run as a regular user with sudo privileges"
   exit 1
fi

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking prerequisites...${NC}"

if ! command_exists nginx; then
    echo -e "${RED}Nginx is not installed. Install it with:${NC}"
    echo "  sudo apt-get install nginx"
    exit 1
fi

if ! command_exists python3; then
    echo -e "${RED}Python 3 is not installed${NC}"
    exit 1
fi

if ! command_exists mcli; then
    echo -e "${RED}MCLI is not installed${NC}"
    echo "Install it with: pip install mcli-framework"
    exit 1
fi

echo -e "${GREEN}✓ All prerequisites met${NC}\n"

# Step 2: Generate API Key
echo -e "${YELLOW}Step 2: Generating API Key...${NC}"

if [ -z "$MCLI_API_KEY" ]; then
    MCLI_API_KEY=$(openssl rand -hex 32)
    echo -e "${GREEN}Generated API Key: $MCLI_API_KEY${NC}"

    # Ask to save to .bashrc
    read -p "Save API key to ~/.bashrc? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "export MCLI_API_KEY=$MCLI_API_KEY" >> ~/.bashrc
        echo -e "${GREEN}✓ API key saved to ~/.bashrc${NC}"
    fi
else
    echo -e "${GREEN}✓ Using existing MCLI_API_KEY from environment${NC}"
fi

echo -e "\n${GREEN}IMPORTANT: Save this API key securely!${NC}"
echo -e "${YELLOW}API Key: $MCLI_API_KEY${NC}\n"

# Step 3: Get domain information
echo -e "${YELLOW}Step 3: Domain configuration...${NC}"

read -p "Enter your domain name (e.g., model.mcli.info): " DOMAIN_NAME

if [ -z "$DOMAIN_NAME" ]; then
    echo -e "${RED}Domain name is required${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Using domain: $DOMAIN_NAME${NC}\n"

# Step 4: Select model
echo -e "${YELLOW}Step 4: Model selection...${NC}"
echo "Available models:"
mcli model list -l 2>/dev/null || echo "  - prajjwal1/bert-tiny (recommended)"

read -p "Enter model name (or press Enter for recommended): " MODEL_NAME

if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME="prajjwal1/bert-tiny"
fi

echo -e "${GREEN}✓ Using model: $MODEL_NAME${NC}\n"

# Step 5: Setup systemd service
echo -e "${YELLOW}Step 5: Creating systemd service...${NC}"

SERVICE_FILE="/tmp/mcli-model.service"
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=MCLI Model Service (OpenAI Compatible)
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment="MCLI_API_KEY=$MCLI_API_KEY"
Environment="PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$(which mcli) model start --model "$MODEL_NAME" --host $BIND_HOST --port 51234 --openai-compatible --api-key "\$MCLI_API_KEY"
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Created systemd service file"
echo -e "${YELLOW}To install the service, run:${NC}"
echo "  sudo cp $SERVICE_FILE /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable mcli-model"
echo "  sudo systemctl start mcli-model"
echo ""

# Step 6: Setup nginx configuration
echo -e "${YELLOW}Step 6: Network architecture...${NC}"
echo "Where is your nginx reverse proxy running?"
echo "  1) On this host server (standard setup)"
echo "  2) On your router (router-level proxy)"
read -p "Select option (1 or 2): " NGINX_LOCATION

if [ "$NGINX_LOCATION" = "2" ]; then
    read -p "Enter this host's internal IP address (e.g., 192.168.8.100): " HOST_IP
    BIND_HOST="0.0.0.0"
    PROXY_TARGET="$HOST_IP:51234"
    echo -e "${YELLOW}⚠️  Router-level setup requires additional firewall configuration!${NC}"
else
    HOST_IP="127.0.0.1"
    BIND_HOST="127.0.0.1"
    PROXY_TARGET="127.0.0.1:51234"
fi

echo -e "${GREEN}✓ Bind host: $BIND_HOST${NC}"
echo -e "${GREEN}✓ Proxy target: $PROXY_TARGET${NC}\n"

echo -e "${YELLOW}Step 7: Creating nginx configuration...${NC}"

NGINX_CONF="/tmp/$DOMAIN_NAME.conf"

cat > "$NGINX_CONF" <<EOF
# Nginx configuration for MCLI Model Service: $DOMAIN_NAME

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name $DOMAIN_NAME;

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$server_name\$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name $DOMAIN_NAME;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES128-GCM-SHA256:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;

    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    access_log /var/log/nginx/$DOMAIN_NAME.access.log;
    error_log /var/log/nginx/$DOMAIN_NAME.error.log;

    location / {
        proxy_pass http://$PROXY_TARGET;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
        proxy_buffering off;
        proxy_request_buffering off;
    }

    location /health {
        proxy_pass http://$PROXY_TARGET/health;
        proxy_set_header Host \$host;
        access_log off;
    }

    location /v1/chat/completions {
        limit_req zone=api_limit burst=5 nodelay;
        proxy_pass http://$PROXY_TARGET/v1/chat/completions;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 600s;
        proxy_buffering off;
        proxy_request_buffering off;
    }
}
EOF

echo "Created nginx configuration file"

if [ "$NGINX_LOCATION" = "2" ]; then
    echo -e "${YELLOW}⚠️  ROUTER-LEVEL SETUP:${NC}"
    echo "1. Copy this config to your router:"
    echo "   scp $NGINX_CONF router:/path/to/nginx/sites-available/"
    echo ""
    echo "2. On this host ($HOST_IP), configure firewall to ONLY allow router:"
    echo "   sudo ufw allow from ROUTER_IP to any port 51234 proto tcp"
    echo "   sudo ufw deny 51234/tcp"
    echo "   sudo ufw enable"
    echo ""
    echo "3. See docs/ROUTER_NGINX_SETUP.md for complete instructions"
    echo ""
else
    echo -e "${YELLOW}To install nginx configuration, run:${NC}"
fi
echo "  sudo mkdir -p /var/www/certbot"
echo "  sudo cp $NGINX_CONF /etc/nginx/sites-available/$DOMAIN_NAME"
echo "  sudo ln -s /etc/nginx/sites-available/$DOMAIN_NAME /etc/nginx/sites-enabled/"
echo ""
echo -e "${YELLOW}Add rate limiting to /etc/nginx/nginx.conf (http block):${NC}"
echo "  limit_req_zone \$binary_remote_addr zone=api_limit:10m rate=10r/m;"
echo ""
echo -e "${YELLOW}Test and reload nginx:${NC}"
echo "  sudo nginx -t"
echo "  sudo systemctl reload nginx"
echo ""

# Step 7: SSL Certificate instructions
echo -e "${YELLOW}Step 7: SSL Certificate setup...${NC}"
read -p "Enter your email for Let's Encrypt: " EMAIL

if [ ! -z "$EMAIL" ]; then
    echo -e "${YELLOW}To obtain SSL certificate, run:${NC}"
    echo "  sudo certbot certonly --webroot -w /var/www/certbot -d $DOMAIN_NAME --email $EMAIL --agree-tos --no-eff-email"
    echo "  sudo systemctl reload nginx"
fi

echo ""

# Step 8: Firewall setup
echo -e "${YELLOW}Step 8: Firewall configuration...${NC}"

if [ "$NGINX_LOCATION" = "2" ]; then
    echo -e "${RED}CRITICAL for router-level setup:${NC}"
    echo "On this host, restrict port 51234 to router only:"
    echo "  sudo ufw allow from ROUTER_IP to any port 51234 proto tcp"
    echo "  sudo ufw deny 51234/tcp"
    echo "  sudo ufw enable"
    echo ""
    echo "Replace ROUTER_IP with your actual router's internal IP"
    echo ""
else
    echo "To configure firewall, run:"
    echo "  sudo ufw allow 80/tcp"
    echo "  sudo ufw allow 443/tcp"
    echo "  sudo ufw enable"
    echo ""
fi

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Setup Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Domain: $DOMAIN_NAME"
echo "Model: $MODEL_NAME"
echo "API Key: $MCLI_API_KEY"
echo ""
echo "Configuration files created:"
echo "  - Systemd service: $SERVICE_FILE"
echo "  - Nginx config: $NGINX_CONF"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Follow the commands above to install the systemd service"
echo "2. Follow the commands above to install nginx configuration"
echo "3. Obtain SSL certificate with certbot"
echo "4. Configure firewall"
echo "5. Test the setup:"
echo "   curl https://$DOMAIN_NAME/health"
echo ""
echo -e "${YELLOW}For aider setup:${NC}"
echo "  export OPENAI_API_KEY=$MCLI_API_KEY"
echo "  export OPENAI_API_BASE=https://$DOMAIN_NAME/v1"
echo "  aider --model $MODEL_NAME"
echo ""
echo -e "${GREEN}See docs/PUBLIC_MODEL_SERVICE_SETUP.md for detailed instructions${NC}"
