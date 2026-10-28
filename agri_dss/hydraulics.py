import geopandas as gpd
from agri_dss.data_mapping import CROP_TABLE


def add_water_demand(cluster: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Add a water_m3_day column: each parcel's daily water need (m³/day).

    water_m3_day = area_ha × crop water demand (m³/ha/day, PDF Table 1).
    Summing this column gives the cluster's Q_day = Σ(Area_i × WaterDemand_i).
    """
    cluster = cluster.copy()
    demand_m3_ha_day = cluster["category"].map(
        lambda code: CROP_TABLE[code]["water_m3_ha_day"]
    )
    cluster["water_m3_day"] = cluster["area_ha"] * demand_m3_ha_day  # ha × m³/ha/day
    return cluster


def pump_power_kw(q_day: float) -> float:
    """Required pump power (kW) to deliver q_day (m³/day) of water.

    Power = ρ · g · Q_day · H / (3.6×10⁶ · t_pump · η)
    """
    # Pump sizing assumptions
    water_density_kg_m3 = 1000  # ρ
    gravity_m_s2 = 9.81  # g
    pump_head_m = 40  # H: total dynamic head (static water depth + friction losses)
    pump_hours_per_day = 6  # t_pump: operating pumping duration
    pump_efficiency = 0.55  # η: pump and motor subsystem efficiency
    joules_per_kwh = 3.6e6  # 1 kWh = 1000 W × 3600 s
    if q_day < 0:
        raise ValueError(f"Daily water demand cannot be negative, got {q_day}")

    # ρ·g·Q·H = energy to lift the water (J/day); ÷ 3.6e6 -> kWh/day
    energy_kwh_day = (
        water_density_kg_m3 * gravity_m_s2 * q_day * pump_head_m / joules_per_kwh
    )
    # ÷ pumping hours -> kW; ÷ efficiency -> power the pump actually needs
    return energy_kwh_day / pump_hours_per_day / pump_efficiency
