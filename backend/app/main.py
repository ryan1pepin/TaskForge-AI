from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routes import auth, projects, tasks

# Initialize FastAPI App
app = FastAPI(
    title="TaskForge AI API",
    description="Type-safe, production-ready workspace for project planning.",
    version="1.0.0"
)

# CORS Middleware Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes under the api/v1 prefix
app.include_router(auth.router, prefix="/api/v1")
app.include_router(projects.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")

@app.get("/health", tags=["health"])
async def health_check():
    """Service health check endpoint."""
    return {"status": "ok", "message": "TaskForge AI service is operational"}
