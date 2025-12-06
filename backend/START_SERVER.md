# How to Start the Server

## ✅ Correct Way (from backend directory)

```bash
cd backend
uvicorn main:app --reload --port 8000
```

## ✅ Alternative (from project root)

If you're in the project root directory (`D:\COmplete project\demo`), use:

```bash
uvicorn backend.main:app --reload --port 8000
```

## ❌ Wrong Way (causes "Could not import module 'main'" error)

```bash
# DON'T do this from project root:
uvicorn main:app --reload --port 8000
```

## Quick Start Commands

### Option 1: From backend directory (Recommended)
```bash
cd backend
python create_database.py
python init_db.py
uvicorn main:app --reload --port 8000
```

### Option 2: From project root
```bash
python backend/create_database.py
python backend/init_db.py
uvicorn backend.main:app --reload --port 8000
```

## Verify Server is Running

After starting, check:
- http://localhost:8000/health
- http://localhost:8000/docs

You should see:
- Health endpoint returns: `{"status": "healthy"}`
- Docs page shows Swagger UI

