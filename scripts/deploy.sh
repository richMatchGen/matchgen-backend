#!/bin/bash

# MatchGen Deployment Script
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
ENVIRONMENT=${1:-staging}
BACKUP_BEFORE_DEPLOY=${2:-true}

echo -e "${GREEN}🚀 Starting MatchGen deployment to $ENVIRONMENT${NC}"

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if environment is valid
if [[ "$ENVIRONMENT" != "staging" && "$ENVIRONMENT" != "production" ]]; then
    print_error "Invalid environment. Use 'staging' or 'production'"
    exit 1
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker and try again."
    exit 1
fi

# Check if environment file exists
ENV_FILE="env.$ENVIRONMENT"
if [[ ! -f "$ENV_FILE" ]]; then
    print_error "Environment file $ENV_FILE not found!"
    exit 1
fi

# Load environment variables
export $(cat $ENV_FILE | grep -v '^#' | xargs)

# Backup database if requested
if [[ "$BACKUP_BEFORE_DEPLOY" == "true" && "$ENVIRONMENT" == "production" ]]; then
    print_warning "Creating database backup before deployment..."
    docker-compose -f docker-compose.prod.yml exec -T db pg_dump $DATABASE_URL > "backup_$(date +%Y%m%d_%H%M%S).sql"
    print_status "Database backup completed"
fi

# Pull latest images
print_warning "Pulling latest images..."
docker-compose -f "docker-compose.$ENVIRONMENT.yml" pull

# Build new images
print_warning "Building new images..."
docker-compose -f "docker-compose.$ENVIRONMENT.yml" build --no-cache

# Stop existing services
print_warning "Stopping existing services..."
docker-compose -f "docker-compose.$ENVIRONMENT.yml" down

# Start services
print_warning "Starting services..."
docker-compose -f "docker-compose.$ENVIRONMENT.yml" up -d

# Wait for services to be ready
print_warning "Waiting for services to be ready..."
sleep 30

# Run database migrations
print_warning "Running database migrations..."
docker-compose -f "docker-compose.$ENVIRONMENT.yml" exec backend python manage.py migrate

# Collect static files
print_warning "Collecting static files..."
docker-compose -f "docker-compose.$ENVIRONMENT.yml" exec backend python manage.py collectstatic --noinput

# Health check
print_warning "Performing health check..."
if curl -f http://localhost:8080/health > /dev/null 2>&1; then
    print_status "Health check passed"
else
    print_error "Health check failed"
    exit 1
fi

# Show running services
print_status "Deployment completed successfully!"
echo -e "${GREEN}📊 Service Status:${NC}"
docker-compose -f "docker-compose.$ENVIRONMENT.yml" ps

echo -e "${GREEN}🌐 Access URLs:${NC}"
if [[ "$ENVIRONMENT" == "staging" ]]; then
    echo "Frontend: http://localhost:3001"
    echo "Backend: http://localhost:8001"
    echo "Nginx: http://localhost:8080"
else
    echo "Production: https://matchgen.com"
fi

print_status "Deployment to $ENVIRONMENT completed successfully! 🎉"

