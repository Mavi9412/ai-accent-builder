"""
Script to create the database if it doesn't exist
"""
import pymysql
import os
from dotenv import load_dotenv

load_dotenv()

# Database connection parameters
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "ai_accent_db")

try:
    # Connect to MySQL server (without specifying database)
    connection = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        charset='utf8mb4'
    )
    
    with connection.cursor() as cursor:
        # Check if database exists
        cursor.execute(f"SHOW DATABASES LIKE '{DB_NAME}'")
        result = cursor.fetchone()
        
        if not result:
            # Create database if it doesn't exist
            cursor.execute(f"CREATE DATABASE {DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ Database '{DB_NAME}' created successfully!")
        else:
            print(f"✅ Database '{DB_NAME}' already exists.")
    
    connection.close()
    print(f"\n✅ Database setup complete! You can now run: uvicorn main:app --reload --port 8000")
    
except pymysql.Error as e:
    print(f"❌ Error: {e}")
    print("\nPlease make sure:")
    print("1. MySQL is running in XAMPP")
    print("2. Database credentials in .env file are correct")
    print("3. MySQL user has permission to create databases")
except Exception as e:
    print(f"❌ Unexpected error: {e}")

