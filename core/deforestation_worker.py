import ee
from PyQt5.QtCore import QThread, pyqtSignal
from core.classification import build_classification_model, PRODUCT_LABELS


class DeforestationWorker(QThread):
    """
    Compares 'Tall Trees' (class ID '4') percentages between two years
    to compute deforestation/reforestation change.
    """
    finished_signal = pyqtSignal(dict)
    status_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    # Class ID for "Tall Trees" and "Orchard/Shrub/Nursery" in PRODUCT_LABELS
    TREE_CLASS_ID = '4'
    SHRUB_CLASS_ID = '7'

    def __init__(self, geometry, mode, date1, date2=None):
        super().__init__()
        self.geometry = geometry
        self.mode = mode
        self.date1 = date1
        self.date2 = date2

    def _determine_years(self):
        """Determine the two years to compare based on analysis mode."""
        try:
            year1 = int(self.date1.split("-")[0])
        except Exception:
            year1 = 2023

        if self.mode == "range" and self.date2:
            try:
                year2 = int(self.date2.split("-")[0])
            except Exception:
                year2 = year1

            # If same year in range mode, fall back to Y vs Y-1
            if year1 == year2:
                return year1 - 1, year1
            
            # Ensure older year is first (period1 = earlier, period2 = later)
            return min(year1, year2), max(year1, year2)
        else:
            # Single mode: compare with previous year
            return year1 - 1, year1

    def _get_forest_percentage(self, year):
        """
        Run classification for a given year and extract the sum of
        'Tall Trees' (4) and 'Orchard/Shrub/Nursery' (7) percentage.
        """
        classified, has_transition = build_classification_model(year, self.geometry)

        if classified is None:
            return None

        stats = classified.reduceRegion(
            reducer=ee.Reducer.frequencyHistogram(),
            geometry=self.geometry,
            scale=30,
            maxPixels=1e9,
            tileScale=4
        ).getInfo()

        if not stats:
            return None

        values_view = list(stats.values())
        if not values_view:
            return None

        histogram = values_view[0]
        if not histogram:
            return None

        total = sum(histogram.values())
        if total == 0:
            return None

        tree_count = histogram.get(self.TREE_CLASS_ID, 0)
        shrub_count = histogram.get(self.SHRUB_CLASS_ID, 0)
        
        return ((tree_count + shrub_count) / total) * 100

    def run(self):
        try:
            year_old, year_new = self._determine_years()

            # --- Period 1 (older/baseline year) ---
            self.status_signal.emit(f"Forest Analysis: Analyzing {year_old}...")
            pct_old = self._get_forest_percentage(year_old)

            # --- Period 2 (newer/current year) ---
            self.status_signal.emit(f"Forest Analysis: Analyzing {year_new}...")
            pct_new = self._get_forest_percentage(year_new)

            # --- Compute change ---
            if pct_old is None and pct_new is None:
                self.error_signal.emit("Insufficient data for both periods.")
                return

            change = None
            if pct_old is not None and pct_new is not None:
                change = pct_new - pct_old

            result = {
                'period1_year': year_old,
                'period2_year': year_new,
                'period1_pct': pct_old,
                'period2_pct': pct_new,
                'change_pct': change,
            }

            self.status_signal.emit("Forest analysis complete.")
            self.finished_signal.emit(result)

        except Exception as e:
            print(f"DEFORESTATION WORKER ERROR: {e}")
            self.error_signal.emit(str(e))
