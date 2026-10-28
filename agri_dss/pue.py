import geopandas as gpd
from agri_dss.data_mapping import CROP_TABLE, PUE_TABLE


def add_harvest_kg(cluster: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add a harvest_kg column: each parcel's fresh harvest per year (kg).

    harvest_kg = area_ha × crop fresh yield (t/ha, PDF Table 1) × 1000 (t -> kg).
    """
    cluster = cluster.copy()
    yield_t_ha = cluster["category"].map(lambda code: CROP_TABLE[code]["yield_t_ha"])
    cluster["harvest_kg"] = cluster["area_ha"] * yield_t_ha * 1000  # ha × t/ha × kg/t
    return cluster


def annual_uplift_usd(asset: str, compatible: gpd.GeoDataFrame) -> float:
    """Money per year (USD) the asset earns from the compatible parcels' harvest (PDF Table 3)."""
    pue = PUE_TABLE[asset]
    harvest_kg = compatible["harvest_kg"]

    if asset == "Cold Room":  # 20% of the harvest saved from spoiling, at each crop's price
        price_usd_kg = compatible["category"].map(lambda code: CROP_TABLE[code]["price_usd_kg"])
        return (harvest_kg * price_usd_kg).sum() * pue["spoilage_prevented"]
    if asset == "Grain Mill":  # processing fee on every kg of grain milled
        return harvest_kg.sum() * pue["fee_usd_kg"]
    if asset == "Solar Dryer":  # price premium on the dried share of the harvest
        return harvest_kg.sum() * pue["dried_share"] * pue["premium_usd_kg"]
    raise ValueError(f"No uplift formula for PUE asset: {asset}")


def select_pue(cluster: gpd.GeoDataFrame, surplus_kwh_day: float) -> dict:
    """Pick the most profitable PUE asset the surplus can run, with its payback (PDF Task 4).

    An asset qualifies if the surplus covers its daily load and the cluster grows a
    compatible crop. If none qualifies, returns a "no investment" status instead of
    a payback (no division by zero).
    """
    if surplus_kwh_day <= 0:
        return {"pue_status": "no investment", "pue_reason": "no surplus solar energy"}

    # Annual uplift of every asset that passes both checks
    options = {}
    for asset, pue in PUE_TABLE.items():
        compatible = cluster[cluster["category"].isin(pue["crops"])]
        if surplus_kwh_day >= pue["load_kwh_day"] and not compatible.empty:
            options[asset] = annual_uplift_usd(asset, compatible)

    if not options or max(options.values()) <= 0:
        return {
            "pue_status": "no investment",
            "pue_reason": "surplus too small for any asset with compatible crops",
        }

    best = max(options, key=options.get)  # highest annual uplift
    uplift = options[best]
    return {
        "pue_status": "invest",
        "pue_asset": best,
        "pue_annual_uplift_usd": uplift,
        "pue_payback_years": PUE_TABLE[best]["capex_usd"] / uplift,
    }
