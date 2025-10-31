from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from pathlib import Path

from app.routes import delineate, cross_section, features, tiles
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    print(f"Starting Hydro-Map API server...")
    print(f"DEM path: {settings.DEM_PATH}")
    print(f"Cache enabled: {settings.CACHE_ENABLED}")

    # Ensure cache directory exists
    if settings.CACHE_ENABLED:
        Path(settings.CACHE_DIR).mkdir(parents=True, exist_ok=True)

    yield

    # Shutdown
    print("Shutting down Hydro-Map API server...")


app = FastAPI(
    title="Hydro-Map API",
    description="API for watershed delineation, cross-sections, and hydrological/geological data",
    version="0.1.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(delineate.router, prefix="/api", tags=["delineate"])
app.include_router(cross_section.router, prefix="/api", tags=["cross-section"])
app.include_router(features.router, prefix="/api", tags=["features"])

# Include tiles router for PMTiles serving with range request support
app.include_router(tiles.router)


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Hydro-Map API",
        "version": "0.1.0",
        "endpoints": {
            "delineate": "/api/delineate",
            "cross_section": "/api/cross-section",
            "feature_info": "/api/feature-info",
            "docs": "/docs",
            "tiles": "/tiles"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.BACKEND_HOST,
        port=settings.BACKEND_PORT,
        reload=settings.BACKEND_RELOAD
    )
