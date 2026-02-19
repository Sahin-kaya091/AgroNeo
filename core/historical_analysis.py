
import ee
import json
import traceback
from datetime import datetime, timedelta
from PyQt5.QtCore import QObject, pyqtSignal
from core.classification import build_classification_model
from core.ee_utils import mask_s2_clouds

class TrendWorker(QObject):
    finished_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, geometry_json, year, start_date_str, end_date_str, legend_colors, label_mapping=None):
        super().__init__()
        self.geometry_json = geometry_json
        self.year = year
        self.start_date_str = start_date_str
        self.end_date_str = end_date_str
        self.legend_colors = legend_colors
        self.label_mapping = label_mapping
        
    def process(self):
        print("DEBUG: TrendWorker process started", flush=True)
        try:
            # 1. Deserialize Geometry
            print("DEBUG: Deserializing geometry...", flush=True)
            if self.geometry_json:
                self.geometry = ee.deserializer.fromJSON(self.geometry_json)
            else:
                 raise ValueError("No geometry provided")

            # 2. Build Classification Model Locally
            print(f"DEBUG: Building classification model for year {self.year}...", flush=True)
            classified_img, _ = build_classification_model(self.year, self.geometry)
            
            if classified_img is None:
                raise ValueError("Failed to build classification model (Insufficient Data)")
            
            # 3. Time Series Analysis
            print(f"DEBUG: Starting Time Series Analysis ({self.start_date_str} - {self.end_date_str})...", flush=True)
            
            # Parse dates
            s_date = datetime.strptime(self.start_date_str, "%d.%m.%Y")
            e_date = datetime.strptime(self.end_date_str, "%d.%m.%Y")
            
            ee_start = ee.Date(s_date.strftime("%Y-%m-%d"))
            ee_end = ee.Date(e_date.strftime("%Y-%m-%d"))
            
            # Fetch Image Collection for trends (NDVI)
            # Use Sentinel-2
            collection = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                          .filterBounds(self.geometry)
                          .filterDate(ee_start, ee_end)
                          .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 50))
                          .map(mask_s2_clouds))
            
            # Define a function to calculate mean INDICES per class for an image
            def calculate_class_means(img):
                date = img.date().format('YYYY-MM-dd')
                
                # Scale bands to 0-1 (Sentinel-2 L2A is 0-10000 range usually)
                # We need to cast to float for division
                img = img.divide(10000.0)
                
                b2 = img.select('B2')
                b3 = img.select('B3')
                b4 = img.select('B4')
                b5 = img.select('B5')
                b6 = img.select('B6')
                b8 = img.select('B8')
                b11 = img.select('B11')

                # Calculate Indices
                # NDVI = (B8 - B4) / (B8 + B4)
                ndvi = img.normalizedDifference(['B8', 'B4']).rename('NDVI')
                
                # GNDVI = (B8 - B3) / (B8 + B3)
                gndvi = img.normalizedDifference(['B8', 'B3']).rename('GNDVI')
                
                # NDWI = (B8 - B11) / (B8 + B11)  (Gao - Water Content)
                ndwi = img.normalizedDifference(['B8', 'B11']).rename('NDWI')
                
                # NDRE = (B8 - B5) / (B8 + B5)
                ndre = img.normalizedDifference(['B8', 'B5']).rename('NDRE')
                
                # RENDVI = (B6 - B5) / (B6 + B5)
                rendvi = img.normalizedDifference(['B6', 'B5']).rename('RENDVI')
                
                # EVI = 2.5 * ((B8 - B4) / (B8 + 6*B4 - 7.5*B2 + 1))
                # Note: using 1.0 instead of 10000 because we scaled bands to 0-1
                evi = b8.subtract(b4).divide(
                    b8.add(b4.multiply(6)).subtract(b2.multiply(7.5)).add(1)
                ).multiply(2.5).rename('EVI')
                
                # SAVI = ((B8 - B4) / (B8 + B4 + 0.5)) * 1.5
                savi = b8.subtract(b4).divide(
                    b8.add(b4).add(0.5)
                ).multiply(1.5).rename('SAVI')

                # Combine all bands
                combined_indices = (ndvi
                                   .addBands(gndvi)
                                   .addBands(ndwi)
                                   .addBands(ndre)
                                   .addBands(rendvi)
                                   .addBands(evi)
                                   .addBands(savi)
                                   .addBands(classified_img)) # Add class as the last band (or check index)
                
                # Reduce
                # groupField is the index of the class band.
                # Attributes added above: 0:NDVI, 1:GNDVI, 2:NDWI, 3:NDRE, 4:RENDVI, 5:EVI, 6:SAVI, 7:Class
                # So groupField=7
                # We have 7 inputs (indices) + 1 group input (class).
                # The mean reducer needs 7 inputs. The group reducer needs 1 (group) + N (inputs for child reducer).
                # Total inputs to group reducer = 7 + 1 = 8.
                # groupField=7 selects the 8th input (0-indexed).
                
                stats = combined_indices.reduceRegion(
                    reducer=ee.Reducer.mean().repeat(7).group(groupField=7, groupName='class'),
                    geometry=self.geometry,
                    scale=10,
                    maxPixels=1e9,
                    bestEffort=True
                )
                
                return ee.Feature(None, {'date': date, 'stats': stats.get('groups')})

            # Map over collection
            # Note: mapping over collection and getting info can be slow or overflow if too many images.
            # Best to filter/limit.
            # Let's limit to one image per 10 days? Or just use all?
            # User wants 3 month period. S2 is every 5 days. Approx 18 images max. Should be fine.
            
            timeseries = collection.map(calculate_class_means).getInfo()
            
            # Process results into Python dict
            # Structure: { 'ClassName': {'dates': [], 'NDVI': [], 'GNDVI': [], ...}, ... }
            
            print("DEBUG: Processing Time Series Results...", flush=True)
            trend_data = {}
            
            # Initialize structure helpers
            index_names = ['NDVI', 'GNDVI', 'NDWI', 'NDRE', 'RENDVI', 'EVI', 'SAVI']
            
            features = timeseries['features']
            for ft in features:
                props = ft['properties']
                date_str = props['date']
                groups = props['stats'] # List of dicts: [{'class': 1, 'mean': [0.5, 0.4, ...]}, ...]
                
                if not groups: continue
                
                for grp in groups:
                    cls_id = str(int(grp['class'])) # Class ID as string
                    
                    # When using repeat(7), the output 'mean' is a LIST of 7 values.
                    # grp = { 'class': 1, 'mean': [val0, val1, ..., val6] }
                    
                    mean_vals = grp.get('mean')
                    if not mean_vals or not isinstance(mean_vals, list):
                         # Fallback or skip
                         continue
                    
                    # Get Class Name
                    cls_name = self.label_mapping.get(cls_id, f"Class {cls_id}")
                    
                    if cls_name not in trend_data:
                        trend_data[cls_name] = {'dates': []}
                        for idx in index_names:
                            trend_data[cls_name][idx] = []
                    
                    trend_data[cls_name]['dates'].append(date_str)
                    
                    # Map list values to index names
                    # Order matches combined_indices order: NDVI, GNDVI, NDWI, NDRE, RENDVI, EVI, SAVI
                    for i, idx_name in enumerate(index_names):
                        if i < len(mean_vals):
                            val = mean_vals[i]
                            if val is None: val = 0.0
                            trend_data[cls_name][idx_name].append(val)
                        else:
                            trend_data[cls_name][idx_name].append(0.0)
                    
            # Sort dates? They should be sorted by collection default.
            
            print("DEBUG: Analysis Complete.", flush=True)
            self.finished_signal.emit(trend_data)

        except Exception as e:
            print("DEBUG: Traceback:", flush=True)
            traceback.print_exc()
            self.error_signal.emit(str(e))
