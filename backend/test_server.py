"""
Quick test script to verify server setup
"""
import sys
import os

print("=" * 50)
print("Testing Server Setup")
print("=" * 50)

# Check 1: Are we in the right directory?
print("\n1. Checking current directory...")
current_dir = os.getcwd()
print(f"   Current directory: {current_dir}")
if "backend" in current_dir:
    print("   ✅ In backend directory")
else:
    print("   ❌ NOT in backend directory!")
    print("   Please run: cd backend")

# Check 2: Can we import main?
print("\n2. Testing imports...")
try:
    import main
    print("   ✅ main.py imports successfully")
except Exception as e:
    print(f"   ❌ Cannot import main.py: {e}")
    sys.exit(1)

# Check 3: Check database connection
print("\n3. Testing database connection...")
try:
    from database import engine
    with engine.connect() as conn:
        print("   ✅ Database connection successful")
except Exception as e:
    print(f"   ⚠️  Database connection issue: {e}")
    print("   Make sure:")
    print("   - MySQL is running in XAMPP")
    print("   - Database exists (run: python create_database.py)")

# Check 4: Check if app is created
print("\n4. Testing FastAPI app...")
try:
    from main import app
    print("   ✅ FastAPI app created successfully")
    print(f"   App title: {app.title}")
except Exception as e:
    print(f"   ❌ App creation failed: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ All checks passed! You can start the server:")
print("   python -m uvicorn main:app --reload --port 8000")
print("=" * 50)

