
import sys
import json
import os
import traceback # Added for crash logging
import ee
import geemap.foliumap as geemap
from folium import plugins
from geopy.geocoders import Nominatim
from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QWidget, QLabel, QFrame, QDateEdit, QPushButton, QMessageBox, QComboBox,
                             QStackedWidget, QSizePolicy, QLineEdit, QInputDialog, QTableWidget, QTableWidgetItem,
                             QHeaderView, QGraphicsDropShadowEffect, QScrollArea)
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtCore import QUrl, QDate, Qt, QSize, QTimer, QThread
from PyQt5.QtGui import QFont, QColor, QIcon
from datetime import datetime

# --- Core modules ---
from core.analysis_worker import AnalysisWorker, PhenologyWorker
from core.map_layer_worker import MapLayerWorker
from core.deforestation_worker import DeforestationWorker
from core.classification import PRODUCT_LABELS
from core.weather_service import WeatherWorker
from core.historical_analysis import TrendWorker
import core.map_utils as map_utils
import core.geo_utils as geo_utils

# --- GUI modules ---
from gui.dialogs import RecordsDialog, ComparisonSelectionDialog, DateSelectionDialog, InfoDialog
import gui.result_utils as result_utils
from gui.trend_dialog import TrendGraphDialog




class NeoAgroApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AgroNeo - Advanced Agricultural Analysis Station")
        self.setGeometry(100, 100, 1400, 850)

        # --- MODERN GLOBAL STYLE ---
        self.apply_modern_theme()

        self.user_mode = "Engineer" # Default mode
        self.band_labels = {}
        self.index_labels = {}

        # --- DATA MANAGEMENT ---
        # self.current_analysis_memory = {}
        # base_dir = os.path.dirname(os.path.abspath(__file__))
        # logs_folder = os.path.join(base_dir, "Saved Logs")
        # if not os.path.exists(logs_folder):
        #     os.makedirs(logs_folder)
        # self.saved_records_file = os.path.join(logs_folder, "saved_records.json")
        # self.load_records()

        # --- DATA MANAGEMENT ---
        self.current_analysis_memory = {}

        # --- DÜZELTME BAŞLANGICI ---
        # Eğer program EXE ise (sys.frozen), exe'nin olduğu klasörü al.
        # Değilse normal dosya yolunu al.
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
        # --- DÜZELTME BİTİŞİ ---

        logs_folder = os.path.join(base_dir, "Saved Logs")

        # Klasör yoksa oluştur
        if not os.path.exists(logs_folder):
            os.makedirs(logs_folder)

        self.saved_records_file = os.path.join(logs_folder, "saved_records.json")
        self.load_records()

        # --- Main Layout ---
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_widget.setLayout(main_layout)

        # --- LEFT PANEL (MAP) ---
        left_container = QWidget()
        left_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_container.setLayout(left_layout)

        self.browser = QWebEngineView()
        self.current_start_date = "2023-06-01"
        self.current_end_date = "2023-09-30"
        self.analysis_mode = "range"

        # Index Descriptions
        self.index_descriptions = {
            "NDVI(PHOTOSYNTHESIS ACTIVITY)": "NDVI (Normalized Difference Vegetation Index)\n\nMeasures the density and greenness of vegetation. High values (close to 1) indicate healthy, dense vegetation, while low values indicate stressed vegetation or bare soil.",
            "EVI(DENSE VEGETATION NDVI)": "EVI (Enhanced Vegetation Index)\n\nSimilar to NDVI but corrects for atmospheric signals and soil background. It is more sensitive in areas with dense vegetation.",
            "SAVI(SPARSE VEGETATION NDVI)": "SAVI (Soil Adjusted Vegetation Index)\n\nAdjusts for soil brightness in areas where vegetative cover is low. Useful for early growth stages.",
            "NDRE(CHLOROPHYLL CHANGING)": "NDRE (Normalized Difference Red Edge)\n\nUses the Red Edge band to estimate chlorophyll content. It is more sensitive than NDVI for crops in later growth stages.",
            "RENDVI(CANOPY STRUCTURE)": "RENDVI (Red Edge NDVI)\n\nA variation of NDVI that uses the Red Edge band. It is useful for assessing plant health in dense canopies.",
            "GNDVI(NITROGEN CONTENT)": "GNDVI (Green NDVI)\n\nUses the Green band instead of the Red band. It is more sensitive to chlorophyll concentration than NDVI.",
            "NDWI(WATER CONTENT)": "NDWI (Normalized Difference Water Index)\n\nMeasures water content in vegetation and soil. High values indicate high water content.",
            "RVI(RADAR VEGETATION INDEX)": "RVI (Radar Vegetation Index)\n\nUses Radar (Sentinel-1) data to estimate vegetation structure and biomass. High values (close to 1) indicate dense vegetation. Useful when optical data is cloudy.",
            
            # --- Band Descriptions ---
            "B2 (Blue)": "Blue Band (490 nm)\n\nUsed for soil and vegetation mapping. It is sensitive to sediments in water and atmospheric scatters.",
            "B3 (Green)": "Green Band (560 nm)\n\nMeasures the green peak reflection of vegetation. It helps in assessing plant vigor.",
            "B4 (Red)": "Red Band (665 nm)\n\nCorresponds to the maximum chlorophyll absorption area. Crucial for vegetation classification.",
            "B5 (RE1)": "Red Edge 1 (705 nm)\n\nFirst Red Edge band. Sensitive to chlorophyll content and provides information on the vegetation stress.",
            "B6 (RE2)": "Red Edge 2 (740 nm)\n\nSecond Red Edge band. Useful for estimating Leaf Area Index (LAI) and biomass.",
            "B7 (RE3)": "Red Edge 3 (783 nm)\n\nThird Red Edge band. Used for classification of vegetation types and health monitoring.",
            "B8 (NIR)": "NIR Band (842 nm)\n\nNear Infrared band. Healthy vegetation reflects this strongly. Key for biomass and stress analysis."
        }

        # --- MAP VIEW STATE ---
        self.last_map_view = None
        self.pre_navigation_view = None # Stores view before "Go to Area"

        self.create_map_html(self.current_start_date, self.current_end_date, mode="range")
        file_path = os.path.abspath("temp_map.html")
        self.browser.setUrl(QUrl.fromLocalFile(file_path))
        self.browser.titleChanged.connect(self.on_map_interaction)

        left_layout.addWidget(self.browser)
        main_layout.addWidget(left_container, stretch=1)

        # --- FLOATING PANELS ---
        self.setup_date_panel()   # Moved up to ensure self.date_start exists
        self.setup_search_panel() # Now safe to call (calls update_weather)
        self.setup_records_button()
        self.setup_test_button()

        # --- RIGHT PANEL ---
        self.setup_right_panel(main_layout)

        self.map_worker = None
        self.stats_worker = None
        self.phenology_worker = None
        self.defor_worker = None
        
        # Deforestation Timer (Persistent for cancellation)
        self.defor_timer = QTimer()
        self.defor_timer.setSingleShot(True)
        self.defor_timer.timeout.connect(self.trigger_deforestation_analysis)



    def apply_modern_theme(self):
        """Defines the general CSS style of the application."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #F4F7F6;
            }
            QWidget {
                font-family: 'Segoe UI', sans-serif;
                font-size: 14px;
                color: #333;
            }

            /* --- STANDART BİLEŞENLER --- */
            QScrollBar:vertical {
                border: none;
                background: #f0f0f0;
                width: 10px;
                margin: 0px; 
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #c1c1c1;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                background: none;
            }

            QPushButton {
                background-color: #ffffff;
                border: 1px solid #dcdcdc;
                border-radius: 8px;
                padding: 6px 12px;
                color: #444;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                border-color: #bbb;
            }

            QLineEdit, QDateEdit, QComboBox {
                background-color: #fff;
                border: 1px solid #ccc;
                border-radius: 6px;
                padding: 5px;
                color: #333; /* Input yazı rengi */
            }

            /* --- TAKVİM (CALENDAR) KESİN ÇÖZÜM --- */

            /* 1. Takvim Ana Penceresi */
            QCalendarWidget {
                background-color: #ffffff;
                color: #000000;
            }

            /* 2. Navigasyon Alanı (Ay/Yıl Başlığı) - ID ile Hedefleme */
            QCalendarWidget QWidget#qt_calendar_navigationbar { 
                background-color: #ffffff; 
                border-bottom: 1px solid #e0e0e0;
            }

            /* 3. Günlerin Listelendiği Alan - ID ile Hedefleme (EN ÖNEMLİ KISIM) */
            /* Bu kısım siyah arka planı zorla beyaza çevirir */
            QCalendarWidget QTableView#qt_calendar_calendarview {
                background-color: #ffffff;  
                alternate-background-color: #ffffff;
                color: #000000;
                selection-background-color: #2E7D32; 
                selection-color: #ffffff;
                border: none;
            }

            /* 4. Başlıktaki Ok İşaretleri */
            QCalendarWidget QToolButton {
                color: #000000;
                background-color: transparent;
                icon-size: 24px;
                border: none;
                margin: 2px;
            }
            QCalendarWidget QToolButton:hover {
                background-color: #f0f0f0;
                border-radius: 4px;
            }
            QCalendarWidget QToolButton::menu-indicator {
                image: none; 
            }

            /* 5. Yıl Seçimi Kutusu */
            QCalendarWidget QSpinBox {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #2E7D32;
                selection-color: #ffffff;
                border: 1px solid #ccc;
            }

            /* 6. Her ihtimale karşı AbstractItemView hedeflemesi */
            QCalendarWidget QAbstractItemView:enabled {
                background-color: #ffffff;
                color: #000000;
                selection-background-color: #2E7D32;
                selection-color: #ffffff;
            }
        """)

    def style_calendar_widget(self, date_edit):
        """
        QDateEdit içindeki takvimi CSS yerine QPalette ile beyaza zorlar.
        Bu yöntem en inatçı siyah arka plan sorunlarını çözer.
        """
        calendar = date_edit.calendarWidget()

        # 1. PALET AYARLARI (CSS'in yapamadığını yapar)
        from PyQt5.QtGui import QPalette
        palette = QPalette()

        # Arka planları BEYAZ yap
        palette.setColor(QPalette.Window, Qt.white)
        palette.setColor(QPalette.Base, Qt.white)  # Izgara zemini
        palette.setColor(QPalette.AlternateBase, Qt.white)
        palette.setColor(QPalette.ToolTipBase, Qt.white)

        # Yazıları SİYAH yap
        palette.setColor(QPalette.Text, Qt.black)
        palette.setColor(QPalette.WindowText, Qt.black)
        palette.setColor(QPalette.ButtonText, Qt.black)

        # Seçili alanı YEŞİL yap
        palette.setColor(QPalette.Highlight, QColor("#2E7D32"))
        palette.setColor(QPalette.HighlightedText, Qt.white)

        calendar.setPalette(palette)

        # 2. CSS AYARLARI (Geri kalan makyaj)
        # Sadece navigasyon barı ve kenarlıklar için CSS kullanıyoruz.
        calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: white;
            }
            QToolButton {
                color: black;
                background-color: transparent;
                icon-size: 24px;
                font-weight: bold;
                border: none;
            }
            QToolButton:hover {
                background-color: #eee;
                border-radius: 4px;
            }
            QToolButton::menu-indicator {
                image: none;
            }
            QSpinBox {
                background-color: white;
                color: black;
                selection-background-color: #2E7D32;
                selection-color: white;
            }
            /* Günlerin olduğu tabloyu hedefle */
            QTableView {
                background-color: white;
                color: black;
                selection-background-color: #2E7D32;
                selection-color: white;
                gridline-color: white;
                outline: 0;
            }
        """)


    def add_shadow(self, widget, blur=20, y_offset=4):
        """Adds a modern shadow effect to widgets."""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(blur)
        shadow.setXOffset(0)
        shadow.setYOffset(y_offset)
        shadow.setColor(QColor(0, 0, 0, 30))
        widget.setGraphicsEffect(shadow)

    def setup_search_panel(self):
        self.search_panel = QFrame(self.browser)
        self.search_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95); 
                border-radius: 25px; 
                border: 1px solid rgba(0,0,0,0.1);
            }
        """)
        self.add_shadow(self.search_panel)

        self.search_panel.setFixedWidth(420)
        self.search_panel.setFixedHeight(55)

        layout = QHBoxLayout()
        layout.setContentsMargins(20, 5, 10, 5)
        self.search_panel.setLayout(layout)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Search location (City, Region, Coordinate)...")
        self.txt_search.setStyleSheet("border: none; background: transparent; font-size: 15px; color: #333;")
        self.txt_search.returnPressed.connect(self.search_location)

        btn_search = QPushButton("🔍")
        btn_search.setCursor(Qt.PointingHandCursor)
        btn_search.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32; 
                color: white; 
                border-radius: 18px; 
                font-weight: bold; 
                width: 36px; 
                height: 36px;
                border: none;
            } 
            QPushButton:hover { background-color: #1B5E20; }
        """)
        btn_search.clicked.connect(self.search_location)

        layout.addWidget(self.txt_search)
        layout.addWidget(btn_search)
        self.search_panel.show()

        self.setup_weather_panel()
        self.setup_recommendation_panel()

    def setup_recommendation_panel(self):
        self.rec_btn = QPushButton("Smart Analysis", self.browser)
        self.add_shadow(self.rec_btn)
        self.rec_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333;
                border: 2px solid #FF9800;
                border-radius: 20px;
                padding: 8px 15px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #FFF3E0; 
            }
        """)
        self.rec_btn.setFixedSize(150, 45)
        self.rec_btn.clicked.connect(self.show_smart_recommendations)
        self.rec_btn.hide() # Hidden by default
        
        # Blinking Timer
        self.blink_timer = QTimer()
        self.blink_timer.interval = 800
        self.blink_timer.timeout.connect(self.toggle_rec_btn_color)
        self.blink_state = False

    def toggle_rec_btn_color(self):
        self.blink_state = not self.blink_state
        if self.blink_state:
            self.rec_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: 2px solid #F57C00;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)
        else:
            self.rec_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #333;
                    border: 2px solid #FF9800;
                    border-radius: 20px;
                    font-weight: bold;
                    font-size: 13px;
                }
            """)

    def generate_recommendations(self, stats):
        recs = []
        
        # --- FARMER MODE LOGIC ---
        if 'farmer_scores' in self.current_analysis_memory:
            scores = self.current_analysis_memory['farmer_scores']
            
            # 1. FERTILIZER (Gübre) Analysis
            f_score = scores.get('fertilizer', 0)
            if f_score < 40:
                recs.append({
                    "title": "Serious Fertilizer Deficiency",
                    "icon": "⚠️",
                    "desc": f"Fertilizer Score is low ({f_score:.1f}/100). Plants are starving.",
                    "action": "Urgent: Perform soil analysis and apply comprehensive N-P-K treatment."
                })
            elif 40 <= f_score < 70:
                recs.append({
                    "title": "Moderate Nutrient Levels",
                    "icon": "🌱",
                    "desc": f"Fertilizer Score is moderate ({f_score:.1f}/100). Growth is acceptable but could be better.",
                    "action": "Consider top-dressing fertilizer application to boost yield."
                })
            else:
                recs.append({
                    "title": "Optimal Nutrient Status",
                    "icon": "✅",
                    "desc": f"Fertilizer Score is good ({f_score:.1f}/100).",
                    "action": "Maintain current fertilization schedule."
                })

            # 2. WATER (Su) Analysis
            w_score = scores.get('water', 0)
            if w_score < 30:
                recs.append({
                    "title": "Critical Water Stress",
                    "icon": "💧",
                    "desc": f"Water Score is critical ({w_score:.1f}/100). Vegetation is dehydrated.",
                    "action": "Immediate irrigation required to prevent permanent wilting."
                })
            elif 30 <= w_score < 60:
                 recs.append({
                    "title": "Moderate Water Stress",
                    "icon": "🚿",
                    "desc": f"Water Score is low ({w_score:.1f}/100).",
                    "action": "Plan irrigation soon. Monitor soil moisture sensors."
                })
            elif w_score > 90:
                 recs.append({
                    "title": "Excess Water Risk",
                    "icon": "🌊",
                    "desc": f"Water Score is very high ({w_score:.1f}/100). Risk of waterlogging.",
                    "action": "Check drainage systems. Pause irrigation."
                })
            else:
                 recs.append({
                    "title": "Ideal Water Balance",
                    "icon": "✅",
                    "desc": "Plant water content is within optimal range.",
                    "action": "Continue current irrigation practices."
                })

            # 3. DENSITY (Sıklık/Verim) Analysis
            d_score = scores.get('density', 0)
            if d_score < 35:
                recs.append({
                    "title": "Low Plant Density",
                    "icon": "📉",
                    "desc": f"Density Score is low ({d_score:.1f}/100). Crop emergence might be poor.",
                    "action": "Check for pest damage, bad seed quality, or soil crusting."
                })
            elif d_score > 85:
                 recs.append({
                    "title": "High Density / High Yield Potential",
                    "icon": "🏆",
                    "desc": "Vegetation cover is excellent.",
                    "action": "Monitor for fungal diseases due to high humidity in canopy."
                })

            # 4. SOIL (Toprak) Analysis
            s_score = scores.get('soil', 0)
            if s_score < 30:
                 recs.append({
                    "title": "Dry Soil",
                    "icon": "🏜️",
                    "desc": "Soil moisture reserves are depleted.",
                    "action": "Deep irrigation recommended to restore soil capacity."
                })
            
            return recs

        # --- ENGINEER/FALLBACK LOGIC ---
        indices = stats.get('indices', {})
        def get_val(key):
            try: return float(indices.get(key, 0))
            except: return 0.0

        gndvi = get_val('GNDVI')
        ndre = get_val('NDRE')
        ndwi = get_val('NDWI')
        ndvi = get_val('NDVI')

        # 1. Chlorophyll Status (NDRE & RENDVI focus)
        if ndre < 0.25:
             recs.append({
                "title": "Low Chlorophyll Detected",
                "icon": "",
                "desc": "Vegetation shows signs of low chlorophyll content.",
                "action": "Check for nutrient deficiencies (Iron, Magnesium) or disease."
            })
        elif ndre > 0.6:
             recs.append({
                "title": "Rich Chlorophyll Content",
                "icon": "",
                "desc": "Plants are green and healthy with high chlorophyll.",
                "action": "Maintain current nutrient management."
            })

        # 2. Nitrogen Status (GNDVI)
        if gndvi < 0.40:
            recs.append({
                "title": "Nitrogen Deficiency Risk",
                "icon": "",
                "desc": "GNDVI levels suggest insufficient nitrogen.",
                "action": "Apply nitrogen-rich fertilizer to support growth."
            })
        elif gndvi > 0.70:
             recs.append({
                "title": "Optimal Nitrogen",
                "icon": "",
                "desc": "Nitrogen levels appear sufficient for this stage.",
                "action": "No additional nitrogen fertilization required."
            })

        # 3. Water Status (NDWI)
        if ndwi < -0.15:
            recs.append({
                "title": "Water Stress (Drought)",
                "icon": "",
                "desc": "Soil/Canopy moisture is critically low.",
                "action": "Irrigate immediately. Check irrigation systems for blockages."
            })
        elif ndwi > 0.35:
             recs.append({
                "title": "Excess Moisture Risk",
                "icon": "",
                "desc": "High water content detected. Potential for waterlogging.",
                "action": "Ensure proper drainage to prevent root rot."
            })
        
        # 4. General Vigor (NDVI)
        if ndvi < 0.3:
            recs.append({
                "title": "Weak Vegetation Health",
                "icon": "",
                "desc": "Overall biomass and density are low.",
                "action": "Scout field for pests, diseases, or soil compaction."
            })
        
        return recs

    def show_smart_recommendations(self):
        # Stop blinking when clicked
        self.blink_timer.stop()
        self.rec_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333;
                border: 2px solid #FF9800;
                border-radius: 20px;
                font-weight: bold;
                font-size: 13px;
            }
        """)
        
        stats = self.current_analysis_memory
        if not stats: return

        recs = self.generate_recommendations(stats)
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Smart Field Analysis")
        msg.setTextFormat(Qt.RichText)
        
        content = "<h2 style='color:#2E7D32;'>Field Status & Action Plan</h2><hr>"
        
        if not recs:
            content += "<p><b>Status:</b> Stable</p><p>No urgent actions detected. Standard maintenance recommended.</p>"
        
        for r in recs:
            content += f"""
            <div style='margin-bottom: 10px; padding: 10px; background-color: #f9f9f9; border-left: 4px solid #FF9800;'>
                <h3 style='margin:0;'>{r['icon']} {r['title']}</h3>
                <p style='margin:5px 0;'><i>{r['desc']}</i></p>
                <p style='margin:5px 0; font-weight:bold; color:#D84315;'> Action: {r['action']}</p>
            </div>
            """
            
        msg.setText(content)
        msg.exec_()

    def setup_weather_panel(self):
        self.weather_panel = QFrame(self.browser)
        self.weather_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.90); 
                border-radius: 20px; 
                border: 1px solid rgba(0,0,0,0.1);
            }
        """)
        self.add_shadow(self.weather_panel)

        self.weather_panel.setFixedWidth(140)
        self.weather_panel.setFixedHeight(55)

        layout = QHBoxLayout()
        layout.setContentsMargins(10, 5, 10, 5)
        self.weather_panel.setLayout(layout)

        # Icon
        self.lbl_weather_icon = QLabel("")
        self.lbl_weather_icon.setStyleSheet("font-size: 24px; border: none; background: transparent;")
        self.lbl_weather_icon.setAlignment(Qt.AlignCenter)

        # Text (Temp + Desc)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(0)
        text_layout.setContentsMargins(5, 0, 0, 0)
        
        self.lbl_weather_temp = QLabel("--°C")
        self.lbl_weather_temp.setStyleSheet("font-size: 14px; font-weight: bold; color: #333; border: none; background: transparent;")
        
        self.lbl_weather_desc = QLabel("Loading...")
        self.lbl_weather_desc.setStyleSheet("font-size: 10px; color: #666; border: none; background: transparent;")
        
        text_layout.addWidget(self.lbl_weather_temp)
        text_layout.addWidget(self.lbl_weather_desc)

        layout.addWidget(self.lbl_weather_icon)
        layout.addLayout(text_layout)
        
        
        
        self.weather_panel.show()
        # Initial load (default location Turkey center)
        self.update_weather(39.0, 35.0)

    def setup_records_button(self):
        self.btn_show_records = QPushButton("Records", self.browser)
        self.add_shadow(self.btn_show_records)
        self.btn_show_records.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #444;
                border: 1px solid #ddd;
                border-radius: 20px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #2196F3; 
                color: white;
                border-color: #2196F3;
            }
        """)
        self.btn_show_records.setFixedSize(120, 45)
        self.btn_show_records.clicked.connect(self.open_records_dialog)
        self.btn_show_records.show()

    def setup_test_button(self):
        self.btn_test = QPushButton("Test", self.browser)
        self.add_shadow(self.btn_test)
        self.btn_test.setStyleSheet("""
            QPushButton {
                background-color: white;
                color: #444;
                border: 1px solid #ddd;
                border-radius: 20px;
                padding: 8px 20px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { 
                background-color: #FFC107; 
                color: #333;
                border-color: #FFC107;
            }
        """)
        self.btn_test.setFixedSize(120, 45)
        self.btn_test.clicked.connect(self.open_test_records_dialog)
        self.btn_test.show()

    def setup_date_panel(self):
        self.date_panel = QFrame(self.browser)
        self.date_panel.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.98); 
                border-radius: 15px;
                border: 1px solid #eee;
            }
            QLabel { font-weight: bold; color: #555; background: transparent; border: none; }
        """)
        self.add_shadow(self.date_panel)
        self.date_panel.setFixedWidth(280)
        self.date_panel.setFixedHeight(380)

        panel_grid = QGridLayout()
        panel_grid.setContentsMargins(20, 20, 20, 20)
        panel_grid.setVerticalSpacing(12)
        self.date_panel.setLayout(panel_grid)

        lbl_title = QLabel("Date & Analysis Settings")
        lbl_title.setStyleSheet("font-size: 16px; color: #2E7D32; margin-bottom: 5px;")
        panel_grid.addWidget(lbl_title, 0, 0, 1, 2, Qt.AlignCenter)

        # --- User Mode (Engineer/Farmer) ---
        self.combo_user_mode = QComboBox()
        self.combo_user_mode.addItems(["Engineer", "Farmer"])
        self.combo_user_mode.currentIndexChanged.connect(self.on_user_mode_change)

        # --- Time Mode ---
        self.combo_mode = QComboBox()
        self.combo_mode.addItems(["Date Range", "Single Date"])
        self.combo_mode.currentIndexChanged.connect(self.on_mode_change)

        # --- Analysis Mode ---
        self.combo_analysis_mode = QComboBox()
        self.combo_analysis_mode.addItems(["Area Scanning", "Product Scanning"])
        self.combo_analysis_mode.currentIndexChanged.connect(self.on_analysis_mode_change)

        # --- Product Selector (Hidden by default) ---
        self.combo_product = QComboBox()
        # Populate with products (exclude 0-8 non-crop if desired, or include all)
        # Using PRODUCT_LABELS from worker
        # We want to store ID as user data
        for pid, label in PRODUCT_LABELS.items():
            # Optionally filter mostly crops?
            # '30': Cotton, '31': Beet, '32': Corn, '33': Sunflower
            # '1': Barley, '2': Wheat
            # The user said "products defined in our product diversity classification".
            # Let's include crops.
            # 1, 2, 30, 31, 32, 33 are main crops. 
            # 7 (Orchard) might be relevant. 
            # Let's simple add all for flexibility or filter?
            # User said: "The products the user can select from in the panel should be those currently defined in our product diversity classification process."
            # So let's add them all, maybe sorted by name?
            self.combo_product.addItem(label, pid)

        self.lbl_product = QLabel("Product:")
        self.lbl_product.setVisible(False)
        self.combo_product.setVisible(False)

        self.date_start = QDateEdit()
        self.date_start.setDisplayFormat("dd.MM.yyyy")
        self.date_start.setDate(QDate.fromString(self.current_start_date, "yyyy-MM-dd"))
        self.date_start.setCalendarPopup(True)
        self.style_calendar_widget(self.date_start)

        self.lbl_end = QLabel("End:")
        self.date_end = QDateEdit()
        self.date_end.setDisplayFormat("dd.MM.yyyy")
        self.date_end.setDate(QDate.fromString(self.current_end_date, "yyyy-MM-dd"))
        self.date_end.setCalendarPopup(True)
        self.style_calendar_widget(self.date_end)

        btn_update = QPushButton("Update Analysis")
        btn_update.setCursor(Qt.PointingHandCursor)
        btn_update.setStyleSheet("""
            QPushButton { background-color: #1976D2; color: white; border: none; padding: 10px; border-radius: 8px; }
            QPushButton:hover { background-color: #1565C0; }
        """)
        btn_update.clicked.connect(self.update_map_date)

        action_layout = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.setCursor(Qt.PointingHandCursor)
        btn_save.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; border:none; } QPushButton:hover { background-color: #388E3C; }")
        btn_save.clicked.connect(self.save_current_analysis)

        btn_compare_main = QPushButton("Compare")
        btn_compare_main.setCursor(Qt.PointingHandCursor)
        btn_compare_main.setStyleSheet(
            "QPushButton { background-color: #FFA000; color: white; border:none; } QPushButton:hover { background-color: #F57C00; }")
        btn_compare_main.clicked.connect(self.open_comparison_dialog)

        action_layout.addWidget(btn_save)
        action_layout.addWidget(btn_compare_main)

        # Layout Rows
        row = 1
        panel_grid.addWidget(QLabel("User Mode:"), row, 0); panel_grid.addWidget(self.combo_user_mode, row, 1); row += 1
        panel_grid.addWidget(QLabel("Time Mode:"), row, 0); panel_grid.addWidget(self.combo_mode, row, 1); row += 1
        panel_grid.addWidget(QLabel("Anlys. Mode:"), row, 0); panel_grid.addWidget(self.combo_analysis_mode, row, 1); row += 1
        
        # Product Row (Dynamic)
        panel_grid.addWidget(self.lbl_product, row, 0)
        panel_grid.addWidget(self.combo_product, row, 1)
        row += 1

        panel_grid.addWidget(QLabel("Start:"), row, 0); panel_grid.addWidget(self.date_start, row, 1); row += 1
        panel_grid.addWidget(self.lbl_end, row, 0); panel_grid.addWidget(self.date_end, row, 1); row += 1
        
        panel_grid.addWidget(btn_update, row, 0, 1, 2); row += 1
        panel_grid.addLayout(action_layout, row, 0, 1, 2)

        self.date_panel.show()
    
    # ... rest of setup_right_panel and others ... (not replacing them, just need the bottom part for update_weather)


    def set_weather_placeholder(self):
        """Sets the weather panel to placeholder state."""
        self.lbl_weather_desc.setText("Unknown")
        self.lbl_weather_temp.setText("--°C")
        self.lbl_weather_icon.setText("🌡️")



    def setup_right_panel(self, main_layout):
        right_panel = QFrame()
        right_panel.setFixedWidth(380)
        right_panel.setStyleSheet("background-color: #FFFFFF; border-left: 1px solid #E0E0E0;")
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(20, 30, 20, 20)
        right_panel.setLayout(right_layout)

        # Header
        header_lbl = QLabel("Analysis Results")
        header_lbl.setFont(QFont("Segoe UI", 60, QFont.Bold))
        header_lbl.setStyleSheet("color: #222; margin-bottom: 5px;")
        right_layout.addWidget(header_lbl)

        self.lbl_status = QLabel("Ready")
        self.lbl_status.setStyleSheet("color: #888; font-style: italic; font-size: 13px; margin-bottom: 15px;")
        right_layout.addWidget(self.lbl_status)

        # --- NEW: Select Mode Dropdown ---
        self.combo_view_mode = QComboBox()
        self.combo_view_mode.setStyleSheet("""
            QComboBox {
                background-color: #f1f3f4;
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 8px;
                font-weight: bold;
                color: #333;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 30px; 
                border-left-width: 1px;
                border-left-color: #ddd;
                border-left-style: solid; 
                border-top-right-radius: 8px; 
                border-bottom-right-radius: 8px;
            }
        """)
        # Populate initial items (Engineer Default)
        self.combo_view_mode.addItems(["Band Values", "Health Indices", "Land Distribution", "Deforestation"])
        self.combo_view_mode.currentIndexChanged.connect(self.on_view_mode_changed)
        right_layout.addWidget(self.combo_view_mode)

        # View Toggle Button (Kept as requested)
        self.btn_toggle_view = QPushButton("View: Band Values")
        self.btn_toggle_view.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_view.setFixedHeight(40)
        self.btn_toggle_view.setStyleSheet("""
            QPushButton {
                background-color: #f1f3f4; 
                color: #333; 
                border: 1px solid #ddd;
                border-radius: 8px; 
                font-weight: 600;
            } 
            QPushButton:hover { background-color: #e8eaed; border-color: #bbb; }
        """)
        self.btn_toggle_view.clicked.connect(self.cycle_results_view)
        right_layout.addWidget(self.btn_toggle_view)
        
        # New Trend Button
        self.btn_trends = QPushButton("Generate Trend Graphs")
        self.btn_trends.setCursor(Qt.PointingHandCursor)
        self.btn_trends.setStyleSheet("""
            QPushButton {
                background-color: #673AB7; 
                color: white; 
                border-radius: 8px; 
                padding: 10px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #5E35B1; }
        """)
        self.btn_trends.hide() # Hidden by default
        self.btn_trends.clicked.connect(self.generate_trends)
        right_layout.addWidget(self.btn_trends)
        
        right_layout.addSpacing(15)

        self.stack = QStackedWidget()

        # --- PAGE 1: BANDS (SCROLL + VBOX) ---
        self.page_bands = QWidget()
        page_bands_layout = QVBoxLayout(self.page_bands)
        page_bands_layout.setContentsMargins(0, 0, 0, 0)

        scroll_bands = QScrollArea()
        scroll_bands.setWidgetResizable(True)
        scroll_bands.setFrameShape(QFrame.NoFrame)

        content_bands = QWidget()
        layout_bands_content = QVBoxLayout(content_bands)
        layout_bands_content.setSpacing(10)
        layout_bands_content.setContentsMargins(5, 5, 5, 5)

        band_names = ["B2 (Blue)", "B3 (Green)", "B4 (Red)", "B5 (RE1)", "B6 (RE2)", "B7 (RE3)", "B8 (NIR)"]
        for b_name in band_names:
            frame, label = self.create_result_card(b_name, "#2E7D32")
            self.band_labels[b_name] = label
            layout_bands_content.addWidget(frame)

        layout_bands_content.addStretch()
        scroll_bands.setWidget(content_bands)
        page_bands_layout.addWidget(scroll_bands)

        # --- PAGE 2: INDICES (SCROLL + VBOX) ---
        self.page_indices = QWidget()
        page_indices_layout = QVBoxLayout(self.page_indices)
        page_indices_layout.setContentsMargins(0, 0, 0, 0)

        scroll_indices = QScrollArea()
        scroll_indices.setWidgetResizable(True)
        scroll_indices.setFrameShape(QFrame.NoFrame)

        content_indices = QWidget()
        layout_indices_content = QVBoxLayout(content_indices)
        layout_indices_content.setSpacing(10)
        layout_indices_content.setContentsMargins(5, 5, 5, 5)

        index_names = ["NDVI(PHOTOSYNTHESIS ACTIVITY)", "EVI(DENSE VEGETATION NDVI)", "SAVI(SPARSE VEGETATION NDVI)", "NDRE(CHLOROPHYLL CHANGING)", "RENDVI(CANOPY STRUCTURE)", "GNDVI(NITROGEN CONTENT)", "NDWI(WATER CONTENT)", "RVI(RADAR VEGETATION INDEX)"]
        for i_name in index_names:
            color = "#1b5e20" if i_name == "NDVI" else "#00695C"
            if "RVI" in i_name: color = "#4527A0" # Different color for Radar
            frame, label = self.create_result_card(i_name, color, is_large=True)
            self.index_labels[i_name] = label
            layout_indices_content.addWidget(frame)

        layout_indices_content.addStretch()
        scroll_indices.setWidget(content_indices)
        page_indices_layout.addWidget(scroll_indices)

        # --- PAGE 3: CLASSIFICATION ---
        self.page_classification = QWidget()
        layout_class = QVBoxLayout()
        layout_class.setContentsMargins(5, 5, 5, 5)
        self.page_classification.setLayout(layout_class)

        lbl_info = QLabel("Land Distribution in Region (AI)\nGoogle Dynamic World Model")
        lbl_info.setStyleSheet("color: #666; font-size: 12px; margin-bottom: 10px; font-weight: bold;")
        lbl_info.setAlignment(Qt.AlignCenter)
        layout_class.addWidget(lbl_info)

        self.table_class = QTableWidget()
        self.table_class.setColumnCount(2)
        self.table_class.setHorizontalHeaderLabels(["Class", "Ratio (%)"])
        self.table_class.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_class.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table_class.verticalHeader().setVisible(False)
        self.table_class.setAlternatingRowColors(True)
        self.table_class.setStyleSheet("""
            QTableWidget {
                border: 1px solid #eee;
                border-radius: 8px;
                background-color: white;
                gridline-color: transparent;
                selection-background-color: #E8F5E9;
                selection-color: black;
            }
            QHeaderView::section {
                background-color: #fafafa;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #eee;
                font-weight: bold;
                color: #555;
            }
            QTableWidget::item {
                padding: 5px;
                border-bottom: 1px solid #f5f5f5;
            }
        """)
        layout_class.addWidget(self.table_class)
        layout_class.addStretch()

        # --- PAGE 4: FARMER HEALTH (SCROLL + VBOX) ---
        self.page_farmer_health = QWidget()
        page_farmer_layout = QVBoxLayout(self.page_farmer_health)
        page_farmer_layout.setContentsMargins(0, 0, 0, 0)

        scroll_farmer = QScrollArea()
        scroll_farmer.setWidgetResizable(True)
        scroll_farmer.setFrameShape(QFrame.NoFrame)

        content_farmer = QWidget()
        self.layout_farmer_content = QVBoxLayout(content_farmer)
        self.layout_farmer_content.setSpacing(15)
        self.layout_farmer_content.setContentsMargins(5, 5, 5, 5)
        
        # Content will be populated dynamically in result_utils
        self.layout_farmer_content.addStretch()

        scroll_farmer.setWidget(content_farmer)
        page_farmer_layout.addWidget(scroll_farmer)

        # --- PAGE 5: DEFORESTATION ---
        self.page_deforestation = QWidget()
        page_defor_layout = QVBoxLayout(self.page_deforestation)
        page_defor_layout.setContentsMargins(0, 0, 0, 0)

        scroll_defor = QScrollArea()
        scroll_defor.setWidgetResizable(True)
        scroll_defor.setFrameShape(QFrame.NoFrame)

        content_defor = QWidget()
        layout_defor = QVBoxLayout(content_defor)
        layout_defor.setSpacing(12)
        layout_defor.setContentsMargins(5, 5, 5, 5)

        # Header
        defor_header = QLabel("Forest & Shrub Analysis")
        defor_header.setFont(QFont("Segoe UI", 14, QFont.Bold))
        defor_header.setStyleSheet("color: #1B5E20; margin-bottom: 5px;")
        layout_defor.addWidget(defor_header)

        defor_desc = QLabel("Compares total forest and shrub coverage between two periods.")
        defor_desc.setStyleSheet("color: #666; font-size: 11px; margin-bottom: 10px;")
        defor_desc.setWordWrap(True)
        layout_defor.addWidget(defor_desc)

        # Status label
        self.lbl_defor_status = QLabel("Select an area and run analysis to begin.")
        self.lbl_defor_status.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
        self.lbl_defor_status.setWordWrap(True)
        layout_defor.addWidget(self.lbl_defor_status)

        # Period 1 Card
        frame_p1 = QFrame()
        frame_p1.setStyleSheet("QFrame { background-color: #F1F8E9; border: 1px solid #C5E1A5; border-radius: 8px; }")
        p1_layout = QVBoxLayout(frame_p1)
        self.lbl_defor_p1_title = QLabel("Period 1 (Baseline)")
        self.lbl_defor_p1_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_defor_p1_title.setStyleSheet("color: #33691E; border: none;")
        self.lbl_defor_p1_value = QLabel("— %")
        self.lbl_defor_p1_value.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_defor_p1_value.setStyleSheet("color: #1B5E20; border: none;")
        self.lbl_defor_p1_value.setAlignment(Qt.AlignCenter)
        p1_layout.addWidget(self.lbl_defor_p1_title)
        p1_layout.addWidget(self.lbl_defor_p1_value)
        layout_defor.addWidget(frame_p1)

        # Period 2 Card
        frame_p2 = QFrame()
        frame_p2.setStyleSheet("QFrame { background-color: #E8F5E9; border: 1px solid #A5D6A7; border-radius: 8px; }")
        p2_layout = QVBoxLayout(frame_p2)
        self.lbl_defor_p2_title = QLabel("Period 2 (Current)")
        self.lbl_defor_p2_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        self.lbl_defor_p2_title.setStyleSheet("color: #33691E; border: none;")
        self.lbl_defor_p2_value = QLabel("— %")
        self.lbl_defor_p2_value.setFont(QFont("Segoe UI", 18, QFont.Bold))
        self.lbl_defor_p2_value.setStyleSheet("color: #1B5E20; border: none;")
        self.lbl_defor_p2_value.setAlignment(Qt.AlignCenter)
        p2_layout.addWidget(self.lbl_defor_p2_title)
        p2_layout.addWidget(self.lbl_defor_p2_value)
        layout_defor.addWidget(frame_p2)

        # Change Indicator
        frame_change = QFrame()
        frame_change.setStyleSheet("QFrame { background-color: #FAFAFA; border: 2px solid #E0E0E0; border-radius: 10px; }")
        change_layout = QVBoxLayout(frame_change)
        lbl_change_title = QLabel("Net Change")
        lbl_change_title.setFont(QFont("Segoe UI", 10))
        lbl_change_title.setStyleSheet("color: #666; border: none;")
        lbl_change_title.setAlignment(Qt.AlignCenter)
        self.lbl_defor_change = QLabel("— %")
        self.lbl_defor_change.setFont(QFont("Segoe UI", 28, QFont.Bold))
        self.lbl_defor_change.setStyleSheet("color: #9E9E9E; border: none;")
        self.lbl_defor_change.setAlignment(Qt.AlignCenter)
        self.lbl_defor_verdict = QLabel("")
        self.lbl_defor_verdict.setFont(QFont("Segoe UI", 11))
        self.lbl_defor_verdict.setStyleSheet("color: #666; border: none;")
        self.lbl_defor_verdict.setAlignment(Qt.AlignCenter)
        self.lbl_defor_verdict.setWordWrap(True)
        change_layout.addWidget(lbl_change_title)
        change_layout.addWidget(self.lbl_defor_change)
        change_layout.addWidget(self.lbl_defor_verdict)
        layout_defor.addWidget(frame_change)

        layout_defor.addStretch()
        scroll_defor.setWidget(content_defor)
        page_defor_layout.addWidget(scroll_defor)

        self.stack.addWidget(self.page_bands)           # Index 0
        self.stack.addWidget(self.page_indices)         # Index 1
        self.stack.addWidget(self.page_classification)  # Index 2
        self.stack.addWidget(self.page_farmer_health)   # Index 3
        self.stack.addWidget(self.page_deforestation)   # Index 4
        right_layout.addWidget(self.stack)
        main_layout.addWidget(right_panel, stretch=0)

    def create_result_card(self, title, color_hex, is_large=False):
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #ffffff; 
                border-radius: 12px; 
                border: 1px solid #eff0f1;
            }
        """)
        self.add_shadow(frame, blur=15, y_offset=3)

        frame.setMinimumHeight(110)

        lay = QVBoxLayout()
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(2)
        lay.setAlignment(Qt.AlignCenter)
        frame.setLayout(lay)

        # Title Layout (Horizontal for Label + Info Button)
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignCenter)
        
        lbl_title = QLabel(title)
        lbl_title.setFont(QFont("Segoe UI", 16,QFont.Bold))
        lbl_title.setStyleSheet("color: #777; border: none; background: transparent;")
        lbl_title.setAlignment(Qt.AlignCenter)
        title_layout.addWidget(lbl_title)

        # Add Info Button if description exists
        if title in self.index_descriptions:
            btn_info = QPushButton("i")
            btn_info.setCursor(Qt.PointingHandCursor)
            btn_info.setFixedSize(20, 20)
            btn_info.setStyleSheet("""
                QPushButton {
                    background-color: #e0e0e0;
                    color: #555;
                    border-radius: 10px;
                    font-weight: bold;
                    border: none;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #bdbdbd;
                    color: #333;
                }
            """)
            btn_info.clicked.connect(lambda checked, t=title: self.show_index_info(t))
            title_layout.addWidget(btn_info)
            # Add a bit of spacing/centering logic if needed, but HBox handles it well.
        
        lay.addLayout(title_layout)

        lbl_val = QLabel("---")
        size = 48 if is_large else 38
        lbl_val.setFont(QFont("Segoe UI", size, QFont.Bold))
        lbl_val.setStyleSheet(f"color: {color_hex}; border: none; background: transparent;")
        lbl_val.setAlignment(Qt.AlignCenter)

        lay.addWidget(lbl_val)
        return frame, lbl_val

    def show_index_info(self, title):
        info_text = self.index_descriptions.get(title, "No information available.")
        dlg = InfoDialog(title, info_text, self)
        dlg.exec_()

    def cycle_results_view(self):
        """
        Cycles through views by updating the ComboBox index.
        The ComboBox handler (on_view_mode_changed) will then trigger the actual view update.
        """
        current_idx = self.combo_view_mode.currentIndex()
        count = self.combo_view_mode.count()
        if count == 0: return

        next_idx = (current_idx + 1) % count
        self.combo_view_mode.setCurrentIndex(next_idx)

    def on_view_mode_changed(self, index):
        """
        Handles view changes triggered by ComboBox selection.
        Updates StackedWidget, Buttons, and Map Layers.
        """
        if index < 0: return

        # Map Dropdown Index to Stack Index
        target_stack_idx = 0
        
        if self.user_mode == "Engineer":
            # 0: Band Values -> Stack 0
            # 1: Health Indices -> Stack 1
            # 2: Land Distribution -> Stack 2
            # 3: Deforestation -> Stack 4
            if index == 3:
                target_stack_idx = 4
            else:
                target_stack_idx = index
        else: # Farmer
            # 0: Health Status -> Stack 3
            # 1: Land Distribution -> Stack 2
            # 2: Deforestation -> Stack 4
            if index == 0: target_stack_idx = 3
            elif index == 1: target_stack_idx = 2
            elif index == 2: target_stack_idx = 4

        self.stack.setCurrentIndex(target_stack_idx)
        self.update_view_state(target_stack_idx)

    def update_view_state(self, stack_idx):
        """
        Updates button text/color and map layers based on the active stack index.
        """
        base_style = "QPushButton { border-radius: 8px; padding: 8px; font-weight: bold; color: white; }"
        target_url = None
        is_class_view = False

        if stack_idx == 0: # Engineer: Bands
            self.btn_toggle_view.setText("View: Band Values")
            self.btn_toggle_view.setStyleSheet(
                base_style + "QPushButton { background-color: #4CAF50; } QPushButton:hover { background-color: #43A047; }")
            target_url = self.current_analysis_memory.get('rgb_url')
            
        elif stack_idx == 1: # Engineer: Indices
            self.btn_toggle_view.setText("View: Health Indices")
            self.btn_toggle_view.setStyleSheet(
                base_style + "QPushButton { background-color: #00897B; } QPushButton:hover { background-color: #00796B; }")
            target_url = self.current_analysis_memory.get('rgb_url')
            
        elif stack_idx == 2: # Both: Classification
            self.btn_toggle_view.setText("View: Land Distribution (AI)")
            self.btn_toggle_view.setStyleSheet(
                base_style + "QPushButton { background-color: #E65100; } QPushButton:hover { background-color: #EF6C00; }")
            target_url = self.current_analysis_memory.get('class_url')
            is_class_view = True

        elif stack_idx == 3: # Farmer: Health Status
            self.btn_toggle_view.setText("View: Health Status")
            self.btn_toggle_view.setStyleSheet(
                base_style + "QPushButton { background-color: #2E7D32; } QPushButton:hover { background-color: #1B5E20; }")
            target_url = self.current_analysis_memory.get('rgb_url')

        elif stack_idx == 4: # Both: Deforestation
            self.btn_toggle_view.setText("View: Deforestation")
            self.btn_toggle_view.setStyleSheet(
                base_style + "QPushButton { background-color: #2E7D32; } QPushButton:hover { background-color: #1B5E20; }")
            target_url = self.current_analysis_memory.get('class_url')
            # Trigger deforestation analysis if we have geometry data
            self.trigger_deforestation_analysis()
        
        # Show/Hide Trend Button and manage Map Layers
        if target_url:
            opacity = 1.0
            if is_class_view and self.combo_analysis_mode.currentIndex() == 1:
                opacity = 0.6
            js = f"window.addSentinelLayer('{target_url}', {opacity})"
            self.browser.page().runJavaScript(js)
        else:
            if is_class_view and not target_url:
                 self.browser.page().runJavaScript("removeSentinelLayer()")
            elif not is_class_view and not target_url:
                 self.browser.page().runJavaScript("removeSentinelLayer()")

        # Trend Button Visibility
        if self.user_mode == "Engineer" and is_class_view and 'classified_image' in self.current_analysis_memory.get('classification', {}):
             self.btn_trends.show()
        else:
             self.btn_trends.hide()

    def on_user_mode_change(self, index):
        self.user_mode = self.combo_user_mode.currentText()
        
        # Block signals to prevent unintended triggers during combo population
        self.combo_view_mode.blockSignals(True)
        self.combo_view_mode.clear()

        if self.user_mode == "Engineer":
            self.combo_view_mode.addItems(["Band Values", "Health Indices", "Land Distribution", "Deforestation"])
            # Default to Bands
            self.combo_view_mode.setCurrentIndex(0)
            self.stack.setCurrentIndex(0)
        else: # Farmer
            self.combo_view_mode.addItems(["Health Status", "Land Distribution", "Deforestation"])
            # Default to Health
            self.combo_view_mode.setCurrentIndex(0)
            self.stack.setCurrentIndex(3) 

        self.combo_view_mode.blockSignals(False)
        
        # Manually trigger state update since we blocked signals
        current_stack = self.stack.currentIndex()
        self.update_view_state(current_stack)

        # Reset data and remove area on mode change (Per Request)
        self.reset_analysis_state()
        if hasattr(self, 'browser'):
             self.browser.page().runJavaScript("if(window.deleteSelectedArea) { window.deleteSelectedArea(); }")

    def resizeEvent(self, event):
        if hasattr(self, 'date_panel') and hasattr(self, 'browser'):
            self.date_panel.move(25, self.browser.height() - 410)

        if hasattr(self, 'search_panel') and hasattr(self, 'browser'):
            # Center Search Panel
            x_pos_search = (self.browser.width() - 420) // 2
            self.search_panel.move(x_pos_search, 25)
            
            # Position Weather Panel to the right of Search Panel
            if hasattr(self, 'weather_panel'):
                self.weather_panel.move(x_pos_search + 430, 25)
            
            # Position Recommendation Button to the LEFT of Search Panel
            if hasattr(self, 'rec_btn'):
                self.rec_btn.move(x_pos_search - 160, 30)

        if hasattr(self, 'btn_show_records') and hasattr(self, 'browser'):
            self.btn_show_records.move(60, 12)
            
        if hasattr(self, 'btn_test') and hasattr(self, 'browser'):
            self.btn_test.move(60, 62)

        super().resizeEvent(event)

    def on_mode_change(self, index):
        self.analysis_mode = "range" if index == 0 else "single"
        self.lbl_end.setVisible(index == 0)
        self.date_end.setVisible(index == 0)
        
        # Reset data and remove area on mode change
        self.reset_analysis_state()
        if hasattr(self, 'browser'):
             self.browser.page().runJavaScript("if(window.deleteSelectedArea) { window.deleteSelectedArea(); }")

    def on_analysis_mode_change(self, index):
        # 0: Area Scanning, 1: Product Scanning
        is_product = (index == 1)
        self.lbl_product.setVisible(is_product)
        self.combo_product.setVisible(is_product)

        # Reset data and remove area on mode change
        self.reset_analysis_state()
        if hasattr(self, 'browser'):
             self.browser.page().runJavaScript("if(window.deleteSelectedArea) { window.deleteSelectedArea(); }")

    def search_location(self):
        query = self.txt_search.text()
        if not query: return
        self.lbl_status.setText(f"Searching for {query}...")
        try:
            geolocator = Nominatim(user_agent="neoagro_app")
            location = geolocator.geocode(query)
            if location:
                js_code = f"window.flyToLocation({location.latitude}, {location.longitude});"
                self.browser.page().runJavaScript(js_code)
                self.lbl_status.setText(f"Found: {query}")
                self.update_weather(location.latitude, location.longitude) # Update weather for new location
            else:
                QMessageBox.warning(self, "Not Found", "Location not found.")
                self.lbl_status.setText("No Location")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Connection error: {str(e)}")

    def create_map_html(self, date1, date2=None, mode="range", center=None, zoom=None):
        map_utils.create_map_html(date1, date2, mode, center, zoom, output_file="temp_map.html")

    def on_browser_load_finished(self, success):
        # Triggered when map reload completes
        if success and self.pending_analysis_geo:
            print("Restoring analysis on reloaded map...")
            # Restore analysis (Fetch Data)
            # Fetch data handles the calculation and UI update. 
            # It also triggers MapLayerWorker -> adds Sentinel Layer.
            # However, the originally drawn POLYGON is lost visually on map.
            # If we want to support further interactions with that area, we should ideally restore it.
            # For now, running analysis restores the 'result' view which is the primary goal.
            self.fetch_data(self.pending_analysis_geo)
            self.pending_analysis_geo = None

    def update_map_date(self):
        d1 = self.date_start.date().toString("yyyy-MM-dd")
        d2 = self.date_end.date().toString("yyyy-MM-dd")
        
        # Capture current geometry before reset
        current_geo = self.current_analysis_memory.get('geometry')

        # Reset Interface (Clears results, sentinel layers, etc.)
        self.reset_analysis_state()

        # Get stored view state
        center = self.last_map_view['center'] if self.last_map_view else None
        zoom = self.last_map_view['zoom'] if self.last_map_view else None

        if self.analysis_mode == "range":
            self.create_map_html(d1, d2, "range", center=center, zoom=zoom)
        else:
            self.create_map_html(d1, mode="single", center=center, zoom=zoom)
            
        # Set pending geometry if we had one, so it restores after reload
        if current_geo:
            self.pending_analysis_geo = current_geo
            
        self.browser.reload()
    
        # Update weather immediately in update_map_date since it's a manual action
        center = self.last_map_view['center'] if self.last_map_view else [39.0, 35.0]
        self.update_weather(center[0], center[1])

    def on_map_interaction(self, title):
        if title == "RESET":
            self.reset_analysis_state()
        elif title == "MOVING":
            # Map is being moved/dragged. Show placeholder.
            self.set_weather_placeholder()
        elif title == "EXIT_VIEW":
            # Restore previous view
            if self.pre_navigation_view:
                c = self.pre_navigation_view.get('center')
                z = self.pre_navigation_view.get('zoom', 6)
                if c:
                    self.browser.page().runJavaScript(f"window.flyToLocation({c[0]}, {c[1]}, {z});")
                    self.lbl_status.setText("Restored previous map view.")
            else:
                self.browser.page().runJavaScript("window.flyToLocation(39.0, 35.0, 6);")
        elif title.startswith("VIEW:"):
            # Use geo_utils to parse view
            data = geo_utils.parse_view_title(title)
            if data:
                self.last_map_view = data
                center = data['center']
                self.update_weather(center[0], center[1])
            else:
                 print("VIEW Parse Error (handled in utils)")

        elif title.startswith("GEOJSON:"):
            geo_dict = geo_utils.parse_geojson_title(title)
            if geo_dict:
                self.fetch_data(geo_dict)
            else:
                 self.lbl_status.setText(f"⚠ Error parsing Geometry")
 
    def on_map_layer_ready(self, url):
        self.current_analysis_memory['rgb_url'] = url
        
        # If currently looking at Bands (0) or Indices (1), show this RGB layer
        # If looking at Classification (2), do NOT show it yet (wait for class result)
        if self.stack.currentIndex() != 2:
            js = f"window.addSentinelLayer('{url}')"
            self.browser.page().runJavaScript(js)
        
        self.lbl_status.setText("Sentinel-2 Image Loaded.")

    def reset_analysis_state(self):
        """Cancels all pending workers and timers to prevent ghost results."""
        # 1. Cancel Stats Worker
        if hasattr(self, 'stats_worker') and self.stats_worker is not None:
            if self.stats_worker.isRunning():
                self.stats_worker.terminate()
                self.stats_worker.wait()
            self.stats_worker = None

        # 2. Cancel Phenology Worker
        if hasattr(self, 'phenology_worker') and self.phenology_worker is not None:
            if self.phenology_worker.isRunning():
                self.phenology_worker.terminate()
                self.phenology_worker.wait()
            self.phenology_worker = None

        # 3. Cancel Deforestation Worker
        if hasattr(self, 'defor_worker') and self.defor_worker is not None:
            if self.defor_worker.isRunning():
                self.defor_worker.terminate()
                self.defor_worker.wait()
            self.defor_worker = None

        # 4. Cancel Deforestation Timer
        if hasattr(self, 'defor_timer'):
            self.defor_timer.stop()

        # 5. Clear UI (via reset_interface or selective clearing)
        # reset_interface clears Map too, which we might strictly want or not.
        # But fetch_data starts new analysis, so clearing everything is safer.
        self.reset_interface()


    def fetch_data(self, geo_data, specific_date=None):
        # Cancel previous tasks immediately
        self.reset_analysis_state()

        self.lbl_status.setText("Analysis Started...")
        bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11']
        d1 = self.date_start.date().toString("yyyy-MM-dd")
        d2 = self.date_end.date().toString("yyyy-MM-dd")

        # --- SAVE GEO DATA FOR LATER ---
        self.current_analysis_memory = {
            "indices": {}, "classification": {}, 
            "stage": "Unknown", "health_score": "0",
            "geometry": geo_data,
            "map_view": self.last_map_view,
            # --- NEW: Save Analysis Params for Restoration ---
            "time_mode": self.analysis_mode,
            "date1": d1,
            "date2": d2,
            "specific_date": specific_date
        }

        # Get Analysis Settings
        # Default to "area" if combo doesn't exist yet (safety)
        analysis_type = "area"
        product_id = None
        
        if hasattr(self, 'combo_analysis_mode'):
            idx = self.combo_analysis_mode.currentIndex()
            if idx == 1:
                analysis_type = "product"
                # Get Product ID from user data
                product_id = self.combo_product.currentData()

        # 1. Start Analysis Worker (Stats Phase)
        # Note: AnalysisWorker (Stats) now DOES NOT trigger classification automatically.
        # We must trigger PhenologyWorker in display_results (the callback).
        self.stats_worker = AnalysisWorker(geo_data, bands, self.analysis_mode, d1, d2, specific_date, analysis_type, product_id)
        self.stats_worker.finished_signal.connect(self.display_results)
        self.stats_worker.date_selection_signal.connect(lambda candidates: self.handle_date_selection(candidates, geo_data))
        # Remove old class_signal connection since StatsWorker doesn't emit it anymore
        self.stats_worker.error_signal.connect(lambda e: self.lbl_status.setText(f"Error: {e}"))
        self.stats_worker.status_signal.connect(lambda s: self.lbl_status.setText(s))
        self.stats_worker.start()

        # 2. Start Map Layer Worker (Visual)
        # Cancel previous if any
        if self.map_worker and self.map_worker.isRunning():
            self.map_worker.terminate()
            self.map_worker.wait()

        self.map_worker = MapLayerWorker(geo_data, self.analysis_mode, d1, d2, specific_date)
        self.map_worker.finished_signal.connect(self.on_map_layer_ready)
        # Show error in status bar
        self.map_worker.error_signal.connect(lambda e: self.lbl_status.setText(f"Map Layer Error: {e}")) 
        self.map_worker.start()

        
    def load_records(self):
        """Loads saved analysis records from JSON file."""
        try:
            if os.path.exists(self.saved_records_file):
                with open(self.saved_records_file, 'r', encoding='utf-8') as f:
                    self.records = json.load(f)
            else:
                self.records = {}
        except (FileNotFoundError, json.JSONDecodeError):
             self.records = {}
        except Exception as e:
             print(f"Error loading records: {e}")
             self.records = {}

    def save_records_to_disk(self):
        """Saves current analysis records to JSON file."""
        try:
            save_dir = os.path.dirname(self.saved_records_file)
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            with open(self.saved_records_file, 'w', encoding='utf-8') as f:
                json.dump(self.records, f, indent=4, ensure_ascii=False)
        except Exception as e:
             print(f"Error saving records: {e}")
             QMessageBox.warning(self, "Save Error", f"Could not save record to disk: {e}")
             
    def handle_date_selection(self, candidates, geo_data):
        self.lbl_status.setText("Waiting for user selection...")
        dlg = DateSelectionDialog(candidates, self)
        if dlg.exec_():
            selected_date = dlg.selected_date
            if selected_date:
                self.lbl_status.setText(f"Selected: {selected_date}")
                # Rerun analysis with specific date
                self.fetch_data(geo_data, specific_date=selected_date)
            else:
                 self.lbl_status.setText("Selection cancelled.")
        else:
             self.lbl_status.setText("Selection cancelled.")

    def save_current_analysis(self):
        if not self.current_analysis_memory.get("indices") and not self.current_analysis_memory.get("classification"):
            QMessageBox.warning(self, "No Data",
                                "No completed analysis yet.\nPlease select an area first and wait for the analysis to finish.")
            return

        name, ok = QInputDialog.getText(self, "Save Record", "Enter a name for this analysis:")
        if ok and name:
            if name in self.records:
                reply = QMessageBox.question(self, "Overwrite?",
                                             f"A record named '{name}' already exists. Overwrite?",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No: return

            
            # --- FIX: Serialize Geometry ---
            # ee.Geometry objects are not JSON serializable. We must convert them to client-side dicts.
            raw_geo = self.current_analysis_memory.get("geometry", None)
            serialized_geo = None
            
            if raw_geo:
                try:
                    # If it's an EE object, fetch info
                    if isinstance(raw_geo, (ee.Geometry, ee.Element)):
                         serialized_geo = raw_geo.getInfo()
                    # If it's already a dict (e.g. from previous load), use it
                    elif isinstance(raw_geo, dict):
                         serialized_geo = raw_geo
                    else:
                         serialized_geo = str(raw_geo) # Fallback
                except Exception as e:
                    print(f"Geometry Serialization Error: {e}")
                    serialized_geo = "Error: Could not serialize geometry"

            # --- FIX: Filter Non-Serializable Data (ee.Image) ---
            # We must filter out 'classified_image' as it is an ee.Image object.
            classification_data = self.current_analysis_memory.get("classification", {}).copy()
            if 'classified_image' in classification_data:
                del classification_data['classified_image']

            # --- NEW: Retrieve Params for Map Restoration ---
            analysis_params = {
                "mode": self.current_analysis_memory.get("time_mode", "range"),
                "date1": self.current_analysis_memory.get("date1"),
                "date2": self.current_analysis_memory.get("date2"),
                "specific_date": self.current_analysis_memory.get("specific_date")
            }

            record_data = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "indices": self.current_analysis_memory.get("indices", {}),
                "classification": classification_data,
                "stage": self.current_analysis_memory.get("stage", "Unknown"),
                "health_score": self.current_analysis_memory.get("health_score", "0"),
                # --- NEW: Location Data ---
                "geometry": serialized_geo,
                "view": self.last_map_view,
                "analysis_params": analysis_params
            }

            self.records[name] = record_data
            self.save_records_to_disk()
            
            # --- NEW: Save to CSV for Test ---
            self.save_test_csv(record_data, name)
            
            QMessageBox.information(self, "Success", "Analysis saved successfully.")

    def open_records_dialog(self):
        if not self.records:
            QMessageBox.information(self, "Empty", "No saved analysis found.")
            return

        # Determine Saved Logs folder path
        logs_folder = os.path.dirname(self.saved_records_file)

        # Pass self as main_app to handle callback
        dlg = RecordsDialog(self.records, logs_folder, self)
        dlg.exec_()

    def save_test_csv(self, record_data, record_name):
        import csv
        
        # 1. Define Fields
        # Standard Fields
        fieldnames = [
            "Name", "Date", "Analysis Mode", "User Mode", "Time Mode", "Start Date", "End Date",
            "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B11",
            "NDVI", "EVI", "SAVI", "NDRE", "RENDVI", "GNDVI", "NDWI", "RVI"
        ]
        
        # Dynamic Product Fields (from worker.PRODUCT_LABELS)
        from core.classification import PRODUCT_LABELS
        product_names = sorted(PRODUCT_LABELS.values())
        fieldnames.extend(product_names)
        
        # Location at the end
        fieldnames.append("Location")
        
        # 2. Prepare Directory/File
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        test_folder = os.path.join(base_dir, "Saved Test")
        if not os.path.exists(test_folder):
            os.makedirs(test_folder)
            
        csv_file = os.path.join(test_folder, "saved_test.csv")
        file_exists = os.path.isfile(csv_file)
        
        # 3. Extract Data
        indices = record_data.get('indices', {})
        classification = record_data.get('classification', {})
        bands = {} 
        # Note: bands are not stored in 'indices' dict in current_analysis_memory structure shown in fetch_data/display_results.
        # They are in current_analysis_memory directly or we need to check where they are saved in 'record_data'.
        # In save_current_analysis:
        # "indices": self.current_analysis_memory.get("indices", {}),
        # Wait, the current implementation of save_current_analysis ONLY saves 'indices' and 'classification'.
        # The band values (B2, B3...) are NOT in 'indices' dict. They are loose in current_analysis_memory.
        # We need to capture them in record_data first if we want them here.
        # Or we can try to get them from self.current_analysis_memory since we are inside the class.
        # BUT 'record_data' is passed to this function. 
        # Let's fix save_current_analysis to include bands in record_data or access self.current_analysis_memory here.
        # Accessing self.current_analysis_memory is safer as record_data depends on what was saved.
        # Actually, let's update record_data creation in save_current_analysis to include bands?
        # No, that changes the JSON structure which users might rely on (or not).
        # Let's just grab them from self.current_analysis_memory here since this is called right after save.
        
        mem = self.current_analysis_memory
        
        # Format Geometry for CSV (Extract Coordinates)
        geo_data = record_data.get('geometry', '')
        geo_str = str(geo_data) # Default fallback

        try:
             # Logic to extract coordinates
             # If it's a string, try to eval it safely (since we know it comes from str(dict))
             if isinstance(geo_data, str):
                import ast
                try:
                    geo_data = ast.literal_eval(geo_data)
                except:
                    pass 

             if isinstance(geo_data, dict) and 'coordinates' in geo_data:
                coords = geo_data['coordinates']
                # Handle Polygon (nested list)
                if geo_data.get('type') == 'Polygon':
                    # coords[0] is the outer ring
                    points = []
                    # GeoJSON is [Lon, Lat] -> Convert to (Lat, Lon)
                    for pt in coords[0]:
                        points.append(f"({pt[1]:.6f}, {pt[0]:.6f})")
                    geo_str = "; ".join(points)
                
                # Handle Point
                elif geo_data.get('type') == 'Point':
                    pt = coords
                    geo_str = f"({pt[1]:.6f}, {pt[0]:.6f})"
        except Exception as e:
            print(f"Geometry Formatting Error: {e}")
            # Fallback to default str(geo_data) which is already set
        
        row = {
            "Name": record_name,
            "Date": record_data.get('date'),
            "Analysis Mode": self.combo_analysis_mode.currentText(),
            "User Mode": self.user_mode,
            "Time Mode": self.combo_mode.currentText(),
            "Start Date": self.date_start.date().toString("dd.MM.yyyy"),
            "End Date": self.date_end.date().toString("dd.MM.yyyy") if self.analysis_mode == "range" else "-",
            "Location": geo_str
        }
        
        # Bands
        for b in ["B2", "B3", "B4", "B5", "B6", "B7", "B8", "B11"]:
            row[b] = mem.get(b, 0)
            
        # Indices
        for k in ["NDVI", "EVI", "SAVI", "NDRE", "RENDVI", "GNDVI", "NDWI", "RVI"]:
             # Indices are in 'indices' dict in memory usually, but also display_engineer_results puts them in indices dict.
             # In memory they are strings "0.45", convert to float?
             # record_data['indices'] has them.
             row[k] = indices.get(k, 0)
             
        # Products
        # classification keys are names like 'Wheat', 'Water' etc.
        for p_name in product_names:
            row[p_name] = classification.get(p_name, 0)
            
        try:
            with open(csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)
        except Exception as e:
            print(f"CSV Save Error: {e}")
            QMessageBox.warning(self, "CSV Error", f"Could not save to CSV: {e}")

    def open_test_records_dialog(self):
        # We need to import TestRecordsDialog from dialogs (will implement next)
        from gui.dialogs import TestRecordsDialog
        
        if getattr(sys, 'frozen', False):
            base_dir = os.path.dirname(sys.executable)
        else:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            
        csv_file = os.path.join(base_dir, "Saved Test", "saved_test.csv")
        
        if not os.path.exists(csv_file):
             QMessageBox.information(self, "No Records", "No test records found yet.")
             return
             
        dlg = TestRecordsDialog(csv_file, self)
        dlg.exec_()

    def load_saved_location(self, record_data):
        """Called by RecordsDialog when 'Alana Git' is clicked."""
        geo_utils.load_saved_location(self, record_data)

        # --- NEW: Restore Sentinel Layer ---
        self.lbl_status.setText("Moving to location... Loading Sentinel-2 imagery...")
        
        # Check if we have saved analysis params
        params = record_data.get("analysis_params")
        geo_data = record_data.get("geometry")

        if params and geo_data:
            try:
                # Cancel previous worker if running
                if hasattr(self, 'map_worker') and self.map_worker and self.map_worker.isRunning():
                    self.map_worker.terminate()
                    self.map_worker.wait()

                # Extract params
                mode = params.get("mode", "range")
                d1 = params.get("date1")
                d2 = params.get("date2")
                specific_date = params.get("specific_date") # Might be None

                # Restart Map Worker
                self.map_worker = MapLayerWorker(geo_data, mode, d1, d2, specific_date)
                self.map_worker.finished_signal.connect(self.on_map_layer_ready)
                self.map_worker.error_signal.connect(lambda e: self.lbl_status.setText(f"Map Layer Error: {e}"))
                self.map_worker.start()
                
            except Exception as e:
                print(f"Error restoring map layer: {e}")
        else:
             # Fallback: We don't have enough info to regenerate the specific map.
             self.lbl_status.setText("Moved to saved location (Map layer data unavailable for old records).")

    def open_comparison_dialog(self):
        if not self.records or len(self.records) < 2:
            QMessageBox.warning(self, "Insufficient Records",
                                "You must have at least 2 saved analyses to make a comparison.")
            return

        dlg = ComparisonSelectionDialog(self.records, self)
        dlg.exec_()

    def display_results(self, stats):
        """
        Called when StatsWorker finishes.
        1. Updates Band/Index/Soil UI.
        2. Triggers PhenologyWorker (Classification).
        """
        result_utils.display_results(self, stats)

        # Sequential Chaining: Trigger Phenology Worker
        source = stats.get('source', 'S2')
        if source == 'S2':
            try:
                # Prepare params for classification
                d1 = self.current_analysis_memory.get('date1')
                year = 2023
                if d1 and "-" in d1:
                    year = int(d1.split("-")[0])
                
                geo_data = self.current_analysis_memory.get('geometry')
                
                # Retrieve analysis type/product params
                analysis_type = "area"
                product_id = None
                if hasattr(self, 'combo_analysis_mode'):
                    idx = self.combo_analysis_mode.currentIndex()
                    if idx == 1:
                        analysis_type = "product"
                        product_id = self.combo_product.currentData()

                self.lbl_status.setText("Classifying vegetation...")
                
                self.phenology_worker = PhenologyWorker(year, geo_data, analysis_type, product_id)
                self.phenology_worker.finished_signal.connect(self.display_classification)
                self.phenology_worker.error_signal.connect(lambda e: self.lbl_status.setText(f"Classification Error: {e}"))
                self.phenology_worker.start()

            except Exception as e:
                print(f"Error starting PhenologyWorker: {e}")
                self.lbl_status.setText(f"Error: {e}")
        else:
             # Radar source -> skip phenology
             self.lbl_status.setText("Analysis Complete (Radar Mode).")
             # Try to display classification placeholder?
             self.display_classification({"Radar Mode Active": 100})

    def display_classification(self, results):
        if 'tile_url' in results:
            self.current_analysis_memory['class_url'] = results['tile_url']
            
            # If currently viewing Classification tab, show this map immediately
            if self.stack.currentIndex() == 2:
                # Determine opacity: 0.6 for Product Scanning (Radar-like), 1.0 for Area
                opacity = 0.6 if self.combo_analysis_mode.currentIndex() == 1 else 1.0
                js = f"window.addSentinelLayer('{results['tile_url']}', {opacity})"
                self.browser.page().runJavaScript(js)
                
                # Also show trend button if we have label mapping (relaxed check)
                # Previously checked for 'classified_image', but that is not saved in records.
                if self.user_mode == "Engineer" and 'label_mapping' in results:
                    self.btn_trends.show()
                else:
                    self.btn_trends.hide()

        result_utils.display_classification(self, results)

        # Always auto-trigger deforestation after classification, 
        # but DELAY it to allow map coloring to finish first.
        # This is now part of the sequential chain (Deforestation follows Phenology).
        self.lbl_status.setText("Forest Analysis pending... (Starting in 6s)")
        # Use persistent timer
        self.defor_timer.start(6000)

    def generate_trends(self):
        print("DEBUG: generate_trends called")
        cls_data = self.current_analysis_memory.get("classification")
        # Relaxed check: We don't strictly need 'classified_image' anymore as TrendWorker rebuilds it.
        if not cls_data:
            QMessageBox.warning(self, "Error", "Classification data not ready.")
            return

        # Get Geometry (Robustly)
        raw_geo = self.current_analysis_memory.get("geometry")
        
        # Handle cases where geometry might be wrapped in a dict under 'geometry' key
        # or might be the dict itself.
        if isinstance(raw_geo, dict) and 'geometry' in raw_geo:
             geom = raw_geo['geometry']
        else:
             geom = raw_geo
             
        if not geom:
            QMessageBox.warning(self, "Error", "Geometry data missing.")
            return

        # Get date from memory or UI
        if self.analysis_mode == "single":
            # For single date, use 2 months before and 2 months after
            center_date = self.date_start.date()
            d1 = center_date.addMonths(-2).toString("dd.MM.yyyy")
            d2 = center_date.addMonths(2).toString("dd.MM.yyyy")
        else:
            # For range, use the selected start and end dates
            d1 = self.date_start.date().toString("dd.MM.yyyy")
            d2 = self.date_end.date().toString("dd.MM.yyyy")

        # 1. Prepare Arguments (No Serialization!)
        print("DEBUG: Preparing TrendWorker arguments...", flush=True)
        try:
            # Serializing Geometry to JSON string for thread safety
            if isinstance(geom, dict):
                ee_geom = ee.Geometry(geom)
            else:
                ee_geom = geom
            
            geo_json = ee_geom.serialize()
            
            # Extract Year from Start Date
            # d1 format is "dd.MM.yyyy"
            year = int(d1.split(".")[2])
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to prepare arguments: {e}")
            return

        # 2. Create Thread and Worker
        legend_colors = cls_data.get('legend_colors')
        self.trend_thread = QThread()
        self.trend_worker = TrendWorker(geo_json, 
                                        year, 
                                        d1, d2, 
                                        legend_colors,
                                        label_mapping=cls_data.get('label_mapping'))
        
        # 2. Move Worker to Thread
        self.trend_worker.moveToThread(self.trend_thread)
        
        # 3. Connect Signals
        self.trend_thread.started.connect(self.trend_worker.process)
        self.trend_worker.finished_signal.connect(self.on_trends_ready)
        self.trend_worker.finished_signal.connect(self.trend_thread.quit)
        self.trend_worker.finished_signal.connect(self.trend_worker.deleteLater)
        self.trend_thread.finished.connect(self.trend_thread.deleteLater)
        
        self.trend_worker.error_signal.connect(lambda e: (QMessageBox.critical(self, "Error", e), self.btn_trends.setEnabled(True), self.trend_thread.quit()))

        # 4. Start
        print("DEBUG: Starting Thread...")
        self.trend_thread.start()

    def on_trends_ready(self, data):
        print("DEBUG: on_trends_ready called")
        self.btn_trends.setEnabled(True)
        
        if not data:
            QMessageBox.warning(self, "No Data", "No historical data found for this period (possibly due to clouds).")
            self.lbl_status.setText("Trend Generation Failed (No Data).")
            return

        self.lbl_status.setText("Trend Graphs Generated.")
        
        try:
            # Cleanup previous window if exists
            if hasattr(self, 'trend_window') and self.trend_window is not None:
                try:
                    self.trend_window.close()
                    self.trend_window.deleteLater()
                except RuntimeError:
                    pass
                self.trend_window = None

            # Use the new Dialog
            print("DEBUG: Creating TrendGraphDialog...")
            colors = self.current_analysis_memory["classification"].get('legend_colors', {})
            self.trend_window = TrendGraphDialog(data, colors, self)
            print("DEBUG: Showing TrendGraphDialog...")
            self.trend_window.show() # Modeless
            # or self.trend_window.exec_() # Modal
        except Exception as e:
            QMessageBox.warning(self, "Plot Error", str(e))

    def reset_interface(self):
        # 1. Remove Map Layers (Visuals)
        if hasattr(self, 'browser'):
            self.browser.page().runJavaScript("removeSentinelLayer()")
            
        # 2. Clear Engineer Data (Index Labels)
        for lbl in self.band_labels.values(): lbl.setText("---")
        
        keys_to_remove = []
        # Dynamic keys from Engineer results (Health/Soil cards in Engineer mode)
        dynamic_keys = [
            "HealthFrame", "HealthScore", "HealthStage", "HealthHeader", "HealthLine",
            "SoilFrame", "SoilScore", "SoilStage", "SoilHeader", "SoilLine"
        ]

        for key, widget in self.index_labels.items():
            if key in dynamic_keys:
                widget.setParent(None)
                widget.deleteLater()
                keys_to_remove.append(key)
            else:
                if hasattr(widget, 'setText'): widget.setText("---")
                
        for k in keys_to_remove: del self.index_labels[k]

        # 3. Clear Farmer Data (NEW)
        if hasattr(self, 'layout_farmer_content'):
            while self.layout_farmer_content.count():
                item = self.layout_farmer_content.takeAt(0)
                widget = item.widget()
                if widget:
                    widget.deleteLater()
                elif item.layout():
                     # Just in case there are nested layouts, though mostly widgets
                     pass

        # 4. Clear Classification Table
        self.table_class.setRowCount(0)

        # 5. Clear Deforestation Data
        if hasattr(self, 'lbl_defor_status'):
            self.lbl_defor_status.setText("Select an area and run analysis to begin.")
            self.lbl_defor_status.setStyleSheet("color: #888; font-style: italic; font-size: 12px;")
            self.lbl_defor_p1_title.setText("Period 1 (Baseline)")
            self.lbl_defor_p1_value.setText("— %")
            self.lbl_defor_p2_title.setText("Period 2 (Current)")
            self.lbl_defor_p2_value.setText("— %")
            self.lbl_defor_change.setText("— %")
            self.lbl_defor_change.setStyleSheet("color: #9E9E9E; border: none;")
            self.lbl_defor_verdict.setText("")

        # 5. Hide Action Buttons
        if hasattr(self, 'rec_btn'): self.rec_btn.hide()
        if hasattr(self, 'btn_trends'): self.btn_trends.hide()

        # 6. Reset Internal State
        self.lbl_status.setText("Ready.")
        self.current_analysis_memory = {"indices": {}, "classification": {}}
        # Explicitly clear URL keys to prevent accidental reuse
        self.current_analysis_memory['rgb_url'] = None
        self.current_analysis_memory['class_url'] = None


    def update_weather(self, lat, lon):
        d1 = self.date_start.date().toString("yyyy-MM-dd")
        d2 = self.date_end.date().toString("yyyy-MM-dd")
        
        # If single mode, use d1 for both start and end
        if self.analysis_mode == "single":
            d2 = None

        self.lbl_weather_desc.setText("Updating...")
        
        # Kill previous worker if running (optional optimization)
        # For simplicity, just start a new one
        self.weather_worker = WeatherWorker(lat, lon, d1, d2)
        self.weather_worker.finished.connect(self.on_weather_update)
        self.weather_worker.start()

    def on_weather_update(self, data):
        if data.get("error"):
            self.lbl_weather_desc.setText("N/A")
            self.lbl_weather_temp.setText("--")
            return

        self.lbl_weather_temp.setText(data['temp'])
        self.lbl_weather_desc.setText(data['condition'])
        self.lbl_weather_icon.setText(data['icon'])

    # ---- DEFORESTATION METHODS ----

    def trigger_deforestation_analysis(self):
        """Start deforestation analysis if geometry is available."""
        geo = self.current_analysis_memory.get("geometry")
        if not geo:
            self.lbl_defor_status.setText("No area selected. Run an analysis first.")
            return

        # Don't re-run if already cached
        if self.current_analysis_memory.get('deforestation'):
            self.on_deforestation_result(self.current_analysis_memory['deforestation'])
            return

        # Determine mode and dates
        mode = self.analysis_mode
        d1 = self.date_start.date().toString("yyyy-MM-dd")
        d2 = self.date_end.date().toString("yyyy-MM-dd") if mode == "range" else None

        self.lbl_defor_status.setText("Running forest analysis...")
        self.lbl_defor_status.setStyleSheet("color: #E65100; font-style: italic; font-size: 12px;")
        self.lbl_status.setText("Performing Forest Analysis...")
        self.lbl_status.setStyleSheet("color: #E65100; font-style: italic; font-size: 13px; margin-bottom: 15px;")

        # Build EE geometry
        try:
            if isinstance(geo, dict):
                if 'geometry' in geo:
                    ee_geometry = ee.Geometry(geo['geometry'])
                else:
                    ee_geometry = ee.Geometry(geo)
            else:
                ee_geometry = geo
        except Exception as e:
            self.lbl_defor_status.setText(f"Geometry error: {e}")
            return

        self.defor_worker = DeforestationWorker(ee_geometry, mode, d1, d2)
        self.defor_worker.status_signal.connect(lambda msg: self.lbl_defor_status.setText(msg))
        self.defor_worker.error_signal.connect(lambda err: self.lbl_defor_status.setText(f"Error: {err}"))
        self.defor_worker.finished_signal.connect(self.on_deforestation_result)
        self.defor_worker.start()

    def on_deforestation_result(self, data):
        """Display deforestation comparison results."""
        # Cache results
        self.current_analysis_memory['deforestation'] = data

        y1 = data.get('period1_year', '?')
        y2 = data.get('period2_year', '?')
        pct1 = data.get('period1_pct')
        pct2 = data.get('period2_pct')
        change = data.get('change_pct')

        # Period 1
        self.lbl_defor_p1_title.setText(f"Period 1 — {y1} (Baseline)")
        if pct1 is not None:
            self.lbl_defor_p1_value.setText(f"{pct1:.1f}%")
        else:
            self.lbl_defor_p1_value.setText("No data")

        # Period 2
        self.lbl_defor_p2_title.setText(f"Period 2 — {y2} (Current)")
        if pct2 is not None:
            self.lbl_defor_p2_value.setText(f"{pct2:.1f}%")
        else:
            self.lbl_defor_p2_value.setText("No data")

        # Change indicator
        if change is not None:
            sign = "+" if change >= 0 else ""
            self.lbl_defor_change.setText(f"{sign}{change:.1f}%")

            if change > 0.5:
                # Trees increased = reforestation (good)
                self.lbl_defor_change.setStyleSheet("color: #2E7D32; border: none;")
                self.lbl_defor_verdict.setText("Forest coverage has increased (Reforestation)")
                self.lbl_defor_verdict.setStyleSheet("color: #2E7D32; border: none;")
            elif change < -0.5:
                # Trees decreased = deforestation (bad)
                self.lbl_defor_change.setStyleSheet("color: #C62828; border: none;")
                self.lbl_defor_verdict.setText("Forest coverage has decreased (Deforestation)")
                self.lbl_defor_verdict.setStyleSheet("color: #C62828; border: none;")
            else:
                # No significant change
                self.lbl_defor_change.setStyleSheet("color: #9E9E9E; border: none;")
                self.lbl_defor_verdict.setText("No significant change in forest coverage")
                self.lbl_defor_verdict.setStyleSheet("color: #666; border: none;")
        else:
            self.lbl_defor_change.setText("N/A")
            self.lbl_defor_change.setStyleSheet("color: #9E9E9E; border: none;")
            self.lbl_defor_verdict.setText("Insufficient data for comparison")
            self.lbl_defor_verdict.setStyleSheet("color: #666; border: none;")

        self.lbl_defor_status.setText("Analysis complete.")
        self.lbl_defor_status.setStyleSheet("color: #2E7D32; font-style: italic; font-size: 12px;")
        self.lbl_status.setText("Analysis Finished")
        self.lbl_status.setStyleSheet("color: #2E7D32; font-style: italic; font-size: 13px; margin-bottom: 15px;")

            
if __name__ == "__main__":
    # Global Exception Hook to catch silent crashes
    def exception_hook(exctype, value, tb):
        print("CRITICAL ERROR CAUGHT:", file=sys.stderr)
        traceback.print_exception(exctype, value, tb)
        sys.exit(1)
        
    sys.excepthook = exception_hook

    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)

    font = app.font()
    font.setPointSize(10)
    app.setFont(font)

    window = NeoAgroApp()
    window.show()
    sys.exit(app.exec_())