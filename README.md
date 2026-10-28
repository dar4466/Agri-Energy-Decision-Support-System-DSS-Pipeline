# Agri-Energy Decision Support System (DSS)

Prototype engine that evaluates a farming cluster around a given location and sizes a solar-powered irrigation system for it:

1. **Spatial ingestion & clustering**: finds all agricultural parcels within 150 m of a coordinate (EuroCrops Portugal) and classifies their crops.
2. **Hydraulic demand & solar resource**: computes the cluster's daily water demand, the required pump power, and Peak Sun Hours from NASA POWER.
3. **Equipment matching & surplus energy**: selects pumps from the IDCOL catalog and models daily solar generation, pump consumption and surplus energy.
4. **Productive Use of Energy (PUE)**: picks the most profitable machine (cold room, grain mill or solar dryer) the surplus energy can run, with its annual uplift and payback, or returns "no investment".

## Requirements

- Python 3.12+
- Internet access on first run (downloads the parcel dataset and NASA POWER data; both are cached locally afterwards and can be used again for the same cluster lat lon without internet access)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip && pip install -r requirements.txt
```

## Usage

Run from the project root:

```bash
python dss_pipeline.py --lat 41.8597 --lon -6.7990
```

`--lat` / `--lon` are WGS84 decimal degrees. Without arguments, the default location is lat `38.0157`, lon `-7.8809` (a wheat parcel in Alentejo).

Example output (cluster-level results):

```
parcels                    2
total_area_ha              0.558
q_day_m3_day               30.705
pump_power_kw              1.014
lowest_month               DEC
lowest_psh                 1.631
avg_psh                    4.542
pumps                      ['Tier 1']
avg_solar_kwh_day          17.031
pump_consumption_kwh_day   6.085
surplus_kwh_day            10.946
pue_status                 invest
pue_asset                  Solar Dryer
pue_annual_uplift_usd      251.219
pue_payback_years          9.951
```

When no asset qualifies, the result says why instead of giving a payback, e.g. for a cluster whose pumps use all the solar energy:

```bash
python dss_pipeline.py --lat 38.2584 --lon -7.9249
```

```
surplus_kwh_day            0.0
pue_status                 no investment
pue_reason                 no surplus solar energy
```

A location with no parcels within 150 m (urban area, water body, outside Portugal) ends with `EmptyClusterError`:

```bash
python dss_pipeline.py --lat 38.722 --lon -9.139   # central Lisbon
```

## Tests

```bash
python -m pytest
```

Verifies Task 1: a valid agricultural location returns parcels, and central Lisbon raises `EmptyClusterError`.

## Project structure

```
dss_pipeline.py            Entry point: CLI, logging, run_pipeline() in task order
agri_dss/
  data_loader.py           Download PT.zip, load parcels, repair geometries, reproject to EPSG:3763
  clustering.py            150 m buffer + spatial index query, EmptyClusterError, area, crop category, centroid
  data_mapping.py          PDF reference tables 1-3 and the HCAT -> crop category mapping
  hydraulics.py            Daily water demand and required pump power
  solar.py                 NASA POWER request (cached) and Peak Sun Hours
  energy.py                Pump tier selection, solar generation, pump consumption, surplus
  pue.py                   Harvest, annual uplift per PUE asset, asset selection and payback
tests/                     Task 1 verification (Task 1.4, checking on hardcoded two locations)
hcat_mapping_explained.md  How EuroCrops HCAT codes were mapped to the PDF crop categories
```

Outputs are kept at two levels: a per-parcel table (area, category, water demand and harvest per parcel) and a cluster-level `results` dictionary.

## Key assumptions

- **Coordinate systems**: parcels are reprojected to ETRS89 / Portugal TM06 (EPSG:3763, meters) before buffering and area calculation. The input point is created in WGS84 (EPSG:4326) and reprojected before the 150 m buffer is applied.
- **Crop categories**: the task description maps the first two digits of `EC_hcat_c` to categories 10/20/30/50, but every code in PT.zip starts with `33` (HCAT's agriculture prefix). Codes are mapped by deeper HCAT levels instead; see `hcat_mapping_explained.md`.
- **Parcel area**: whole parcel areas are used, not only the part inside the buffer, since whole fields are irrigated.
- **NASA units**: the task description's NASA POWER URL (`community=AG`) returns MJ/m²/day; values are converted to kWh/m²/day (Peak Sun Hours) by dividing by 3.6. Responses are cached in `data/.cache/` since climatology is a multi-year average.
- **Multiple pumps**: if the required power exceeds Tier 4, as many Tier 4 pumps as fit fully are used, plus the smallest tier covering the remainder (e.g. 15.01 kW -> Tier 4 + Tier 2, cheaper than 2 x Tier 4).
- **Pump consumption**: `E_pump` uses the required pump power rather than the rated motor power. Energy use follows the water actually pumped, and with rated power the surplus is zero for every Portuguese location (each tier's panels are only ~35% larger than its motor).
- **Harvest**: each parcel's annual fresh harvest is area × its category's yield (Table 1), converted from tons to kg. Each PUE asset only counts the parcels whose category it is compatible with (Table 3); pastures and Other are compatible with no asset.
- **PUE uplift**: the task description gives no operating costs, so the annual net uplift equals the gross uplift from Table 3: cold room = 20% of compatible harvest × each crop's farmgate price; grain mill = $0.05/kg of cereal harvest; solar dryer = $0.12/kg on 15% of compatible harvest. At most one asset is recommended: the qualifying one with the highest annual uplift.

## Known limitations

- **Large estates**: because whole parcel areas are counted, a buffer that touches the edge of a very large parcel (hundreds of hectares) attributes the entire estate's water demand to one communal well, which can require 20+ pumps. Clipping parcels to the 150 m buffer would cap the cluster at ~7 ha.
- **Dataset coverage**: PT.zip contains 100,000 parcels and does not cover all of Portugal.
- **PUE outcomes**: with the task description's tables, the surplus never exceeds ~18 kWh/day (a Tier 1 system with almost no pumping load: 5 kWp × ~4.9 PSH × 0.75). The cold room (20 kWh/day) and grain mill (25 kWh/day) can therefore never qualify, so the result is always the solar dryer or no investment. In a survey of 10,000 random locations, roughly a third qualified for the dryer; the best paybacks (~10 years) come from small vegetable clusters on a Tier 1 pump.
- **Category-level crop values**: yields, prices and water demand are per macro category (Table 1), so all crops in a category share one value (e.g. olives and apples both use 12 t/ha).

## Scaling to regional analysis (Monte Carlo)

`run_pipeline(lat, lon)` evaluates one cluster with fixed inputs. To model regional policy incentives, it can be called repeatedly in a Monte Carlo loop:

1. **Sample**: in each iteration, pick a random location in the region (drawn from the parcel data) and draw uncertain inputs from plausible ranges, e.g. crop prices and yields ±20%, PSH ±5%, equipment CAPEX.
2. **Apply the policy**: e.g. a 50% CAPEX subsidy on PUE assets or pumps.
3. **Run**: call `run_pipeline` for the sampled location and inputs.
4. **Aggregate**: over thousands of iterations, report the share of clusters that invest, the payback distribution and the total subsidy cost. Comparing these results across policies shows which incentive changes outcomes most.

The only code change needed is to let `run_pipeline` take the reference tables (`CROP_TABLE`, `PUMP_TABLE`, `PUE_TABLE`) as optional parameters instead of using the module-level constants, so each iteration can pass its own sampled values.
