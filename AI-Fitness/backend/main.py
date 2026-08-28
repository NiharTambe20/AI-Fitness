from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import settings
from backend.database import init_db
from backend.api.users import router as users_router
from backend.api.exercises import router as exercises_router
from backend.api.workouts import router as workouts_router
from backend.api.ai import router as ai_router
from backend.api.auth import router as auth_router
from backend.api.streaks import router as streaks_router
from backend.api.achievements import router as achievements_router
from backend.api.analytics import router as analytics_router
from backend.api.goals import router as goals_router
from backend.api.readiness import router as readiness_router
from backend.api.training_load import router as training_load_router
from backend.api.structured_workouts import router as structured_workouts_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB tables and seed exercises on startup
    init_db()
    yield

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="FastAPI Backend Foundation for FitQuest / AI-Fitness Platform",
    lifespan=lifespan
)

# Configure CORS for development & frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Root endpoint
@app.get("/")
def read_root():
    return {
        "status": "running",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs_url": "/docs",
        "api_v1_prefix": "/api/v1"
    }

# Health check endpoint
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": settings.APP_NAME
    }

# Mount API v1 Routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(streaks_router, prefix="/api/v1")
app.include_router(achievements_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(exercises_router, prefix="/api/v1")
app.include_router(workouts_router, prefix="/api/v1")
app.include_router(ai_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(goals_router, prefix="/api/v1")
app.include_router(readiness_router, prefix="/api/v1")
app.include_router(training_load_router, prefix="/api/v1")
app.include_router(structured_workouts_router, prefix="/api/v1")




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
