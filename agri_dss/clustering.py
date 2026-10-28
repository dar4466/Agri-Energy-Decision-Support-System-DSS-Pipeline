import geopandas as gpd
from agri_dss.data_mapping import CROP_TABLE, HCAT_PREFIX_TO_CATEGORY, OTHER

BUFFER_RADIUS_M = 150  # communal tube-well command zone radius (~7 ha)
METRIC_CRS = 3763  # ETRS89 / Portugal TM06, units in meters


class EmptyClusterError(Exception):
    """Raised when no agricultural parcels intersect the buffer around a location."""


def validate_coordinates(lat: float, lon: float) -> None:
    """Raise ValueError unless lat/lon are valid WGS84 decimal degrees (also rejects nan/inf)."""
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError(f"Invalid decimal degree coordinates: lat={lat}, lon={lon}")


def find_cluster(parcels: gpd.GeoDataFrame, lat: float, lon: float) -> gpd.GeoDataFrame:
    """Return the parcels intersecting a 150 m buffer around (lat, lon).

    parcels must be in EPSG:3763 (meters); lat/lon are WGS84 decimal degrees.
    Raises EmptyClusterError if no parcels intersect the buffer.
    """
    if parcels.crs != METRIC_CRS:
        # Mixed CRS would silently return no matches (degrees vs meters)
        raise ValueError(f"Parcels must be in EPSG:{METRIC_CRS}, got {parcels.crs}")

    # Point in WGS84 -> reproject to meters -> buffer. Note: x = lon, y = lat
    point = gpd.GeoSeries.from_xy([lon], [lat], crs=4326).to_crs(METRIC_CRS)
    circle = point.buffer(BUFFER_RADIUS_M).iloc[0]

    # Spatial index on the parcels: bounding-box pre-filter, then exact intersects check
    idx = parcels.sindex.query(circle, predicate="intersects")
    cluster = parcels.iloc[idx]

    if cluster.empty:
        raise EmptyClusterError(
            "Location is out of agricultural domain or contains no parcels within the 150m radius."
        )
    return cluster


def cluster_centroid(cluster: gpd.GeoDataFrame) -> tuple[float, float]:
    """Return the cluster's centre point as (lat, lon) in WGS84 decimal degrees."""
    centre = cluster.union_all().centroid  # centre of all parcels together, in meters
    centre = gpd.GeoSeries([centre], crs=cluster.crs).to_crs(4326).iloc[0]
    return centre.y, centre.x  # y = lat, x = lon


def add_area_ha(cluster: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add an area_ha column with each parcel's surface area in hectares.

    Uses the whole parcel area (not just the part inside the 150 m buffer), since
    farmers irrigate whole fields. Cluster must be in a metric CRS (EPSG:3763).
    Cross-check: matches the dataset's own OSA_AREA column (m²) for the test parcel.
    """
    cluster = cluster.copy()  # find_cluster returns a slice; copy before adding a column
    cluster["area_ha"] = cluster.geometry.area / 10_000  # m² -> ha
    return cluster


def assign_category(code: str) -> str:
    """Return the PDF macro category ("10", "20", "30", "50" or "Other") for an HCAT code."""
    if not isinstance(code, str) or not code.strip():
        return OTHER  # missing code -> PDF's "Other / NaN" row

    code = code.strip()
    for prefix, category in HCAT_PREFIX_TO_CATEGORY.items():
        if code.startswith(prefix):
            return category  # first match wins; return ends the loop
    return OTHER  # no prefix matched


def add_crop_category(cluster: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add category (PDF Table 1 code) and category_name columns from EC_hcat_c."""
    cluster = cluster.copy()
    cluster["category"] = cluster["EC_hcat_c"].apply(assign_category)
    cluster["category_name"] = cluster["category"].map(
        lambda code: CROP_TABLE[code]["name"]
    )
    return cluster
