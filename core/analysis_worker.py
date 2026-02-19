import ee
from PyQt5.QtCore import QThread, pyqtSignal
from datetime import datetime
from core.ee_utils import mask_s2_clouds
from core.database import LicenseManager
from core.cache_utils import cache_manager
from core.classification import (
    build_classification_model, PRODUCT_LABELS, ID_TO_PALETTE_IDX, PALETTE_COLORS
)


class AnalysisWorker(QThread):
    finished_signal = pyqtSignal(dict)
    date_selection_signal = pyqtSignal(list)
    class_signal = pyqtSignal(dict) # Kept for backward compat or radar msg
    error_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str)

    def __init__(self, geo_data, bands, mode, date1, date2=None, specific_date=None, analysis_type="area", product_id=None):
        super().__init__()
        self.geo_data = geo_data
        self.bands = bands
        self.mode = mode
        self.date1 = date1
        self.date2 = date2
        self.specific_date = specific_date
        self.analysis_type = analysis_type
        self.product_id = product_id
        self.geometry = None

        self.license_manager = LicenseManager()

        try:
            if isinstance(date1, str) and "-" in date1:
                self.year = int(date1.split("-")[0])
            else:
                self.year = datetime.now().year
        except Exception as e:
            print(f"DATE ERROR: {e}")
            self.year = 2023


    def run(self):
        print("DEBUG: Worker Run Started (Optimized)...")

        allowed, message = self.license_manager.check_access()

        if not allowed:
            user_id = self.license_manager.get_user_id()
            self.error_signal.emit(f"{message}\nUser ID: {user_id}")
            return

        self.status_signal.emit(f"License Approved: {message}")

        try:
            if isinstance(self.geo_data, dict):
                if 'geometry' in self.geo_data:
                    raw_geometry = ee.Geometry(self.geo_data['geometry'])
                else:
                    raw_geometry = ee.Geometry(self.geo_data)
            else:
                raw_geometry = self.geo_data

            self.geometry = raw_geometry

            # --- 0. CACHE CHECK ---
            print("DEBUG: Checking Cache...")
            cached_stats = cache_manager.get(self.geometry.getInfo(), self.date1, self.date2, self.mode, self.analysis_type)
            if cached_stats:
                self.status_signal.emit("Data loaded from Cache (Instant).")
                self.finished_signal.emit(cached_stats)
                
                # Unlike before, we DO NOT trigger classification here.
                # The GUI must handle the chain based on the result.
                return

            stats = None
            used_source = "S2"
            target_image = None
            ee_current_date = ee.Date(self.date1)

            # --- 1. IMAGE IDENTIFICATION (Metadata Checks) ---
            try:
                if self.mode == "range":
                    target_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                    .filterBounds(self.geometry)
                                    .filterDate(self.date1, self.date2)
                                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                                    .map(mask_s2_clouds).median())
                elif self.mode == "single":
                    found_exact = False
                    if not self.specific_date:
                        exact_date_str = self.find_exact_match(ee_current_date)
                        if exact_date_str:
                            self.specific_date = exact_date_str
                            self.status_signal.emit(f"✓ Exact cloudy-free image found: {exact_date_str}")
                            found_exact = True

                    if self.specific_date:
                        self.status_signal.emit(f"Processing target date: {self.specific_date}...")
                        t_date = ee.Date(self.specific_date)
                        target_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                                        .filterBounds(self.geometry)
                                        .filterDate(t_date, t_date.advance(1, 'day'))
                                        .map(mask_s2_clouds).first())
                    else:
                        self.status_signal.emit(f"Searching for best images around {self.date1}...")
                        candidates = self.find_candidates(ee_current_date)
                        if candidates:
                            self.date_selection_signal.emit(candidates)
                            return
                        else:
                            self.error_signal.emit("No suitable images found.")
                            return
            except Exception as e:
                self.error_signal.emit(f"Image error: {e}")
                return

            # --- 2. MASTER CONSOLIDATED REQUEST ---
            self.status_signal.emit("Fetching analysis data (Optimized)...")
            
            master_request = {}
            
            # A. Optical Data Prep
            if target_image:
                # Coverage Check
                tot_count = ee.Image(1).clip(self.geometry).reduceRegion(
                    reducer=ee.Reducer.count(), geometry=self.geometry, scale=10, maxPixels=1e9
                )
                val_count = target_image.select(['B4']).reduceRegion(
                    reducer=ee.Reducer.count(), geometry=self.geometry, scale=10, maxPixels=1e9
                )
                # Main Stats
                optical_stats = target_image.select(self.bands).reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=self.geometry, scale=10, maxPixels=1e9
                )
                
                master_request['total_pixels'] = tot_count.get('constant', 1)
                master_request['valid_pixels'] = val_count.get('B4', 0)
                master_request['optical_stats'] = optical_stats
                
                # B. Historical Data Prep
                past_start = ee_current_date.advance(-45, 'day')
                past_end = ee_current_date.advance(-15, 'day')
                past_image = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                              .filterBounds(self.geometry)
                              .filterDate(past_start, past_end)
                              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                              .map(mask_s2_clouds).median())
                
                past_stats = past_image.select(['B4', 'B8']).reduceRegion(
                    reducer=ee.Reducer.mean(), geometry=self.geometry, scale=10, maxPixels=1e9
                )
                master_request['past_stats'] = past_stats
            
            # C. Radar (S1) Data Prep
            s1 = (ee.ImageCollection('COPERNICUS/S1_GRD')
                  .filterBounds(self.geometry)
                  .filterDate(ee_current_date.advance(-15, 'day'), ee_current_date.advance(15, 'day'))
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                  .filter(ee.Filter.eq('instrumentMode', 'IW')).median())
            
            # Check availability
            s1_stats = s1.select(['VV', 'VH']).reduceRegion(
                reducer=ee.Reducer.mean(), geometry=self.geometry, scale=10, maxPixels=1e9
            )
            master_request['s1_stats'] = s1_stats
            
            # D. SMI (Soil Moisture) Prep
            smi_start = ee_current_date.advance(-6, 'day')
            smi_end = ee_current_date.advance(6, 'day')
            s1_smi_col = (ee.ImageCollection('COPERNICUS/S1_GRD')
                  .filterBounds(self.geometry)
                  .filterDate(smi_start, smi_end)
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV'))
                  .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH'))
                  .filter(ee.Filter.eq('instrumentMode', 'IW'))
                  .median().clip(self.geometry))
            
            s1_smi_smooth = s1_smi_col.focalMedian(30, 'circle', 'meters')
            vv = s1_smi_smooth.select('VV')
            vh = s1_smi_smooth.select('VH')
            soil_proxy = vv.add(vh.multiply(0.53)).rename('Soil_Proxy')
            # Normalize
            min_val = -25.0
            max_val = -10.0
            smi_img = soil_proxy.expression('(VAL - MIN) / (MAX - MIN)', 
                {'VAL': soil_proxy, 'MIN': min_val, 'MAX': max_val}
            ).clamp(0.0, 1.0)
            
            smi_val = smi_img.reduceRegion(
                reducer=ee.Reducer.mean(), geometry=self.geometry, scale=10, maxPixels=1e9
            )
            master_request['smi_val'] = smi_val
            
            # --- 3. EXECUTE FETCH ---
            results = ee.Dictionary(master_request).getInfo()
            
            # --- 4. PROCESS RESULTS ---
            
            # A. Process Optical
            if 'optical_stats' in results:
                t_pix = results.get('total_pixels', 1) or 1
                v_pix = results.get('valid_pixels', 0) or 0
                
                # Check coverage
                if (v_pix / t_pix) < 0.30:
                     self.status_signal.emit("Insufficient Optical Data. Switching to Radar...")
                     stats = None
                else:
                     opt_data = results.get('optical_stats', {})
                     if opt_data and opt_data.get('B4') is not None:
                         stats = opt_data
                         stats['source'] = 'S2'
                         
                         # Process Past Data
                         past_data = results.get('past_stats', {})
                         if past_data and past_data.get('B4') is not None:
                             p_b8 = past_data['B8']
                             p_b4 = past_data['B4']
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
            
            # B. Process Radar (Fallback or Merge)
            s1_data = results.get('s1_stats', {})
            if s1_data and s1_data.get('VH') is not None:
                if stats:
                    stats['VH'] = s1_data.get('VH')
                    stats['VV'] = s1_data.get('VV')
                elif stats is None:
                    # Fallback to Radar
                    stats = s1_data
                    stats['source'] = 'S1'
                    used_source = 'S1'
            else:
                 if stats is None:
                     self.error_signal.emit("No Optical or Radar data available.")
                     return

            # C. Process SMI
            smi_data = results.get('smi_val', {})
            smi_res = 0.0
            if smi_data:
                vals = list(smi_data.values())
                if vals and vals[0] is not None:
                    smi_res = float(vals[0])
            
            if stats:
                stats['soil_moisture'] = smi_res

            # --- FINALIZE ---
            if stats:
                self.license_manager.decrement_credit()
                
                # 1. Update source cache first
                # Not necessarily fully cached yet as we split tasks, but cache stores 'stats' dict.
                # If we want to cache the whole result, we must wait for classification? 
                # No, cache stores 'stats' dict. 'Classification' is separate usually?
                # The old code cached 'stats'. If cached, it contained source info. 
                # If 'S2', it triggered classification. 
                # We can keep caching the 'stats' here.
                cache_manager.set(self.geometry.getInfo(), self.date1, self.date2, self.mode, stats, self.analysis_type)

                self.finished_signal.emit(stats)
            else:
                self.error_signal.emit("Analysis produced no valid data.")

        except Exception as e:
            print(f"GENERAL WORKER ERROR: {e}")
            self.error_signal.emit(str(e))


    def find_candidates(self, center_date):
        """Finds best image before and after the center date."""
        try:
            candidates = []
            
            # 1. Search BEFORE
            before_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                          .filterBounds(self.geometry)
                          .filterDate(center_date.advance(-60, 'day'), center_date)
                          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30))
                          .sort('system:time_start', False)) # Closest to date first
            
            # Take the closest valid image
            best_before = before_col.first()
            info_before = best_before.getInfo()
            
            if info_before:
                dt = info_before['properties']['system:time_start'] # ms
                date_str = datetime.fromtimestamp(dt / 1000.0).strftime('%Y-%m-%d')
                cloud_cov = info_before['properties']['CLOUDY_PIXEL_PERCENTAGE']
                candidates.append({'label': 'BEFORE', 'date': date_str, 'cloud': cloud_cov})

            # 2. Search AFTER
            after_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                          .filterBounds(self.geometry)
                          .filterDate(center_date, center_date.advance(60, 'day'))
                          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 40))
                          .sort('system:time_start', True)) # Closest to date first (ascending)
            
            best_after = after_col.first()
            info_after = best_after.getInfo()
            
            if info_after:
                dt = info_after['properties']['system:time_start'] # ms
                date_str = datetime.fromtimestamp(dt / 1000.0).strftime('%Y-%m-%d')
                cloud_cov = info_after['properties']['CLOUDY_PIXEL_PERCENTAGE']
                candidates.append({'label': 'AFTER', 'date': date_str, 'cloud': cloud_cov})

            return candidates

        except Exception as e:
            print(f"Candidate Search Error: {e}")
            return []

    def find_exact_match(self, date):
        """Checks if the exact requested date (or very close) has a clean image."""
        try:
            col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                   .filterBounds(self.geometry)
                   .filterDate(date, date.advance(1, 'day'))
                   .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 30)))
            
            img = col.first()
            info = img.getInfo()
            
            if info:
                dt = info['properties']['system:time_start']
                date_str = datetime.fromtimestamp(dt / 1000.0).strftime('%Y-%m-%d')
                cloud = info['properties']['CLOUDY_PIXEL_PERCENTAGE']
                print(f"DEBUG: Exact match found! Date: {date_str}, Cloud: {cloud}")
                return date_str
            return None
        except Exception as e:
            print(f"Exact match check warning: {e}")
            return None


class PhenologyWorker(QThread):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)

    def __init__(self, year, geometry, analysis_type="area", product_id=None):
        super().__init__()
        self.year = year
        self.geometry = geometry
        self.analysis_type = analysis_type
        self.product_id = product_id

    def run(self):
        try:
            classified, has_transition = build_classification_model(self.year, self.geometry)
            
            if classified is None:
                self.finished_signal.emit({"Insufficient Data": 100})
                return

            stats = classified.reduceRegion(reducer=ee.Reducer.frequencyHistogram(), geometry=self.geometry, scale=30,
                                            maxPixels=1e9, tileScale=4).getInfo()

            if not stats: self.finished_signal.emit({"No Result": 0}); return
            values_view = list(stats.values())
            if not values_view: self.finished_signal.emit({"No Data": 0}); return
            histogram = values_view[0]
            if not histogram: self.finished_signal.emit({"No Data": 0}); return

            total = sum(histogram.values())
            if total == 0: total = 1

            labels = PRODUCT_LABELS.copy()
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
            
            # 1. Separate Keepers (>= 6.5%) and Remnants (< 6.5%)
            keepers = {}
            remnant_total = 0.0
            
            for cls_idx, percent in temp_results.items():
                if percent >= 6.5:
                    keepers[cls_idx] = percent
                else:
                    remnant_total += percent
            
            # 2. Distribute Remnant Equally
            if keepers:
                share_per_keeper = remnant_total / len(keepers)
                for k in keepers:
                    keepers[k] += share_per_keeper
            else:
                keepers = temp_results

            # 3. Populate Final Results
            for cls_idx, percent in keepers.items():
                name = labels.get(cls_idx, 'Unknown')
                final_results[name] = percent


            # --- MAP COLORIZATION START ---
            try:
                id_to_palette_idx = ID_TO_PALETTE_IDX
                palette = PALETTE_COLORS

                # Generate Legend Colors for UI
                legend_colors = {}
                for cls_id, name in labels.items():
                    if cls_id in id_to_palette_idx:
                        idx = id_to_palette_idx[cls_id]
                        if idx < len(palette):
                            legend_colors[name] = palette[idx]
                
                final_results['legend_colors'] = legend_colors

                # EE Remap Logic
                from_vals = [int(k) for k in id_to_palette_idx.keys()]
                to_vals =   [v for v in id_to_palette_idx.values()]
                
                vis_classified = classified.remap(from_vals, to_vals).clip(self.geometry)
                
                # --- PRODUCT SCANNING MODE ---
                if self.analysis_type == "product" and self.product_id:
                    try:
                        target_id = int(self.product_id)
                        if str(target_id) in id_to_palette_idx:
                            remapped_target = id_to_palette_idx[str(target_id)]
                            vis_classified = vis_classified.updateMask(vis_classified.eq(remapped_target))
                        else:
                            print(f"Product ID {target_id} not in palette map")
                    except Exception as e:
                        print(f"Product Mask Error: {e}")

                vis_params = {'min': 0, 'max': 12, 'palette': palette}
                
                # Create Tile URL
                map_id_dict = vis_classified.getMapId(vis_params)
                tile_url = map_id_dict['tile_fetcher'].url_format
                
                # Add to results
                final_results['tile_url'] = tile_url

            except Exception as e:
                print(f"Viz Error: {e}")
            # --- MAP COLORIZATION END ---
            
            # Export the EE Image object for historical analysis
            final_results['classified_image'] = classified
            final_results['label_mapping'] = labels

            # --- FILTER RESULTS FOR PRODUCT MODE ---
            if self.analysis_type == "product" and self.product_id:
                target_name = labels.get(str(self.product_id))
                if target_name:
                    filtered = {}
                    for k, v in final_results.items():
                        if k in ['tile_url', 'legend_colors', 'classified_image', 'label_mapping']:
                            filtered[k] = v
                        elif k == target_name:
                            filtered[k] = v
                    final_results = filtered

            self.finished_signal.emit(final_results)

        except Exception as e:
            print(f"CLASSIFICATION ERROR: {e}")
            self.error_signal.emit(str(e))
