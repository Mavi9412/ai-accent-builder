# Quick Start Guide - Fixing Common Errors

## Error: "Unknown database 'ai_accent_db'"

This error occurs when the MySQL database doesn't exist yet.

### Solution:

1. **Create the database first:**
   ```bash
   cd backend
   python create_database.py
   ```

2. **Then start the server:**
   ```bash
   uvicorn main:app --reload --port 8000
   ```

## Complete Setup Steps

### 1. Start MySQL in XAMPP
- Open XAMPP Control Panel
- Click "Start" for MySQL

### 2. Create Database
```bash
cd backend
python create_database.py
```

### 3. Initialize Database Tables and Sample Data
```bash
python init_db.py
```

### 4. Start FastAPI Server
```bash
uvicorn main:app --reload --port 8000
```

### 5. Test the API
- Open browser: http://localhost:8000/docs
- Or test health: http://localhost:8000/health

## Common Issues

### Issue 1: MySQL Connection Error
**Error:** `Can't connect to MySQL server`

**Solution:**
- Make sure MySQL is running in XAMPP
- Check `.env` file has correct credentials:
  ```
  DB_HOST=localhost
  DB_PORT=3306
  DB_USER=root
  DB_PASSWORD=        # Leave empty if no password
  ```

### Issue 2: Port Already in Use
**Error:** `Address already in use`

**Solution:**
```bash
# Use a different port
uvicorn main:app --reload --port 8001
```

### Issue 3: Module Not Found
**Error:** `ModuleNotFoundError`

**Solution:**
```bash
# Install dependencies
pip install -r requirements.txt
```

### Issue 4: Database Permission Error
**Error:** `Access denied for user`

**Solution:**
- Check MySQL username and password in `.env`
- Make sure MySQL user has CREATE DATABASE permission
- Try creating database manually in phpMyAdmin

## Manual Database Creation (Alternative)

If the script doesn't work, create database manually:

1. Open phpMyAdmin: http://localhost/phpmyadmin
2. Click "New" to create database
3. Name: `ai_accent_db`
4. Collation: `utf8mb4_unicode_ci`
5. Click "Create"

Then run:
```bash
python init_db.py
uvicorn main:app --reload --port 8000
```

## Verification

After setup, verify everything works:

1. **Check database exists:**
   - Open phpMyAdmin
   - You should see `ai_accent_db` database

2. **Check API is running:**
   - Visit: http://localhost:8000/docs
   - You should see Swagger UI

3. **Test registration:**
   - Use the `/api/auth/register` endpoint in Swagger UI
   - Create a test user

4. **Test login:**
   - Use the `/api/auth/login` endpoint
   - Get access token

## Need Help?

If you still encounter errors:
1. Check MySQL is running
2. Verify `.env` file exists and has correct values
3. Make sure all Python packages are installed
4. Check the error message for specific details

