# Backward compatibility shim - imports from core package
# This file allows old `from worker import ...` to still work.

from core.analysis_worker import AnalysisWorker
from core.map_layer_worker import MapLayerWorker
from core.deforestation_worker import DeforestationWorker
from core.classification import (
    build_classification_model,
    PRODUCT_LABELS,
    ID_TO_PALETTE_IDX,
    PALETTE_COLORS
)