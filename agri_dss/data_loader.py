import shutil
import logging
import urllib.request
import geopandas as gpd
from pathlib import Path

logger = logging.getLogger(__name__)


def url_downloader(url: str) -> Path:
    """Download url into ./data and return the file path. Skips if already downloaded.

    Gives up after 30 s without a response, so a dead connection can't hang the pipeline.
    """
    file_path = Path("data") / Path(url).name

    if file_path.exists():
        logger.info(f"File {file_path} already exists. Skipping download.")
        return file_path

    file_path.parent.mkdir(exist_ok=True)
    try:
        # Stream the response into the file; timeout stops it hanging forever on a dead connection
        with urllib.request.urlopen(url, timeout=30) as response, open(
            file_path, "wb"
        ) as f:
            shutil.copyfileobj(response, f)
        logger.info(f"File downloaded to {file_path}.")
    except Exception as e:  # wrong URL (404 etc.), no internet, or timeout
        file_path.unlink(missing_ok=True)  # don't leave a half-downloaded file behind
        raise RuntimeError(f"Download failed for {url}: {e}") from e

    return file_path


def load_parcels(file_path: Path, crs: int = 3763) -> gpd.GeoDataFrame:
    """Read parcels, repair invalid geometries, and reproject to crs (default EPSG:3763, meters)."""

    file_path = Path(file_path)  # also accepts plain strings
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    try:
        gdf = gpd.read_file(file_path)
    except Exception as e:  # corrupt zip, unreadable format
        raise RuntimeError(f"Could not read {file_path}: {e}") from e

    if gdf.empty:
        raise ValueError(f"No parcels found in {file_path}")
    if gdf.crs is None:
        raise ValueError(f"{file_path} has no CRS; cannot reproject safely")

    if gdf.crs != crs:
        logger.info(f"Converting CRS from {gdf.crs} to EPSG:{crs}.")
        gdf = gdf.to_crs(epsg=crs)

    # Drop missing geometries and repair invalid ones.
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()
    gdf["geometry"] = gdf.geometry.make_valid()
    return gdf
