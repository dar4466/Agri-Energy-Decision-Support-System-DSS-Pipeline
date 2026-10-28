import logging
from agri_dss.data_mapping import PUMP_TABLE

logger = logging.getLogger(__name__)


def select_pumps(required_kw: float) -> list[str]:
    """Pick pump tiers whose motor power together covers required_kw (PDF Table 2).

    If required_kw exceeds the largest tier, the PDF says multiple pumps are needed.
    We use as many of the largest tier as fit fully, then the smallest tier that covers
    what's left, e.g. 15.01 kW -> Tier 4 (11 kW) + Tier 2 (5.5 kW) instead of 2 x Tier 4.
    """
    largest_tier = list(PUMP_TABLE)[-1]
    largest_kw = PUMP_TABLE[largest_tier]["motor_kw"]

    full_pumps = int(required_kw // largest_kw)  # whole largest pumps that fit
    remaining_kw = required_kw - full_pumps * largest_kw
    pumps = [largest_tier] * full_pumps

    if remaining_kw > 0:
        for tier, pump in PUMP_TABLE.items():  # tiers are listed smallest first
            if pump["motor_kw"] >= remaining_kw:
                pumps.append(tier)  # first match wins
                break

    if len(pumps) > 1:
        logger.warning(f"{required_kw:.2f} kW exceeds {largest_tier}: pumps {pumps}.")
    return pumps


def avg_solar_kwh_day(pumps: list[str], avg_psh: float) -> float:
    """Electricity the solar panels make on an average day (kWh/day).

    PDF formula: E_PV = PV_kWp × PSH_avg × 0.75 (PV = photovoltaic = solar panels).
    Each pump comes with its own panels (PDF Table 2), so we add up every pump's panels.
    """
    losses = 0.75  # panels deliver 75% after heat, dust and wiring losses (fixed by PDF)
    panels_kw = sum(PUMP_TABLE[tier]["pv_kwp"] for tier in pumps)  # all panels together
    return panels_kw * avg_psh * losses  # kW × sun hours per day = kWh per day


def pump_consumption_kwh_day(required_kw: float) -> float:
    """Electricity the pumps use per day (kWh/day): E_pump = P_motor × t_pump.

    The PDF writes P_motor; we use the required power (pump_power_kw) rather than the
    rated motor_kw: energy use follows the water actually pumped, and the rated reading
    gives zero surplus for any Portuguese location (panels are only ~35% larger than motors).
    """
    pump_hours_per_day = 6  # t_pump: same 6 sunny pumping hours as in pump_power_kw
    return required_kw * pump_hours_per_day  # kW × hours per day = kWh per day


def surplus_kwh_day(avg_solar_kwh_day: float, pump_consumption_kwh_day: float) -> float:
    """Net daily surplus solar energy (kWh/day): E_excess = max(0, E_PV - E_pump).

    Solar made minus pump used, never below 0 (a shortfall means no surplus).
    """
    return max(0.0, avg_solar_kwh_day - pump_consumption_kwh_day)
