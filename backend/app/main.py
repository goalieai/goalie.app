from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import settings

# Initialize Opik for observability (optional)
if settings.opik_api_key:
    try:
        import opik
        opik.configure(api_key=settings.opik_api_key)
    except Exception as e:
        print(f"Opik initialization skipped: {e}")

print("STARTING APP - VERSION: CORS_FIX_V2_NO_REGEX")

app = FastAPI(
    title="Goally API",
    description="AI agent to help achieve New Year's resolutions",
    version="0.1.0"
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
        "http://localhost:5173",
        "http://localhost:3000",
        "https://goalie-app.vercel.app",
        "https://goalie-app-git-main-goalieais-projects.vercel.app",
        "https://goalie-iycetyrnb-goalieais-projects.vercel.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Goally API", "status": "running"}
