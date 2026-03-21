#!/bin/bash
set -e

echo "=========================================="
echo "  AI Sale Agent — Deploy"
echo "=========================================="
echo ""

# --- Detect OS ---
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_ID=$ID
else
    OS_ID="unknown"
fi
echo "OS: $PRETTY_NAME"

# --- 1. Swap (if RAM < 1GB) ---
TOTAL_MEM=$(grep MemTotal /proc/meminfo | awk '{print $2}')
if [ "$TOTAL_MEM" -lt 1048576 ] && [ ! -f /swapfile ]; then
    echo "[1/6] RAM < 1GB, creating 2GB swap..."
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "  Swap created: 2GB"
else
    echo "[1/6] Memory OK ($(( TOTAL_MEM / 1024 )) MB RAM)"
fi

# --- 2. Docker ---
if ! command -v docker &> /dev/null; then
    echo "[2/6] Installing Docker..."
    if [[ "$OS_ID" == "ubuntu" || "$OS_ID" == "debian" ]]; then
        apt-get update -qq
        apt-get install -y -qq ca-certificates curl gnupg
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null
        apt-get update -qq
        apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    elif [[ "$OS_ID" == "almalinux" || "$OS_ID" == "centos" || "$OS_ID" == "rocky" || "$OS_ID" == "rhel" || "$OS_ID" == "fedora" ]]; then
        dnf install -y dnf-plugins-core
        dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
        dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        systemctl start docker
        systemctl enable docker
    else
        echo "ERROR: Unsupported OS ($OS_ID). Install Docker manually."
        exit 1
    fi
    echo "  Docker installed"
else
    echo "[2/6] Docker OK: $(docker --version | head -1)"
fi

# --- 3. Docker Compose check ---
if docker compose version &> /dev/null; then
    echo "[3/6] Docker Compose OK"
else
    echo "[3/6] ERROR: docker compose not found!"
    exit 1
fi

# --- 4. .env check ---
if [ ! -f .env ]; then
    echo "[4/6] ERROR: .env not found! Run: cp .env.example .env"
    exit 1
else
    echo "[4/6] .env found"
fi

# --- 5. Build & Start ---
mkdir -p logs chroma_data

echo "[5/6] Building and starting containers..."
docker compose down --remove-orphans 2>/dev/null || true
docker compose build
docker compose up -d

echo ""

# --- 6. Health check ---
echo "[6/6] Waiting for services..."
sleep 15

MAX_ATTEMPTS=12
for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -sf http://localhost/api/health > /dev/null 2>&1; then
        echo ""
        echo "=========================================="
        echo "  DEPLOY SUCCESS!"
        echo "=========================================="
        echo ""
        docker compose ps --format "table {{.Name}}\t{{.Status}}"
        echo ""
        SERVER_IP=$(hostname -I | awk '{print $1}')
        echo "  Widget:  http://${SERVER_IP}"
        echo "  API:     http://${SERVER_IP}/api/health"
        echo "  Logs:    docker compose logs -f"
        echo ""
        exit 0
    fi
    echo "  Attempt $i/$MAX_ATTEMPTS — waiting..."
    sleep 10
done

echo "WARNING: Health check failed. Check logs:"
echo "  docker compose logs backend"
docker compose ps
