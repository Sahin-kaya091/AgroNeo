
import ee
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime
from utils import mask_s2_clouds

class AnalysisWorker(QThread):
    finished_signal = pyqtSignal(dict)
    class_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, geo_data, bands, mode, date1, date2=None):
        super().__init__()
        self.geo_data = geo_data
        self.bands = bands
        self.mode = mode
        self.date1 = date1
        self.date2 = date2
        self.geometry = None
        try:
            if isinstance(date1, str) and "-" in date1:
                self.year = int(date1.split("-")[0])
            else:
                self.year = datetime.now().year
        except Exception as e:
            print(f"DATE ERROR: {e}")
            self.year = 2023

    def run(self):
        print("DEBUG: Worker Run Started...")
        try:
            if isinstance(self.geo_data, dict):
                if 'geometry' in self.geo_data:
                    raw_geometry = ee.Geometry(self.geo_data['geometry'])
                else:
                    raw_geometry = ee.Geometry(self.geo_data)
            else:
                raw_geometry = self.geo_data



            self.geometry = raw_geometry

            stats = None
            used_source = "S2"
            target_image = None
            ee_current_date = ee.Date(self.date1)

            try:
                if self.mode == "range":
                    target_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                    .filterBounds(self.geometry)
                                    .filterDate(self.date1, self.date2)
                                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                                    .map(mask_s2_clouds).median())
                elif self.mode == "single":
                    self.status_signal.emit(f"Scanning {self.date1}...")
                    target_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                    .filterBounds(self.geometry)
                                    .filterDate(ee_current_date.advance(-15, 'day'), ee_current_date.advance(15, 'day'))
                                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
                                    .map(mask_s2_clouds).median())
            except Exception as e:
                self.error_signal.emit(f"Image error: {e}")
                return

            if target_image:
                try:
                    total_pixels = ee.Image(1).clip(self.geometry).reduceRegion(
                        reducer=ee.Reducer.count(), geometry=self.geometry, scale=5, maxPixels=1e9
                    ).getInfo().get('constant')

                    valid_pixels = target_image.select(['B4']).reduceRegion(
                        reducer=ee.Reducer.count(), geometry=self.geometry, scale=5, maxPixels=1e9
                    ).getInfo().get('B4')

                    total = total_pixels if total_pixels else 1
                    valid = valid_pixels if valid_pixels else 0
                    coverage_ratio = valid / total

                    if coverage_ratio < 0.30:
                        self.status_signal.emit("⚠️ Insufficient Data (below 30%). Trying Radar...")
                        stats = None
                    else:
                        temp_stats = target_image.select(self.bands).reduceRegion(
                            reducer=ee.Reducer.mean(), geometry=self.geometry, scale=5, maxPixels=1e9
                        ).getInfo()

                        if temp_stats and temp_stats.get('B4') is not None:
                            stats = temp_stats
                            stats['source'] = 'S2'
                        else:
                            stats = None
                except Exception as e:
                    print(f"DATA FETCH ERROR: {e}")
                    stats = None

            if stats and stats['source'] == 'S2':
                try:
                    past_start = ee_current_date.advance(-45, 'day')
                    past_end = ee_current_date.advance(-15, 'day')
                    past_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                  .filterBounds(self.geometry)
                                  .filterDate(past_start, past_end)
                                  .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                                  .map(mask_s2_clouds).median())
                    past_vals = past_image.select(['B4', 'B8']).reduceRegion(
                        reducer=ee.Reducer.mean(), geometry=self.geometry, scale=5, maxPixels=1e9
                    ).getInfo()
                    if past_vals and past_vals.get('B8') is not None and past_vals.get('B4') is not None:
                        p_b8 = past_vals['B8']
                        p_b4 = past_vals['B4']
                        denom = p_b8 + p_b4
                        past_ndvi = (p_b8 - p_b4) / denom if denom != 0 else 0.0
                        curr_b8 = stats.get('B8', 0)
                        curr_b4 = stats.get('B4', 0)
                        curr_denom = curr_b8 + curr_b4
                        curr_ndvi = (curr_b8 - curr_b4) / curr_denom if curr_denom != 0 else 0.0
                        stats['past_ndvi'] = past_ndvi
                        stats['ndvi_change'] = curr_ndvi - past_ndvi
                    else:
                        stats['past_ndvi'] = None
                except Exception as e:
                    stats['past_ndvi'] = None
                    print(f"Historical data error: {e}")

            if stats is None:
                if used_source == "S2": self.status_signal.emit("⚠️ No Optical -> Radar (S1) Active...")
                stats = self.analyze_with_sentinel1()
                used_source = "S1"

            if stats:
                self.finished_signal.emit(stats)
            else:
                self.error_signal.emit("No data received.")
                return

            if used_source == "S2":
                self.status_signal.emit("Classifying vegetation...")
                self.perform_phenology_classification()
            else:
                self.class_signal.emit({"Radar Mode Active": 100})

        except Exception as e:
            print(f"GENERAL WORKER ERROR: {e}")
            self.error_signal.emit(str(e))

    def analyze_with_sentinel1(self):
        try:
            ee_date = ee.Date(self.date1)
            s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
                  .filterBounds(self.geometry)
                  .filterDate(ee_date.advance(-15, 'day'), ee_date.advance(15, 'day'))
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                  .filter(ee.Filter.eq('instrumentMode', 'IW')).median())
            check = s1.select(['VH']).reduceRegion(ee.Reducer.first(), self.geometry, 50).getInfo()
            if not check: return None
            s1_stats = s1.select(['VV', 'VH']).reduceRegion(reducer=ee.Reducer.mean(), geometry=self.geometry, scale=5,
                                                            maxPixels=1e9).getInfo()
            if s1_stats:
                s1_stats['source'] = 'S1'
                return s1_stats
            return None
        except:
            return None

    def perform_phenology_classification(self):

        try:
            year = self.year
            # --- Image Collections ---
            spring_col = (
                ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-04-10', f'{year}-05-25').filter(
                    ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))
            summer_col = (
                ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-07-15', f'{year}-08-25').filter(
                    ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))
            sept_col = (
                ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-09-01', f'{year}-09-30').filter(
                    ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).map(mask_s2_clouds))
            oct_col = (
                ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-10-01', f'{year}-10-30').filter(
                    ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)).map(mask_s2_clouds))
            transition_col = (
                ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(f'{year}-06-01', f'{year}-06-20').filter(
                    ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).map(mask_s2_clouds))

            if spring_col.size().getInfo() == 0 or summer_col.size().getInfo() == 0:
                self.class_signal.emit({"Insufficient Data": 100})
                return

            spring_img = spring_col.median().clip(self.geometry)
            summer_img = summer_col.median().clip(self.geometry)

            has_sept = sept_col.size().getInfo() > 0
            sept_ndvi = sept_col.median().clip(self.geometry).normalizedDifference(
                ['B8', 'B4']) if has_sept else ee.Image(0)
            has_oct = oct_col.size().getInfo() > 0
            oct_ndvi = oct_col.median().clip(self.geometry).normalizedDifference(['B8', 'B4']) if has_oct else ee.Image(
                0)
            has_transition = transition_col.size().getInfo() > 0
            transition_ndvi = transition_col.median().clip(self.geometry).normalizedDifference(
                ['B8', 'B4']) if has_transition else None

            spring_ndvi = spring_img.normalizedDifference(['B8', 'B4'])
            summer_ndvi = summer_img.normalizedDifference(['B8', 'B4'])


            summer_ndbi = summer_img.normalizedDifference(['B11', 'B8'])
            spring_ndwi = spring_img.normalizedDifference(['B3', 'B8'])


            s1_col = (ee.ImageCollection('COPERNICUS/S1_GRD').filterBounds(self.geometry).filterDate(f'{year}-07-01',
                                                                                                     f'{year}-08-30')
                      .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                      .filter(ee.Filter.eq('instrumentMode', 'IW')).select('VH'))

            if s1_col.size().getInfo() > 0:
                s1_img_raw = s1_col.median().clip(self.geometry)
                s1_img = s1_img_raw.focalMedian(30, 'circle', 'meters')
            else:
                s1_img = ee.Image(-20).clip(self.geometry)
                s1_img_raw = ee.Image(-20).clip(self.geometry)


            classified = ee.Image(0)


            is_winter_crop = spring_ndvi.gt(0.40).And(summer_ndvi.lt(0.30))


            is_summer_crop_base = spring_ndvi.lt(0.35).And(summer_ndvi.gt(0.40))


            is_perennial = spring_ndvi.gt(0.33).And(summer_ndvi.gt(0.33))


            is_forest = is_perennial.And(s1_img.gt(-14.8)).And(summer_ndvi.gt(0.45))
            is_grass = is_perennial.And(s1_img.lt(-16.6)).And(is_forest.Not())
            is_garden_shrub = is_perennial.And(is_forest.Not()).And(is_grass.Not())


            is_corn = is_summer_crop_base.And(s1_img.gt(-14.5))


            is_beet_candidate = is_summer_crop_base.And(is_corn.Not()).And(is_perennial.Not())


            is_strict_beet_candidate = is_beet_candidate.And(spring_ndvi.lt(0.30))

            if has_oct:

                is_beet = is_strict_beet_candidate.And(oct_ndvi.gt(0.50))
                is_other_summer = is_strict_beet_candidate.And(is_beet.Not())
            else:
                is_beet = is_strict_beet_candidate.And(sept_ndvi.gt(0.55))
                is_other_summer = is_strict_beet_candidate.And(is_beet.Not())

            is_sunflower = is_other_summer.And(sept_ndvi.lt(0.35))
            is_cotton = is_other_summer.And(is_sunflower.Not())


            is_water = spring_ndwi.gt(spring_ndvi).Or(spring_ndwi.gt(0.1))



            is_bare_soil = spring_ndvi.gt(0.13) \
                .And(summer_ndvi.gt(0.13)) \
                .And(is_perennial.Not()) \
                .And(is_summer_crop_base.Not()) \
                .And(is_winter_crop.Not()) \
                .And(is_water.Not())




            classified = classified.where(is_bare_soil, 6)
            classified = classified.where(is_water, 5)


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


            stats = classified.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=self.geometry, scale=10,
                                            maxPixels=1e9).getInfo()

            if not stats: self.class_signal.emit({"No Result": 0}); return
            values_view = list(stats.values())
            if not values_view: self.class_signal.emit({"No Data": 0}); return
            histogram = values_view[0]
            if not histogram: self.class_signal.emit({"No Data": 0}); return

            total = sum(histogram.values())
            if total == 0: total = 1

            labels = {
                '0': 'Road / Structure / Rocky', '1': 'Barley / Lentil (Early)', '2': 'Wheat (Late Grain)',
                '3': 'Summer Crop (Undefined)', '4': 'Dense Forest', '5': 'Water', '6': 'Stubble / Plowed Soil',
                '7': 'Orchard / Shrub / Nursery', '8': 'Grass / Green Area',
                '30': 'Cotton', '31': 'Winter Vegetables (Sugar Beet, Carrot)', '32': 'Corn', '33': 'Sunflower'
            }
            if not has_transition: labels['1'] = 'Winter Grain'


            temp_results = {}
            max_percent = -1
            dominant_idx = None

            for cls_idx, count in histogram.items():
                percent = (count / total) * 100
                temp_results[cls_idx] = percent
                if percent > max_percent:
                    max_percent = percent
                    dominant_idx = cls_idx

            final_results = {}
            remnant_share = 0

            for cls_idx, percent in temp_results.items():
                if percent < 6.5 and cls_idx != dominant_idx:
                    remnant_share += percent
                else:
                    name = labels.get(cls_idx, 'Unknown')
                    final_results[name] = percent

            if dominant_idx is not None:
                dominant_name = labels.get(dominant_idx, 'Unknown')
                if dominant_name in final_results:
                    final_results[dominant_name] += remnant_share
                else:
                    final_results[dominant_name] = final_results.get(dominant_name, 0) + remnant_share

            self.class_signal.emit(final_results)

        except Exception as e:
            print(f"CLASSIFICATION ERROR: {e}")
            self.class_signal.emit({"Error": 0})
