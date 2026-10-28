"""
CROP_TABLE: PDF Reference Table 1 (crop categories)
PUMP_TABLE: PDF Reference Table 2 (solar pump catalog)
PUE_TABLE: PDF Reference Table 3 (productive use of energy catalog)
HCAT_PREFIX_TO_CATEGORY: Mapping of HCAT codes to PDF macro categories (10, 20, 30, 50, Other)

The PDF says to use the first two digits of EC_hcat_c, but every code in PT.zip
starts with "33" (HCAT's agriculture prefix), so that rule cannot work. Instead we
map by deeper HCAT levels and treat 10/20/30/50 as category labels, not code digits.

For detailed explanation on how the mapping was derived, see hcat_mapping_explained.md in this repo.

"""

# PDF Reference Table 1, one entry per category code (units in the key names)
OTHER = "Other"  # PDF's "Other/NA" fallback field crop
CROP_TABLE = {
    "10": {
        "name": "Cereals & Grains",
        "water_m3_ha_day": 35,
        "yield_t_ha": 7.0,
        "price_usd_kg": 0.25,
    },
    "20": {
        "name": "Orchards & Fruits",
        "water_m3_ha_day": 45,
        "yield_t_ha": 12.0,
        "price_usd_kg": 0.80,
    },
    "30": {
        "name": "Pastures & Meadows",
        "water_m3_ha_day": 15,
        "yield_t_ha": 4.0,
        "price_usd_kg": 0.10,
    },
    "50": {
        "name": "Vegetables / High-Value",
        "water_m3_ha_day": 55,
        "yield_t_ha": 25.0,
        "price_usd_kg": 0.60,
    },
    OTHER: {
        "name": "Fallback Field Crop",
        "water_m3_ha_day": 30,
        "yield_t_ha": 5.0,
        "price_usd_kg": 0.30,
    },
}


# PDF Reference Table 2: IDCOL solar irrigation pump catalog
PUMP_TABLE = {
    "Tier 1": {"motor_kw": 3.7, "pv_kwp": 5.0, "capex_usd": 7_500, "max_m3_day": 250},
    "Tier 2": {"motor_kw": 5.5, "pv_kwp": 7.5, "capex_usd": 10_500, "max_m3_day": 400},
    "Tier 3": {"motor_kw": 7.5, "pv_kwp": 10.0, "capex_usd": 14_000, "max_m3_day": 580},
    "Tier 4": {
        "motor_kw": 11.0,
        "pv_kwp": 15.0,
        "capex_usd": 19_500,
        "max_m3_day": 850,
    },
}


# PDF Reference Table 3: Productive Use of Energy (PUE) catalog
# crops = compatible category codes from CROP_TABLE; the uplift formulas live in the Task 4 code
PUE_TABLE = {
    "Cold Room": {  # 5 MT; prevents 20% spoilage on total harvested volume
        "crops": ["20", "50"],
        "load_kwh_day": 20.0,
        "capex_usd": 6_000,
        "spoilage_prevented": 0.20,
    },
    "Grain Mill": {  # earns a processing fee on milled grain
        "crops": ["10"],
        "load_kwh_day": 25.0,
        "capex_usd": 4_500,
        "fee_usd_kg": 0.05,
    },
    "Solar Dryer": {  # hybrid dryer; premium price on the dried share of the harvest
        "crops": ["10", "20", "50"],
        "load_kwh_day": 10.0,
        "capex_usd": 2_500,
        "premium_usd_kg": 0.12,
        "dried_share": 0.15,
    },
}


# EC_hcat_c code gets the category of pdf reference table 1.
HCAT_PREFIX_TO_CATEGORY = {
    # 10 Cereals & Grains
    "330101": "10",  # wheat, maize, barley, oats, rice, rye etc
    # 20 Orchards & Fruits
    "3303": "20",  # fruit trees, olives, vineyards etc
    # 30 Pastures & Meadows
    "3302": "30",  # permanent grassland
    "330109": "30",  # ryegrass, alfalfa, clover etc
    # 50 Vegetables / High-Value. HCAT has no single "vegetables" prefix, so manual filter used
    "330103": "50",  # potatoes
    "330104": "50",  # sweet potatoes
    "330107": "50",  # fresh vegetables
    "330113": "50",  # strawberries
    "330114": "50",  # melon, watermelon, pumpkin, zucchini
    "330121": "50",  # cabbage, mustard, cress
    "330122": "50",  # garlic, onions
    "330126": "50",  # aubergine
    "330128": "50",  # tomato
    "330129": "50",  # beetroot, carrots, turnips
    "330131": "50",  # lettuce, salads, spinach
    "3301061228": "50",  # bell pepper
    # Everything else (pulses, oilseeds, herbs, flowers, fallow, forest, unknown) goes to Other
}
