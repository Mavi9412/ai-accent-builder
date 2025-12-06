# ✅ SOLUTION: How to Fix the Errors

## The Two Errors You're Getting:

### Error 1: `uvicorn is not recognized`
**Cause:** You're using `uvicorn` directly instead of `python -m uvicorn`

### Error 2: `Could not import module "main"`
**Cause:** You're running from the wrong directory (project root instead of backend)

---

## ✅ THE CORRECT WAY (Copy & Paste This):

### Option 1: Use the Batch File (Easiest)
Just double-click: **`start_backend.bat`** in the project root

### Option 2: Manual Steps

**Step 1:** Open PowerShell or Command Prompt

**Step 2:** Navigate to backend directory:
```bash
cd "D:\COmplete project\demo\backend"
```

**Step 3:** Run this EXACT command:
```bash
python -m uvicorn main:app --reload --port 8000
```

**IMPORTANT:** 
- ✅ Use `python -m uvicorn` (NOT just `uvicorn`)
- ✅ Make sure you're in the `backend` directory
- ✅ The command should show: `INFO: Uvicorn running on http://127.0.0.1:8000`

---

## 🔍 How to Verify You're in the Right Place:

```bash
# Check current directory
pwd

# Should show: D:\COmplete project\demo\backend

# List files - you should see main.py
dir

# Should show: main.py, database.py, etc.
```

---

## 📋 Complete Setup Checklist:

1. ✅ **Navigate to backend:**
   ```bash
   cd backend
   ```

2. ✅ **Create database (if not done):**
   ```bash
   python create_database.py
   ```

3. ✅ **Initialize data (if not done):**
   ```bash
   python init_db.py
   ```

4. ✅ **Start server (USE THIS EXACT COMMAND):**
   ```bash
   python -m uvicorn main:app --reload --port 8000
   ```

---

## ✅ Test It Works:

After starting, open browser:
- http://localhost:8000/health → Should show `{"status": "healthy"}`
- http://localhost:8000/docs → Should show Swagger UI

---

## 🎯 Quick Reference Card:

```
✅ CORRECT:
cd backend
python -m uvicorn main:app --reload --port 8000

❌ WRONG:
uvicorn main:app --reload --port 8000
python -m uvicorn main:app --reload --port 8000  (from project root)
```

---

## 💡 Pro Tip:

I've created `start_backend.bat` - just double-click it and it will:
1. Navigate to the right directory
2. Start the server with correct command
3. Show you any errors

**Just double-click: `start_backend.bat`** 🚀

