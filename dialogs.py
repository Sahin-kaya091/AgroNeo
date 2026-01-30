from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QAbstractItemView, QTextEdit,
                             QHBoxLayout, QListWidgetItem, QGridLayout, QFrame, QTableWidget, QHeaderView, QTableWidgetItem, QWidget)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QSize

# --- KAYITLARI GÖSTERME DİYALOĞU ---
class RecordsDialog(QDialog):
    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Kayıtlı Analizler")
        self.resize(500, 400)
        self.records = records

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.refresh_list()
        self.list_widget.itemDoubleClicked.connect(self.show_details)
        layout.addWidget(QLabel("Kayıtlar (Detaylar için çift tıklayın):"))
        layout.addWidget(self.list_widget)

        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.close)
        layout.addWidget(btn_close)

    def refresh_list(self):
        self.list_widget.clear()
        for name in self.records.keys():
            self.list_widget.addItem(name)

    def show_details(self, item):
        name = item.text()
        data = self.records.get(name)
        if not data: return

        detail_text = f"--- {name} Detayları ---\n\n"
        detail_text += f"📅 Kayıt Tarihi: {data.get('date', 'N/A')}\n"
        detail_text += f"📊 Sağlık Skoru: {data.get('health_score', 'N/A')}\n"
        detail_text += f"🌱 Evre: {data.get('stage', 'N/A')}\n\n"
        detail_text += "[ İNDEKS DEĞERLERİ ]\n"
        for k, v in data.get('indices', {}).items():
            detail_text += f"• {k}: {v}\n"
        detail_text += "\n[ ARAZİ SINIFLANDIRMASI ]\n"
        for k, v in data.get('classification', {}).items():
            detail_text += f"• {k}: %{v:.1f}\n"

        msg = QDialog(self)
        msg.setWindowTitle(f"{name} Analiz Raporu")
        msg.resize(400, 500)
        l = QVBoxLayout()
        msg.setLayout(l)
        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setText(detail_text)
        txt.setFont(QFont("Consolas", 10))
        l.addWidget(txt)
        btn_ok = QPushButton("Tamam")
        btn_ok.clicked.connect(msg.close)
        l.addWidget(btn_ok)
        msg.exec_()


# --- YENİ EKLENEN SINIFLAR: KARŞILAŞTIRMA MODÜLÜ ---

class ComparisonSelectionDialog(QDialog):
    """
    Kullanıcının karşılaştırmak için 2 kayıt seçtiği ekran.
    Kullanıcı deneyimi için Checkbox kullanıyoruz (Çoklu seçim için en doğrusu budur).
    Ancak 'çift tıklayarak seçme' isteğine uygun olarak, çift tıklandığında da seçimi tersine çeviriyoruz.
    """

    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Karşılaştırma İçin Kayıt Seç")
        self.resize(500, 450)
        self.records = records
        self.selected_records = []

        layout = QVBoxLayout()
        self.setLayout(layout)

        lbl = QLabel("Karşılaştırmak istediğiniz tam olarak 2 kaydı seçiniz:")
        lbl.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)  # Seçimi Checkbox ile yöneteceğiz
        self.populate_list()

        # Sinyaller
        self.list_widget.itemChanged.connect(self.check_selection_count)
        self.list_widget.itemDoubleClicked.connect(self.toggle_check_on_double_click)

        layout.addWidget(self.list_widget)

        # Butonlar
        btn_layout = QHBoxLayout()

        self.btn_compare = QPushButton("Karşılaştır")
        self.btn_compare.setEnabled(False)  # Başlangıçta pasif
        self.btn_compare.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 6px; }
            QPushButton:disabled { background-color: #B0BEC5; color: #555; }
        """)
        self.btn_compare.clicked.connect(self.run_comparison)

        btn_close = QPushButton("Kapat")
        btn_close.clicked.connect(self.close)

        btn_layout.addWidget(btn_close)
        btn_layout.addWidget(self.btn_compare)
        layout.addLayout(btn_layout)

    def populate_list(self):
        for name in self.records.keys():
            item = QListWidgetItem(name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)

    def toggle_check_on_double_click(self, item):
        """Çift tıklandığında seçimi (tik işaretini) tersine çevir"""
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)

    def check_selection_count(self):
        """Kaç tane seçildiğini sayar ve butonu yönetir"""
        checked_items = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.Checked:
                checked_items.append(item.text())

        self.selected_records = checked_items

        # Tam olarak 2 tane seçildiyse butonu aç
        if len(checked_items) == 2:
            self.btn_compare.setEnabled(True)
            self.btn_compare.setText(f"Karşılaştır ({checked_items[0]} vs {checked_items[1]})")
        else:
            self.btn_compare.setEnabled(False)
            self.btn_compare.setText("Karşılaştır (Lütfen 2 kayıt seçin)")

    def run_comparison(self):
        if len(self.selected_records) == 2:
            data1 = self.records[self.selected_records[0]]
            data2 = self.records[self.selected_records[1]]

            # Veri paketini oluştur
            comp_data = {
                "name1": self.selected_records[0],
                "data1": data1,
                "name2": self.selected_records[1],
                "data2": data2
            }

            # Rapor ekranını aç
            report = ComparisonReportDialog(comp_data, self)
            report.exec_()


class ComparisonReportDialog(QDialog):
    """Karşılaştırma Sonuçlarını Gösteren Ekran"""

    def __init__(self, comp_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Karşılaştırma Raporu: {comp_data['name1']} vs {comp_data['name2']}")
        self.resize(900, 600)
        self.data = comp_data

        layout = QVBoxLayout()
        self.setLayout(layout)

        # 1. Başlıklar ve Genel Bilgi
        header_layout = QGridLayout()

        # İsimler
        lbl_n1 = QLabel(self.data['name1']);
        lbl_n1.setFont(QFont("Arial", 12, QFont.Bold));
        lbl_n1.setStyleSheet("color: #1565C0")
        lbl_n2 = QLabel(self.data['name2']);
        lbl_n2.setFont(QFont("Arial", 12, QFont.Bold));
        lbl_n2.setStyleSheet("color: #C62828")

        # Tarihler
        date1 = self.data['data1'].get('date', '-')
        date2 = self.data['data2'].get('date', '-')

        header_layout.addWidget(QLabel("Kayıt Adı:"), 0, 0);
        header_layout.addWidget(lbl_n1, 0, 1)
        header_layout.addWidget(QLabel("Kayıt Adı:"), 0, 2);
        header_layout.addWidget(lbl_n2, 0, 3)

        header_layout.addWidget(QLabel("Tarih:"), 1, 0);
        header_layout.addWidget(QLabel(date1), 1, 1)
        header_layout.addWidget(QLabel("Tarih:"), 1, 2);
        header_layout.addWidget(QLabel(date2), 1, 3)

        frame_header = QFrame();
        frame_header.setLayout(header_layout);
        frame_header.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(frame_header)

        # 2. Sağlık Skoru Karşılaştırması
        h_layout = QHBoxLayout()

        score1 = float(self.data['data1'].get('health_score', 0))
        score2 = float(self.data['data2'].get('health_score', 0))
        diff_score = score2 - score1

        box1 = self.create_score_box(score1, self.data['data1'].get('stage', '-'))
        box2 = self.create_score_box(score2, self.data['data2'].get('stage', '-'))

        # Fark Kutusu
        box_diff = QFrame();
        box_diff_l = QVBoxLayout();
        box_diff.setLayout(box_diff_l)
        lbl_diff_t = QLabel("Fark");
        lbl_diff_t.setAlignment(Qt.AlignCenter)
        lbl_diff_v = QLabel(f"{diff_score:+.1f}");
        lbl_diff_v.setFont(QFont("Arial", 16, QFont.Bold))
        lbl_diff_v.setAlignment(Qt.AlignCenter)

        if diff_score > 0:
            lbl_diff_v.setStyleSheet("color: green")
        elif diff_score < 0:
            lbl_diff_v.setStyleSheet("color: red")
        else:
            lbl_diff_v.setStyleSheet("color: gray")

        box_diff_l.addWidget(lbl_diff_t);
        box_diff_l.addWidget(lbl_diff_v)
        box_diff.setStyleSheet("border: 1px dashed #999; border-radius: 5px;")

        h_layout.addWidget(box1);
        h_layout.addWidget(box_diff);
        h_layout.addWidget(box2)
        layout.addLayout(h_layout)

        # 3. İndeks Tablosu (Yan Yana)
        layout.addWidget(QLabel("📊 İndeks Karşılaştırması"))
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["İndeks", f"{self.data['name1']}", f"{self.data['name2']}", "Değişim"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        indices = ["NDVI", "EVI", "SAVI", "NDRE", "GNDVI", "NDWI"]
        self.table.setRowCount(len(indices))

        for i, idx_name in enumerate(indices):
            val1 = float(self.data['data1'].get('indices', {}).get(idx_name, 0))
            val2 = float(self.data['data2'].get('indices', {}).get(idx_name, 0))
            diff = val2 - val1

            self.table.setItem(i, 0, QTableWidgetItem(idx_name))
            self.table.setItem(i, 1, QTableWidgetItem(f"{val1:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{val2:.2f}"))

            item_diff = QTableWidgetItem(f"{diff:+.2f}")
            if diff > 0:
                item_diff.setForeground(QColor("green"))
            elif diff < 0:
                item_diff.setForeground(QColor("red"))
            self.table.setItem(i, 3, item_diff)

        layout.addWidget(self.table)

        # 4. Kapat Butonu
        btn_ok = QPushButton("Kapat")
        btn_ok.clicked.connect(self.close)
        layout.addWidget(btn_ok)

    def create_score_box(self, score, stage):
        frame = QFrame()
        l = QVBoxLayout()
        frame.setLayout(l)

        l_score = QLabel(f"{score:.1f}")
        l_score.setFont(QFont("Arial", 20, QFont.Bold))
        l_score.setAlignment(Qt.AlignCenter)

        l_stage = QLabel(stage)
        l_stage.setWordWrap(True)
        l_stage.setAlignment(Qt.AlignCenter)

        l.addWidget(QLabel("Sağlık Skoru"));
        l.addWidget(l_score);
        l.addWidget(l_stage)
        frame.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 8px;")
        return frame


class DateSelectionDialog(QDialog):
    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Tarih Seçimi")
        self.resize(450, 350)
        self.candidates = candidates
        self.selected_date = None
        
        # --- MODERN STYLING ---
        self.setStyleSheet("""
            QDialog {
                background-color: #F8F9FA;
            }
            QLabel#TitleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #2E7D32;
                margin-bottom: 10px;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
                outline: none;
                padding: 5px;
            }
            QListWidget::item {
                background-color: #FAFAFA;
                border: 1px solid #EEEEEE;
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
                color: #333;
            }
            QListWidget::item:hover {
                background-color: #E8F5E9;
                border-color: #C8E6C9;
            }
            QListWidget::item:selected {
                background-color: #C8E6C9;
                border-color: #2E7D32;
                color: #1B5E20;
            }
            QPushButton#SelectButton {
                background-color: #2E7D32; 
                color: white; 
                border-radius: 8px;
                padding: 10px 20px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton#SelectButton:hover {
                background-color: #1B5E20;
            }
            QPushButton#CancelButton {
                background-color: transparent;
                color: #757575;
                border: none;
                font-size: 13px;
            }
            QPushButton#CancelButton:hover {
                color: #424242;
                background-color: #EEEEEE;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        self.setLayout(layout)
        
        lbl = QLabel("Analiz için en uygun tarihi seçiniz:")
        lbl.setObjectName("TitleLabel")
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        for cand in candidates:
            date_str = cand['date']
            cloud = cand['cloud']
            label_text = cand.get('label', 'ADAY')
            
            # Rich text formatting for modern look
            display_text = f"{date_str}\n" 
            
            # Item setup
            item = QListWidgetItem()
            item.setData(Qt.UserRole, date_str)
            item.setTextAlignment(Qt.AlignLeft)
            
            # Create a custom widget for this item to look nice
            widget = QWidget()
            w_layout = QHBoxLayout()
            w_layout.setContentsMargins(10, 5, 10, 5)
            widget.setLayout(w_layout)
            
            # Icon or Tag
            tag_color = "#1976D2" if label_text == "ÖNCE" else "#E64A19" # Blue for Before, Orange for After
            tag_lbl = QLabel(label_text)
            tag_lbl.setStyleSheet(f"background-color: {tag_color}; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;")
            tag_lbl.setFixedWidth(60)
            tag_lbl.setAlignment(Qt.AlignCenter)
            
            # Date Info
            info_layout = QVBoxLayout()
            date_lbl = QLabel(date_str)
            date_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            date_lbl.setStyleSheet("color: #333;")
            
            cloud_lbl = QLabel(f"Bulut Oranı: %{cloud:.1f}")
            cloud_lbl.setStyleSheet("color: #666; font-size: 12px;")
            
            info_layout.addWidget(date_lbl)
            info_layout.addWidget(cloud_lbl)
            
            w_layout.addWidget(tag_lbl)
            w_layout.addSpacing(10)
            w_layout.addLayout(info_layout)
            w_layout.addStretch()
            
            # Add widget to item
            item.setSizeHint(QSize(widget.sizeHint().width(), 80))
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, widget)
            
        layout.addWidget(self.list_widget)
        
        # Select first by default
        if self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)
        
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setObjectName("CancelButton")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Seç ve Analiz Et")
        btn_ok.setObjectName("SelectButton")
        btn_ok.setCursor(Qt.PointingHandCursor)
        btn_ok.clicked.connect(self.accept_selection)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_ok)
        
        layout.addLayout(btn_layout)
        
    def accept_selection(self):
        current_item = self.list_widget.currentItem()
        if current_item:
            self.selected_date = current_item.data(Qt.UserRole)
            self.accept()
        else:
            # Fallback if somehow nothing selected but list not empty
            if self.list_widget.count() > 0:
                self.selected_date = self.list_widget.item(0).data(Qt.UserRole)
                self.accept()


class InfoDialog(QDialog):
    def __init__(self, title, info_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"About {title}")
        self.resize(400, 300)
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #2E7D32; margin-bottom: 10px;")
        lbl_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl_title)
        
        txt_info = QTextEdit()
        txt_info.setReadOnly(True)
        txt_info.setText(info_text)
        txt_info.setStyleSheet("font-size: 14px; color: #333; background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; border-radius: 5px;")
        layout.addWidget(txt_info)
        
        btn_close = QPushButton("Close")
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #ddd;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #ccc;
            }
        """)
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)
