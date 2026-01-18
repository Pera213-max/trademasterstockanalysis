"""
TradeMaster Pro API
===================
Professional Trading Platform Backend

FastAPI application with real-time data, AI predictions,
and comprehensive market analytics.
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import socketio
import os
from datetime import datetime
import logging

# Import routers
from app.routers import stocks, crypto, social, macro, news, portfolio, chart, auth, watchlist, fi
from app.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

SCHEDULER_LOCK_PATH = os.getenv("SCHEDULER_LOCK_PATH", "/tmp/trademaster_scheduler.lock")
SCHEDULER_LOCK_ACQUIRED = False


def _acquire_scheduler_lock() -> bool:
    """Ensure only one worker starts the background scheduler."""
    global SCHEDULER_LOCK_ACQUIRED
    if SCHEDULER_LOCK_ACQUIRED:
        return True
    try:
        fd = os.open(SCHEDULER_LOCK_PATH, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.close(fd)
        SCHEDULER_LOCK_ACQUIRED = True
        return True
    except FileExistsError:
        return False
    except OSError as exc:
        logger.warning("Scheduler lock error: %s", exc)
        return False

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="TradeMaster Pro API",
    description="Professional Trading Platform API with real-time market data, "
                "AI-powered predictions, and comprehensive analytics",
    version="1.0.0",
    docs_url="/docs",          # Swagger UI
    redoc_url="/redoc",        # ReDoc UI
    contact={
        "name": "TradeMaster Pro",
        "url": "https://trademaster.pro",
    },
    license_info={
        "name": "Private",
    }
)

# ============================================================================
# Global Exception Handlers
# ============================================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed error messages"""
    logger.error(f"Validation error for {request.url}: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": "Validation Error",
            "detail": exc.errors(),
            "message": "Invalid request parameters. Please check your input."
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception for {request.url}: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later.",
            "detail": str(exc) if settings.DEBUG else None  # Only show in debug mode
        }
    )

# ============================================================================
# CORS Middleware Configuration
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",      # Next.js US frontend
        "http://localhost:8000",      # FastAPI development
        "http://frontend:3000",       # Docker container
        *settings.CORS_ORIGINS        # Additional origins from settings
    ],
    allow_credentials=True,
    allow_methods=["*"],              # Allow all HTTP methods
    allow_headers=["*"],              # Allow all headers
)

# ============================================================================
# Socket.IO Setup (Real-time Communication)
# ============================================================================

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=[
        "http://localhost:3000",      # US frontend
        "http://localhost:8000",
        "http://frontend:3000",
    ]
)

# Wrap FastAPI with Socket.IO
socket_app = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app
)

# Socket.IO event handlers
@sio.event
async def connect(sid, environ):
    """Handle client connection"""
    print(f"Client connected: {sid}")
    await sio.emit('connection_established', {
        'status': 'connected',
        'timestamp': datetime.now().isoformat()
    }, room=sid)

@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    print(f"Client disconnected: {sid}")

@sio.event
async def subscribe_ticker(sid, data):
    """Subscribe to real-time ticker updates"""
    ticker = data.get('ticker')
    print(f"Client {sid} subscribed to {ticker}")
    # Join room for this ticker
    await sio.enter_room(sid, f"ticker_{ticker}")
    await sio.emit('subscribed', {
        'ticker': ticker,
        'status': 'subscribed'
    }, room=sid)

@sio.event
async def unsubscribe_ticker(sid, data):
    """Unsubscribe from ticker updates"""
    ticker = data.get('ticker')
    print(f"Client {sid} unsubscribed from {ticker}")
    await sio.leave_room(sid, f"ticker_{ticker}")
    await sio.emit('unsubscribed', {
        'ticker': ticker,
        'status': 'unsubscribed'
    }, room=sid)

# ============================================================================
# API Routers
# ============================================================================

# Include all routers
app.include_router(
    stocks.router,
    tags=["Stocks"],
)

app.include_router(
    crypto.router,
    tags=["Crypto"],
)

app.include_router(
    social.router,
    tags=["Social Media"],
)

app.include_router(
    macro.router,
    tags=["Macro Economics"],
)

app.include_router(
    news.router,
    tags=["News"],
)

app.include_router(
    portfolio.router,
    tags=["Portfolio & Alerts"],
)

app.include_router(
    chart.router,
    tags=["Chart Data"],
)

app.include_router(
    auth.router,
    tags=["Auth"],
)

app.include_router(
    watchlist.router,
    tags=["Watchlist"],
)

app.include_router(
    fi.router,
    tags=["Finland (Nasdaq Helsinki)"],
)

# ============================================================================
# Root & Health Endpoints
# ============================================================================

@app.get(
    "/",
    tags=["Root"],
    summary="API Root",
    description="Get API information and status"
)
async def root():
    """
    API root endpoint

    Returns basic information about the API including:
    - API name and version
    - Status
    - Available endpoints
    - Documentation links
    """
    return {
        "name": "TradeMaster Pro API",
        "version": "1.0.0",
        "status": "operational",
        "timestamp": datetime.now().isoformat(),
        "documentation": {
            "swagger": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "stocks": "/api/stocks",
            "crypto": "/api/crypto",
            "social": "/api/social",
            "macro": "/api/macro"
        },
        "features": [
            "Real-time market data",
            "AI-powered predictions",
            "Social sentiment analysis",
            "Macro economic indicators",
            "WebSocket support"
        ]
    }

@app.get(
    "/health",
    tags=["Health"],
    summary="Health Check",
    description="Check API health status"
)
async def health_check():
    """
    Health check endpoint

    Returns the current health status of the API.
    Used by monitoring systems and load balancers.

    Returns:
        dict: Health status information
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "TradeMaster Pro API",
        "version": "1.0.0"
    }

@app.get(
    "/ping",
    tags=["Health"],
    summary="Ping",
    description="Simple ping endpoint"
)
async def ping():
    """Simple ping endpoint for connectivity testing"""
    return {"ping": "pong"}

# ============================================================================
# Startup & Shutdown Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """
    Execute on application startup

    - Initialize database connections
    - Start background tasks
    - Load ML models
    """
    print("=" * 60)
    print("🚀 TradeMaster Pro API Starting...")
    print("=" * 60)
    print(f"📊 Version: 1.0.0")
    print(f"🌐 Docs: http://localhost:8000/docs")
    print(f"📡 Socket.IO: Enabled")
    print(f"🔒 CORS: Configured for localhost:3000")
    print("=" * 60)

    # Initialize database
    try:
        from app.models.database import init_db
        init_db()
    except Exception as e:
        print(f"Database initialization failed: {e}")
        print("=" * 60)

    # Start background scheduler for auto-updates (single worker only)
    if os.getenv("SCHEDULER_ENABLED", "true").lower() == "true":
        if _acquire_scheduler_lock():
            try:
                from app.services.scheduler_service import get_scheduler
                scheduler = get_scheduler()
                scheduler.start()
                print("? Background scheduler started!")
                print("   ?? News: Auto-refresh every 5 minutes")
                print("   ?? Market data: Auto-refresh every 2 minutes")
                print("=" * 60)
            except Exception as e:
                print(f"??  Background scheduler failed: {e}")
                print("=" * 60)
        else:
            print("??  Background scheduler already running; skipping start")

    # Start Finnish stocks cache warming in background (Redis lock prevents duplicates)
    try:
        from app.services.fi_data import get_fi_data_service
        fi_service = get_fi_data_service()
        fi_service.warm_cache_async()
        print("🇫🇮 Finnish stocks cache warming requested")
        print("=" * 60)
    except Exception as e:
        print(f"⚠️  Finnish cache warming failed: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Execute on application shutdown

    - Close database connections
    - Stop background tasks
    - Cleanup resources
    """
    print("=" * 60)
    print("🛑 TradeMaster Pro API Shutting down...")
    print("=" * 60)

    # Stop background scheduler
    try:
        from app.services.scheduler_service import get_scheduler
        scheduler = get_scheduler()
        scheduler.stop()
        print("✅ Background scheduler stopped")
    except Exception as e:
        print(f"⚠️  Scheduler shutdown error: {e}")
    if SCHEDULER_LOCK_ACQUIRED:
        try:
            os.remove(SCHEDULER_LOCK_PATH)
        except FileNotFoundError:
            pass

