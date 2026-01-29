from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.api.routes import router
from app.core.config import settings

# Initialize Opik for observability (optional)
if settings.opik_api_key:
    try:
        import opik
        opik.configure(api_key=settings.opik_api_key)
    except Exception as e:
        print(f"Opik initialization skipped: {e}")

print("STARTING APP - VERSION: CORS_FIX_V4_ROOT_APP")


class PreflightCORSMiddleware:
    """
    Raw ASGI middleware that handles OPTIONS preflight requests BEFORE CORSMiddleware.
    This ensures preflight always succeeds regardless of origin.
    """
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if scope["type"] == "http" and scope["method"] == "OPTIONS":
            headers = dict(scope.get("headers", []))
            origin = headers.get(b"origin", b"*").decode()

            print(f"PREFLIGHT: OPTIONS {scope['path']} | Origin: {origin}")

            response_headers = [
                (b"access-control-allow-origin", origin.encode()),
                (b"access-control-allow-methods", b"GET, POST, PUT, DELETE, OPTIONS, PATCH"),
                (b"access-control-allow-headers", b"Authorization, Content-Type, X-Requested-With"),
                (b"access-control-allow-credentials", b"true"),
                (b"access-control-max-age", b"600"),
                (b"content-length", b"0"),
            ]

            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": response_headers,
            })
            await send({
                "type": "http.response.body",
                "body": b"",
            })
            return

        await self.app(scope, receive, send)


app = FastAPI(
    title="Goally API",
    description="AI agent to help achieve New Year's resolutions",
    version="0.1.0"
)

# CORS allowed origins
origins = [
    "http://localhost:5173",
    "http://localhost:3000",
    "https://goalie-app.vercel.app",
]

# Regex to match any Vercel deployment
origin_regex = r"https://.*\.vercel\.app"

# Add CORSMiddleware (handles actual requests)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add preflight handler AFTER CORSMiddleware (so it runs BEFORE)
app.add_middleware(PreflightCORSMiddleware)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/")
async def root():
    return {"message": "Goally API", "status": "running"}
