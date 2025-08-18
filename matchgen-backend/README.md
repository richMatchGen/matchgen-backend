# MatchGen Backend API

A Django REST API for managing sports clubs, matches, players, and generating matchday graphics.

## 🚀 Features

- **User Authentication**: JWT-based authentication with email/password
- **Club Management**: Create and manage sports clubs
- **Match Management**: Schedule and track matches
- **Player Management**: Manage club players
- **Graphic Generation**: Generate matchday graphics using templates
- **Bulk Operations**: Upload matches via CSV
- **Social Authentication**: Google OAuth integration

## 🏗️ Project Structure

```
matchgen-backend/
├── matchgen/                 # Main Django project
│   ├── settings.py          # Django settings
│   ├── urls.py              # Main URL configuration
│   └── utils.py             # Utility functions
├── users/                   # User management app
│   ├── models.py            # User and Club models
│   ├── views.py             # User and Club views
│   ├── serializers.py       # User and Club serializers
│   └── urls.py              # User and Club URLs
├── content/                 # Content management app
│   ├── models.py            # Match and Player models
│   ├── views.py             # Match and Player views
│   ├── serializers.py       # Match and Player serializers
│   └── urls.py              # Content URLs
├── graphicpack/             # Graphic generation app
│   ├── models.py            # Template and graphic models
│   ├── views.py             # Graphic generation views
│   ├── serializers.py       # Graphic serializers
│   ├── utils.py             # Font and image utilities
│   └── urls.py              # Graphic URLs
├── requirements.txt         # Python dependencies
├── manage.py               # Django management script
└── README.md               # This file
```

## 🔧 Recent Improvements

### Security Enhancements
- ✅ Removed hardcoded secret key from settings
- ✅ Added environment variable configuration
- ✅ Implemented proper password validation
- ✅ Added security headers for production
- ✅ Enhanced CORS configuration

### Code Quality Improvements
- ✅ Replaced print statements with proper logging
- ✅ Added comprehensive error handling
- ✅ Implemented custom exception handler
- ✅ Added input validation and sanitization
- ✅ Removed duplicate authentication endpoints
- ✅ Added proper docstrings and comments

### API Improvements
- ✅ Consistent error response format
- ✅ Better HTTP status codes
- ✅ Enhanced serializers with validation
- ✅ Improved bulk upload functionality
- ✅ Added pagination support

### Performance & Reliability
- ✅ Added request timeouts
- ✅ Improved image processing error handling
- ✅ Enhanced database query optimization
- ✅ Added proper logging configuration
- ✅ Extended URLField max_length to 500 characters for better URL support

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd matchgen-backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=False
   DATABASE_URL=your-database-url
   CLOUDINARY_CLOUD_NAME=your-cloudinary-cloud-name
   CLOUDINARY_API_KEY=your-cloudinary-api-key
   CLOUDINARY_API_SECRET=your-cloudinary-api-secret
   ALLOWED_HOSTS=your-domain.com,localhost,127.0.0.1
   CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://your-frontend.com
   CORS_ALLOWED_ORIGINS=https://your-frontend.com,http://localhost:3000
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## 📚 API Documentation

### Authentication Endpoints

#### Register User
```http
POST /api/users/register/
Content-Type: application/json

{
    "email": "user@example.com",
    "username": "username",
    "password": "SecurePass123",
    "password_confirm": "SecurePass123"
}
```

#### Login
```http
POST /api/users/login/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "SecurePass123"
}
```

#### Get JWT Token
```http
POST /api/users/token/
Content-Type: application/json

{
    "email": "user@example.com",
    "password": "SecurePass123"
}
```

### Club Management

#### Create Club
```http
POST /api/users/club/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "FC Example",
    "sport": "Football",
    "logo": "https://example.com/logo.png",
    "location": "Example City",
    "founded_year": 2020,
    "venue_name": "Example Stadium",
    "website": "https://example.com",
    "primary_color": "#FF0000",
    "secondary_color": "#0000FF",
    "bio": "A great football club",
    "league": "Premier League"
}
```

#### Get User's Club
```http
GET /api/users/my-club/
Authorization: Bearer <token>
```

### Match Management

#### Create Match
```http
POST /api/content/matches/
Authorization: Bearer <token>
Content-Type: application/json

{
    "opponent": "Rival FC",
    "date": "2024-01-15T15:00:00Z",
    "time_start": "15:00",
    "venue": "Home Stadium",
    "location": "Example City",
    "match_type": "League",
    "club_logo": "https://example.com/club-logo.png",
    "opponent_logo": "https://example.com/opponent-logo.png"
}
```

#### Get Matches
```http
GET /api/content/matches/
Authorization: Bearer <token>
```

#### Get Next Match
```http
GET /api/content/matchday/
Authorization: Bearer <token>
```

#### Get Last Match
```http
GET /api/content/last-match/
Authorization: Bearer <token>
```

### Player Management

#### Create Player
```http
POST /api/content/players/
Authorization: Bearer <token>
Content-Type: application/json

{
    "name": "John Doe",
    "squad_no": "10",
    "position": "Forward",
    "player_pic": "https://example.com/player.jpg"
}
```

#### Get Players
```http
GET /api/content/players/
Authorization: Bearer <token>
```

### Graphic Generation

#### Select Graphic Pack
```http
POST /api/graphicpack/select/
Authorization: Bearer <token>
Content-Type: application/json

{
    "pack_id": 1
}
```

#### Generate Matchday Graphic
```http
GET /api/graphicpack/generate-matchday/{match_id}/
Authorization: Bearer <token>
```

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Validation**: Strong password requirements
- **Input Sanitization**: Protection against malicious input
- **CORS Protection**: Configured for specific origins
- **CSRF Protection**: Enabled for all forms
- **Rate Limiting**: Built-in Django REST framework protection
- **SQL Injection Protection**: Django ORM protection
- **XSS Protection**: Security headers enabled

## 📊 Error Handling

The API returns consistent error responses:

```json
{
    "error": true,
    "message": "Error description",
    "code": 400,
    "fields": {
        "field_name": ["Field-specific error"]
    }
}
```

## 🚀 Deployment

### Railway Deployment
1. Connect your GitHub repository to Railway
2. Set environment variables in Railway dashboard
3. Deploy automatically on push to main branch

### Environment Variables for Production
- `SECRET_KEY`: Django secret key
- `DEBUG`: Set to `False`
- `DATABASE_URL`: PostgreSQL connection string
- `CLOUDINARY_*`: Cloudinary credentials
- `ALLOWED_HOSTS`: Comma-separated list of allowed hosts
- `CSRF_TRUSTED_ORIGINS`: Comma-separated list of trusted origins
- `CORS_ALLOWED_ORIGINS`: Comma-separated list of CORS origins

## 🧪 Testing

Run the test suite:
```bash
python manage.py test
```

## 📝 Logging

The application uses structured logging with different levels:
- **INFO**: General application events
- **WARNING**: Non-critical issues
- **ERROR**: Critical errors with stack traces

Logs are written to both console and file (`logs/django.log`).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For support, please open an issue in the GitHub repository or contact the development team.
