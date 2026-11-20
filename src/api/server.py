"""
server.py — FastAPI application server.
Serves both the REST API and the built React frontend as static files.
The user only needs to run `python src/main.py` and open http://localhost:8000.
"""

import logging
import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from src.api.routes import router
from src.api.auth import PinAuthManager, PinAuthMiddleware

logger = logging.getLogger(__name__)

# Path to the built React frontend
DASHBOARD_DIR = Path(__file__).parent.parent.parent / "dashboard" / "dist"

# Cache-busting headers for index.html to guarantee clients always load the latest UI bundle
HTML_NO_CACHE_HEADERS = {
    "Cache-Control": "no-cache, no-store, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


class SPAFallbackMiddleware(BaseHTTPMiddleware):
    """Middleware to serve the SPA index.html for non-API, non-asset paths.
    
    This replaces the catch-all GET route which was causing 405 Method Not Allowed
    errors because FastAPI would match PUT/DELETE/POST requests against the catch-all
    GET route and return 405 instead of routing them to the API router.
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Only intercept 404 responses for GET requests to non-API paths
        # This ensures PUT/DELETE/POST requests to /api/* routes work correctly
        if (
            response.status_code == 404 
            and request.method == "GET"
            and not request.url.path.startswith("/api/")
            and not request.url.path.startswith("/api")
            and not request.url.path.startswith("/assets/")
            and DASHBOARD_DIR.exists()
        ):
            # Try to serve the exact file from dist
            clean_path = request.url.path.lstrip("/")
            file_path = DASHBOARD_DIR / clean_path
            if clean_path and file_path.exists() and file_path.is_file():
                return FileResponse(str(file_path))
            # Fall back to index.html for SPA routing
            index_path = DASHBOARD_DIR / "index.html"
            if index_path.exists():
                return FileResponse(str(index_path), headers=HTML_NO_CACHE_HEADERS)
        
        return response


def create_app(cctv_app) -> FastAPI:
    """Create and configure the FastAPI application."""
    
    api_app = FastAPI(
        title="CCTV AI Dashboard API",
        description="REST API and MJPEG streams for the CCTV AI Detection system",
        version="1.0.0",
        redirect_slashes=False,
    )

    # Add CORS middleware to allow the frontend to access the API.
    # This must be added BEFORE routes to ensure preflight (OPTIONS) requests
    # are handled correctly, especially when accessed via Cloudflare Tunnel.
    api_app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,
    )

    # Add SPA fallback middleware — replaces the old catch-all route
    # that was causing 405 errors for PUT/DELETE/POST API requests.
    api_app.add_middleware(SPAFallbackMiddleware)

    # Attach the main CCTV application state so routes can access it
    api_app.state.cctv_app = cctv_app

    # PIN Authentication Gate
    dashboard_pin = os.getenv("DASHBOARD_PIN")
    auth_manager = PinAuthManager(pin=dashboard_pin)
    api_app.state.auth_manager = auth_manager

    @api_app.post("/api/auth/login")
    async def login_pin(request: Request):
        try:
            body = await request.json()
            candidate_pin = body.get("pin", "")
        except Exception:
            candidate_pin = ""
        client_ip = request.client.host if request.client else "unknown"
        if auth_manager.verify_pin(candidate_pin, client_ip=client_ip):
            token = auth_manager.create_session()
            resp = JSONResponse({"status": "ok", "token": token})
            resp.set_cookie("cctv_session", token, max_age=2592000, httponly=False, samesite="lax")
            return resp
        return JSONResponse({"status": "error", "message": "Invalid PIN"}, status_code=401)

    @api_app.get("/api/auth/status")
    async def auth_status(request: Request):
        token = request.cookies.get("cctv_session") or request.query_params.get("token")
        return {
            "pin_required": auth_manager.is_enabled,
            "authenticated": auth_manager.is_valid_session(token),
        }

    # PinAuthMiddleware secures all endpoints and serves Mobile Login HTML when unauthenticated
    api_app.add_middleware(PinAuthMiddleware, auth_manager=auth_manager)

    # Include API routes under /api
    api_app.include_router(router, prefix="/api")

    # --- Serve the built React frontend static assets ---
    if DASHBOARD_DIR.exists():
        assets_dir = DASHBOARD_DIR / "assets"
        if assets_dir.exists():
            api_app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        
        # Root path serves index.html directly
        @api_app.get("/")
        async def serve_index():
            return FileResponse(str(DASHBOARD_DIR / "index.html"), headers=HTML_NO_CACHE_HEADERS)

        logger.info("Dashboard frontend enabled: serving from %s", DASHBOARD_DIR)
    else:
        @api_app.get("/")
        async def root():
            return {
                "status": "ok", 
                "service": "CCTV AI Backend",
                "message": "Dashboard not built yet. Run 'cd dashboard && npm run build' first."
            }
        logger.warning("Dashboard not found at %s — run 'cd dashboard && npm run build'", DASHBOARD_DIR)

    return api_app
