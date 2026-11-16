"""FastAPI application entrypoint for Automated Multi-Platform Posting System."""

from contextlib import asynccontextmanager
from typing import Dict, Any
from fastapi import FastAPI, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from app.config import settings, Settings
from app.schemas import PostingRequest, PostingResponse
from app.services.posting_service import PostingService
from app.ui import HTML_PAGE




@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle event handler for application startup and shutdown."""
    # Startup: logging and configuration check
    yield
    # Shutdown: cleanup resources if needed


app = FastAPI(
    title="Automated Multi-Platform Posting System",
    description=(
        "Production-ready REST API to validate short promotional messages and automatically "
        "publish them simultaneously to Instagram, LinkedIn, Telegram, and Discord using "
        "their official APIs."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Enable CORS for browser Swagger UI and cross-origin clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



def get_posting_service() -> PostingService:
    """Dependency provider for PostingService instance."""
    return PostingService(settings=Settings())



@app.get(
    "/",
    tags=["General"],
    summary="Root service info & cute web UI",
)
async def root(request: Request):
    """Serves the cute interactive Web Studio for browsers, and JSON for API clients."""
    accept = request.headers.get("accept", "")
    if "text/html" in accept and not request.query_params.get("json"):
        return HTMLResponse(content=HTML_PAGE)
    return {
        "service": "Automated Multi-Platform Posting System",
        "version": "1.0.0",
        "status": "online",
        "supported_platforms": ["Instagram", "LinkedIn", "Telegram", "Discord"],
        "docs_url": "/docs",
        "posting_endpoint": "POST /posting",
    }


@app.get(
    "/ui",
    response_class=HTMLResponse,
    tags=["General"],
    summary="Cute Web Studio UI",
)
async def web_ui():
    """Interactive web dashboard for easy posting across all 4 platforms."""
    return HTMLResponse(content=HTML_PAGE)



@app.get(
    "/health",
    tags=["General"],
    summary="Health check endpoint",
    response_model=Dict[str, str],
)
async def health_check():
    """Health status probe for orchestrators and monitoring tools."""
    return {"status": "healthy"}


@app.post(
    "/posting",
    response_model=PostingResponse,
    status_code=status.HTTP_200_OK,
    tags=["Publishing"],
    summary="Publish message across all four platforms",
    description=(
        "Accepts a short message (maximum 200 characters) containing exactly one CTA URL (HTTP/HTTPS) "
        "and automatically broadcasts it across Instagram, LinkedIn, Telegram, and Discord. "
        "Each platform is handled independently so failure in one platform does not abort others."
    ),
)
async def post_to_platforms(
    request: PostingRequest,
    service: PostingService = Depends(get_posting_service),
) -> PostingResponse:
    """Publishes validated message across Instagram, LinkedIn, Telegram, and Discord."""
    return await service.publish_all(request.message)

