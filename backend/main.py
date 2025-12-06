"""
AI Accent Builder - FastAPI Backend
Complete REST API for pronunciation training and accent analysis
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os
from pathlib import Path

# Import routers
from routers.auth import router as auth_router
from routers.users import router as users_router
from routers.courses import router as courses_router
from routers.progress import router as progress_router
from controllers.accent import router as accent_router

# Create FastAPI app
app = FastAPI(
    title="AI Accent Builder API",
    description="Backend API for pronunciation training and British accent learning",
    version="1.0.0"
)

# CORS middleware - allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Create uploads directory if it doesn't exist
uploads_dir = Path(__file__).parent / "uploads"
uploads_dir.mkdir(exist_ok=True)
(uploads_dir / "audio").mkdir(exist_ok=True)
(uploads_dir / "generated_audio").mkdir(exist_ok=True)

# Mount static files for audio playback
app.mount("/static", StaticFiles(directory=str(uploads_dir)), name="static")

# Include routers
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(courses_router)
app.include_router(progress_router)
app.include_router(accent_router)


@app.get("/")
def root():
    """Root endpoint - API health check"""
    return {
        "status": "running",
        "message": "AI Accent Builder API is running",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
