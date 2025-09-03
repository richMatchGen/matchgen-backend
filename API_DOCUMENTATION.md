# MatchGen Backend - API Documentation

## 📋 Overview

The MatchGen Backend API provides comprehensive endpoints for sports club management, match scheduling, player management, and graphic generation. This documentation covers all available endpoints, request/response formats, and authentication requirements.

**Base URL**: `https://matchgen-backend-production.up.railway.app`

---

## 🔐 Authentication

### JWT Authentication
All protected endpoints require JWT authentication. Include the access token in the Authorization header:

```
Authorization: Bearer <access_token>
```

### Token Endpoints
- **Obtain Token**: `POST /api/users/token/`
- **Refresh Token**: `POST /api/users/token/refresh/`

---

## 👤 User Management

### User Registration
**Endpoint**: `POST /api/users/register/`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response** (201 Created):
```json
{
  "message": "Account created successfully! Please check your email to verify your account.",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "email_verified": false
  }
}
```

### User Login
**Endpoint**: `POST /api/users/token/`

**Request Body**:
```json
{
  "email": "user@example.com",
  "password": "securepassword123"
}
```

**Response** (200 OK):
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "email_verified": true
  }
}
```

### Get Current User
**Endpoint**: `GET /api/users/me/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "email": "user@example.com",
  "username": "john_doe",
  "profile_picture": "https://res.cloudinary.com/...",
  "email_verified": true,
  "is_active": true
}
```

### Email Verification
**Endpoint**: `POST /api/users/verify-email/`

**Request Body**:
```json
{
  "token": "verification_token_here"
}
```

**Response** (200 OK):
```json
{
  "message": "Email verified successfully!"
}
```

### Resend Verification Email
**Endpoint**: `POST /api/users/resend-verification/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "message": "Verification email sent successfully!"
}
```

---

## 🏢 Club Management

### Create Club (Enhanced)
**Endpoint**: `POST /api/users/club/enhanced/`

**Headers**: 
- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

**Request Body** (FormData):
```
name: "Manchester United"
sport: "Football"
venue_name: "Old Trafford"
location: "Manchester, UK"
primary_color: "#DA291C"
secondary_color: "#FBE122"
bio: "Premier League club"
league: "Premier League"
website: "https://manutd.com"
founded_year: 1878
logo: [file upload]
```

**Response** (201 Created):
```json
{
  "message": "Club created successfully!",
  "club": {
    "id": 1,
    "name": "Manchester United",
    "sport": "Football",
    "logo": "https://res.cloudinary.com/...",
    "venue_name": "Old Trafford",
    "location": "Manchester, UK",
    "primary_color": "#DA291C",
    "secondary_color": "#FBE122",
    "bio": "Premier League club",
    "league": "Premier League",
    "website": "https://manutd.com",
    "founded_year": 1878,
    "subscription_tier": "basic",
    "subscription_active": true
  }
}
```

### Get User's Club
**Endpoint**: `GET /api/users/my-club/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Manchester United",
  "sport": "Football",
  "logo": "https://res.cloudinary.com/...",
  "venue_name": "Old Trafford",
  "location": "Manchester, UK",
  "primary_color": "#DA291C",
  "secondary_color": "#FBE122",
  "bio": "Premier League club",
  "league": "Premier League",
  "website": "https://manutd.com",
  "founded_year": 1878,
  "subscription_tier": "basic",
  "subscription_active": true,
  "selected_pack": null
}
```

### Update Club (Graphic Pack)
**Endpoint**: `PATCH /api/users/club/enhanced/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "graphic_pack_id": 1
}
```

**Response** (200 OK):
```json
{
  "message": "Club updated successfully!",
  "club": {
    "id": 1,
    "name": "Manchester United",
    "selected_pack": {
      "id": 1,
      "name": "Default Pack",
      "description": "Professional templates"
    }
  }
}
```

### Upload Club Logo
**Endpoint**: `POST /api/users/club/upload-logo/`

**Headers**: 
- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

**Request Body** (FormData):
```
logo: [file upload]
```

**Response** (200 OK):
```json
{
  "message": "Logo uploaded successfully!",
  "logo_url": "https://res.cloudinary.com/..."
}
```

---

## 👥 Team Management

### Get Team Members
**Endpoint**: `GET /api/users/team-management/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "members": [
    {
      "id": 1,
      "user": {
        "id": 1,
        "email": "owner@club.com",
        "username": "owner"
      },
      "role": {
        "name": "owner",
        "description": "Club owner with full access"
      },
      "status": "active",
      "invited_at": "2025-09-02T19:30:00Z",
      "accepted_at": "2025-09-02T19:30:00Z"
    }
  ],
  "invites": [
    {
      "id": 2,
      "user": {
        "id": 2,
        "email": "member@club.com",
        "username": "member"
      },
      "role": {
        "name": "editor",
        "description": "Can edit content"
      },
      "status": "pending",
      "invited_at": "2025-09-02T19:30:00Z"
    }
  ]
}
```

### Invite Team Member
**Endpoint**: `POST /api/users/team-management/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "email": "newmember@club.com",
  "role": "editor"
}
```

**Response** (201 Created):
```json
{
  "message": "Invitation sent successfully!",
  "invite": {
    "id": 3,
    "user": {
      "id": 3,
      "email": "newmember@club.com"
    },
    "role": {
      "name": "editor",
      "description": "Can edit content"
    },
    "status": "pending"
  }
}
```

### Update Member Role
**Endpoint**: `PATCH /api/users/members/{id}/update-role/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "role": "admin"
}
```

**Response** (200 OK):
```json
{
  "message": "Role updated successfully!",
  "member": {
    "id": 2,
    "role": {
      "name": "admin",
      "description": "Administrator with management access"
    }
  }
}
```

### Remove Member
**Endpoint**: `DELETE /api/users/members/{id}/remove/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "message": "Member removed successfully!"
}
```

### Accept Invitation
**Endpoint**: `POST /api/users/invites/{id}/accept/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "message": "Invitation accepted successfully!",
  "membership": {
    "id": 2,
    "status": "active",
    "accepted_at": "2025-09-02T19:30:00Z"
  }
}
```

---

## ⚽ Match Management

### List Matches
**Endpoint**: `GET /api/content/matches/`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `match_type`: Filter by match type
- `home_away`: Filter by home/away

**Response** (200 OK):
```json
{
  "count": 10,
  "next": "https://api.example.com/matches/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "match_type": "League",
      "opponent": "Liverpool",
      "home_away": "HOME",
      "club_logo": "https://res.cloudinary.com/...",
      "opponent_logo": "https://res.cloudinary.com/...",
      "sponsor": "https://res.cloudinary.com/...",
      "date": "2025-09-15T15:00:00Z",
      "time_start": "15:00",
      "venue": "Old Trafford",
      "location": "Manchester, UK",
      "matchday_post_url": "https://res.cloudinary.com/..."
    }
  ]
}
```

### Create Match
**Endpoint**: `POST /api/content/matches/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "match_type": "League",
  "opponent": "Liverpool",
  "home_away": "HOME",
  "opponent_logo": "https://res.cloudinary.com/...",
  "sponsor": "https://res.cloudinary.com/...",
  "date": "2025-09-15T15:00:00Z",
  "time_start": "15:00",
  "venue": "Old Trafford",
  "location": "Manchester, UK"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "match_type": "League",
  "opponent": "Liverpool",
  "home_away": "HOME",
  "club_logo": "https://res.cloudinary.com/...",
  "opponent_logo": "https://res.cloudinary.com/...",
  "sponsor": "https://res.cloudinary.com/...",
  "date": "2025-09-15T15:00:00Z",
  "time_start": "15:00",
  "venue": "Old Trafford",
  "location": "Manchester, UK"
}
```

### Get Match
**Endpoint**: `GET /api/content/matches/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "match_type": "League",
  "opponent": "Liverpool",
  "home_away": "HOME",
  "club_logo": "https://res.cloudinary.com/...",
  "opponent_logo": "https://res.cloudinary.com/...",
  "sponsor": "https://res.cloudinary.com/...",
  "date": "2025-09-15T15:00:00Z",
  "time_start": "15:00",
  "venue": "Old Trafford",
  "location": "Manchester, UK",
  "matchday_post_url": "https://res.cloudinary.com/..."
}
```

### Update Match
**Endpoint**: `PATCH /api/content/matches/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "opponent": "Arsenal",
  "date": "2025-09-20T15:00:00Z"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "match_type": "League",
  "opponent": "Arsenal",
  "home_away": "HOME",
  "date": "2025-09-20T15:00:00Z"
}
```

### Delete Match
**Endpoint**: `DELETE /api/content/matches/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (204 No Content)

### Bulk Upload Matches
**Endpoint**: `POST /api/content/matches/bulk-upload/`

**Headers**: 
- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

**Request Body** (FormData):
```
csv_file: [CSV file upload]
```

**CSV Format**:
```csv
match_type,opponent,home_away,date,time_start,venue,location
League,Liverpool,HOME,2025-09-15,15:00,Old Trafford,Manchester
Cup,Arsenal,AWAY,2025-09-20,19:45,Emirates Stadium,London
```

**Response** (201 Created):
```json
{
  "message": "Matches uploaded successfully!",
  "created": 2,
  "errors": []
}
```

### Get Matchday Matches
**Endpoint**: `GET /api/content/matches/matchday/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "matches": [
    {
      "id": 1,
      "match_type": "League",
      "opponent": "Liverpool",
      "home_away": "HOME",
      "date": "2025-09-15T15:00:00Z",
      "time_start": "15:00",
      "venue": "Old Trafford"
    }
  ]
}
```

---

## 👤 Player Management

### List Players
**Endpoint**: `GET /api/content/players/`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `position`: Filter by position

**Response** (200 OK):
```json
{
  "count": 25,
  "next": "https://api.example.com/players/?page=2",
  "previous": null,
  "results": [
    {
      "id": 1,
      "name": "Marcus Rashford",
      "squad_no": "10",
      "player_pic": "https://res.cloudinary.com/...",
      "formatted_pic": "https://res.cloudinary.com/...",
      "sponsor": "https://res.cloudinary.com/...",
      "position": "Forward"
    }
  ]
}
```

### Create Player
**Endpoint**: `POST /api/content/players/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "name": "Marcus Rashford",
  "squad_no": "10",
  "player_pic": "https://res.cloudinary.com/...",
  "sponsor": "https://res.cloudinary.com/...",
  "position": "Forward"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "name": "Marcus Rashford",
  "squad_no": "10",
  "player_pic": "https://res.cloudinary.com/...",
  "formatted_pic": "https://res.cloudinary.com/...",
  "sponsor": "https://res.cloudinary.com/...",
  "position": "Forward"
}
```

### Get Player
**Endpoint**: `GET /api/content/players/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Marcus Rashford",
  "squad_no": "10",
  "player_pic": "https://res.cloudinary.com/...",
  "formatted_pic": "https://res.cloudinary.com/...",
  "sponsor": "https://res.cloudinary.com/...",
  "position": "Forward"
}
```

### Update Player
**Endpoint**: `PATCH /api/content/players/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "squad_no": "11",
  "position": "Winger"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Marcus Rashford",
  "squad_no": "11",
  "position": "Winger"
}
```

### Delete Player
**Endpoint**: `DELETE /api/content/players/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (204 No Content)

### Bulk Upload Players
**Endpoint**: `POST /api/content/players/bulk-upload/`

**Headers**: 
- `Authorization: Bearer <access_token>`
- `Content-Type: multipart/form-data`

**Request Body** (FormData):
```
csv_file: [CSV file upload]
```

**CSV Format**:
```csv
name,squad_no,position,player_pic,sponsor
Marcus Rashford,10,Forward,https://res.cloudinary.com/...,https://res.cloudinary.com/...
Bruno Fernandes,8,Midfielder,https://res.cloudinary.com/...,https://res.cloudinary.com/...
```

**Response** (201 Created):
```json
{
  "message": "Players uploaded successfully!",
  "created": 2,
  "errors": []
}
```

---

## 🎨 Graphic Generation

### List Graphic Packs
**Endpoint**: `GET /api/graphicpack/packs/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "count": 3,
  "results": [
    {
      "id": 1,
      "name": "Default Pack",
      "description": "Professional templates for all sports",
      "preview_image_url": "https://res.cloudinary.com/...",
      "zip_file_url": "https://res.cloudinary.com/..."
    }
  ]
}
```

### Get Graphic Pack
**Endpoint**: `GET /api/graphicpack/packs/{id}/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Default Pack",
  "description": "Professional templates for all sports",
  "preview_image_url": "https://res.cloudinary.com/...",
  "zip_file_url": "https://res.cloudinary.com/...",
  "templates": [
    {
      "id": 1,
      "content_type": "matchday",
      "image_url": "https://res.cloudinary.com/...",
      "sport": "Football"
    }
  ]
}
```

### Generate Graphic
**Endpoint**: `POST /api/graphicpack/generate/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "template_id": 1,
  "match_id": 1,
  "custom_data": {
    "title": "Matchday",
    "subtitle": "vs Liverpool"
  }
}
```

**Response** (200 OK):
```json
{
  "message": "Graphic generated successfully!",
  "graphic_url": "https://res.cloudinary.com/...",
  "template_used": {
    "id": 1,
    "content_type": "matchday"
  }
}
```

### List Templates
**Endpoint**: `GET /api/graphicpack/templates/`

**Headers**: `Authorization: Bearer <access_token>`

**Query Parameters**:
- `content_type`: Filter by content type
- `sport`: Filter by sport
- `graphic_pack`: Filter by graphic pack

**Response** (200 OK):
```json
{
  "count": 10,
  "results": [
    {
      "id": 1,
      "content_type": "matchday",
      "image_url": "https://res.cloudinary.com/...",
      "sport": "Football",
      "graphic_pack": {
        "id": 1,
        "name": "Default Pack"
      }
    }
  ]
}
```

---

## 💳 Subscription & Billing

### Get Available Features
**Endpoint**: `GET /api/users/features/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "subscription_tier": "basic",
  "available_features": [
    "basic_generation",
    "club_management",
    "match_management"
  ],
  "upgrade_available": true,
  "next_tier": "semipro"
}
```

### Get Feature Catalog
**Endpoint**: `GET /api/users/features/catalog/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "tiers": {
    "basic": {
      "name": "Basic Gen",
      "price": 0,
      "features": [
        "basic_generation",
        "club_management",
        "match_management"
      ]
    },
    "semipro": {
      "name": "SemiPro Gen",
      "price": 29.99,
      "features": [
        "advanced_generation",
        "bulk_operations",
        "priority_support"
      ]
    },
    "prem": {
      "name": "Prem Gen",
      "price": 99.99,
      "features": [
        "premium_templates",
        "custom_branding",
        "api_access"
      ]
    }
  }
}
```

### Update Subscription Tier
**Endpoint**: `PATCH /api/users/subscription/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "tier": "semipro"
}
```

**Response** (200 OK):
```json
{
  "message": "Subscription updated successfully!",
  "subscription": {
    "tier": "semipro",
    "active": true,
    "start_date": "2025-09-02T19:30:00Z"
  }
}
```

### Stripe Checkout
**Endpoint**: `POST /api/users/stripe/checkout/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "price_id": "price_1234567890",
  "success_url": "https://matchgen-frontend.vercel.app/success",
  "cancel_url": "https://matchgen-frontend.vercel.app/cancel"
}
```

**Response** (200 OK):
```json
{
  "checkout_url": "https://checkout.stripe.com/...",
  "session_id": "cs_1234567890"
}
```

### Stripe Billing Portal
**Endpoint**: `POST /api/users/stripe/billing-portal/`

**Headers**: `Authorization: Bearer <access_token>`

**Request Body**:
```json
{
  "return_url": "https://matchgen-frontend.vercel.app/account"
}
```

**Response** (200 OK):
```json
{
  "portal_url": "https://billing.stripe.com/...",
  "session_id": "bps_1234567890"
}
```

---

## 🔧 System Endpoints

### Health Check
**Endpoint**: `GET /api/health/`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "message": "MatchGen API is working",
  "timestamp": "2025-09-02T19:30:00Z",
  "endpoints": {
    "root": "/",
    "health": "/api/health/",
    "users": "/api/users/",
    "content": "/api/content/",
    "graphicpack": "/api/graphicpack/"
  },
  "database": "connected",
  "authentication": "jwt_enabled"
}
```

### Test Token
**Endpoint**: `GET /api/test-token/`

**Headers**: `Authorization: Bearer <access_token>`

**Response** (200 OK):
```json
{
  "message": "Token is valid",
  "user_id": 1,
  "expires_at": "2025-09-02T20:30:00Z"
}
```

---

## ❌ Error Responses

### Standard Error Format
```json
{
  "error": "Error message description",
  "detail": "Additional error details",
  "code": "ERROR_CODE"
}
```

### Common HTTP Status Codes
- **400 Bad Request**: Invalid request data
- **401 Unauthorized**: Missing or invalid authentication
- **403 Forbidden**: Insufficient permissions
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server error

### Validation Error Example
```json
{
  "error": "Validation failed",
  "detail": {
    "email": ["This field is required."],
    "password": ["This password is too short."]
  },
  "code": "VALIDATION_ERROR"
}
```

---

## 📊 Rate Limiting

### Limits
- **Authentication endpoints**: 5 requests per minute
- **API endpoints**: 100 requests per minute per user
- **File uploads**: 10 requests per minute per user

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1630609200
```

---

## 🔄 Pagination

### Standard Pagination
All list endpoints support pagination with the following query parameters:
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20, max: 100)

### Pagination Response Format
```json
{
  "count": 150,
  "next": "https://api.example.com/endpoint/?page=3",
  "previous": "https://api.example.com/endpoint/?page=1",
  "results": [...]
}
```

---

## 📝 File Upload Guidelines

### Supported Formats
- **Images**: JPG, PNG, GIF, WebP
- **Documents**: CSV (for bulk uploads)

### File Size Limits
- **Club logos**: 5MB
- **Player photos**: 5MB
- **CSV files**: 10MB

### Upload Endpoints
- Club logo: `POST /api/users/club/upload-logo/`
- Player photo: Include in player creation/update
- Bulk CSV: `POST /api/content/matches/bulk-upload/`

---

## 🔐 Security Considerations

### Authentication
- JWT tokens expire after 60 minutes
- Refresh tokens expire after 7 days
- Tokens are automatically invalidated on logout

### Data Protection
- All sensitive data is encrypted in transit (HTTPS)
- Passwords are hashed using Django's secure hashing
- File uploads are validated for type and size

### CORS Configuration
- Frontend domain: `https://matchgen-frontend.vercel.app`
- Development: `http://localhost:3000`
- All requests must include proper headers

---

*Last Updated: September 2025*
*Version: 1.0.0*
