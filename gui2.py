# import sys
# import json
# import os
# import ee
# import geemap.foliumap as geemap
# from folium import plugins
# from geopy.geocoders import Nominatim
# from PyQt5.QtWidgets import (QMainWindow, QVBoxLayout, QHBoxLayout, QGridLayout,
#                              QWidget, QLabel, QFrame, QDateEdit, QPushButton, QMessageBox, QComboBox,
#                              QStackedWidget, QSizePolicy, QLineEdit, QInputDialog, QTableWidget, QTableWidgetItem,
#                              QHeaderView)
# from PyQt5.QtWebEngineWidgets import QWebEngineView
# from PyQt5.QtCore import QUrl, QDate, Qt
# from PyQt5.QtGui import QFont, QColor
# from datetime import datetime
#
# from worker import AnalysisWorker
# from dialogs import RecordsDialog, ComparisonSelectionDialog
#
# class NeoAgroApp(QMainWindow):
#     def __init__(self):
#         super().__init__()
#         self.setWindowTitle("NeoAgro - Gelişmiş Analiz İstasyonu")
#         self.setGeometry(100, 100, 1400, 800)
#
#         self.band_labels = {}
#         self.index_labels = {}
#
#         # --- VERİ YÖNETİMİ ---
#         self.current_analysis_memory = {}
#         base_dir = os.path.dirname(os.path.abspath(__file__))
#         logs_folder = os.path.join(base_dir, "Saved Logs")
#         if not os.path.exists(logs_folder):
#             os.makedirs(logs_folder)
#         self.saved_records_file = os.path.join(logs_folder, "saved_records.json")
#         self.load_records()
#
#         # --- Ana Düzen ---
#         main_widget = QWidget()
#         self.setCentralWidget(main_widget)
#         main_layout = QHBoxLayout()
#         main_layout.setContentsMargins(0, 0, 0, 0)
#         main_layout.setSpacing(0)
#         main_widget.setLayout(main_layout)
#
#         # --- SOL PANEL (HARİTA) ---
#         left_container = QWidget()
#         left_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
#         left_layout = QVBoxLayout()
#         left_layout.setContentsMargins(0, 0, 0, 0)
#         left_container.setLayout(left_layout)
#
#         self.browser = QWebEngineView()
#         self.current_start_date = "2023-06-01"
#         self.current_end_date = "2023-09-30"
#         self.analysis_mode = "range"
#
#         self.create_map_html(self.current_start_date, self.current_end_date, mode="range")
#         file_path = os.path.abspath("temp_map.html")
#         self.browser.setUrl(QUrl.fromLocalFile(file_path))
#         self.browser.titleChanged.connect(self.on_map_interaction)
#
#         left_layout.addWidget(self.browser)
#         main_layout.addWidget(left_container, stretch=1)
#
#         # --- YÜZEN PANELLER ---
#         self.setup_date_panel()
#         self.setup_search_panel()
#         self.setup_records_button()
#
#         # --- SAĞ PANEL ---
#         self.setup_right_panel(main_layout)
#
#     def load_records(self):
#         if os.path.exists(self.saved_records_file):
#             try:
#                 with open(self.saved_records_file, 'r', encoding='utf-8') as f:
#                     self.records = json.load(f)
#             except:
#                 self.records = {}
#         else:
#             self.records = {}
#
#     def save_records_to_disk(self):
#         try:
#             with open(self.saved_records_file, 'w', encoding='utf-8') as f:
#                 json.dump(self.records, f, ensure_ascii=False, indent=4)
#         except Exception as e:
#             print(f"Kayıt Hatası: {e}")
#
#     def setup_search_panel(self):
#         self.search_panel = QFrame(self.browser)
#         self.search_panel.setStyleSheet(
#             "QFrame {background-color: rgba(255, 255, 255, 0.9); border-radius: 20px; border: 1px solid #ccc;}")
#         self.search_panel.setFixedWidth(400)
#         self.search_panel.setFixedHeight(50)
#         layout = QHBoxLayout()
#         layout.setContentsMargins(15, 5, 5, 5)
#         self.search_panel.setLayout(layout)
#         self.txt_search = QLineEdit()
#         self.txt_search.setPlaceholderText("Şehir, İlçe veya Bölge adı girin...")
#         self.txt_search.setStyleSheet("border: none; background: transparent; font-size: 14px;")
#         self.txt_search.returnPressed.connect(self.search_location)
#         btn_search = QPushButton("🔍")
#         btn_search.setStyleSheet(
#             "QPushButton {background-color: #2196F3; color: white; border-radius: 15px; font-weight: bold; width: 30px; height: 30px;} QPushButton:hover { background-color: #1976D2; }")
#         btn_search.clicked.connect(self.search_location)
#         layout.addWidget(self.txt_search)
#         layout.addWidget(btn_search)
#         self.search_panel.show()
#
#     def setup_records_button(self):
#         self.btn_show_records = QPushButton("📂 Kayıtları Göster", self.browser)
#         self.btn_show_records.setStyleSheet("""
#             QPushButton {
#                 background-color: white;
#                 color: #333;
#                 border: 2px solid #ccc;
#                 border-radius: 5px;
#                 padding: 5px;
#                 font-weight: bold;
#             }
#             QPushButton:hover { background-color: #eee; }
#         """)
#         self.btn_show_records.setFixedSize(140, 35)
#         self.btn_show_records.move(30, 650)
#         self.btn_show_records.clicked.connect(self.open_records_dialog)
#         self.btn_show_records.show()
#
#     def setup_date_panel(self):
#         self.date_panel = QFrame(self.browser)
#         self.date_panel.setStyleSheet("background-color: rgba(255, 255, 255, 0.95); border-radius: 8px;")
#         self.date_panel.setFixedWidth(250)
#         # Panelin yüksekliğini arttırıyoruz çünkü yeni buton ekledik
#         self.date_panel.setFixedHeight(250)
#
#         panel_grid = QGridLayout()
#         self.date_panel.setLayout(panel_grid)
#
#         self.combo_mode = QComboBox()
#         self.combo_mode.addItems(["Tarih Aralığı", "Tek Tarih"])
#         self.combo_mode.currentIndexChanged.connect(self.on_mode_change)
#
#         self.date_start = QDateEdit()
#         self.date_start.setDisplayFormat("yyyy-MM-dd")
#         self.date_start.setDate(QDate.fromString(self.current_start_date, "yyyy-MM-dd"))
#         self.date_start.setCalendarPopup(True)
#
#         self.lbl_end = QLabel("Bitiş:")
#         self.date_end = QDateEdit()
#         self.date_end.setDisplayFormat("yyyy-MM-dd")
#         self.date_end.setDate(QDate.fromString(self.current_end_date, "yyyy-MM-dd"))
#         self.date_end.setCalendarPopup(True)
#
#         btn_update = QPushButton("Analizi Güncelle")
#         btn_update.setStyleSheet(
#             "background-color: #2196F3; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold;")
#         btn_update.clicked.connect(self.update_map_date)
#
#         # KAYIT ET BUTONU
#         btn_save = QPushButton("💾 Kayıt Et")
#         btn_save.setStyleSheet(
#             "background-color: #4CAF50; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold; margin-top: 5px;")
#         btn_save.clicked.connect(self.save_current_analysis)
#
#         # --- YENİ KARŞILAŞTIR BUTONU ---
#         btn_compare_main = QPushButton("⚖️ Karşılaştır")
#         btn_compare_main.setStyleSheet(
#             "background-color: #FF9800; color: white; border: none; padding: 6px; border-radius: 4px; font-weight: bold; margin-top: 2px;")
#         btn_compare_main.clicked.connect(self.open_comparison_dialog)
#
#         panel_grid.addWidget(QLabel("Mod:"), 0, 0)
#         panel_grid.addWidget(self.combo_mode, 0, 1)
#         panel_grid.addWidget(QLabel("Başlangıç:"), 1, 0)
#         panel_grid.addWidget(self.date_start, 1, 1)
#         panel_grid.addWidget(self.lbl_end, 2, 0)
#         panel_grid.addWidget(self.date_end, 2, 1)
#         panel_grid.addWidget(btn_update, 3, 0, 1, 2)
#         panel_grid.addWidget(btn_save, 4, 0, 1, 2)
#         panel_grid.addWidget(btn_compare_main, 5, 0, 1, 2)  # Yeni buton
#         self.date_panel.show()
#
#     def setup_right_panel(self, main_layout):
#         right_panel = QFrame()
#         right_panel.setFixedWidth(350)
#         right_panel.setStyleSheet("background-color: #f9f9f9; border-left: 1px solid #ddd;")
#         right_layout = QVBoxLayout()
#         right_panel.setLayout(right_layout)
#
#         header_lbl = QLabel("Analiz Sonuçları")
#         header_lbl.setFont(QFont("Arial", 14, QFont.Bold))
#         right_layout.addWidget(header_lbl)
#
#         self.lbl_status = QLabel("Hazır")
#         self.lbl_status.setStyleSheet("color: #777; font-style: italic;")
#         right_layout.addWidget(self.lbl_status)
#
#         self.btn_toggle_view = QPushButton("Görünüm: Bant Değerleri")
#         self.btn_toggle_view.setCursor(Qt.PointingHandCursor)
#         self.btn_toggle_view.setStyleSheet(
#             "QPushButton {background-color: #4CAF50; color: white; border-radius: 4px; font-weight: bold; padding: 8px; margin-top: 10px;} QPushButton:hover { background-color: #45a049; }")
#         self.btn_toggle_view.clicked.connect(self.cycle_results_view)
#         right_layout.addWidget(self.btn_toggle_view)
#         right_layout.addSpacing(10)
#
#         self.stack = QStackedWidget()
#
#         self.page_bands = QWidget();
#         layout_bands = QVBoxLayout();
#         layout_bands.setContentsMargins(0, 0, 0, 0);
#         self.page_bands.setLayout(layout_bands)
#         band_names = ["B2 (Blue)", "B3 (Green)", "B4 (Red)", "B5 (RE1)", "B6 (RE2)", "B7 (RE3)", "B8 (NIR)"]
#         for b_name in band_names:
#             frame, label = self.create_result_card(b_name, "#2E7D32")
#             self.band_labels[b_name] = label
#             layout_bands.addWidget(frame)
#         layout_bands.addStretch()
#
#         self.page_indices = QWidget();
#         layout_indices = QVBoxLayout();
#         layout_indices.setContentsMargins(0, 0, 0, 0);
#         self.page_indices.setLayout(layout_indices)
#         index_names = ["NDVI", "EVI", "SAVI", "NDRE", "RENDVI", "GNDVI", "NDWI"]
#         for i_name in index_names:
#             color = "#1b5e20" if i_name == "NDVI" else "#00796B"
#             frame, label = self.create_result_card(i_name, color, is_large=True)
#             self.index_labels[i_name] = label
#             layout_indices.addWidget(frame)
#         layout_indices.addStretch()
#
#         self.page_classification = QWidget();
#         layout_class = QVBoxLayout();
#         layout_class.setContentsMargins(0, 0, 0, 0);
#         self.page_classification.setLayout(layout_class)
#         lbl_info = QLabel("Bölgedeki Arazi Dağılımı (AI)\nGoogle Dynamic World Modeli");
#         lbl_info.setStyleSheet("color: #555; font-size: 11px; margin-bottom: 5px;");
#         lbl_info.setAlignment(Qt.AlignCenter);
#         layout_class.addWidget(lbl_info)
#         self.table_class = QTableWidget();
#         self.table_class.setColumnCount(2);
#         self.table_class.setHorizontalHeaderLabels(["Sınıf", "Oran (%)"]);
#         self.table_class.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch);
#         self.table_class.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents);
#         self.table_class.verticalHeader().setVisible(False);
#         self.table_class.setStyleSheet("border: 1px solid #ddd; background-color: white;");
#         layout_class.addWidget(self.table_class)
#         layout_class.addStretch()
#
#         self.stack.addWidget(self.page_bands);
#         self.stack.addWidget(self.page_indices);
#         self.stack.addWidget(self.page_classification)
#         right_layout.addWidget(self.stack)
#         main_layout.addWidget(right_panel, stretch=0)
#
#     def create_result_card(self, title, color_hex, is_large=False):
#         frame = QFrame()
#         frame.setStyleSheet("background-color: white; border-radius: 6px; border: 1px solid #eee;")
#         lay = QVBoxLayout()
#         lay.setContentsMargins(10, 5, 10, 5)
#         frame.setLayout(lay)
#         lbl_title = QLabel(title)
#         lbl_title.setFont(QFont("Arial", 9))
#         lbl_title.setStyleSheet("color: #666;")
#         lbl_val = QLabel("---")
#         size = 22 if is_large else 18
#         lbl_val.setFont(QFont("Arial", size, QFont.Bold))
#         lbl_val.setStyleSheet(f"color: {color_hex};")
#         lay.addWidget(lbl_title)
#         lay.addWidget(lbl_val)
#         return frame, lbl_val
#
#     def cycle_results_view(self):
#         current = self.stack.currentIndex();
#         next_idx = (current + 1) % 3;
#         self.stack.setCurrentIndex(next_idx)
#         if next_idx == 0:
#             self.btn_toggle_view.setText("Görünüm: Bant Değerleri");
#             self.btn_toggle_view.setStyleSheet(
#                 "background-color: #4CAF50; color: white; padding: 8px; border-radius:4px;")
#         elif next_idx == 1:
#             self.btn_toggle_view.setText("Görünüm: Sağlık İndeksleri");
#             self.btn_toggle_view.setStyleSheet(
#                 "background-color: #00897B; color: white; padding: 8px; border-radius:4px;")
#         elif next_idx == 2:
#             self.btn_toggle_view.setText("Görünüm: Arazi Dağılımı (AI)");
#             self.btn_toggle_view.setStyleSheet(
#                 "background-color: #E65100; color: white; padding: 8px; border-radius:4px;")
#
#     def resizeEvent(self, event):
#         if hasattr(self, 'date_panel') and hasattr(self, 'browser'): self.date_panel.move(20,
#                                                                                           self.browser.height() - 270)
#         if hasattr(self, 'search_panel') and hasattr(self, 'browser'): x_pos = (
#                                                                                        self.browser.width() - 400) // 2; self.search_panel.setGeometry(
#             x_pos, 20, 400, 50)
#         super().resizeEvent(event)
#
#     def on_mode_change(self, index):
#         self.analysis_mode = "range" if index == 0 else "single"
#         self.lbl_end.setVisible(index == 0);
#         self.date_end.setVisible(index == 0)
#
#     def search_location(self):
#         query = self.txt_search.text();
#         if not query: return
#         self.lbl_status.setText(f"🔎 {query} aranıyor...")
#         try:
#             geolocator = Nominatim(user_agent="neoagro_app")
#             location = geolocator.geocode(query)
#             if location:
#                 js_code = f"window.flyToLocation({location.latitude}, {location.longitude});"
#                 self.browser.page().runJavaScript(js_code)
#                 self.lbl_status.setText(f"📍 Bulundu: {query}")
#             else:
#                 QMessageBox.warning(self, "Bulunamadı", "Konum bulunamadı.")
#                 self.lbl_status.setText("❌ Konum Yok")
#         except Exception as e:
#             QMessageBox.warning(self, "Hata", f"Bağlantı hatası: {str(e)}")
#
#     def create_map_html(self, date1, date2=None, mode="range"):
#         if mode == "range":
#             s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(date1, date2).filter(
#                 ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)).median()
#         else:
#             t = ee.Date(date1)
#             s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterDate(t.advance(-15, 'day'),
#                                                                               t.advance(15, 'day')).median()
#
#         m = geemap.Map(center=[39.0, 35.0], zoom=6, tiles="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",
#                        attr="Google Hybrid")
#
#         draw = plugins.Draw(export=False, position='topleft',
#                             draw_options={'polyline': False, 'circle': False, 'marker': False, 'circlemarker': False},
#                             edit_options={'edit': False})
#         draw.add_to(m)
#         m.save("temp_map.html")
#
#         js = """
#         <script>
#         document.addEventListener("DOMContentLoaded", function() {
#             var mapInstance = null;
#             var attempts = 0;
#             function findMap() {
#                 var found = false;
#                 for(var k in window){
#                     if(window[k] && window[k].on && window[k].addLayer && window[k].dragging){
#                         var map = window[k];
#                         mapInstance = map;
#                         console.log("Harita Bulundu!");
#                         map.on(L.Draw.Event.CREATED, function(e){
#                             var layer = e.layer;
#                             var geojson = layer.toGeoJSON();
#                             document.title = "GEOJSON:" + JSON.stringify(geojson);
#                             map.addLayer(layer);
#                         });
#                         map.on(L.Draw.Event.DELETED, function(e){
#                             document.title = "RESET";
#                         });
#                         found = true;
#                         break;
#                     }
#                 }
#                 if(!found && attempts < 20) {
#                     attempts++;
#                     setTimeout(findMap, 500);
#                 }
#             }
#             findMap();
#             window.flyToLocation = function(lat, lon) {
#                 if (mapInstance) {
#                     mapInstance.flyTo([lat, lon], 12, {animate: true, duration: 1.5});
#                 }
#             };
#         });
#         </script>
#         """
#         try:
#             with open("temp_map.html", "r", encoding="utf-8") as f:
#                 content = f.read()
#             if "</body>" in content:
#                 new_content = content.replace("</body>", js + "</body>")
#             else:
#                 new_content = content + js
#             with open("temp_map.html", "w", encoding="utf-8") as f:
#                 f.write(new_content)
#         except Exception as e:
#             print(f"Harita dosyası hatası: {e}")
#
#     def update_map_date(self):
#         d1 = self.date_start.date().toString("yyyy-MM-dd");
#         d2 = self.date_end.date().toString("yyyy-MM-dd")
#         if self.analysis_mode == "range":
#             self.create_map_html(d1, d2, "range")
#         else:
#             self.create_map_html(d1, mode="single")
#         self.browser.reload()
#
#     def on_map_interaction(self, title):
#         if title == "RESET":
#             self.reset_interface()
#         elif title.startswith("GEOJSON:"):
#             try:
#                 json_str = title[8:]
#                 raw_json = json.loads(json_str)
#                 if 'geometry' in raw_json:
#                     geo_dict = raw_json['geometry']
#                 else:
#                     geo_dict = raw_json
#                 self.fetch_data(geo_dict)
#
#             except Exception as e:
#                 self.lbl_status.setText(f"⚠️ Hata: {str(e)}")
#
#     def fetch_data(self, geo_data):
#         self.lbl_status.setText("⏳ Analiz Başladı...")
#         bands = ['B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B11']
#         d1 = self.date_start.date().toString("yyyy-MM-dd")
#         d2 = self.date_end.date().toString("yyyy-MM-dd")
#
#         self.current_analysis_memory = {"indices": {}, "classification": {}, "stage": "Bilinmiyor", "health_score": "0"}
#
#         self.worker = AnalysisWorker(geo_data, bands, self.analysis_mode, d1, d2)
#         self.worker.finished_signal.connect(self.display_results)
#         self.worker.class_signal.connect(self.display_classification)
#         self.worker.error_signal.connect(lambda e: self.lbl_status.setText(f"❌ Hata: {e}"))
#         self.worker.status_signal.connect(lambda s: self.lbl_status.setText(s))
#         self.worker.start()
#
#     def save_current_analysis(self):
#         if not self.current_analysis_memory.get("indices") and not self.current_analysis_memory.get("classification"):
#             QMessageBox.warning(self, "Veri Yok",
#                                 "Henüz tamamlanmış bir analiz yok.\nLütfen önce bir alan seçip analizin bitmesini bekleyin.")
#             return
#
#         name, ok = QInputDialog.getText(self, "Kayıt Et", "Bu analiz için bir isim giriniz:")
#         if ok and name:
#             if name in self.records:
#                 reply = QMessageBox.question(self, "Üzerine Yaz?",
#                                              f"'{name}' isminde bir kayıt zaten var. Üzerine yazılsın mı?",
#                                              QMessageBox.Yes | QMessageBox.No)
#                 if reply == QMessageBox.No: return
#
#             record_data = {
#                 "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                 "indices": self.current_analysis_memory.get("indices", {}),
#                 "classification": self.current_analysis_memory.get("classification", {}),
#                 "stage": self.current_analysis_memory.get("stage", "Bilinmiyor"),
#                 "health_score": self.current_analysis_memory.get("health_score", "0")
#             }
#
#             self.records[name] = record_data
#             self.save_records_to_disk()
#             QMessageBox.information(self, "Başarılı", "Analiz başarıyla kaydedildi.")
#
#     def open_records_dialog(self):
#         if not self.records:
#             QMessageBox.information(self, "Boş", "Henüz kaydedilmiş bir analiz yok.")
#             return
#         dlg = RecordsDialog(self.records, self)
#         dlg.exec_()
#
#     def open_comparison_dialog(self):
#         """Yeni Karşılaştırma Ekranını Açar"""
#         if not self.records or len(self.records) < 2:
#             QMessageBox.warning(self, "Yetersiz Kayıt",
#                                 "Karşılaştırma yapmak için en az 2 adet kayıtlı analiziniz olmalıdır.")
#             return
#
#         dlg = ComparisonSelectionDialog(self.records, self)
#         dlg.exec_()
#
#     def display_results(self, stats):
#         source = stats.get('source', 'S2')
#         keys_to_clear = ["HealthLine", "HealthHeader", "HealthFrame", "HealthScore", "HealthStage"]
#         for k in keys_to_clear:
#             if k in self.index_labels:
#                 try:
#                     self.index_labels[k].setParent(None);
#                     self.index_labels[k].deleteLater();
#                     del self.index_labels[k]
#                 except:
#                     pass
#
#         if source == 'S2':
#             self.lbl_status.setText("✅ Analiz Tamamlandı (Sentinel-2 Optik)");
#             self.lbl_status.setStyleSheet("color: #2E7D32; font-style: italic;")
#             b2, b3, b4 = stats.get('B2', 0), stats.get('B3', 0), stats.get('B4', 0)
#             b5, b6, b7 = stats.get('B5', 0), stats.get('B6', 0), stats.get('B7', 0)
#             b8, b11 = stats.get('B8', 0), stats.get('B11', 0)
#
#             self.band_labels["B2 (Blue)"].setText(f"{b2:.0f}");
#             self.band_labels["B3 (Green)"].setText(f"{b3:.0f}")
#             self.band_labels["B4 (Red)"].setText(f"{b4:.0f}");
#             self.band_labels["B5 (RE1)"].setText(f"{b5:.0f}")
#             self.band_labels["B6 (RE2)"].setText(f"{b6:.0f}");
#             self.band_labels["B7 (RE3)"].setText(f"{b7:.0f}")
#             self.band_labels["B8 (NIR)"].setText(f"{b8:.0f}")
#
#             def calc_idx(n, d):
#                 return n / d if d != 0 else 0.0
#
#             ndvi = calc_idx(b8 - b4, b8 + b4);
#             evi = 2.5 * calc_idx(b8 - b4, b8 + 6 * b4 - 7.5 * b2 + 10000)
#             _b8, _b4 = b8 / 10000.0, b4 / 10000.0
#             savi = ((_b8 - _b4) / (_b8 + _b4 + 0.5)) * 1.5
#             ndre = calc_idx(b8 - b5, b8 + b5);
#             rendvi = calc_idx(b6 - b5, b6 + b5);
#             gndvi = calc_idx(b8 - b3, b8 + b3);
#             ndwi = calc_idx(b8 - b11, b8 + b11)
#
#             self.index_labels["NDVI"].setText(f"{ndvi:.2f}");
#             self.index_labels["EVI"].setText(f"{evi:.2f}")
#             self.index_labels["SAVI"].setText(f"{savi:.2f}");
#             self.index_labels["NDRE"].setText(f"{ndre:.2f}")
#             self.index_labels["RENDVI"].setText(f"{rendvi:.2f}");
#             self.index_labels["GNDVI"].setText(f"{gndvi:.2f}")
#             self.index_labels["NDWI"].setText(f"{ndwi:.2f}")
#
#             self.current_analysis_memory["indices"] = {
#                 "NDVI": f"{ndvi:.2f}", "EVI": f"{evi:.2f}", "SAVI": f"{savi:.2f}",
#                 "NDRE": f"{ndre:.2f}", "RENDVI": f"{rendvi:.2f}", "GNDVI": f"{gndvi:.2f}", "NDWI": f"{ndwi:.2f}"
#             }
#
#             past_ndvi = stats.get('past_ndvi', None);
#             delta_ndvi = stats.get('ndvi_change', 0.0)
#
#             f_ndvi = max(0, ndvi);
#             f_savi = max(0, savi);
#             f_ndwi = max(0, ndwi);
#             f_evi = max(0, evi);
#             f_rendvi = max(0, rendvi);
#             f_gndvi = max(0, gndvi)
#
#             stage_name = "Bilinmiyor";
#             health_score = 0.0
#
#             if ndvi < 0.25:
#                 stage_name = "🟤 Nadas / Hazırlık (Toprak)"
#                 health_score = ((0.8 * f_savi) + (0.2 * f_ndvi)) * 0.6
#             elif past_ndvi is not None:
#                 if delta_ndvi > 0.05:
#                     stage_name = "🚀 Hızlı Gelişim (Aktif)"
#                     s_ndvi = min(1.0, f_ndvi / 0.80);
#                     s_ndwi = min(1.0, f_ndwi / 0.50)
#                     s_rendvi = min(1.0, f_rendvi / 0.60);
#                     s_gndvi = min(1.0, f_gndvi / 0.75)
#                     health_score = (0.30 * s_ndvi) + (0.20 * s_ndwi) + (0.30 * s_rendvi) + (0.20 * s_gndvi)
#                 elif delta_ndvi < -0.05:
#                     stage_name = "🍂 Hasat / Olgunlaşma"
#                     s_evi = min(1.0, f_evi / 0.60)
#                     health_score = (0.6 * s_evi) + (0.4 * f_ndvi)
#                 elif ndvi > 0.60:
#                     stage_name = "🌳 Olgunluk / Zirve Dönemi"
#                     s_evi = min(1.0, f_evi / 0.60);
#                     s_ndwi = min(1.0, f_ndwi / 0.50)
#                     s_rendvi = min(1.0, f_rendvi / 0.60);
#                     s_gndvi = min(1.0, f_gndvi / 0.80)
#                     health_score = (0.35 * s_evi) + (0.15 * s_ndwi) + (0.40 * s_rendvi) + (0.10 * s_gndvi)
#                 else:
#                     stage_name = "🌱 Erken Dönem / Yavaş Gelişim"
#                     s_savi = min(1.0, f_savi / 0.40);
#                     s_ndvi = min(1.0, f_ndvi / 0.50)
#                     health_score = (0.40 * s_savi) + (0.40 * s_ndvi) + (0.20 * f_ndwi)
#             else:
#                 if ndvi < 0.45:
#                     stage_name = "🌱 Erken Dönem (Tahmini)";
#                     health_score = ((0.5 * f_savi) + (0.5 * f_ndvi)) * 1.5
#                 elif ndvi < 0.70:
#                     stage_name = "🌿 Gelişim Dönemi (Tahmini)";
#                     s_ndvi = min(1.0, f_ndvi / 0.75);
#                     health_score = s_ndvi
#                 else:
#                     stage_name = "🌳 Olgunluk Dönemi (Tahmini)";
#                     s_evi = min(1.0, f_evi / 0.60);
#                     health_score = s_evi
#
#             final_score = min(100, max(0, health_score * 100))
#
#             self.current_analysis_memory["stage"] = stage_name
#             self.current_analysis_memory["health_score"] = f"{final_score:.1f}"
#
#             layout = self.page_indices.layout()
#             line = QFrame();
#             line.setFrameShape(QFrame.HLine);
#             line.setFrameShadow(QFrame.Sunken);
#             layout.addWidget(line)
#             lbl_head = QLabel("YZ Tabanlı Sağlık Analizi");
#             lbl_head.setFont(QFont("Arial", 10, QFont.Bold));
#             lbl_head.setAlignment(Qt.AlignCenter);
#             layout.addWidget(lbl_head)
#             frame = QFrame();
#             l = QVBoxLayout();
#             frame.setLayout(l)
#             lbl_stage = QLabel(stage_name);
#             lbl_stage.setAlignment(Qt.AlignCenter);
#             lbl_stage.setFont(QFont("Arial", 9, QFont.Bold))
#             lbl_score_val = QLabel(f"{final_score:.1f} / 100");
#             lbl_score_val.setAlignment(Qt.AlignCenter);
#             lbl_score_val.setFont(QFont("Arial", 24, QFont.Bold))
#             l.addWidget(lbl_stage);
#             l.addWidget(lbl_score_val);
#             layout.addWidget(frame)
#
#             bg, border, text = "#E8F5E9", "#4CAF50", "#1B5E20"
#             if final_score < 40:
#                 bg, border, text = "#FFEBEE", "#D32F2F", "#B71C1C"
#             elif final_score < 70:
#                 bg, border, text = "#FFF8E1", "#FFA000", "#E65100"
#
#             frame.setStyleSheet(f"background-color: {bg}; border-radius: 10px; border: 2px solid {border};")
#             lbl_stage.setStyleSheet(f"color: {border};");
#             lbl_score_val.setStyleSheet(f"color: {text};")
#
#             self.index_labels["HealthLine"] = line;
#             self.index_labels["HealthHeader"] = lbl_head
#             self.index_labels["HealthFrame"] = frame;
#             self.index_labels["HealthScore"] = lbl_score_val
#             self.index_labels["HealthStage"] = lbl_stage
#
#         elif source == 'S1':
#             self.lbl_status.setText("☁️ Optik Veri Yok -> Radar (S1)");
#             self.lbl_status.setStyleSheet("color: #D32F2F; font-weight: bold;")
#             vv, vh = stats.get('VV', 0), stats.get('VH', 0)
#             self.band_labels["B2 (Blue)"].setText("-");
#             self.band_labels["B3 (Green)"].setText("-");
#             self.band_labels["B4 (Red)"].setText(f"VV: {vv:.1f}");
#             self.band_labels["B8 (NIR)"].setText(f"VH: {vh:.1f}")
#             for k, lbl in self.index_labels.items():
#                 if hasattr(lbl, 'setText'): lbl.setText("---")
#             bitki_durumu = "Yoğun Bitki" if vh > -15 else ("Orta Seviye" if vh > -20 else "Çıplak Toprak")
#             QMessageBox.information(self, "Radar Analizi",
#                                     f"Optik veri yok. Radar kullanıldı.\nVH: {vh:.1f} dB\nDurum: {bitki_durumu}")
#
#     def display_classification(self, results):
#         self.table_class.setRowCount(0)
#         self.current_analysis_memory["classification"] = results
#         sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
#         for name, percent in sorted_results:
#             row_idx = self.table_class.rowCount()
#             self.table_class.insertRow(row_idx)
#             self.table_class.setItem(row_idx, 0, QTableWidgetItem(name))
#             percent_item = QTableWidgetItem(f"%{percent:.1f}")
#             percent_item.setTextAlignment(Qt.AlignCenter)
#             if name == "Tarım Arazisi":
#                 percent_item.setForeground(QColor("#2E7D32"));
#                 percent_item.setFont(QFont("Arial", 9, QFont.Bold))
#             elif name == "Su":
#                 percent_item.setForeground(QColor("#1565C0"))
#             self.table_class.setItem(row_idx, 1, percent_item)
#
#     def reset_interface(self):
#         for lbl in self.band_labels.values(): lbl.setText("---")
#         keys_to_remove = []
#         for key, widget in self.index_labels.items():
#             if key == "HealthFrame":
#                 widget.setParent(None);
#                 widget.deleteLater();
#                 keys_to_remove.append(key)
#             elif key in ["HealthScore", "HealthStage"]:
#                 widget.setParent(None);
#                 widget.deleteLater();
#                 keys_to_remove.append(key)
#             else:
#                 if hasattr(widget, 'setText'): widget.setText("---")
#         for k in keys_to_remove: del self.index_labels[k]
#         self.table_class.setRowCount(0)
#         self.lbl_status.setText("Hazır")
#         self.current_analysis_memory = {}
#
#
#