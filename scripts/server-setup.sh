#!/bin/bash
set -e

echo "=========================================="
echo "  Ratatoskr Server Setup"
echo "=========================================="

# === System Updates ===
echo "Updating system..."
apt-get update && apt-get upgrade -y

# === Install Docker ===
echo "Installing Docker..."
curl -fsSL https://get.docker.com | sh

# === Verify Docker Compose ===
docker compose version || {
    echo "Installing Docker Compose plugin..."
    apt-get install -y docker-compose-plugin
}

# === Create swap (2GB — helps on small droplets) ===
if [ ! -f /swapfile ]; then
    echo "Creating 2GB swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

# === Firewall ===
echo "Configuring firewall..."
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# === Create app user ===
if ! id "ratatoskr" &>/dev/null; then
    echo "Creating ratatoskr user..."
    useradd -m -s /bin/bash -G docker ratatoskr
fi

# === Create app directory ===
mkdir -p /opt/ratatoskr
chown ratatoskr:ratatoskr /opt/ratatoskr

# === Install git ===
apt-get install -y git

echo ""
echo "=========================================="
echo "  Server setup complete!"
echo ""
echo "  Next steps:"
echo "  1. su - ratatoskr"
echo "  2. cd /opt/ratatoskr"
echo "  3. git clone https://github.com/pmccurry/Ratatoskr-v4.git ."
echo "  4. cp .env.production.example .env"
echo "  5. nano .env  (fill in all values)"
echo "  6. ./scripts/deploy.sh"
echo "=========================================="
