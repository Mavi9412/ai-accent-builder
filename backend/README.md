# AI Accent Backend API

FastAPI backend for the AI-powered language learning platform with MySQL database.

## Features

- **Authentication**: JWT-based authentication with user registration and login
- **User Management**: Profile management, settings, password change
- **Course Management**: CRUD operations for courses and lessons
- **Progress Tracking**: Track user progress, practice sessions, achievements
- **Dashboard Stats**: Comprehensive statistics and analytics
- **RESTful API**: Clean REST API design with proper error handling

## Prerequisites

- Python 3.8 or higher
- MySQL Server (via XAMPP)
- pip (Python package manager)

## Setup Instructions

### 1. Install XAMPP and Start MySQL

1. Download and install [XAMPP](https://www.apachefriends.org/)
2. Start MySQL from XAMPP Control Panel
3. Open phpMyAdmin (usually at http://localhost/phpmyadmin)
4. Create a new database named `ai_accent_db`

### 2. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment Variables

1. Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

2. Edit `.env` file with your MySQL credentials:
```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=          # Leave empty if no password, or enter your MySQL password
DB_NAME=ai_accent_db

SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

CORS_ORIGINS=http://localhost:3000,http://localhost:3001
```

### 4. Initialize Database

Run the initialization script to create tables and sample data:

```bash
python init_db.py
```

This will create:
- Database tables
- Sample user (email: `demo@example.com`, password: `password123`)
- Sample courses and lessons
- Sample progress data

### 5. Run the Server

Start the FastAPI development server:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative Docs: http://localhost:8000/redoc

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get access token
- `GET /api/auth/me` - Get current user info

### Users
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/me` - Update user profile
- `GET /api/users/me/settings` - Get user settings
- `PUT /api/users/me/settings` - Update user settings
- `POST /api/users/me/change-password` - Change password
- `DELETE /api/users/me` - Delete account

### Courses
- `GET /api/courses` - Get all courses
- `GET /api/courses/{course_id}` - Get specific course
- `POST /api/courses` - Create new course
- `PUT /api/courses/{course_id}` - Update course
- `DELETE /api/courses/{course_id}` - Delete course
- `GET /api/courses/{course_id}/lessons` - Get course lessons
- `GET /api/courses/lessons/{lesson_id}` - Get specific lesson
- `POST /api/courses/lessons` - Create new lesson
- `PUT /api/courses/lessons/{lesson_id}` - Update lesson
- `DELETE /api/courses/lessons/{lesson_id}` - Delete lesson

### Progress
- `GET /api/progress/dashboard` - Get dashboard statistics
- `GET /api/progress/lessons` - Get user progress
- `POST /api/progress/lessons` - Create/update lesson progress
- `PUT /api/progress/lessons/{progress_id}` - Update progress
- `GET /api/progress/practice` - Get practice sessions
- `POST /api/progress/practice` - Create practice session
- `GET /api/progress/achievements` - Get achievements
- `POST /api/progress/achievements` - Create achievement
- `GET /api/progress/modules` - Get module progress
- `GET /api/progress/modules/{module_name}` - Get specific module progress
- `PUT /api/progress/modules/{module_id}` - Update module progress

## Authentication

Most endpoints require authentication. Include the JWT token in the Authorization header:

```
Authorization: Bearer <your_access_token>
```

## Database Schema

### Tables
- `users` - User accounts
- `user_settings` - User preferences and settings
- `courses` - Learning courses
- `lessons` - Course lessons
- `user_progress` - User lesson progress
- `practice_sessions` - Practice session records
- `achievements` - User achievements
- `module_progress` - Practice module progress

## Testing the API

### Using cURL

1. **Register a user:**
```bash
curl -X POST "http://localhost:8000/api/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "full_name": "Test User",
    "password": "password123",
    "language": "english"
  }'
```

2. **Login:**
```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123"
  }'
```

3. **Get dashboard stats (with token):**
```bash
curl -X GET "http://localhost:8000/api/progress/dashboard" \
  -H "Authorization: Bearer <your_token>"
```

### Using the Interactive Docs

Visit http://localhost:8000/docs to use the interactive Swagger UI documentation where you can test all endpoints directly.

## Development

### Project Structure
```
backend/
├── main.py              # FastAPI application entry point
├── database.py          # Database configuration
├── models.py            # SQLAlchemy models
├── schemas.py           # Pydantic schemas
├── auth.py              # Authentication utilities
├── init_db.py           # Database initialization script
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
├── routers/             # API route modules
│   ├── auth.py          # Authentication routes
│   ├── users.py         # User management routes
│   ├── courses.py       # Course management routes
│   └── progress.py      # Progress tracking routes
└── README.md            # This file
```

## Troubleshooting

### MySQL Connection Issues
- Ensure MySQL is running in XAMPP
- Check database credentials in `.env` file
- Verify database `ai_accent_db` exists in phpMyAdmin

### Port Already in Use
If port 8000 is already in use, change it:
```bash
uvicorn main:app --reload --port 8001
```

### Import Errors
Make sure you're in the `backend` directory and all dependencies are installed:
```bash
pip install -r requirements.txt
```

## Production Deployment

For production:
1. Change `SECRET_KEY` to a strong random string
2. Set proper `CORS_ORIGINS` with your frontend domain
3. Use environment variables for all sensitive data
4. Use a production ASGI server like Gunicorn with Uvicorn workers
5. Set up proper database connection pooling
6. Enable HTTPS

## License

This project is part of the AI Accent language learning platform.

