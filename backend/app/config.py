from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Server settings
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    BACKEND_RELOAD: bool = True

    # Data paths (relative to project root, one level up from backend/)
    DEM_PATH: str = "../data/processed/dem/filled_dem.tif"
    FLOW_DIR_PATH: str = "../data/processed/dem/flow_direction.tif"
    FLOW_ACC_PATH: str = "../data/processed/dem/flow_accumulation.tif"
    GEOLOGY_PATH: str = "../data/processed/geology.gpkg"
    FAIRFAX_WATERSHEDS_PATH: str = "../data/processed/fairfax_watersheds.gpkg"

    # Dataset mapping for logical layer names to file paths
    # Maps frontend layer IDs to (file_path, layer_name) tuples
    LAYER_DATASET_MAP: dict = {
        "geology": ("../data/processed/geology.gpkg", None),
        "fairfax-watersheds": ("../data/processed/fairfax_watersheds.gpkg", "fairfax_watersheds"),
        "fairfax-water-lines": ("../data/processed/fairfax_water_lines.gpkg", "fairfax_water_lines"),
        "fairfax-water-polys": ("../data/processed/fairfax_water_polys.gpkg", "fairfax_water_polys"),
        "inadequate-outfalls": ("../data/raw/fairfax/inadequate_outfalls.gpkg", "inadequate_outfalls")
    }

    # Watershed delineation settings
    SNAP_TO_STREAM: bool = True
    DEFAULT_SNAP_RADIUS: int = 100  # meters
    CACHE_ENABLED: bool = True
    CACHE_DIR: str = "./data/cache"

    # PMTiles URLs
    PUBLIC_HILLSHADE_URL: str = "/tiles/hillshade.pmtiles"
    PUBLIC_SLOPE_URL: str = "/tiles/slope.pmtiles"
    PUBLIC_ASPECT_URL: str = "/tiles/aspect.pmtiles"
    PUBLIC_STREAMS_URL: str = "/tiles/streams.pmtiles"
    PUBLIC_GEOLOGY_URL: str = "/tiles/geology.pmtiles"
    PUBLIC_CONTOURS_URL: str = "/tiles/contours.pmtiles"

    # Cross-section settings
    CROSS_SECTION_SAMPLE_DISTANCE: int = 10  # meters
    CROSS_SECTION_MAX_POINTS: int = 1000

    # CORS settings
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Optional Redis settings
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0


settings = Settings()
