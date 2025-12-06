# How to Fix Common Errors

## ❌ Error 1: "uvicorn is not recognized"

**Problem:** You're using `uvicorn` directly instead of `python -m uvicorn`

**Solution:** Always use:
```bash
python -m uvicorn main:app --reload --port 8000
```

NOT:
```bash
uvicorn main:app --reload --port 8000  ❌
```

---

## ❌ Error 2: "Could not import module 'main'"

**Problem:** You're running the command from the wrong directory (project root instead of backend folder)

**Solution:** Make sure you're in the `backend` directory:

```bash
# Check your current directory
pwd

# If you're NOT in backend, navigate there:
cd backend

# Then run:
python -m uvicorn main:app --reload --port 8000
```

---

## ✅ CORRECT WAY - Complete Steps

### Step 1: Navigate to backend directory
```bash
cd backend
```

### Step 2: Verify you're in the right place
```bash
# You should see files like: main.py, database.py, etc.
dir
```

### Step 3: Create database (if not done)
```bash
python create_database.py
```

### Step 4: Initialize database (if not done)
```bash
python init_db.py
```

### Step 5: Start server (USE THIS EXACT COMMAND)
```bash
python -m uvicorn main:app --reload --port 8000
```

---

## ✅ Quick Test

After starting, open in browser:
- http://localhost:8000/health
- http://localhost:8000/docs

You should see:
- Health: `{"status": "healthy"}`
- Docs: Swagger UI interface

---

## 🔍 Troubleshooting Checklist

1. ✅ Are you in the `backend` directory?
   ```bash
   cd backend
   ```

2. ✅ Are you using `python -m uvicorn` (not just `uvicorn`)?
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```

3. ✅ Is MySQL running in XAMPP?
   - Check XAMPP Control Panel
   - MySQL should be "Running"

4. ✅ Does the database exist?
   ```bash
   python create_database.py
   ```

5. ✅ Are all dependencies installed?
   ```bash
   pip install -r requirements.txt
   ```

---

## 📝 Summary

**ALWAYS use these commands from the `backend` directory:**

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

That's it! The key is:
- ✅ Use `python -m uvicorn` (not just `uvicorn`)
- ✅ Run from `backend` directory (not project root)

