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

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware

# CORS middleware for frontend
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://goalie-app.vercel.app",
    "https://goalie-app-git-main-goalieais-projects.vercel.app",
    "https://goalie-iycetyrnb-goalieais-projects.vercel.app",
    "https://goalie-k7n1wr1mi-goalieais-projects.vercel.app",  # Specific user request
]

# Regex to match any Vercel preview deployment from this project
# Matches https://goalie-*-goalieais-projects.vercel.app
origin_regex = r"https://goalie-.*-goalieais-projects\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def cors_handler(request: Request, call_next):
    """
    Manual CORS handler to ensure OPTIONS requests always return 200 OK.
    This acts as a failsafe if the main CORSMiddleware rejects the preflight.
    """
    if request.method == "OPTIONS":
        response = Response(status_code=200)
        # Allow all origins for OPTIONS to ensure preflight passes
        # The browser will still enforce security based on the subsequent request's headers
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("Origin", "*")
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, DELETE, PUT, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
        return response

    return await call_next(request)


# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Goally API", "status": "running"}
