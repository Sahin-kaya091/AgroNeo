# core package - backend logic modules for AgroNeo3
#
# This package contains:
#   ee_utils         - Earth Engine initialization and cloud masking
#   classification   - Vegetation classification model and constants
#   analysis_worker  - AnalysisWorker QThread for data analysis
#   map_layer_worker - MapLayerWorker QThread for map tile generation
#   database         - LicenseManager (Firebase)
#   cache_utils      - AnalysisCache (SQLite)
#   weather_service  - WeatherWorker (Open-Meteo API)
#   historical_analysis - TrendWorker for historical trends
#   map_utils        - Map HTML generation
#   geo_utils        - GeoJSON/view parsing utilities
