from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QAbstractItemView, QTextEdit,
                             QHBoxLayout, QListWidgetItem, QGridLayout, QFrame, QTableWidget, QHeaderView, QTableWidgetItem)
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt

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
