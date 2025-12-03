#!/usr/bin/env bash
# Setup PostgreSQL database for FoKS Intelligence

set -e

echo "=========================================="
echo "  FoKS Intelligence - PostgreSQL Setup"
echo "=========================================="
echo ""

# Default values
DB_NAME="${FOKS_DB_NAME:-foks_intelligence}"
DB_USER="${FOKS_DB_USER:-foks_user}"
DB_PASSWORD="${FOKS_DB_PASSWORD:-foks_password}"
DB_HOST="${FOKS_DB_HOST:-localhost}"
DB_PORT="${FOKS_DB_PORT:-5432}"

echo "Database configuration:"
echo "  Name: $DB_NAME"
echo "  User: $DB_USER"
echo "  Host: $DB_HOST"
echo "  Port: $DB_PORT"
echo ""

# Check if PostgreSQL is running
if ! pg_isready -h "$DB_HOST" -p "$DB_PORT" >/dev/null 2>&1; then
    echo "❌ ERROR: PostgreSQL is not running on $DB_HOST:$DB_PORT"
    echo "   Please start PostgreSQL and try again"
    exit 1
fi

echo "✅ PostgreSQL is running"
echo ""

# Create database and user
echo "Creating database and user..."

# Create user (ignore error if exists)
psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';" 2>/dev/null || echo "User already exists"

# Create database (ignore error if exists)
psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;" 2>/dev/null || echo "Database already exists"

# Grant privileges
psql -h "$DB_HOST" -p "$DB_PORT" -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;" 2>/dev/null || true

echo "✅ Database and user created"
echo ""

# Generate connection string
CONNECTION_STRING="postgresql://$DB_USER:$DB_PASSWORD@$DB_HOST:$DB_PORT/$DB_NAME"

echo "=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo "Add this to your .env file:"
echo ""
echo "DATABASE_URL=$CONNECTION_STRING"
echo ""
echo "Then run migrations:"
echo "  cd backend"
echo "  alembic upgrade head"
echo ""

