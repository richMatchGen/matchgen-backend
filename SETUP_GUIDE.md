# 🚀 MatchGen Production Setup Guide

## **Critical Next Actions Implementation**

### **1. Staging Environment Setup**

#### **Quick Start:**
```bash
# 1. Set up staging environment
cp env.staging .env
docker-compose -f docker-compose.staging.yml up -d

# 2. Run migrations
docker-compose -f docker-compose.staging.yml exec backend python manage.py migrate

# 3. Create superuser
docker-compose -f docker-compose.staging.yml exec backend python manage.py createsuperuser

# 4. Access staging
# Frontend: http://localhost:3001
# Backend: http://localhost:8001
# Nginx: http://localhost:8080
```

#### **Staging Features:**
- ✅ Separate database (port 5433)
- ✅ Separate Redis (port 6380)
- ✅ Different ports to avoid conflicts
- ✅ Staging-specific environment variables
- ✅ Health check endpoints
- ✅ Staging headers for identification

### **2. Production Environment Setup**

#### **Security Configuration:**
```bash
# 1. Copy production environment
cp env.production .env

# 2. IMPORTANT: Change all default values!
# - Database passwords
# - Secret keys
# - API keys
# - SSL certificates

# 3. Deploy to production
docker-compose -f docker-compose.prod.yml up -d
```

#### **Production Security Features:**
- ✅ **SSL/TLS encryption** with HTTPS redirect
- ✅ **Security headers** (HSTS, CSP, XSS protection)
- ✅ **Rate limiting** on API endpoints
- ✅ **Non-root containers** for security
- ✅ **Network isolation** between services
- ✅ **Strong password requirements**
- ✅ **Content Security Policy**

### **3. Monitoring Setup**

#### **Start Monitoring Stack:**
```bash
# Start monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Access monitoring
# Prometheus: http://localhost:9090
# Grafana: http://localhost:3000 (admin/admin)
# Alertmanager: http://localhost:9093
```

#### **Monitoring Features:**
- ✅ **Prometheus** for metrics collection
- ✅ **Grafana** for visualization
- ✅ **Alertmanager** for alerting
- ✅ **Node Exporter** for system metrics
- ✅ **cAdvisor** for container metrics
- ✅ **Health checks** for all services

### **4. Backup Strategy**

#### **Automated Backups:**
```bash
# Manual backup
docker-compose -f docker-compose.prod.yml exec db pg_dump $DATABASE_URL > backup.sql

# Automated daily backups (configured in docker-compose.prod.yml)
# Backups stored in ./backups/ directory
# Retention: 30 days
```

#### **Backup Features:**
- ✅ **Daily automated backups**
- ✅ **Compressed backups** (gzip)
- ✅ **Retention policy** (30 days)
- ✅ **Backup verification**
- ✅ **Cloud storage ready** (AWS S3)

## **🔧 Deployment Commands**

### **Staging Deployment:**
```bash
# Deploy to staging
./scripts/deploy.sh staging

# View logs
docker-compose -f docker-compose.staging.yml logs -f

# Stop staging
docker-compose -f docker-compose.staging.yml down
```

### **Production Deployment:**
```bash
# Deploy to production (with backup)
./scripts/deploy.sh production true

# Deploy without backup (faster)
./scripts/deploy.sh production false

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

## **🚨 Security Checklist**

### **Before Going Live:**
- [ ] **Change all default passwords**
- [ ] **Generate strong secret keys**
- [ ] **Configure SSL certificates**
- [ ] **Set up domain names**
- [ ] **Configure firewall rules**
- [ ] **Set up monitoring alerts**
- [ ] **Test backup/restore procedures**
- [ ] **Configure log aggregation**
- [ ] **Set up error tracking (Sentry)**
- [ ] **Review security headers**

### **Environment Variables to Change:**
```bash
# Database
POSTGRES_PASSWORD=CHANGE_THIS_STRONG_PASSWORD
REDIS_PASSWORD=CHANGE_THIS_REDIS_PASSWORD

# Django
SECRET_KEY=CHANGE_THIS_TO_A_VERY_LONG_RANDOM_SECRET_KEY

# Email
EMAIL_HOST_PASSWORD=CHANGE_THIS_SENDGRID_API_KEY

# Cloudinary
CLOUDINARY_CLOUD_NAME=CHANGE_THIS_CLOUD_NAME
CLOUDINARY_API_KEY=CHANGE_THIS_API_KEY
CLOUDINARY_API_SECRET=CHANGE_THIS_API_SECRET

# Stripe
STRIPE_PUBLISHABLE_KEY=pk_live_CHANGE_THIS
STRIPE_SECRET_KEY=sk_live_CHANGE_THIS
STRIPE_WEBHOOK_SECRET=whsec_CHANGE_THIS
```

## **📊 Monitoring & Alerts**

### **Key Metrics to Monitor:**
- **Response time** < 500ms
- **Error rate** < 1%
- **CPU usage** < 80%
- **Memory usage** < 80%
- **Disk space** < 85%
- **Database connections** < 80%

### **Alert Conditions:**
- **High error rate** (> 5%)
- **Slow response time** (> 2s)
- **High resource usage** (> 90%)
- **Database connection failures**
- **SSL certificate expiration**

## **🔄 Workflow**

### **Development Workflow:**
1. **Create feature branch** from `develop`
2. **Develop and test** locally
3. **Create Pull Request** to `develop`
4. **Deploy to staging** for testing
5. **Merge to `main`** for production

### **Hotfix Workflow:**
1. **Create hotfix branch** from `main`
2. **Fix and test** quickly
3. **Create Pull Request** to `main`
4. **Deploy immediately** to production

## **🚨 Emergency Procedures**

### **Rollback:**
```bash
# Quick rollback
git checkout main
git reset --hard HEAD~1
docker-compose -f docker-compose.prod.yml up -d --build
```

### **Database Recovery:**
```bash
# Restore from backup
docker-compose -f docker-compose.prod.yml exec -T db psql $DATABASE_URL < backup.sql
```

### **Service Restart:**
```bash
# Restart specific service
docker-compose -f docker-compose.prod.yml restart backend

# Restart all services
docker-compose -f docker-compose.prod.yml restart
```

## **✅ Success Criteria**

### **Staging Environment:**
- [ ] All services running
- [ ] Database migrations applied
- [ ] Health checks passing
- [ ] API endpoints responding
- [ ] Frontend loading correctly

### **Production Environment:**
- [ ] SSL certificates configured
- [ ] Security headers active
- [ ] Rate limiting working
- [ ] Monitoring active
- [ ] Backups scheduled
- [ ] Alerts configured

## **🎯 Next Steps**

1. **Set up staging environment** and test thoroughly
2. **Configure production environment** with real credentials
3. **Set up monitoring** and configure alerts
4. **Test backup/restore** procedures
5. **Train team** on new workflow
6. **Go live** with confidence! 🚀




