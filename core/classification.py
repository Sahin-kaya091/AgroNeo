import ee
from core.ee_utils import mask_s2_clouds

# --- CONSTANTS ---
PRODUCT_LABELS = {
    '0': 'Road / Structure / Rocky', '1': 'Barley / Lentil (Early)', '2': 'Wheat (Late Grain)',
    '3': 'Summer Crop (Undefined)', '4': 'Tall Trees', '5': 'Water', '6': 'Stubble / Plowed Soil',
    '7': 'Orchard / Shrub / Nursery', '8': 'Grass / Green Area',
    '30': 'Cotton', '31': 'Winter Vegetables (Sugar Beet, Carrot)', '32': 'Corn', '33': 'Sunflower'
}

ID_TO_PALETTE_IDX = {
    '0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
    '5': 5, '6': 6, '7': 7, '8': 8,
    '30': 9, '31': 10, '32': 11, '33': 12
}

PALETTE_COLORS = [
    '#BDBDBD', # 0: Structure (Gray)
    '#FFD54F', # 1: Barley (Light Gold)
    '#FF9800', # 2: Wheat (Orange)
    '#CDDC39', # 3: Summer Undef (Lime)
    '#1B5E20', # 4: Trees (Dark Green)
    '#2196F3', # 5: Water (Blue)
    '#795548', # 6: Stubble (Brown)
    '#827717', # 7: Shrub (Dark Olive)
    '#76FF03', # 8: Grass (Bright Lime)
    '#F48FB1', # 9: Cotton (Pinkish)
    '#9C27B0', # 10: Beet (Purple)
    '#FFEB3B', # 11: Corn (Yellow)
    '#FFA726'  # 12: Sunflower (Deep Orange)
]

def build_classification_model(year, geometry):
    # --- Image Collections ---
    spring_col = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-03-23', f'{year}-05-20').filter(
            ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))
    summer_col = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-06-20', f'{year}-08-25').filter(
            ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))
    sept_col = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-09-01', f'{year}-09-30').filter(
            ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))
    oct_col = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-10-01', f'{year}-10-20').filter(
            ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))
    transition_col = (
        ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-06-01', f'{year}-06-20').filter(
            ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))

    # --- OPTIMIZATION: BATCH METADATA FETCHING ---
    
    # 1. Define S1 Collection FIRST (Fix for UnboundLocalError)
    s1_col = (ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(geometry).filterDate(f'{year}-07-01',
                                                                                             f'{year}-08-30')
              .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
              .filter(ee.Filter.eq('instrumentMode', 'IW')).select('VH'))

    # 2. Batch Metadata Fetching
    console_counts = ee.Dictionary({
        'spring': spring_col.size(),
        'summer': summer_col.size(),
        'sept': sept_col.size(),
        'oct': oct_col.size(),
        'trans': transition_col.size(),
        's1': s1_col.size()
    }).getInfo()

    if console_counts['spring'] == 0 or console_counts['summer'] == 0:
        return None, False # Insufficient Data

    spring_img = spring_col.median().clip(geometry)
    summer_img = summer_col.median().clip(geometry)

    has_sept = console_counts['sept'] > 0
    sept_ndvi = sept_col.median().clip(geometry).normalizedDifference(
        ['B8', 'B4']) if has_sept else ee.Image(0)
    
    has_oct = console_counts['oct'] > 0
    oct_ndvi = oct_col.median().clip(geometry).normalizedDifference(['B8', 'B4']) if has_oct else ee.Image(
        0)
    
    has_transition = console_counts['trans'] > 0
    transition_ndvi = transition_col.median().clip(geometry).normalizedDifference(
        ['B8', 'B4']) if has_transition else None

    spring_ndvi = spring_img.normalizedDifference(['B8', 'B4'])
    summer_ndvi = summer_img.normalizedDifference(['B8', 'B4'])
    summer_ndmi = summer_img.normalizedDifference(['B8', 'B11'])


    summer_ndbi = summer_img.normalizedDifference(['B11', 'B8'])
    spring_ndwi = spring_img.normalizedDifference(['B3', 'B8'])
    
    # usage of s1_col size check
    if console_counts['s1'] > 0:
        s1_img_raw = s1_col.median().clip(geometry)
        s1_img = s1_img_raw.focalMedian(10, 'circle', 'meters')
    else:
        s1_img = ee.Image(-20).clip(geometry)


    classified = ee.Image(6)


    is_winter_crop = spring_ndvi.gt(0.40).And(summer_ndvi.lt(0.30))


    is_summer_crop_base = spring_ndvi.lt(0.35).And(summer_ndvi.gt(0.40))


    is_perennial = spring_ndvi.gt(0.40).And(summer_ndvi.gt(0.40))

    canopy_height = ee.Image("UMD/hansen/global_forest_change_2024_v1_12").select('treecover2000').clip(geometry)
    is_tall_enough = canopy_height.gte(30)


    # is_forest = is_perennial.And(s1_img.gt(-14.8)).And(summer_ndvi.gt(0.45))
    is_forest = is_perennial.And(is_tall_enough).And(s1_img.gt(-15)).And(summer_ndvi.gt(0.45))
    is_grass = is_perennial.And(s1_img.lt(-16.8)).And(is_forest.Not())
    is_garden_shrub = is_perennial.And(is_forest.Not()).And(is_grass.Not())

    has_volume = s1_img.gt(-16.0)
    is_very_green = summer_ndvi.gt(0.60)
    is_moist = summer_ndmi.gt(0.15)
    not_dead_in_sept = sept_ndvi.lt(0.35)

    is_corn = is_summer_crop_base \
        .And(is_moist) \
        .And(not_dead_in_sept) \
        .And(has_volume.Or(is_very_green))

    # --- Sugar Beet Block ---

    # 1. Base Candidate Definition (Not corn, not perennial)
    is_beet_candidate = is_summer_crop_base.And(is_corn.Not()).And(is_perennial.Not())

    # 2. Spring field should be empty (below 0.30)
    is_strict_beet_candidate = is_beet_candidate.And(spring_ndvi.lt(0.35))

    # --- Enhanced Beet Details ---

    # Dense canopy in summer
    is_dense_canopy = summer_ndvi.gt(0.65)

    # Very moist
    is_very_moist = summer_ndmi.gt(0.15)

    # Phenological Stability (Should stay green in October, no sudden drop)
    if has_oct:
        is_late_green = oct_ndvi.gt(0.55)
        ndvi_drop = summer_ndvi.subtract(oct_ndvi)
        is_stable = ndvi_drop.lt(0.25)
        is_beet_phenology = is_late_green.And(is_stable)
    else:
        # If no data, check with September
        is_late_green = sept_ndvi.gt(0.60)
        is_beet_phenology = is_late_green

    # 3. Final Beet Definition (Combination of all conditions)
    is_beet = is_strict_beet_candidate \
        .And(is_dense_canopy) \
        .And(is_very_moist) \
        .And(is_beet_phenology)

    # 4. Others (Beet candidates that didn't pass the beet test)
    is_other_summer = is_strict_beet_candidate.And(is_beet.Not())

    is_high_biomass = summer_ndvi.gt(0.60)
    is_senesced_in_sept = sept_ndvi.lt(0.40)
    ndvi_drop = summer_ndvi.subtract(sept_ndvi)
    is_rapid_dry_down = ndvi_drop.gt(0.25)
    is_low_moisture = summer_ndmi.lt(0.15)

    is_sunflower = is_other_summer \
        .And(is_high_biomass) \
        .And(is_senesced_in_sept) \
        .And(is_rapid_dry_down)

    is_summer_green = summer_ndvi.gt(0.50)
    is_sept_middle = sept_ndvi.gte(0.35).And(sept_ndvi.lt(0.65))
    is_shrub_structure = s1_img.lt(-15.0).And(s1_img.gt(-21.0))
    is_moderate_moisture = summer_ndmi.lt(0.25).And(summer_ndmi.gt(0.05))


    is_cotton = is_summer_crop_base \
        .And(is_summer_green) \
        .And(is_sept_middle) \
        .And(is_shrub_structure) \
        .And(is_moderate_moisture)
    
    is_water = spring_ndwi.gt(spring_ndvi).Or(spring_ndwi.gt(0.1))

    bsi = summer_img.expression(
        '((RED + SWIR) - (NIR + BLUE)) / ((RED + SWIR) + (NIR + BLUE))', {
            'RED': summer_img.select('B4'),
            'SWIR': summer_img.select('B11'),
            'NIR': summer_img.select('B8'),
            'BLUE': summer_img.select('B2')
        }
    )

    is_structure = spring_ndvi.lt(0.25) \
        .And(summer_ndvi.lt(0.25)) \
        .And(summer_ndbi.gt(-0.01)) \
        .And(is_water.Not())

    classified = classified.where(is_water, 5)
    classified = classified.where(is_structure, 0)

    classified = classified.where(is_cotton, 30).where(is_sunflower, 33)
    classified = classified.where(is_beet, 31).where(is_corn, 32)


    if has_transition and transition_ndvi:
        is_barley_cond = is_winter_crop.And(transition_ndvi.lt(0.35))
        is_wheat_cond = is_winter_crop.And(transition_ndvi.gte(0.35))
        classified = classified.where(is_barley_cond, 1).where(is_wheat_cond, 2)
    else:
        classified = classified.where(is_winter_crop, 1)


    classified = classified.where(is_grass, 8)
    classified = classified.where(is_garden_shrub, 7)
    classified = classified.where(is_forest, 4)
    
    return classified, has_transition
