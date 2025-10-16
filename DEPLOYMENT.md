# MatchGen Deployment Guide

## 🚀 Development Workflow

### Branch Strategy
- **`main`** - Production branch (stable, tested code)
- **`develop`** - Development branch (integration branch)
- **`feature/*`** - Feature branches (new features)
- **`hotfix/*`** - Hotfix branches (urgent production fixes)

### Workflow
1. Create feature branch from `develop`
2. Develop and test locally
3. Create Pull Request to `develop`
4. Test on staging environment
5. Merge to `main` for production deployment

## 🐳 Docker Setup

### Prerequisites
- Docker & Docker Compose
- Git

### Local Development
```bash
# Clone repository
git clone <your-repo>
cd MatchGen

# Copy environment file
cp env.example .env

# Start development environment
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser
```

### Production Deployment
```bash
# Build and start production
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic
```

## 🌍 Environment Setup

### Development
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Database: localhost:5432

### Production
- Configure environment variables in `.env`
- Set up SSL certificates
- Configure domain names
- Set up monitoring and logging

## 📋 Deployment Checklist

### Before Deployment
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Static files collected
- [ ] SSL certificates valid

### After Deployment
- [ ] Health checks passing
- [ ] Database connectivity verified
- [ ] API endpoints responding
- [ ] Frontend loading correctly
- [ ] Error monitoring active

## 🔧 Useful Commands

```bash
# View logs
docker-compose logs -f [service]

# Restart services
docker-compose restart [service]

# Scale services
docker-compose up -d --scale backend=3

# Backup database
docker-compose exec db pg_dump -U matchgen matchgen > backup.sql

# Restore database
docker-compose exec -T db psql -U matchgen matchgen < backup.sql
```

## 🚨 Emergency Procedures

### Rollback
```bash
# Rollback to previous version
git checkout main
git reset --hard HEAD~1
docker-compose -f docker-compose.prod.yml up -d --build
```

### Database Issues
```bash
# Check database status
docker-compose exec db pg_isready

# Connect to database
docker-compose exec db psql -U matchgen matchgen
```

## 📊 Monitoring

### Health Checks
- Backend: `/api/users/health/`
- Frontend: Root endpoint
- Database: Connection test

### Logs
- Application logs: `docker-compose logs`
- Nginx logs: `docker-compose logs nginx`
- Database logs: `docker-compose logs db`



