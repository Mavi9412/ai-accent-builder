# Quick Setup Guide

## Step-by-Step Setup

### 1. Install XAMPP and Start MySQL
- Download XAMPP from https://www.apachefriends.org/
- Install and start MySQL from XAMPP Control Panel
- Open phpMyAdmin (http://localhost/phpmyadmin)
- Create database: `ai_accent_db`

### 2. Install Python Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy the example file
copy .env.example .env

# Edit .env file with your MySQL password (if any)
# Default settings work if MySQL has no password
```

### 4. Create Database
```bash
python create_database.py
```

This creates the MySQL database if it doesn't exist.

### 5. Initialize Database Tables and Sample Data
```bash
python init_db.py
```

This creates:
- All database tables
- Sample user: `demo@example.com` / `password123`
- Sample courses and lessons
- Sample progress data

### 6. Start the Server
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**OR** if you get "Unknown database" error, make sure you ran step 4 first!

### 6. Test the API
- Open browser: http://localhost:8000/docs
- Try the interactive API documentation

## Default Credentials
- Email: `demo@example.com`
- Password: `password123`

## API Base URL
- Development: http://localhost:8000
- Docs: http://localhost:8000/docs

## Troubleshooting

**MySQL Connection Error:**
- Make sure MySQL is running in XAMPP
- Check `.env` file has correct credentials
- Verify database `ai_accent_db` exists

**Port Already in Use:**
```bash
uvicorn main:app --reload --port 8001
```

**Module Not Found:**
```bash
pip install -r requirements.txt
```

