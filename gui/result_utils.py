
from PyQt5.QtWidgets import (QMessageBox, QFrame, QVBoxLayout, QLabel, QTableWidgetItem)
from PyQt5.QtGui import QFont, QColor, QPixmap, QIcon, QPainter
from PyQt5.QtCore import Qt

def display_results(app, stats):
    """
    Updates the UI with analysis results.
    'app' is the main application instance (NeoAgroApp).
    'stats' is the dictionary containing analysis data.
    """
    # 1. Store stats in memory (if not already there by worker callback)
    # The worker callback usually does this, but safely ensure it.
    if hasattr(app, 'current_analysis_memory'):
        app.current_analysis_memory.update(stats)

    # 2. Branch based on Mode
    if app.user_mode == "Farmer":
        display_farmer_results(app, stats)
    else:
        display_engineer_results(app, stats)

def display_farmer_results(app, stats):
    """
    Simplified view for Farmer Mode.
    Shows: 
    - Health Status (Fertilizer, Water, Density)
    - Soil Analysis (SMI)
    """
    source = stats.get('source', 'S2')
    is_radar = (source == 'S1')

    # --- CLEAR PREVIOUS FARMER WIDGETS ---
    # Retrieve layout from app.page_farmer_health
    layout = app.layout_farmer_content
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()
        elif item.layout():
             # Recursively delete layouts if needed, but we mostly have widgets
             pass

    if is_radar:
        app.lbl_status.setText("No Optical Data -> Radar (S1)")
        # Show specific Radar msg for Farmer?
        lbl = QLabel("Optical data not available due to clouds.\nRadar analysis active (limited).")
        lbl.setStyleSheet("color: #D32F2F; font-size: 14px; padding: 20px;")
        layout.addWidget(lbl)
        layout.addStretch()
        return

    # --- OPTICAL DATA CALCULATIONS ---
    app.lbl_status.setText("Analysis Completed (Farmer Mode)")
    
    b3, b4 = stats.get('B3', 0), stats.get('B4', 0)
    b8, b11 = stats.get('B8', 0), stats.get('B11', 0)

    def calc_idx(n, d): return n / d if d != 0 else 0.0

    # 1. Plant Fertilizer Balance (GNDVI %)
    # GNDVI = (NIR - GREEN) / (NIR + GREEN) = (B8 - B3) / (B8 + B3)
    gndvi = calc_idx(b8 - b3, b8 + b3)
    fert_score = max(0, min(100, gndvi * 100.0))
    
    # 2. Plant Water Balance (NDVI scaled %)
    # NDVI = (NIR - RED) / (NIR + RED)
    # User Request: 0.5 NDVI = 100/100
    ndvi = calc_idx(b8 - b4, b8 + b4)
    ndmı = calc_idx(b8 - b11, b8 + b11)

    water_score = max(0, min(100, ((ndmı + 0.1 )/0.5) * 100.0))

    # 3. Plant Density Status (NDVI %)
    # User Request: NDVI out of 100 (0-1 -> 0-100)
    density_score = max(0, min(100, ndvi * 100.0))

    # --- UI CREATION HELPER ---
    def create_farmer_card(title, score, color_theme, status_text=None, force_color=None):
        # color_theme: 'yellow', 'blue', 'green'
        # force_color: tuple (bg, border, text) overrides theme logic
        
        # Default Colors
        bg, text, border = "#ffffff", "#333333", "#dddddd"
        
        if force_color:
            bg, border, text = force_color
        else:
            if color_theme == 'yellow': # Fertilizer
                # Shades of Yellow
                if score > 50: bg, text, border = "#FFF8E1", "#F57F17", "#FFD54F" # Darker yellow/orange
                else:          bg, text, border = "#FFFDE7", "#F9A825", "#FFF59D" # Light yellow
                
            elif color_theme == 'blue': # Water
                # Shades of Blue
                if score > 50: bg, text, border = "#E3F2FD", "#0D47A1", "#64B5F6" # Dark blue text
                else:          bg, text, border = "#E1F5FE", "#0277BD", "#81D4FA" # Light blue
                
            elif color_theme == 'green': # Density
                # Shades of Green
                if score > 50: bg, text, border = "#E8F5E9", "#1B5E20", "#81C784" # Dark green text
                else:          bg, text, border = "#F1F8E9", "#33691E", "#AED581" # Light green

        frame = QFrame()
        app.add_shadow(frame, blur=15, y_offset=3)
        frame.setStyleSheet(f"background-color: {bg}; border-radius: 12px; border: 1px solid {border};")
        frame.setMinimumHeight(120 if status_text else 110)
        
        l = QVBoxLayout(frame)
        l.setAlignment(Qt.AlignCenter)
        
        lbl_t = QLabel(title)
        lbl_t.setFont(QFont("Segoe UI", 12, QFont.Bold))
        lbl_t.setStyleSheet(f"color: {text}; border:none; background:transparent;")
        lbl_t.setAlignment(Qt.AlignCenter)
        
        # Status Text (New)
        if status_text:
            lbl_s = QLabel(status_text)
            lbl_s.setFont(QFont("Segoe UI", 11, QFont.Bold))
            lbl_s.setStyleSheet(f"color: {text}; border:none; background:transparent;")
            lbl_s.setAlignment(Qt.AlignCenter)
            # l.addWidget(lbl_s)  <-- REMOVED, will add later
        
        lbl_v = QLabel(f"{score:.1f} / 100")
        lbl_v.setFont(QFont("Segoe UI", 32, QFont.Bold))
        lbl_v.setStyleSheet(f"color: {text}; border:none; background:transparent;")
        lbl_v.setAlignment(Qt.AlignCenter)

        # Add to layout in correct order: Title -> Status -> Value
        l.addWidget(lbl_t)
        if status_text:
             # Ensure lbl_s was created above if status_text is True
             # We need to make sure lbl_s reference exists or move creation here
             # To be safe, let's redefine the flow slightly in this block
             pass 
             # Actually, simpler to just replace the whole block to be clean.
             
        # Re-writing the block cleanly below:
        
        l.addWidget(lbl_t)
        if 'lbl_s' in locals():
            l.addWidget(lbl_s)
        l.addWidget(lbl_v)
        
        return frame

    # --- ADD CARDS TO LAYOUT ---
    
    # Section Title
    lbl_h = QLabel("Health Status")
    lbl_h.setFont(QFont("Segoe UI", 14, QFont.Bold))
    lbl_h.setStyleSheet("color: #333; margin-bottom: 5px;")
    lbl_h.setAlignment(Qt.AlignCenter)
    layout.addWidget(lbl_h)

    # 0. AI-Based Health Analysis
    # ... (Keep existing Health Logic) ...
    # --- Health Calculation Replica ---
    past_ndvi = stats.get('past_ndvi', None)
    delta_ndvi = stats.get('ndvi_change', 0.0)
    evi = calc_idx(b8 - b4, b8 + 6 * b4 - 7.5 * stats.get('B2', 0) + 10000) * 2.5
    savi = (( (b8/10000) - (b4/10000) ) / ( (b8/10000) + (b4/10000) + 0.5 )) * 1.5
    ndre = calc_idx(b8 - stats.get('B5',0), b8 + stats.get('B5',0))
    rendvi = calc_idx(stats.get('B6',0) - stats.get('B5',0), stats.get('B6',0) + stats.get('B5',0))
    
    f_ndvi = max(0, ndvi)
    f_savi = max(0, savi)
    f_ndwi = max(0, calc_idx(b8 - b11, b8 + b11))
    f_evi = max(0, evi)
    f_rendvi = max(0, rendvi)
    f_gndvi = max(0, gndvi)
    
    stage_name = "Unknown"
    health_score = 0.0

    if ndvi < 0.25:
        stage_name = "Fallow / Preparation (Soil)"
        health_score = ((0.8 * f_savi) + (0.2 * f_ndvi)) * 0.6
    elif past_ndvi is not None:
        if delta_ndvi > 0.05:
            stage_name = "Rapid Growth (Active)"
            s_ndvi = min(1.0, f_ndvi / 0.80)
            s_ndwi = min(1.0, f_ndwi / 0.50)
            s_rendvi = min(1.0, f_rendvi / 0.60)
            s_gndvi = min(1.0, f_gndvi / 0.75)
            health_score = (0.30 * s_ndvi) + (0.20 * s_ndwi) + (0.30 * s_rendvi) + (0.20 * s_gndvi)
        elif delta_ndvi < -0.05:
            stage_name = "Harvest / Maturation"
            s_evi = min(1.0, f_evi / 0.60)
            health_score = (0.6 * s_evi) + (0.4 * f_ndvi)
        elif ndvi > 0.60:
            stage_name = "Maturity / Peak Period"
            s_evi = min(1.0, f_evi / 0.60)
            s_ndwi = min(1.0, f_ndwi / 0.50)
            s_rendvi = min(1.0, f_rendvi / 0.60)
            s_gndvi = min(1.0, f_gndvi / 0.80)
            health_score = (0.35 * s_evi) + (0.15 * s_ndwi) + (0.40 * s_rendvi) + (0.10 * s_gndvi)
        else:
            stage_name = "Early Stage / Slow Growth"
            s_savi = min(1.0, f_savi / 0.40)
            s_ndvi = min(1.0, f_ndvi / 0.50)
            health_score = (0.40 * s_savi) + (0.40 * s_ndvi) + (0.20 * f_ndwi)
    else:
        if ndvi < 0.45:
            stage_name = "Early Stage (Estimated)"
            health_score = ((0.5 * f_savi) + (0.5 * f_ndvi)) * 1.5
        elif ndvi < 0.70:
            stage_name = "Growth Stage (Estimated)"
            s_ndvi = min(1.0, f_ndvi / 0.75)
            health_score = s_ndvi
        else:
            stage_name = "Maturity Stage (Estimated)"
            s_evi = min(1.0, f_evi / 0.60)
            health_score = s_evi

    final_health_score = min(100, max(0, health_score * 100))
    
    app.current_analysis_memory["stage"] = stage_name
    app.current_analysis_memory["health_score"] = f"{final_health_score:.1f}"

    # Visuals for Health Card
    h_bg, h_border, h_text = "#E8F5E9", "#4CAF50", "#1B5E20"
    if final_health_score < 40:
        h_bg, h_border, h_text = "#FFEBEE", "#EF5350", "#B71C1C"
    elif final_health_score < 70:
        h_bg, h_border, h_text = "#FFF8E1", "#FFB74D", "#E65100"

    card_health = create_farmer_card("AI-Based Health Analysis", final_health_score, 'green', 
                                     status_text=stage_name, force_color=(h_bg, h_border, h_text))
    layout.addWidget(card_health)
    layout.addSpacing(10)

    # 1. PLANT FERTILIZER BALANCE (Updated Logic with Yellow Theme)
    fert_status = "Normal"
    # Using Shades of Yellow/Orange uniformly
    # Format: (BG, Border, Text)
    f_colors = ("#FFFDE7", "#FBC02D", "#F57F17") # Default

    if fert_score < 15:
        fert_status = "Critical Fertilizer Deficiency"
        # Pale Yellow / Cream
        f_colors = ("#FFF9C4", "#FBC02D", "#E65100") 
    elif fert_score < 40:
        fert_status = "Fertilizer Deficiency"
        # Light Yellow
        f_colors = ("#FFF59D", "#FBC02D", "#EF6C00")
    elif fert_score < 47:
        fert_status = "Normal (Potential Fertilizer Deficiency)"
        # Yellow
        f_colors = ("#FFF176", "#FBC02D", "#F57F17")
    elif fert_score < 57:
        fert_status = "Normal"
        # Gold / Rich Yellow (Ideal) - Distinctive
        f_colors = ("#FFD54F", "#FFA000", "#BF360C")
    elif fert_score < 63:
        fert_status = "Normal (Potential Fertilizer Excess)"
        # Yellow (Same as 40-47 roughly)
        f_colors = ("#FFF176", "#FBC02D", "#F57F17")
    elif fert_score < 76:
        fert_status = "Excess Fertilizer"
        # Orange-Yellow
        f_colors = ("#FFB74D", "#FB8C00", "#E65100")
    else: # 76-100
        fert_status = "Critical Fertilizer Excess"
        # Dark Orange / Amber
        f_colors = ("#FF9800", "#F57C00", "#3E2723")

    card_fert = create_farmer_card("Plant Fertilizer Balance", fert_score, 'yellow', 
                                   status_text=fert_status, force_color=f_colors)
    layout.addWidget(card_fert)

    # 2. Plant Water Balance (Updated Logic with Blue Theme)
    water_status = "Normal"
    # Format: (BG, Border, Text)
    # Default
    w_colors = ("#E1F5FE", "#29B6F6", "#01579B") 

    if water_score < 15:
        water_status = "Very Dry"
        # Pale Blue / White-ish
        w_colors = ("#E1F5FE", "#81D4FA", "#01579B")
    elif water_score < 33:
        water_status = "Dry"
        # Light Blue
        w_colors = ("#B3E5FC", "#4FC3F7", "#01579B")
    elif water_score < 38:
        water_status = "Normal (Potential Dry)"
        # Soft Blue
        w_colors = ("#81D4FA", "#29B6F6", "#0D47A1")
    elif water_score < 50:
        water_status = "Normal"
        # Sky Blue (Ideal) - Vibrant
        w_colors = ("#4FC3F7", "#039BE5", "#0D47A1")
    elif water_score < 55:
        water_status = "Normal (Potential Moist)"
        # Medium Blue
        w_colors = ("#29B6F6", "#0288D1", "#000000")
    elif water_score < 70:
        water_status = "Moist"
        # Deep Blue
        w_colors = ("#039BE5", "#0277BD", "#FFFFFF")
    else: # 70-100
        water_status = "Very Moist"
        # Dark Blue
        w_colors = ("#0277BD", "#01579B", "#FFFFFF")

    card_water = create_farmer_card("Plant Water Balance", water_score, 'blue',
                                    status_text=water_status, force_color=w_colors)
    layout.addWidget(card_water)

    # 3. Plant Density Status (Updated Logic with Green Theme)
    density_status = "Normal"
    # Format: (BG, Border, Text)
    
    # Default
    d_colors = ("#E8F5E9", "#66BB6A", "#1B5E20")

    if density_score < 20:
        density_status = "Very Low Yielding Plant"
        # Pale Green / White-ish
        d_colors = ("#F1F8E9", "#AED581", "#33691E")
    elif density_score < 37:
        density_status = "Low Yielding Plant"
        # Light Green
        d_colors = ("#DCEDC8", "#8BC34A", "#33691E")
    elif density_score < 45:
        density_status = "Normal (Potentially Low Yielding Plant)"
        # Soft Green
        d_colors = ("#C8E6C9", "#66BB6A", "#1B5E20")
    elif density_score < 55:
        density_status = "Normal"
        # Medium Green (Ideal)
        d_colors = ("#A5D6A7", "#4CAF50", "#1B5E20")
    elif density_score < 60:
        density_status = "Normal (Potentially High Yielding Plant)"
        # Rich Green
        d_colors = ("#81C784", "#43A047", "#000000")
    elif density_score < 75:
        density_status = "High Yielding Plant"
        # Deep Green
        d_colors = ("#66BB6A", "#388E3C", "#FFFFFF")
    else: # 75-100
        density_status = "Very High Yielding Plant"
        # Dark Green
        d_colors = ("#4CAF50", "#2E7D32", "#FFFFFF")

    card_dens = create_farmer_card("Plant Density Status", density_score, 'green',
                                   status_text=density_status, force_color=d_colors)
    layout.addWidget(card_dens)

    # 4. Soil Analysis (Using reuse logic or simple duplicate)
    # User wanted "AI-Based Soil Analysis" same as before. 
    # Let's recalculate SMI here for display consistency or pass logic.
    # The SMI is already in 'stats'.
    smi_raw = stats.get('soil_moisture', 0.0)
    smi_percent = min(100.0, max(0.0, (smi_raw * 100.0) + 10.0))
    
    # Colors for Soil (Blue scales)
    s_bg, s_border, s_text = "#E3F2FD", "#90CAF9", "#0D47A1"
    stage_soil = "Very Dry"
    if smi_percent > 85: stage_soil = "Very Moist"; s_bg = "#0D47A1"; s_text = "white"
    elif smi_percent > 70: stage_soil = "Moist"; s_bg = "#1976D2"; s_text = "white"
    elif smi_percent > 40: stage_soil = "Healthy"; s_bg = "#64B5F6"; s_text = "black"
    elif smi_percent > 20: stage_soil = "Dry"; s_bg = "#BBDEFB"; s_text = "#0D47A1"

    frame_soil = QFrame()
    app.add_shadow(frame_soil, blur=15, y_offset=3)
    frame_soil.setStyleSheet(f"background-color: {s_bg}; border-radius: 12px; border: 1px solid {s_border};")
    frame_soil.setMinimumHeight(110)
    
    ls = QVBoxLayout(frame_soil)
    ls.setAlignment(Qt.AlignCenter)
    
    lbl_st = QLabel("AI Based Soil Analysis")
    lbl_st.setFont(QFont("Segoe UI", 12, QFont.Bold))
    lbl_st.setStyleSheet(f"color: {s_text}; border:none; background:transparent;")
    lbl_st.setAlignment(Qt.AlignCenter)

    lbl_sv = QLabel(f"{smi_percent:.1f} / 100")
    lbl_sv.setFont(QFont("Segoe UI", 32, QFont.Bold))
    lbl_sv.setStyleSheet(f"color: {s_text}; border:none; background:transparent;")
    lbl_sv.setAlignment(Qt.AlignCenter)

    lbl_ss = QLabel(stage_soil)
    lbl_ss.setFont(QFont("Segoe UI", 10, QFont.Bold))
    lbl_ss.setStyleSheet(f"color: {s_text}; border:none; background:transparent;")
    lbl_ss.setAlignment(Qt.AlignCenter)

    ls.addWidget(lbl_st)
    ls.addWidget(lbl_ss)
    ls.addWidget(lbl_sv)

    layout.addSpacing(10)
    layout.addWidget(frame_soil)
    layout.addStretch()
    
    # Ensure button is shown
    app.rec_btn.show()

    # --- SAVE SCORES FOR SMART ANALYSIS (NEW) ---
    app.current_analysis_memory['farmer_scores'] = {
        'fertilizer': fert_score,
        'water': water_score,
        'density': density_score,
        'soil': smi_percent
    }

def display_engineer_results(app, stats):
    source = stats.get('source', 'S2')
    
    # helper for cleanup
    keys_to_clear = ["HealthLine", "HealthHeader", "HealthFrame", "HealthScore", "HealthStage",
                     "SoilLine", "SoilHeader", "SoilFrame", "SoilScore", "SoilStage"]
    for k in keys_to_clear:
        if k in app.index_labels:
            try:
                app.index_labels[k].setParent(None)
                app.index_labels[k].deleteLater()
                del app.index_labels[k]
            except:
                pass

    if source == 'S2':
        app.lbl_status.setText("Analysis Completed (Sentinel-2 Optical)")
        app.lbl_status.setStyleSheet("color: #2E7D32; font-style: italic; font-weight: 500;")
        
        b2, b3, b4 = stats.get('B2', 0), stats.get('B3', 0), stats.get('B4', 0)
        b5, b6, b7 = stats.get('B5', 0), stats.get('B6', 0), stats.get('B7', 0)
        b8, b11 = stats.get('B8', 0), stats.get('B11', 0)

        app.band_labels["B2 (Blue)"].setText(f"{b2:.0f}")
        app.band_labels["B3 (Green)"].setText(f"{b3:.0f}")
        app.band_labels["B4 (Red)"].setText(f"{b4:.0f}")
        app.band_labels["B5 (RE1)"].setText(f"{b5:.0f}")
        app.band_labels["B6 (RE2)"].setText(f"{b6:.0f}")
        app.band_labels["B7 (RE3)"].setText(f"{b7:.0f}")
        app.band_labels["B8 (NIR)"].setText(f"{b8:.0f}")

        def calc_idx(n, d):
            return n / d if d != 0 else 0.0

        ndvi = calc_idx(b8 - b4, b8 + b4)
        evi = 2.5 * calc_idx(b8 - b4, b8 + 6 * b4 - 7.5 * b2 + 10000)
        _b8, _b4 = b8 / 10000.0, b4 / 10000.0
        savi = ((_b8 - _b4) / (_b8 + _b4 + 0.5)) * 1.5
        ndre = calc_idx(b8 - b5, b8 + b5)
        rendvi = calc_idx(b6 - b5, b6 + b5)
        gndvi = calc_idx(b8 - b3, b8 + b3)
        ndwi = calc_idx(b8 - b11, b8 + b11)

        app.index_labels["NDVI(PHOTOSYNTHESIS ACTIVITY)"].setText(f"{ndvi:.2f}")
        app.index_labels["EVI(DENSE VEGETATION NDVI)"].setText(f"{evi:.2f}")
        app.index_labels["SAVI(SPARSE VEGETATION NDVI)"].setText(f"{savi:.2f}")
        app.index_labels["NDRE(CHLOROPHYLL CHANGING)"].setText(f"{ndre:.2f}")
        app.index_labels["RENDVI(CANOPY STRUCTURE)"].setText(f"{rendvi:.2f}")
        app.index_labels["GNDVI(NITROGEN CONTENT)"].setText(f"{gndvi:.2f}")
        app.index_labels["NDWI(WATER CONTENT)"].setText(f"{ndwi:.2f}")

        # --- RVI CALCULATION ---
        rvi_val = 0.0
        if 'VH' in stats and 'VV' in stats:
            try:
                vh_db = stats['VH']
                vv_db = stats['VV']
                # dB to Linear conversion: 10^(dB/10)
                vh_lin = 10 ** (vh_db / 10.0)
                vv_lin = 10 ** (vv_db / 10.0)
                
                # RVI = (4 * VH) / (VV + VH)
                denom = vv_lin + vh_lin
                if denom != 0:
                    rvi_val = (4 * vh_lin) / denom
            except Exception as e:
                print(f"RVI Calc Error: {e}")
        
        app.index_labels["RVI(RADAR VEGETATION INDEX)"].setText(f"{rvi_val:.2f}")

        app.current_analysis_memory["indices"] = {
            "NDVI": f"{ndvi:.2f}", "EVI": f"{evi:.2f}", "SAVI": f"{savi:.2f}",
            "NDRE": f"{ndre:.2f}", "RENDVI": f"{rendvi:.2f}", "GNDVI": f"{gndvi:.2f}", 
            "NDWI": f"{ndwi:.2f}", "RVI": f"{rvi_val:.2f}"
        }
        
        # Activate Smart Recommendation Button
        app.rec_btn.show()
        if hasattr(app, 'blink_timer') and not app.blink_timer.isActive():
            app.blink_timer.start()

        past_ndvi = stats.get('past_ndvi', None)
        delta_ndvi = stats.get('ndvi_change', 0.0)

        f_ndvi = max(0, ndvi)
        f_savi = max(0, savi)
        f_ndwi = max(0, ndwi)
        f_evi = max(0, evi)
        f_rendvi = max(0, rendvi)
        f_gndvi = max(0, gndvi)

        stage_name = "Unknown"
        health_score = 0.0

        # Health Algorithm (Preserved Logic)
        if ndvi < 0.25:
            stage_name = "Fallow / Preparation (Soil)"
            health_score = ((0.8 * f_savi) + (0.2 * f_ndvi)) * 0.6
        elif past_ndvi is not None:
            if delta_ndvi > 0.05:
                stage_name = "Rapid Growth (Active)"
                s_ndvi = min(1.0, f_ndvi / 0.80)
                s_ndwi = min(1.0, f_ndwi / 0.50)
                s_rendvi = min(1.0, f_rendvi / 0.60)
                s_gndvi = min(1.0, f_gndvi / 0.75)
                health_score = (0.30 * s_ndvi) + (0.20 * s_ndwi) + (0.30 * s_rendvi) + (0.20 * s_gndvi)
            elif delta_ndvi < -0.05:
                # Assuming harvest
                stage_name = "Harvest / Maturation"
                s_evi = min(1.0, f_evi / 0.60)
                health_score = (0.6 * s_evi) + (0.4 * f_ndvi)
            elif ndvi > 0.60:
                stage_name = "Maturity / Peak Period"
                s_evi = min(1.0, f_evi / 0.60)
                s_ndwi = min(1.0, f_ndwi / 0.50)
                s_rendvi = min(1.0, f_rendvi / 0.60)
                s_gndvi = min(1.0, f_gndvi / 0.80)
                health_score = (0.35 * s_evi) + (0.15 * s_ndwi) + (0.40 * s_rendvi) + (0.10 * s_gndvi)
            else:
                stage_name = "Early Stage / Slow Growth"
                s_savi = min(1.0, f_savi / 0.40)
                s_ndvi = min(1.0, f_ndvi / 0.50)
                health_score = (0.40 * s_savi) + (0.40 * s_ndvi) + (0.20 * f_ndwi)
        else:
            if ndvi < 0.45:
                stage_name = "Early Stage (Estimated)"
                health_score = ((0.5 * f_savi) + (0.5 * f_ndvi)) * 1.5
            elif ndvi < 0.70:
                stage_name = "Growth Stage (Estimated)"
                s_ndvi = min(1.0, f_ndvi / 0.75)
                health_score = s_ndvi
            else:
                stage_name = "Maturity Stage (Estimated)"
                s_evi = min(1.0, f_evi / 0.60)
                health_score = s_evi

        final_score = min(100, max(0, health_score * 100))

        app.current_analysis_memory["stage"] = stage_name
        app.current_analysis_memory["health_score"] = f"{final_score:.1f}"

        scroll_area = app.page_indices.layout().itemAt(0).widget()
        content_widget = scroll_area.widget()
        layout_target = content_widget.layout()

        # Separator Line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Plain)
        line.setStyleSheet("border-top: 1px solid #eee; margin: 10px 0;")
        layout_target.addWidget(line)

        lbl_head = QLabel("AI-Based Health Analysis")
        lbl_head.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_head.setAlignment(Qt.AlignCenter)
        lbl_head.setStyleSheet("color: #333;")
        layout_target.addWidget(lbl_head)

        frame = QFrame()
        app.add_shadow(frame, blur=15, y_offset=3)
        frame.setMinimumHeight(100)

        l = QVBoxLayout()
        l.setContentsMargins(15, 15, 15, 15)
        frame.setLayout(l)

        lbl_stage = QLabel(stage_name)
        lbl_stage.setAlignment(Qt.AlignCenter)
        lbl_stage.setFont(QFont("Segoe UI", 11, QFont.Bold))

        lbl_score_val = QLabel(f"{final_score:.1f} / 100")
        lbl_score_val.setAlignment(Qt.AlignCenter)
        lbl_score_val.setFont(QFont("Segoe UI", 32, QFont.Bold))

        l.addWidget(lbl_stage)
        l.addWidget(lbl_score_val)
        layout_target.addWidget(frame)

        bg, border, text = "#E8F5E9", "#4CAF50", "#1B5E20"
        if final_score < 40:
            bg, border, text = "#FFEBEE", "#EF5350", "#B71C1C"
        elif final_score < 70:
            bg, border, text = "#FFF8E1", "#FFB74D", "#E65100"

        frame.setStyleSheet(f"background-color: {bg}; border-radius: 12px; border: 1px solid {border};")
        lbl_stage.setStyleSheet(f"color: {text}; border:none; background:transparent;")
        lbl_score_val.setStyleSheet(f"color: {text}; border:none; background:transparent;")

        app.index_labels["HealthLine"] = line
        app.index_labels["HealthHeader"] = lbl_head
        app.index_labels["HealthFrame"] = frame
        app.index_labels["HealthScore"] = lbl_score_val
        app.index_labels["HealthStage"] = lbl_stage

        # --- NEW: AI BASED SOIL ANALYSIS UI (SMI) ---
        smi_raw = stats.get('soil_moisture', 0.0)
        smi_percent = min(100.0, max(0.0, (smi_raw * 100.0) + 10.0))

        # Determine Labels and Colors based on SMI
        soil_stage = "Unknown"
        s_bg, s_border, s_text = "#E3F2FD", "#90CAF9", "#0D47A1" # Default Very Dry

        if smi_percent < 20:
            soil_stage = "Very Dry"
            s_bg = "#E3F2FD"     # 0-20 Very Light Blue
            s_border = "#90CAF9"
            s_text = "#0D47A1"   # Dark Blue Text
        elif smi_percent < 40:
            soil_stage = "Dry"
            s_bg = "#BBDEFB"     # 20-40 Light Blue
            s_border = "#64B5F6"
            s_text = "#0D47A1"   # Dark Blue Text
        elif smi_percent < 70:
            soil_stage = "Healthy"
            s_bg = "#64B5F6"     # 40-70 Medium Blue
            s_border = "#2196F3"
            s_text = "#000000"   # Black Text for contrast
        elif smi_percent < 85:
            soil_stage = "Moist"
            s_bg = "#1976D2"     # 70-85 Darker Blue
            s_border = "#1565C0"
            s_text = "#FFFFFF"   # White Text
        else:
            soil_stage = "Very Moist"
            s_bg = "#0D47A1"     # 85-100 Deepest Blue
            s_border = "#002171"
            s_text = "#FFFFFF"   # White Text

        # UI Elements for Soil
        line_soil = QFrame()
        line_soil.setFrameShape(QFrame.HLine)
        line_soil.setFrameShadow(QFrame.Plain)
        line_soil.setStyleSheet("border-top: 1px solid #eee; margin: 10px 0;")
        layout_target.addWidget(line_soil)

        lbl_head_soil = QLabel("AI Based Soil Analysis")
        lbl_head_soil.setFont(QFont("Segoe UI", 11, QFont.Bold))
        lbl_head_soil.setAlignment(Qt.AlignCenter)
        lbl_head_soil.setStyleSheet("color: #333;")
        layout_target.addWidget(lbl_head_soil)

        frame_soil = QFrame()
        app.add_shadow(frame_soil, blur=15, y_offset=3)
        frame_soil.setMinimumHeight(100)
        
        l_soil = QVBoxLayout()
        l_soil.setContentsMargins(15, 15, 15, 15)
        frame_soil.setLayout(l_soil)

        lbl_soil_stage = QLabel(soil_stage)
        lbl_soil_stage.setAlignment(Qt.AlignCenter)
        lbl_soil_stage.setFont(QFont("Segoe UI", 11, QFont.Bold))

        lbl_soil_val = QLabel(f"{smi_percent:.1f} / 100")
        lbl_soil_val.setAlignment(Qt.AlignCenter)
        lbl_soil_val.setFont(QFont("Segoe UI", 32, QFont.Bold))

        l_soil.addWidget(lbl_soil_stage)
        l_soil.addWidget(lbl_soil_val)
        layout_target.addWidget(frame_soil)

        # Apply Styles
        frame_soil.setStyleSheet(f"background-color: {s_bg}; border-radius: 12px; border: 1px solid {s_border};")
        lbl_soil_stage.setStyleSheet(f"color: {s_text}; border:none; background:transparent;")
        lbl_soil_val.setStyleSheet(f"color: {s_text}; border:none; background:transparent;")

        # Save references for cleanup
        app.index_labels["SoilLine"] = line_soil
        app.index_labels["SoilHeader"] = lbl_head_soil
        app.index_labels["SoilFrame"] = frame_soil
        app.index_labels["SoilScore"] = lbl_soil_val
        app.index_labels["SoilStage"] = lbl_soil_stage

        scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().maximum())

    elif source == 'S1':
        app.lbl_status.setText("No Optical Data -> Radar (S1)")
        app.lbl_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
        vv, vh = stats.get('VV', 0), stats.get('VH', 0)
        app.band_labels["B2 (Blue)"].setText("-")
        app.band_labels["B3 (Green)"].setText("-")
        app.band_labels["B4 (Red)"].setText(f"VV: {vv:.1f}")
        app.band_labels["B8 (NIR)"].setText(f"VH: {vh:.1f}")
        for k, lbl in app.index_labels.items():
            if hasattr(lbl, 'setText'): lbl.setText("---")
        bitki_durumu = "Dense Vegetation" if vh > -15 else ("Moderate Level" if vh > -20 else "Bare Soil")
        QMessageBox.information(app, "Radar Analysis",
                                f"No optical data. Radar used.\nVH: {vh:.1f} dB\nStatus: {bitki_durumu}")

def display_classification(app, results):
    app.table_class.setRowCount(0)
    app.current_analysis_memory["classification"] = results
    
    # Filter out metadata like 'tile_url' and ensure values are numeric
    filtered_items = {k: v for k, v in results.items() if k not in ['tile_url', 'legend_colors'] and isinstance(v, (int, float))}
    legend_colors = results.get('legend_colors', {})

    sorted_results = sorted(filtered_items.items(), key=lambda x: x[1], reverse=True)
    for name, percent in sorted_results:
        row_idx = app.table_class.rowCount()
        app.table_class.insertRow(row_idx)

        # Translate class names if necessary
        display_name = name
        if name == "Tarım Arazisi":
            display_name = "Agricultural Land"
        elif name == "Su":
            display_name = "Water"
        # Add other translations as needed based on worker output

        name_item = QTableWidgetItem(display_name)
        
        # --- ICON GENERATION ---
        # Look up color using original name (key in legend_colors) or display_name
        color_hex = legend_colors.get(name) or legend_colors.get(display_name)
        if color_hex:
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(color_hex))
            name_item.setIcon(QIcon(pixmap))
        # -----------------------

        app.table_class.setItem(row_idx, 0, name_item)
        percent_item = QTableWidgetItem(f"%{percent:.1f}")
        percent_item.setTextAlignment(Qt.AlignCenter)
        if name == "Tarım Arazisi" or display_name == "Agricultural Land":
            percent_item.setForeground(QColor("#2E7D32"))
            percent_item.setFont(QFont("Segoe UI", 9, QFont.Bold))
        elif name == "Su" or display_name == "Water":
            percent_item.setForeground(QColor("#1565C0"))
        app.table_class.setItem(row_idx, 1, percent_item)
