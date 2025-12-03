#!/usr/bin/env bash
# FoKS Intelligence - Deployment Script
# Automated deployment script for production

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ROOT="/Users/dnigga/Documents/_PROJECTS_OFICIAL/FoKS_Intelligence"
BACKEND_DIR="$PROJECT_ROOT/backend"
VENV_DIR="$BACKEND_DIR/.venv_foks"
LOG_DIR="$PROJECT_ROOT/logs"

echo -e "${GREEN}🚀 FoKS Intelligence - Deployment Script${NC}"
echo ""

# Check if virtual environment exists
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment not found. Creating...${NC}"
    cd "$BACKEND_DIR"
    python3 -m venv .venv_foks
fi

# Activate virtual environment
echo -e "${GREEN}📦 Activating virtual environment...${NC}"
source "$VENV_DIR/bin/activate"

# Install/update dependencies
echo -e "${GREEN}📥 Installing dependencies...${NC}"
cd "$BACKEND_DIR"
pip install --upgrade pip
pip install -r requirements.txt

# Run tests
echo -e "${GREEN}🧪 Running tests...${NC}"
export SKIP_CONFIG_VALIDATION=true
export LMSTUDIO_BASE_URL=http://localhost:1234/v1/chat/completions
pytest tests/ -v --tb=short || {
    echo -e "${RED}❌ Tests failed. Deployment aborted.${NC}"
    exit 1
}

# Run linting
echo -e "${GREEN}🔍 Running linting...${NC}"
ruff check app tests || {
    echo -e "${YELLOW}⚠️  Linting issues found, but continuing...${NC}"
}

# Check code formatting
echo -e "${GREEN}✨ Checking code formatting...${NC}"
black --check app tests || {
    echo -e "${YELLOW}⚠️  Formatting issues found, but continuing...${NC}"
}

# Create necessary directories
echo -e "${GREEN}📁 Creating directories...${NC}"
mkdir -p "$LOG_DIR"
mkdir -p "$BACKEND_DIR/data"

# Database migrations (if using Alembic)
if [ -f "$BACKEND_DIR/alembic.ini" ]; then
    echo -e "${GREEN}🗄️  Running database migrations...${NC}"
    cd "$BACKEND_DIR"
    alembic upgrade head || {
        echo -e "${YELLOW}⚠️  Migration issues, but continuing...${NC}"
    }
fi

# Backup database (if exists)
if [ -f "$BACKEND_DIR/data/conversations.db" ]; then
    echo -e "${GREEN}💾 Backing up database...${NC}"
    BACKUP_FILE="$PROJECT_ROOT/backups/conversations_$(date +%Y%m%d_%H%M%S).db"
    mkdir -p "$PROJECT_ROOT/backups"
    cp "$BACKEND_DIR/data/conversations.db" "$BACKUP_FILE"
    echo "Backup saved to: $BACKUP_FILE"
fi

# Check if service is running
echo -e "${GREEN}🔍 Checking if service is running...${NC}"
if pgrep -f "uvicorn app.main:app" > /dev/null; then
    echo -e "${YELLOW}⚠️  Service is already running. Restarting...${NC}"
    pkill -f "uvicorn app.main:app" || true
    sleep 2
fi

# Start service
echo -e "${GREEN}🚀 Starting FoKS Intelligence service...${NC}"
cd "$BACKEND_DIR"
nohup uvicorn app.main:app --host 0.0.0.0 --port 8001 > "$LOG_DIR/deploy.log" 2>&1 &
SERVICE_PID=$!

# Wait a bit and check if service started
sleep 3
if ps -p $SERVICE_PID > /dev/null; then
    echo -e "${GREEN}✅ Service started successfully (PID: $SERVICE_PID)${NC}"
    echo "Service is running on http://0.0.0.0:8001"
    echo "Logs: $LOG_DIR/deploy.log"
else
    echo -e "${RED}❌ Service failed to start. Check logs: $LOG_DIR/deploy.log${NC}"
    exit 1
fi

# Health check
echo -e "${GREEN}🏥 Performing health check...${NC}"
sleep 2
if curl -f http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
else
    echo -e "${YELLOW}⚠️  Health check failed, but service may still be starting...${NC}"
fi

echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo "Service information:"
echo "  - URL: http://localhost:8001"
echo "  - Docs: http://localhost:8001/docs"
echo "  - Health: http://localhost:8001/health"
echo "  - Logs: $LOG_DIR/deploy.log"
echo "  - PID: $SERVICE_PID"

