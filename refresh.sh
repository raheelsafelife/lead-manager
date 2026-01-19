#!/bin/bash

# ==============================================================================
# Lead Manager: Universal "Clean Slate" Refresh Script
# ==============================================================================
# This script resolves Docker conflicts, "KeyError: ContainerConfig",
# and stuck containers by performing a deep cleanup before restarting.

echo "🚀 Starting Universal Docker Refresh..."

# 1. Stop and remove all containers for this project
echo "🛑 Stopping existing services..."
docker compose down --remove-orphans 2>/dev/null || docker-compose down --remove-orphans 2>/dev/null

# 2. Force cleanup of any containers matching the project prefix
# This catches containers that docker-compose might miss due to state mismatches
echo "🧹 Clearing trapped containers..."
PROJECT_NAME=$(basename $(pwd))
STUCK_CONTAINERS=$(docker ps -a -q --filter "name=${PROJECT_NAME}")
if [ ! -z "$STUCK_CONTAINERS" ]; then
    docker rm -f $STUCK_CONTAINERS
fi

# 3. Prune dangling resources to clear metadata errors (KeyError fix)
echo "💎 Pruning system metadata..."
docker system prune -f --volumes

# 4. Pull latest changes if on AWS (optional, but helpful)
if [ -d ".git" ]; then
    echo "📥 Pulling latest code from Git..."
    git pull origin main
fi

# 5. Build and Start using the modern Compose V2
echo "🏗️  Rebuilding and Starting services (Background)..."
docker compose up -d --build

echo "✅ Refresh Complete! Your app is starting at https://ccpleads.safelifehomehealth.com/"
echo "Check logs with: docker compose logs -f"
