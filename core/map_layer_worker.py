import ee
from PyQt5.QtCore import QThread, pyqtSignal
from core.ee_utils import mask_s2_clouds


class MapLayerWorker(QThread):
    finished_signal = pyqtSignal(str)  # Returns Tile URL
    error_signal = pyqtSignal(str)

    def __init__(self, geo_data, mode, date1, date2=None, specific_date=None):
        super().__init__()
        self.geo_data = geo_data
        self.mode = mode
        self.date1 = date1
        self.date2 = date2
        self.specific_date = specific_date

    def run(self):
        try:
            # 1. Geometry Setup
            if isinstance(self.geo_data, dict):
                if 'geometry' in self.geo_data:
                    geometry = ee.Geometry(self.geo_data['geometry'])
                else:
                    geometry = ee.Geometry(self.geo_data)
            else:
                geometry = self.geo_data

            # 2. Image Selection Logic
            image = None
            vis_params = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 3000, 'gamma': 1.4}
            
            ee_date = ee.Date(self.date1)

            if self.mode == "range":
                col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                         .filterBounds(geometry)
                         .filterDate(self.date1, self.date2)
                         .map(mask_s2_clouds))
                
                # Sort by Cloud Cover (Ascending)
                image = col.sort('CLOUDY_PIXEL_PERCENTAGE', True).first()
                
                if image:
                    image = image.clip(geometry)
            
            elif self.mode == "single":
                target_date = ee.Date(self.specific_date) if self.specific_date else ee_date
                
                search_col = (ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED')
                              .filterBounds(geometry)
                              .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 10)))

                if self.specific_date:
                     col = search_col.filterDate(target_date, target_date.advance(1, 'day'))
                     image = col.first()
                else:
                    col = (search_col
                           .filterDate(target_date.advance(-30, 'day'), target_date.advance(30, 'day'))
                           .sort('CLOUDY_PIXEL_PERCENTAGE', True))
                    
                    image = col.first()

                if image:
                    image = image.clip(geometry)

            # 3. Fetch Map ID
            if image:
                map_id_dict = image.getMapId(vis_params)
                tile_url = map_id_dict['tile_fetcher'].url_format
                self.finished_signal.emit(tile_url)
            else:
                self.error_signal.emit("No suitable map image found.")

        except Exception as e:
            print(f"Map Worker Error: {e}")
            self.error_signal.emit(str(e))
