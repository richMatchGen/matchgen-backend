# MatchGen Deployment Commands

## 🚀 Quick Deployment Commands

### Local Development
```bash
# Start development environment
docker-compose up --build

# Stop development environment
docker-compose down

# View logs
docker-compose logs -f

# Run tests
docker exec -it matchgen-backend python manage.py test
```

### Staging Deployment
```bash
# Deploy to staging
docker-compose -f docker-compose.staging.yml up -d --build

# Run migrations on staging
docker-compose -f docker-compose.staging.yml exec backend python manage.py migrate

# View staging logs
docker-compose -f docker-compose.staging.yml logs -f

# Stop staging
docker-compose -f docker-compose.staging.yml down
```

### Production Deployment
```bash
# Deploy to production
docker-compose -f docker-compose.prod.yml up -d --build

# Run migrations on production
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput

# View production logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop production
docker-compose -f docker-compose.prod.yml down
```

### Database Operations
```bash
# Backup database
docker-compose exec db pg_dump -U matchgen matchgen > backup.sql

# Restore database
docker-compose exec -T db psql -U matchgen matchgen < backup.sql

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Run migrations
docker-compose exec backend python manage.py migrate
```

### Monitoring & Debugging
```bash
# Check container status
docker ps

# View container logs
docker logs [container-name]

# Access container shell
docker exec -it [container-name] bash

# Check resource usage
docker stats

# View network
docker network ls
```

### Git Workflow
```bash
# Create feature branch
git checkout -b feature/new-feature

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push branch
git push origin feature/new-feature

# Merge to develop
git checkout develop
git merge feature/new-feature
git push origin develop

# Deploy to staging
docker-compose -f docker-compose.staging.yml up -d --build

# Merge to main
git checkout main
git merge develop
git tag v1.0.0
git push origin main --tags

# Deploy to production
docker-compose -f docker-compose.prod.yml up -d --build
```

## 🌐 Environment URLs

### Development
- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- Database: localhost:5432

### Staging
- Frontend: http://localhost:3001
- Backend: http://localhost:8001
- Nginx: http://localhost:8080

### Production
- Frontend: https://yourdomain.com
- Backend: https://api.yourdomain.com
- Admin: https://yourdomain.com/admin
