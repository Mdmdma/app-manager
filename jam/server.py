from __future__ import annotations

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from jam.html_page import HTML_PAGE

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main web UI."""
    return HTMLResponse(content=HTML_PAGE)


@router.get("/health")
async def health():
    """Basic health check."""
    return {"status": "ok"}


app = FastAPI(title="jam API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router, prefix="/api/v1")
