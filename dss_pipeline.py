## DEPENDENCIES
import sys
import logging
import argparse
from time import perf_counter

try:
    import geopandas as gpd
    from agri_dss.data_loader import url_downloader, load_parcels
    from agri_dss.clustering import (
        EmptyClusterError,
        validate_coordinates,
        find_cluster,
        cluster_centroid,
        add_area_ha,
        add_crop_category,
    )
    from agri_dss.hydraulics import add_water_demand, pump_power_kw
    from agri_dss.solar import fetch_nasa_solar, solar_peak_hours
    from agri_dss.energy import (
        select_pumps,
        avg_solar_kwh_day,
        pump_consumption_kwh_day,
        surplus_kwh_day,
    )
    from agri_dss.pue import add_harvest_kg, select_pue

except ModuleNotFoundError as e:
    missing_module = e.name
    print(f"❌ Required module not found: '{missing_module}'.")
    sys.exit(1)
except ImportError as e:
    # For C-extension or version issues
    print(f"❌ ImportError: {e}")
    print("   This may happen if the package is partially installed or incompatible.")
    sys.exit(1)


## SETTINGS
DATA_URL = "https://zenodo.org/records/10118572/files/PT.zip"
DECIMALS = 3  # rounding for console output only; calculations keep full precision

logger = logging.getLogger(__name__)


## PIPELINE
def run_pipeline(lat: float, lon: float) -> tuple[gpd.GeoDataFrame, dict]:
    """Run all tasks for one location, in PDF order.

    Returns two levels of output:
      cluster -> per-parcel values (one row per parcel, a column per step)
      results -> cluster-level values (one number each, an entry per step)
    """
    # Check the user's input first, before any slow loading
    validate_coordinates(lat, lon)

    # --- Task 1: spatial ingestion & clustering
    parcels = load_parcels(url_downloader(DATA_URL))
    logger.info(f"Loaded {len(parcels)} parcels, CRS {parcels.crs}.")

    cluster = find_cluster(parcels, lat, lon)
    logger.info(f"Found {len(cluster)} parcel/s within 150 m of ({lat}, {lon}).")
    cluster = add_area_ha(cluster)
    cluster = add_crop_category(cluster)

    # --- Task 2: hydraulic demand & NASA solar data
    cluster = add_water_demand(cluster)
    results = {
        "parcels": len(cluster),
        "total_area_ha": cluster["area_ha"].sum(),
        "q_day_m3_day": cluster["water_m3_day"].sum(),
    }
    results["pump_power_kw"] = pump_power_kw(results["q_day_m3_day"])

    centroid_lat, centroid_lon = cluster_centroid(cluster)
    nasa_data = fetch_nasa_solar(centroid_lat, centroid_lon)
    results.update(solar_peak_hours(nasa_data))  # lowest_month, lowest_psh, avg_psh

    # --- Task 3: equipment matching & surplus energy
    results["pumps"] = select_pumps(results["pump_power_kw"])
    results["avg_solar_kwh_day"] = avg_solar_kwh_day(
        results["pumps"], results["avg_psh"]
    )
    results["pump_consumption_kwh_day"] = pump_consumption_kwh_day(
        results["pump_power_kw"]
    )
    results["surplus_kwh_day"] = surplus_kwh_day(
        results["avg_solar_kwh_day"], results["pump_consumption_kwh_day"]
    )

    # --- Task 4: productive use of energy (PUE)
    cluster = add_harvest_kg(cluster)
    results.update(select_pue(cluster, results["surplus_kwh_day"]))

    return cluster, results


## EXECUTE
def main() -> None:
    """Command line entry point: read args, set up logging, run, report, handle errors."""
    # Read --lat / --lon from the command line (argparse converts them to float).
    # Defaults: a valid point inside a wheat parcel ~1.3 km west of the PDF's Alentejo
    # example (38.015, -7.865), which has no parcels within 150 m in PT.zip
    parser = argparse.ArgumentParser(description="Agri-Energy DSS pipeline")
    parser.add_argument(
        "--lat", type=float, default=38.0157, help="Latitude in decimal degrees"
    )
    parser.add_argument(
        "--lon", type=float, default=-7.8809, help="Longitude in decimal degrees"
    )
    args = parser.parse_args()

    # Setup logging once for the whole program (all modules' messages print here)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    try:
        start_time = perf_counter()
        logger.info("Starting the Agri DSS pipeline...")

        cluster, results = run_pipeline(args.lat, args.lon)

        columns = [
            "EC_hcat_n",
            "category",
            "category_name",
            "area_ha",
            "water_m3_day",
            "harvest_kg",
        ]
        parcels_text = cluster[columns].round(DECIMALS).to_string(index=False)
        logger.info(f"Cluster parcels:\n{parcels_text}")

        results_text = "\n".join(
            f"  {key:<26} {round(value, DECIMALS) if isinstance(value, float) else value}"
            for key, value in results.items()
        )
        logger.info(f"Cluster results:\n{results_text}")

        elapsed_time = perf_counter() - start_time
        logger.info(f"✅  Computation completed in {elapsed_time:.2f} seconds.")

    except EmptyClusterError as e:
        # Expected outcome for urban/water/out-of-Portugal locations, not a crash
        logger.warning(f"⚠️  {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()


# TEST COMMANDS (each covers a different case)
# --- Input errors (stop before loading data)
# python dss_pipeline.py --lat 300 --lon 10            # invalid coordinates -> ValueError
# python dss_pipeline.py --lat nan --lon -7.88         # nan coordinates -> ValueError
# python dss_pipeline.py --lat abc                     # not a number -> argparse error (exit 2)
# --- Task 1: no parcels within 150 m -> EmptyClusterError
# python dss_pipeline.py --lat 38.722 --lon -9.139     # central Lisbon (urban)
# python dss_pipeline.py --lat 38.015 --lon -7.865     # task's Alentejo example: no parcels in PT.zip
# --- Task 1-2: cluster sizes and crop mixes
# python dss_pipeline.py                               # default: 1 wheat parcel
# python dss_pipeline.py --lat 41.8382 --lon -6.5858   # 15 parcels, all 5 crop categories
# --- Task 3: pump selection
# python dss_pipeline.py --lat 38.2584 --lon -7.9249   # 2 pumps (Tier 4 + Tier 2), surplus 0
# python dss_pipeline.py --lat 38.6576 --lon -8.6184   # 3 pumps (Tier 4 + Tier 4 + Tier 1)
# python dss_pipeline.py --lat 37.9243 --lon -8.4095   # 4 pumps (3 x Tier 4 + Tier 3)
# python dss_pipeline.py --lat 38.9259 --lon -7.6788   # 25 pumps: huge estate (known limitation)
# --- Task 4: PUE decision
# python dss_pipeline.py --lat 41.8597 --lon -6.7990   # invest: Solar Dryer, payback ~10 years
# python dss_pipeline.py --lat 41.0527 --lon -8.2705   # invest: Solar Dryer, payback ~29 years
# python dss_pipeline.py --lat 38.2584 --lon -7.9249   # no investment: no surplus (0 kWh/day)
# python dss_pipeline.py --lat 41.8382 --lon -6.5858   # no investment: surplus 8.4 < dryer's 10
# python dss_pipeline.py --lat 38.9904 --lon -9.1296   # no investment: surplus 18 but pasture only
