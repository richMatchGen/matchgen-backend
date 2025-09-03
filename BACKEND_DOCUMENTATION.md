# MatchGen Backend - Complete Documentation

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Architecture & Technology Stack](#architecture--technology-stack)
3. [Project Structure](#project-structure)
4. [Database Models](#database-models)
5. [API Endpoints](#api-endpoints)
6. [Authentication & Authorization](#authentication--authorization)
7. [Deployment](#deployment)
8. [Environment Variables](#environment-variables)
9. [Development Setup](#development-setup)
10. [Testing](#testing)
11. [Security Features](#security-features)
12. [Performance Optimizations](#performance-optimizations)
13. [Troubleshooting](#troubleshooting)

---

## 🎯 Project Overview

**MatchGen Backend** is a Django REST API that powers a sports club management and graphic generation platform. It provides comprehensive functionality for managing clubs, matches, players, and generating professional matchday graphics.

### Key Features
- **User Management**: JWT-based authentication with email verification
- **Club Management**: Complete CRUD operations for sports clubs
- **Match Management**: Schedule and track matches with detailed information
- **Player Management**: Manage club rosters and player information
- **Graphic Generation**: Generate professional matchday graphics using templates
- **Subscription Management**: Role-based access control with subscription tiers
- **File Upload**: Cloudinary integration for logo and image uploads
- **Bulk Operations**: CSV upload for matches and players

---

## 🏗️ Architecture & Technology Stack

### Core Technologies
- **Framework**: Django 5.1.7
- **API**: Django REST Framework 3.15.2
- **Authentication**: JWT (djangorestframework-simplejwt 5.5.0)
- **Database**: PostgreSQL (via dj-database-url)
- **File Storage**: Cloudinary
- **Payment Processing**: Stripe
- **Social Auth**: Django Allauth (Google OAuth)

### Additional Libraries
- **Image Processing**: Pillow, OpenCV
- **Email**: Django core mail
- **CORS**: django-cors-headers
- **Environment**: python-decouple, django-environ
- **Production**: Gunicorn, Whitenoise

---

## 📁 Project Structure

```
matchgen-backend/
├── matchgen/                     # Main Django project
│   ├── settings.py              # Django settings & configuration
│   ├── urls.py                  # Main URL routing
│   ├── utils.py                 # Utility functions
│   └── wsgi.py                  # WSGI configuration
├── users/                       # User & Club management app
│   ├── models.py                # User, Club, UserRole, ClubMembership models
│   ├── views.py                 # User & Club views (1753 lines)
│   ├── serializers.py           # User & Club serializers
│   ├── urls.py                  # User & Club URL routing
│   ├── authentication.py        # Custom JWT authentication
│   ├── permissions.py           # Role-based permissions
│   └── migrations/              # Database migrations
├── content/                     # Content management app
│   ├── models.py                # Match & Player models
│   ├── views.py                 # Match & Player views (465 lines)
│   ├── serializers.py           # Match & Player serializers
│   ├── urls.py                  # Content URL routing
│   └── migrations/              # Database migrations
├── graphicpack/                 # Graphic generation app
│   ├── models.py                # Template & graphic models
│   ├── views.py                 # Graphic generation views (2222 lines)
│   ├── serializers.py           # Graphic serializers
│   ├── utils.py                 # Font & image utilities
│   ├── urls.py                  # Graphic URL routing
│   └── migrations/              # Database migrations
├── requirements.txt             # Python dependencies (56 packages)
├── manage.py                    # Django management script
├── Procfile                     # Railway deployment configuration
├── railway_migrate.py           # Railway migration helper
├── quick_migrate.py             # Quick migration script
└── README.md                    # Project documentation
```

---

## 🗄️ Database Models

### User Management (`users/models.py`)

#### User Model
```python
class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    profile_picture = models.URLField(max_length=500, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    
    # Email verification
    email_verified = models.BooleanField(default=False)
    email_verification_token = models.CharField(max_length=100, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(blank=True, null=True)
```

#### Club Model
```python
class Club(models.Model):
    SUBSCRIPTION_TIERS = [
        ('basic', 'Basic Gen'),
        ('semipro', 'SemiPro Gen'),
        ('prem', 'Prem Gen'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="clubs")
    name = models.CharField(max_length=100)
    logo = models.URLField(max_length=500, blank=True, null=True)
    sport = models.CharField(max_length=50)
    location = models.CharField(max_length=500, blank=True, null=True)
    founded_year = models.PositiveIntegerField(blank=True, null=True)
    venue_name = models.CharField(max_length=100, blank=True, null=True)
    website = models.URLField(max_length=500, blank=True, null=True)
    primary_color = models.CharField(max_length=7, blank=True, null=True)
    secondary_color = models.CharField(max_length=7, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    league = models.CharField(max_length=100, blank=True, null=True)
    selected_pack = models.ForeignKey(GraphicPack, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Subscription fields
    subscription_tier = models.CharField(max_length=20, choices=SUBSCRIPTION_TIERS, default='basic')
    subscription_active = models.BooleanField(default=True)
    subscription_start_date = models.DateTimeField(default=timezone.now)
    subscription_end_date = models.DateTimeField(blank=True, null=True)
```

#### UserRole & ClubMembership Models
```python
class UserRole(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('admin', 'Admin'),
        ('editor', 'Editor'),
        ('viewer', 'Viewer'),
    ]
    name = models.CharField(max_length=20, choices=ROLE_CHOICES, unique=True)
    description = models.TextField(blank=True)

class ClubMembership(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    club = models.ForeignKey(Club, on_delete=models.CASCADE)
    role = models.ForeignKey(UserRole, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    invited_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invites_sent')
    invited_at = models.DateTimeField(auto_now_add=True)
    accepted_at = models.DateTimeField(blank=True, null=True)
```

### Content Management (`content/models.py`)

#### Match Model
```python
class Match(models.Model):
    HOME_AWAY_CHOICES = [
        ('HOME', 'Home'),
        ('AWAY', 'Away'),
    ]
    
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="matches")
    match_type = models.CharField(max_length=255, default="League")
    opponent = models.CharField(max_length=255)
    home_away = models.CharField(max_length=4, choices=HOME_AWAY_CHOICES, default='HOME')
    club_logo = models.URLField(max_length=500, blank=True, null=True)
    opponent_logo = models.URLField(max_length=500, blank=True, null=True)
    sponsor = models.URLField(max_length=500, blank=True, null=True)
    date = models.DateTimeField()
    time_start = models.CharField(max_length=20, blank=True, null=True)
    venue = models.CharField(max_length=255, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    matchday_post_url = models.URLField(max_length=500, blank=True, null=True)
```

#### Player Model
```python
class Player(models.Model):
    club = models.ForeignKey(Club, on_delete=models.CASCADE, related_name="players")
    name = models.CharField(max_length=255)
    squad_no = models.CharField(max_length=4)
    player_pic = models.URLField(max_length=500, blank=True, null=True)
    formatted_pic = models.URLField(max_length=500, blank=True, null=True)
    sponsor = models.URLField(max_length=500, blank=True, null=True)
    position = models.CharField(max_length=255)
```

### Graphic Generation (`graphicpack/models.py`)

#### GraphicPack Model
```python
class GraphicPack(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    preview_image_url = models.URLField(max_length=500, blank=True, null=True)
    zip_file_url = models.URLField(max_length=500, blank=True, null=True)
```

#### Template Model
```python
class Template(models.Model):
    CONTENT_CHOICES = [
        ("matchday", "Matchday"),
        ("result", "Result"),
        ("lineup", "Lineup"),
        ("fixture", "Fixture"),
        ("upcomingFixtures", "Upcoming Fixtures"),
        ("upcomingFixture", "Upcoming Fixture"),
        ("startingXI", "Starting XI"),
        ("goal", "Goal"),
        ("sub", "Substitution"),
        ("halftime", "Halftime"),
        ("fulltime", "Full-time"),
        ("alert", "Alert"),
        ("player", "Player"),
    ]

    graphic_pack = models.ForeignKey(GraphicPack, on_delete=models.CASCADE, related_name="templates")
    content_type = models.CharField(max_length=100, choices=CONTENT_CHOICES)
    image_url = models.URLField(max_length=500)
    sport = models.CharField(max_length=50, blank=True)
    template_config = models.JSONField(default=dict, blank=True)
```

---

## 🔌 API Endpoints

### Authentication Endpoints
```
POST /api/users/register/              # User registration
POST /api/users/token/                 # JWT token obtain
POST /api/users/token/refresh/         # JWT token refresh
POST /api/users/verify-email/          # Email verification
POST /api/users/resend-verification/   # Resend verification email
GET  /api/users/me/                    # Get current user
POST /api/users/google/                # Google OAuth login
```

### User Management Endpoints
```
GET  /api/users/all-users/             # List all users (admin)
GET  /api/users/profile/               # User profile
PATCH /api/users/profile/              # Update user profile
POST /api/users/change-password/       # Change password
```

### Club Management Endpoints
```
POST /api/users/club/                  # Create club
POST /api/users/club/enhanced/         # Enhanced club creation with logo
PATCH /api/users/club/enhanced/        # Update club (graphic pack)
GET  /api/users/my-club/               # Get user's club
GET  /api/users/club/<id>/             # Get specific club
PATCH /api/users/club/<id>/            # Update club
DELETE /api/users/club/<id>/           # Delete club
POST /api/users/club/upload-logo/      # Upload club logo
```

### Team Management Endpoints
```
GET  /api/users/team-management/       # Get team members
POST /api/users/team-management/       # Invite team member
PATCH /api/users/members/<id>/update-role/  # Update member role
DELETE /api/users/members/<id>/remove/      # Remove member
POST /api/users/invites/<id>/accept/   # Accept invitation
GET  /api/users/pending-invites/       # Get pending invites
```

### Content Management Endpoints
```
# Matches
GET  /api/content/matches/             # List matches
POST /api/content/matches/             # Create match
GET  /api/content/matches/<id>/        # Get specific match
PATCH /api/content/matches/<id>/       # Update match
DELETE /api/content/matches/<id>/      # Delete match
POST /api/content/matches/bulk-upload/ # Bulk upload matches
GET  /api/content/matches/matchday/    # Get matchday matches

# Players
GET  /api/content/players/             # List players
POST /api/content/players/             # Create player
GET  /api/content/players/<id>/        # Get specific player
PATCH /api/content/players/<id>/       # Update player
DELETE /api/content/players/<id>/      # Delete player
POST /api/content/players/bulk-upload/ # Bulk upload players
```

### Graphic Generation Endpoints
```
GET  /api/graphicpack/packs/           # List graphic packs
GET  /api/graphicpack/packs/<id>/      # Get specific pack
POST /api/graphicpack/generate/        # Generate graphic
GET  /api/graphicpack/templates/       # List templates
GET  /api/graphicpack/templates/<id>/  # Get specific template
POST /api/graphicpack/upload/          # Upload template
```

### Subscription & Billing Endpoints
```
GET  /api/users/features/              # Get available features
GET  /api/users/features/catalog/      # Get feature catalog
PATCH /api/users/subscription/         # Update subscription tier
POST /api/users/stripe/checkout/       # Stripe checkout
POST /api/users/stripe/billing-portal/ # Stripe billing portal
POST /api/users/stripe/webhook/        # Stripe webhook
```

### System Endpoints
```
GET  /api/health/                      # Health check
GET  /api/test-token/                  # Test token endpoint
GET  /api/test-token-refresh/          # Test token refresh
```

---

## 🔐 Authentication & Authorization

### JWT Authentication
- **Token Type**: Access & Refresh tokens
- **Expiration**: Configurable via settings
- **Custom Authentication**: `CustomJWTAuthentication` for graceful database field handling

### Role-Based Access Control (RBAC)
- **Roles**: Owner, Admin, Editor, Viewer
- **Permissions**: Feature-based access control
- **Subscription Tiers**: Basic, SemiPro, Prem

### Feature Gating
```python
class FeaturePermission:
    @staticmethod
    def get_available_features(club):
        # Returns available features based on subscription tier
        pass
```

---

## 🚀 Deployment

### Railway Deployment

#### Current Configuration
- **Platform**: Railway
- **Service**: matchgen-backend
- **Environment**: Production
- **Database**: PostgreSQL (Railway managed)

#### Procfile Configuration
```
web: python manage.py migrate && python manage.py runserver 0.0.0.0:8000
```

#### Deployment Commands
```bash
# Connect to Railway
npx @railway/cli login
npx @railway/cli link

# Run migrations
npx @railway/cli run python manage.py migrate --noinput

# Check migration status
npx @railway/cli run python manage.py showmigrations

# View logs
npx @railway/cli logs
```

### Environment Variables (Railway)
```
SECRET_KEY=your-secret-key
DEBUG=False
DATABASE_URL=postgresql://...
ALLOWED_HOSTS=matchgen-backend-production.up.railway.app,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://matchgen-backend-production.up.railway.app,https://matchgen-frontend.vercel.app
CORS_ALLOWED_ORIGINS=https://matchgen-frontend.vercel.app,http://localhost:3000

# Cloudinary
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Stripe
STRIPE_SECRET_KEY=your-stripe-secret
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable
STRIPE_WEBHOOK_SECRET=your-webhook-secret

# Email (Optional)
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
```

---

## 🔧 Environment Variables

### Required Variables
```env
SECRET_KEY=django-insecure-your-secret-key
DEBUG=False
DATABASE_URL=postgresql://username:password@host:port/database
ALLOWED_HOSTS=matchgen-backend-production.up.railway.app,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=https://matchgen-backend-production.up.railway.app,https://matchgen-frontend.vercel.app
CORS_ALLOWED_ORIGINS=https://matchgen-frontend.vercel.app,http://localhost:3000
```

### Optional Variables
```env
# Cloudinary (for file uploads)
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret

# Stripe (for payments)
STRIPE_SECRET_KEY=your-stripe-secret
STRIPE_PUBLISHABLE_KEY=your-stripe-publishable
STRIPE_WEBHOOK_SECRET=your-webhook-secret

# Email (for verification)
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-password
```

---

## 💻 Development Setup

### Prerequisites
- Python 3.8+
- PostgreSQL
- Git

### Installation Steps
```bash
# Clone repository
git clone <repository-url>
cd matchgen-backend/matchgen-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Development Tools
```bash
# Check code quality
python manage.py check

# Run tests
python manage.py test

# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Collect static files
python manage.py collectstatic
```

---

## 🧪 Testing

### Test Structure
```
users/tests.py          # User & Club tests
content/tests.py        # Match & Player tests
graphicpack/tests.py    # Graphic generation tests
```

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test users
python manage.py test content
python manage.py test graphicpack

# Run with coverage
coverage run --source='.' manage.py test
coverage report
```

---

## 🔒 Security Features

### Authentication Security
- JWT token-based authentication
- Email verification system
- Password validation and hashing
- Rate limiting on sensitive endpoints

### Data Security
- CORS configuration for frontend access
- CSRF protection
- Input validation and sanitization
- SQL injection prevention (Django ORM)

### File Upload Security
- File type validation
- File size limits (5MB for logos)
- Cloudinary integration for secure storage
- URL validation for external images

### API Security
- Role-based access control
- Feature gating based on subscription
- Audit logging for sensitive operations
- Request validation and error handling

---

## ⚡ Performance Optimizations

### Database Optimizations
- Proper indexing on frequently queried fields
- Efficient foreign key relationships
- Database connection pooling
- Query optimization with select_related and prefetch_related

### Caching Strategy
- Django cache framework integration
- Rate limiting with cache-based storage
- Static file caching with Whitenoise

### Image Processing
- Asynchronous image processing
- Optimized image formats and sizes
- Cloudinary CDN for fast image delivery

### API Performance
- Pagination for large datasets
- Efficient serialization
- Request/response optimization
- Error handling without performance impact

---

## 🐛 Troubleshooting

### Common Issues

#### 1. Database Migration Errors
```bash
# Check migration status
python manage.py showmigrations

# Reset migrations (if needed)
python manage.py migrate --fake users zero
python manage.py migrate --fake content zero
python manage.py migrate --fake graphicpack zero

# Recreate migrations
python manage.py makemigrations
python manage.py migrate
```

#### 2. Authentication Issues
```bash
# Check JWT settings
python manage.py shell
>>> from rest_framework_simplejwt.settings import api_settings
>>> print(api_settings.ACCESS_TOKEN_LIFETIME)
```

#### 3. File Upload Issues
```bash
# Check Cloudinary configuration
python manage.py shell
>>> import cloudinary
>>> print(cloudinary.config())
```

#### 4. CORS Issues
- Verify CORS_ALLOWED_ORIGINS in settings
- Check frontend URL in allowed origins
- Ensure proper headers in requests

### Debug Commands
```bash
# Check Django configuration
python manage.py check --deploy

# Validate models
python manage.py validate

# Check for broken links
python manage.py check --database default

# View current settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DATABASES)
```

### Logging
- Application logs are available in Railway dashboard
- Error tracking via Django's logging framework
- Custom exception handler for API errors

---

## 📊 Monitoring & Analytics

### Health Checks
- `/api/health/` endpoint for system status
- Database connectivity monitoring
- Authentication system status

### Performance Monitoring
- Request/response time tracking
- Database query performance
- Memory usage monitoring

### Error Tracking
- Comprehensive error logging
- Custom exception handling
- Error response standardization

---

## 🔄 CI/CD Pipeline

### Current Setup
- **Repository**: GitHub
- **Deployment**: Railway (automatic on push to main)
- **Database**: Railway PostgreSQL
- **Static Files**: Whitenoise

### Deployment Process
1. Code pushed to main branch
2. Railway automatically deploys
3. Migrations run automatically
4. Health checks performed
5. Application available at Railway URL

---

## 📈 Future Enhancements

### Planned Features
- **Real-time Notifications**: WebSocket integration
- **Advanced Analytics**: Match statistics and insights
- **Mobile API**: Optimized endpoints for mobile apps
- **Caching Layer**: Redis integration for better performance
- **Background Tasks**: Celery for async operations
- **API Versioning**: Versioned API endpoints
- **Rate Limiting**: Advanced rate limiting per user/subscription

### Technical Improvements
- **Microservices**: Split into smaller services
- **Containerization**: Docker deployment
- **Load Balancing**: Multiple instance support
- **Monitoring**: Advanced APM integration
- **Testing**: Comprehensive test coverage

---

## 📞 Support & Contact

### Documentation
- This documentation is maintained in the repository
- API documentation available via endpoints
- Code comments for complex functionality

### Issues & Bug Reports
- GitHub Issues for bug reports
- Pull requests for contributions
- Code review process for changes

### Deployment Support
- Railway dashboard for deployment monitoring
- Environment variable management
- Database backup and restore procedures

---

*Last Updated: September 2025*
*Version: 1.0.0*
