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

# 2. Clear stray local databases that cause migration confusion on AWS host
echo "🧹 Cleaning stray database files..."
rm -f leads.db backend/leads.db backend/Leads.db 2>/dev/null
# Keep ./data/leads.db as it is the persistent one
# This catches containers that docker-compose might miss due to state mismatches
echo "🧹 Clearing trapped containers..."
PROJECT_NAME=$(basename $(pwd))
STUCK_CONTAINERS=$(docker ps -a -q --filter "name=${PROJECT_NAME}")
if [ ! -z "$STUCK_CONTAINERS" ]; then
    docker rm -f $STUCK_CONTAINERS
fi

# 3. Prune dangling resources to clear metadata errors (KeyError fix)
echo "💎 Clearing disk space and system metadata..."
df -h | grep '^/dev/' || df -h
docker system prune -af --volumes

# 4. Pull latest changes
if [ -d ".git" ]; then
    echo "📥 Forcing clean pull from Git..."
    git fetch origin main
    git reset --hard origin/main
fi

# 5. Build and Start using the modern Compose V2
echo "🏗️  Rebuilding and Starting services..."
mkdir -p data && chmod -R 777 data
docker compose build --no-cache
docker compose up -d

echo "⏳ Waiting for database setup to complete..."
docker compose wait setup
SETUP_EXIT_CODE=$?

if [ $SETUP_EXIT_CODE -ne 0 ]; then
    echo "❌ ERROR: Database setup failed! Printing logs..."
    docker compose logs setup
    exit 1
fi

echo "✅ Database setup successful."

echo "✅ Refresh Complete! Your app is starting at https://ccpleads.safelifehomehealth.com/"
echo "Check logs with: docker compose logs -f"
