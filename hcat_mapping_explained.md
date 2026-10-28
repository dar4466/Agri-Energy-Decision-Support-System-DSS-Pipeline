# HCAT code to crop category mapping

How the EuroCrops crop codes in `PT.zip` (`EC_hcat_c`) are mapped to the macro crop categories of the task description's Reference Table 1. The mapping is implemented in `agri_dss/data_mapping.py` (`HCAT_PREFIX_TO_CATEGORY`) and `agri_dss/clustering.py` (`assign_category`).

## The problem

The task description says to map the **first two digits** of `EC_hcat_c` to categories `10`, `20`, `30` and `50`. In `PT.zip`, all 79 distinct codes start with `33`, which is HCAT's prefix for agriculture, so that rule would put every parcel in one category.

Instead, codes are mapped by their deeper HCAT levels, and `10` / `20` / `30` / `50` are treated as category labels rather than digits in the code.

## Relevant dataset columns

| Column | Content |
|---|---|
| `EC_hcat_c` | 10-digit HCAT code encoding the crop's place in the hierarchy |
| `EC_hcat_n` | Machine-readable HCAT crop name |
| `EC_trans_n` | Original national crop name, translated to English |
| `EC_org_n` | Original national crop name (Portuguese) |

## How HCAT codes are structured

The 10-digit code is made of 2-digit levels, read like a folder path:

```
33 | 01 | 01 | 03 | 00     →  agriculture / arable crops / cereals / rye
```

| Digits | Level | Values in PT.zip |
|---|---|---|
| 1–2 | Domain | `33` agriculture (all codes) |
| 3–4 | Land use class | `01` arable crops, `02` grassland, `03` permanent crops, `06` forest/trees, `99` not known |
| 5–6 | Crop group | e.g. `330101` cereals, `330109` plants harvested green (fodder), `330128` tomato |
| 7–10 | Individual crop / variety | e.g. `3301010300` rye |

The structure was verified against the HCAT taxonomy published by the EuroCrops project (HCAT2/HCAT3 code lists and hierarchy):

- https://collections.eurodatacube.com/eurocrops/
- https://github.com/maja601/EuroCrops

## Mapping rules

A code is assigned the category of the first prefix it starts with; codes matching no prefix fall back to **Other**.

| Category | Prefixes | Reasoning |
|---|---|---|
| **10** Cereals & Grains | `330101` | HCAT cereals group |
| **20** Orchards & Fruits | `3303` | All permanent crops: fruit trees, olives, vineyards, nuts, citrus, berries (perennial woody crops) |
| **30** Pastures & Meadows | `3302`, `330109` | Permanent grassland, plus fodder sown on arable land (temporary grass, ryegrass, alfalfa, clover) |
| **50** Vegetables / High-Value | `330103`, `330104`, `330107`, `330113`, `330114`, `330121`, `330122`, `330126`, `330128`, `330129`, `330131`, `3301061228` | HCAT has no single vegetables prefix: each vegetable group is a sibling of cereals under `3301`, so all 46 arable codes in PT.zip were reviewed and the vegetable groups listed individually |
| **Other** Fallback Field Crop | everything else | Pulses, oilseeds, herbs, flowers, fallow land, forest, other arable crops and not known; this is the task description's "Other / NaN" row |

### Special cases

- **Bell pepper** (`3301061228`, `piper_pepper`): the original Portuguese record is `PIMENTO` (bell pepper), mislabelled as *Piper* (the spice) in EuroCrops. It is mapped to Vegetables by its full code, since the rest of its group `330106` (oilseeds, herbs) belongs to Other.
- **Wire bush** (`3303080700`): the original Portuguese record is `SUPERFÍCIE ARBUSTIVA NÃO PASTOREÁVEL` (non-grazable shrubland). It is kept under Orchards to apply the HCAT hierarchy consistently.
- **Fallow land and forest**: not irrigated in practice, but kept in Other to follow the task description's fallback rule.

## Result

| Category | Codes | Parcels in PT.zip |
|---|---|---|
| 10 Cereals & Grains | 9 | 6,471 |
| 20 Orchards & Fruits | 28 | 32,478 |
| 30 Pastures & Meadows | 6 | 21,056 |
| 50 Vegetables / High-Value | 21 | 3,003 |
| Other Fallback Field Crop | 15 | 36,992 |
| **Total** | **79** | **100,000** |

The full code-by-code mapping, which was reviewed by hand and against which the implementation was checked (79/79 match), is in `data/pt_unique_code_mapping.csv`.

## Codes per category

### 10 Cereals & Grains

| EC_hcat_c | EC_hcat_n | Parcels |
|---|---|---|
| 3301010100 | common_soft_wheat | 191 |
| 3301010300 | rye | 282 |
| 3301010400 | barley | 69 |
| 3301010500 | oats | 934 |
| 3301010600 | grain_maize_corn_popcorn | 4,475 |
| 3301010700 | rice | 271 |
| 3301010800 | triticale | 29 |
| 3301010900 | millet_sorghum | 95 |
| 3301019900 | other_cereals | 125 |

### 20 Orchards & Fruits

| EC_hcat_c | EC_hcat_n | Parcels |
|---|---|---|
| 3303000000 | permanent_crops_perennial | 103 |
| 3303010000 | orchards_fruits | 446 |
| 3303010200 | apples | 332 |
| 3303010300 | apricots | 4 |
| 3303010400 | cherry_cherries | 153 |
| 3303010600 | fig | 27 |
| 3303010700 | kiwi | 97 |
| 3303011100 | peach | 58 |
| 3303011200 | pears | 558 |
| 3303011300 | plums | 39 |
| 3303011400 | pomegranate | 3 |
| 3303011500 | quinces | 11 |
| 3303020200 | blackberry | 1 |
| 3303020400 | blueberry | 19 |
| 3303021000 | raspberry_raspberries | 2 |
| 3303030000 | nuts | 426 |
| 3303030100 | almond | 345 |
| 3303030200 | hazelnuts_hazel | 12 |
| 3303030400 | pistachio | 2 |
| 3303030500 | sweet_chestnuts | 3,708 |
| 3303040000 | citrus_plantations | 255 |
| 3303050000 | olive_plantations | 18,712 |
| 3303060000 | vineyards_wine_vine_rebland_grapes | 5,363 |
| 3303070000 | nurseries_nursery | 4 |
| 3303080700 | wire_bush (see special cases) | 971 |
| 3303100000 | avocado | 2 |
| 3303120000 | unspecified_permanent_crops | 820 |
| 3303990000 | other_permanent_crops_plantations | 5 |

### 30 Pastures & Meadows

| EC_hcat_c | EC_hcat_n | Parcels |
|---|---|---|
| 3301090100 | temporary_grass | 4,225 |
| 3301090205 | lolium_ryegrass | 339 |
| 3301090300 | legumes_harvested_green | 1 |
| 3301090301 | alfalfa_lucerne | 13 |
| 3301090303 | clover | 3 |
| 3302000000 | pasture_meadow_grassland_grass | 16,475 |

### 50 Vegetables / High-Value

| EC_hcat_c | EC_hcat_n | Parcels |
|---|---|---|
| 3301030000 | potatoes | 526 |
| 3301040000 | sweet_potatoes | 16 |
| 3301061228 | piper_pepper (bell pepper, see special cases) | 3 |
| 3301070000 | fresh_vegetables | 1,976 |
| 3301130000 | strawberries | 4 |
| 3301140300 | melon | 7 |
| 3301140400 | pumpkin_squash_gourd | 249 |
| 3301140500 | watermelon | 2 |
| 3301140600 | zucchini_courgette | 4 |
| 3301210100 | mustard | 1 |
| 3301210200 | brassica_oleracea_cabbage | 73 |
| 3301210300 | cress | 1 |
| 3301220200 | garlic | 5 |
| 3301220400 | onions | 15 |
| 3301260000 | aubergine_eggplant | 1 |
| 3301280000 | tomato | 70 |
| 3301290200 | beetroot_beets | 1 |
| 3301290300 | carrots_daucus | 18 |
| 3301290800 | turnips | 25 |
| 3301310000 | salads_lettuce_leaf_vegetables | 5 |
| 3301310800 | spinach | 1 |

### Other (Fallback Field Crop)

| EC_hcat_c | EC_hcat_n | Parcels |
|---|---|---|
| 3301020100 | beans | 188 |
| 3301020200 | chickpeas | 16 |
| 3301020600 | peas | 18 |
| 3301020700 | sweet_lupins | 67 |
| 3301060400 | rapeseed_rape | 1 |
| 3301060500 | sunflower | 11 |
| 3301060800 | oilseed_crops | 1 |
| 3301061200 | aromatic_medicinal_culinary_plants_spices_herbs | 10 |
| 3301080000 | flowers_ornamental_plants | 8 |
| 3301110000 | fallow_land_not_crop | 1,748 |
| 3301990000 | other_arable_land_crops | 2,493 |
| 3306000000 | tree_wood_forest | 707 |
| 3306050000 | eucalyptus | 27 |
| 3306060000 | oak | 2,108 |
| 3399000000 | not_known_and_other | 29,589 |
