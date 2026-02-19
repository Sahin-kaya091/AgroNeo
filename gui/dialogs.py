from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QListWidget, QAbstractItemView, QTextEdit,
                             QHBoxLayout, QListWidgetItem, QGridLayout, QFrame, QTableWidget, QHeaderView, QTableWidgetItem, QWidget, QMessageBox, QFileDialog)
import csv
import os
from PyQt5.QtGui import QFont, QColor
from PyQt5.QtCore import Qt, QSize

# --- RECORDS DIALOG ---
class RecordsDialog(QDialog):
    def __init__(self, records, logs_folder, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Saved Analyses")
        self.resize(500, 400)
        self.records = records
        self.logs_folder = logs_folder

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        self.refresh_list()
        self.list_widget.itemDoubleClicked.connect(self.show_details)
        layout.addWidget(QLabel("Records (Double click for details):"))
        layout.addWidget(self.list_widget)

        
        btn_layout = QHBoxLayout()
        
        btn_export = QPushButton("Export")
        btn_export.clicked.connect(self.export_records)
        btn_layout.addWidget(btn_export)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def export_records(self):
        try:
            # Ask user for destination directory
            dest_dir = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
            if not dest_dir:
                return

            # Source: self.logs_folder (Saved Logs)
            # Destination: dest_dir/Saved Logs
            
            # Helper to ignore errors just in case
            import shutil
            
            target_path = os.path.join(dest_dir, "Saved Logs")
            
            # If target already exists, maybe ask to overwrite or rename? 
            # shutil.copytree requires dest to NOT exist usually, or dirs_exist_ok in Python 3.8+
            
            if os.path.exists(target_path):
                reply = QMessageBox.question(self, "Overwrite?", 
                                             f"The folder '{target_path}' already exists. Overwrite contents?",
                                             QMessageBox.Yes | QMessageBox.No)
                if reply == QMessageBox.No: return
                
                # dirs_exist_ok=True is available in Python 3.8+
                shutil.copytree(self.logs_folder, target_path, dirs_exist_ok=True)
            else:
                 shutil.copytree(self.logs_folder, target_path)

            QMessageBox.information(self, "Success", f"Records exported to:\n{target_path}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export: {e}")

    def refresh_list(self):
        self.list_widget.clear()
        for name in self.records.keys():
            self.list_widget.addItem(name)

    def show_details(self, item):
        name = item.text()
        data = self.records.get(name)
        if not data: return
        
        # New Custom Dialog
        detail_dlg = RecordDetailsDialog(name, data, self)
        detail_dlg.exec_()
        
        # After closing detail dialog, refresh list in case of deletion
        self.refresh_list()
        
    def delete_record(self, name):
        if name in self.records:
            del self.records[name]
            # Call save on parent (NeoAgroApp)
            if hasattr(self.parent(), 'save_records_to_disk'):
                self.parent().save_records_to_disk()
            self.refresh_list()
            
    def go_to_area(self, record_data):
        self.close() # Close records dialog
        if hasattr(self.parent(), 'load_saved_location'):
            self.parent().load_saved_location(record_data)
            # Fix: Ensure main window comes to foreground
            self.parent().raise_()
            self.parent().activateWindow()


class RecordDetailsDialog(QDialog):
    def __init__(self, record_name, record_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{record_name} Analysis Report")
        self.resize(450, 550)
        self.record_name = record_name
        self.record_data = record_data
        self.parent_dialog = parent # RecordsDialog instance
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # 1. Info Text
        detail_text = f"--- {record_name} Details ---\n\n"
        detail_text += f"Date: {record_data.get('date', 'N/A')}\n"
        detail_text += f"Health Score: {record_data.get('health_score', 'N/A')}\n"
        detail_text += f"Stage: {record_data.get('stage', 'N/A')}\n\n"
        detail_text += "[ INDEX VALUES ]\n"
        for k, v in record_data.get('indices', {}).items():
            detail_text += f"• {k}: {v}\n"
        detail_text += "\n[ LAND CLASSIFICATION ]\n"

        for k, v in record_data.get('classification', {}).items():
            if isinstance(v, (int, float)):
                detail_text += f"• {k}: %{v:.1f}\n"

        txt = QTextEdit()
        txt.setReadOnly(True)
        txt.setText(detail_text)
        txt.setFont(QFont("Consolas", 10))
        layout.addWidget(txt)
        
        # 2. Action Buttons (Grid or HBox)
        btn_layout = QHBoxLayout()
        
        # A. Back
        btn_back = QPushButton("Back")
        btn_back.clicked.connect(self.close)
        
        # B. Delete
        btn_delete = QPushButton("Delete")
        btn_delete.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold;")
        btn_delete.clicked.connect(self.delete_me)
        
        # C. Go to Area
        btn_go = QPushButton("Go to Area")
        btn_go.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold;")
        btn_go.clicked.connect(self.go_to_area)
        
        btn_layout.addWidget(btn_back)
        btn_layout.addStretch()
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_go)
        
        layout.addLayout(btn_layout)
        
    def delete_me(self):
        # Confirmation (English as requested)
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Confirm Deletion")
        msg_box.setText(f"Are you sure you want to delete the record '{self.record_name}'?")
        msg_box.setIcon(QMessageBox.Warning)
        
        btn_yes = msg_box.addButton("Delete", QMessageBox.DestructiveRole) 
        btn_cancel = msg_box.addButton("Cancel", QMessageBox.RejectRole)
        
        msg_box.exec_()
        
        if msg_box.clickedButton() == btn_yes:
            # Call parent to delete logic
            if self.parent_dialog and hasattr(self.parent_dialog, 'delete_record'):
                self.parent_dialog.delete_record(self.record_name)
            self.close()

    def go_to_area(self):
        if self.parent_dialog and hasattr(self.parent_dialog, 'go_to_area'):
            self.parent_dialog.go_to_area(self.record_data)
        self.close()


# --- NEW CLASSES: COMPARISON MODULE ---

class ComparisonSelectionDialog(QDialog):
    """
    Dialog for user to select 2 records for comparison.
    Uses Checkboxes for UX.
    Double clicking also toggles selection.
    """

    def __init__(self, records, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Records for Comparison")
        self.resize(500, 450)
        self.records = records
        self.selected_records = []

        layout = QVBoxLayout()
        self.setLayout(layout)

        lbl = QLabel("Select exactly 2 records to compare:")
        lbl.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(lbl)

        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.NoSelection)  # Managed by Checkbox
        self.populate_list()

        # Signals
        self.list_widget.itemChanged.connect(self.check_selection_count)
        self.list_widget.itemDoubleClicked.connect(self.toggle_check_on_double_click)

        layout.addWidget(self.list_widget)

        # Buttons
        btn_layout = QHBoxLayout()

        self.btn_compare = QPushButton("Compare")
        self.btn_compare.setEnabled(False)  # Disabled initially
        self.btn_compare.setStyleSheet("""
            QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 6px; }
            QPushButton:disabled { background-color: #B0BEC5; color: #555; }
        """)
        self.btn_compare.clicked.connect(self.run_comparison)

        btn_close = QPushButton("Close")
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
        """Toggle check state on double click"""
        if item.checkState() == Qt.Checked:
            item.setCheckState(Qt.Unchecked)
        else:
            item.setCheckState(Qt.Checked)

    def check_selection_count(self):
        """Counts selected items and manages button state"""
        checked_items = []
        for index in range(self.list_widget.count()):
            item = self.list_widget.item(index)
            if item.checkState() == Qt.Checked:
                checked_items.append(item.text())

        self.selected_records = checked_items

        # Enable button if exactly 2 are selected
        if len(checked_items) == 2:
            self.btn_compare.setEnabled(True)
            self.btn_compare.setText(f"Compare ({checked_items[0]} vs {checked_items[1]})")
        else:
            self.btn_compare.setEnabled(False)
            self.btn_compare.setText("Compare (Select 2 records)")

    def run_comparison(self):
        if len(self.selected_records) == 2:
            data1 = self.records[self.selected_records[0]]
            data2 = self.records[self.selected_records[1]]

            # Create data package
            comp_data = {
                "name1": self.selected_records[0],
                "data1": data1,
                "name2": self.selected_records[1],
                "data2": data2
            }

            # Open Report Screen
            report = ComparisonReportDialog(comp_data, self)
            report.exec_()


class ComparisonReportDialog(QDialog):
    """Screen Showing Comparison Results"""

    def __init__(self, comp_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Comparison Report: {comp_data['name1']} vs {comp_data['name2']}")
        self.resize(900, 600)
        self.data = comp_data

        layout = QVBoxLayout()
        self.setLayout(layout)

        # 1. Headers and General Info
        header_layout = QGridLayout()

        # Names
        lbl_n1 = QLabel(self.data['name1']);
        lbl_n1.setFont(QFont("Arial", 12, QFont.Bold));
        lbl_n1.setStyleSheet("color: #1565C0")
        lbl_n2 = QLabel(self.data['name2']);
        lbl_n2.setFont(QFont("Arial", 12, QFont.Bold));
        lbl_n2.setStyleSheet("color: #C62828")

        # Dates
        date1 = self.data['data1'].get('date', '-')
        date2 = self.data['data2'].get('date', '-')

        header_layout.addWidget(QLabel("Record Name:"), 0, 0);
        header_layout.addWidget(lbl_n1, 0, 1)
        header_layout.addWidget(QLabel("Record Name:"), 0, 2);
        header_layout.addWidget(lbl_n2, 0, 3)

        header_layout.addWidget(QLabel("Date:"), 1, 0);
        header_layout.addWidget(QLabel(date1), 1, 1)
        header_layout.addWidget(QLabel("Date:"), 1, 2);
        header_layout.addWidget(QLabel(date2), 1, 3)

        frame_header = QFrame();
        frame_header.setLayout(header_layout);
        frame_header.setStyleSheet("background-color: #f5f5f5; border-radius: 5px;")
        layout.addWidget(frame_header)

        # 2. Health Score Comparison
        h_layout = QHBoxLayout()

        score1 = float(self.data['data1'].get('health_score', 0))
        score2 = float(self.data['data2'].get('health_score', 0))
        diff_score = score2 - score1

        box1 = self.create_score_box(score1, self.data['data1'].get('stage', '-'))
        box2 = self.create_score_box(score2, self.data['data2'].get('stage', '-'))

        # Difference Box
        box_diff = QFrame();
        box_diff_l = QVBoxLayout();
        box_diff.setLayout(box_diff_l)
        lbl_diff_t = QLabel("Diff");
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

        # 3. Index Table (Side by Side)
        layout.addWidget(QLabel("Index Comparison"))
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Index", f"{self.data['name1']}", f"{self.data['name2']}", "Change"])
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

        # 4. Close Button
        btn_ok = QPushButton("Close")
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

        l.addWidget(QLabel("Health Score"));
        l.addWidget(l_score);
        l.addWidget(l_stage)
        frame.setStyleSheet("background-color: white; border: 1px solid #ccc; border-radius: 8px;")
        return frame


class DateSelectionDialog(QDialog):
    def __init__(self, candidates, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Date Selection")
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
        
        lbl = QLabel("Select the most suitable date for analysis:")
        lbl.setObjectName("TitleLabel")
        layout.addWidget(lbl)
        
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QAbstractItemView.SingleSelection)
        
        for cand in candidates:
            date_str = cand['date']
            cloud = cand['cloud']
            label_text = cand.get('label', 'CANDIDATE')
            
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
            tag_color = "#1976D2" if label_text == "BEFORE" else "#E64A19" # Blue for Before, Orange for After
            tag_lbl = QLabel(label_text)
            tag_lbl.setStyleSheet(f"background-color: {tag_color}; color: white; border-radius: 4px; padding: 4px 8px; font-weight: bold; font-size: 11px;")
            tag_lbl.setFixedWidth(60)
            tag_lbl.setAlignment(Qt.AlignCenter)
            
            # Date Info
            info_layout = QVBoxLayout()
            date_lbl = QLabel(date_str)
            date_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
            date_lbl.setStyleSheet("color: #333;")
            
            cloud_lbl = QLabel(f"Cloud Cover: %{cloud:.1f}")
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
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("CancelButton")
        btn_cancel.clicked.connect(self.reject)
        
        btn_ok = QPushButton("Select and Analyze")
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
        layout.addWidget(btn_close, alignment=Qt.AlignCenter)


class TestRecordsDialog(QDialog):
    def __init__(self, csv_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Test Records (CSV)")
        self.resize(1000, 600)
        self.csv_path = csv_path
        
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Header
        lbl = QLabel(f"Records File: {os.path.basename(csv_path)}")
        lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(lbl)
        
        # Table
        self.table = QTableWidget()
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.table)
        
        # Load Data
        self.load_csv()
        
        # Close Button
        # Actions
        btn_layout = QHBoxLayout()
        
        btn_delete = QPushButton("Delete Record")
        btn_delete.setStyleSheet("background-color: #D32F2F; color: white; font-weight: bold; padding: 5px 15px;")
        btn_delete.clicked.connect(self.delete_selected_record)

        # Go Area Button
        btn_go = QPushButton("Go Area")
        btn_go.setStyleSheet("background-color: #1976D2; color: white; font-weight: bold; padding: 5px 15px;")
        btn_go.clicked.connect(self.go_to_selected_area)
        
        btn_export = QPushButton("Export")
        btn_export.setStyleSheet("background-color: #FFA000; color: white; font-weight: bold; padding: 5px 15px;")
        btn_export.clicked.connect(self.export_csv)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.close)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_delete)
        btn_layout.addWidget(btn_go)
        btn_layout.addWidget(btn_export)
        btn_layout.addWidget(btn_close)
        
        layout.addLayout(btn_layout)

    def export_csv(self):
        try:
            # Ask user for destination file
            # Get default name from current file
            default_name = os.path.basename(self.csv_path)
            
            file_path, _ = QFileDialog.getSaveFileName(self, "Export CSV", default_name, "CSV Files (*.csv)")
            if not file_path:
                return

            import shutil
            shutil.copy(self.csv_path, file_path)
            
            QMessageBox.information(self, "Success", f"File exported successfully to:\n{file_path}")

        except Exception as e:
             QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")
        
    def load_csv(self):
        try:
            with open(self.csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader, None)
                
                if not headers:
                    self.table.setColumnCount(1)
                    self.table.setHorizontalHeaderLabels(["Empty File"])
                    return
                    
                self.table.setColumnCount(len(headers))
                self.table.setHorizontalHeaderLabels(headers)
                
                rows = list(reader)
                self.table.setRowCount(len(rows))
                
                for i, row in enumerate(rows):
                    for j, val in enumerate(row):
                        self.table.setItem(i, j, QTableWidgetItem(val))
                        
            self.table.resizeColumnsToContents()
                
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to read CSV: {e}")

    def delete_selected_record(self):
        # Get selected rows
        selected_rows = sorted(set(index.row() for index in self.table.selectedIndexes()), reverse=True)
        
        if not selected_rows:
            QMessageBox.warning(self, "No Selection", "Please select record(s) to delete.")
            return
            
        # Confirm
        msg = "Are you sure you want to delete this record?" if len(selected_rows) == 1 else f"Are you sure you want to delete {len(selected_rows)} records?"
        reply = QMessageBox.question(self, "Confirm Delete", 
                                     f"{msg}\nThis cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                # Read all lines
                with open(self.csv_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                
                # CSV file structure:
                # Line 0: Header
                # Line 1: Record 1 (Table Row 0)
                # ...
                
                # We interpret table row `r` as file line `r + 1`
                # Since we iterate reversed (highest index first), deleting lines won't affect lower indices
                
                lines_modified = False
                for row in selected_rows:
                    line_idx = row + 1
                    if line_idx < len(lines):
                        del lines[line_idx]
                        lines_modified = True
                        
                if lines_modified:
                    # Write back
                    with open(self.csv_path, 'w', encoding='utf-8') as f:
                        f.writelines(lines)
                        
                    # Update Table (also reverse order to avoid shifting issues)
                    for row in selected_rows:
                        self.table.removeRow(row)
                        
                    QMessageBox.information(self, "Success", "Records deleted.")
                else:
                    QMessageBox.warning(self, "Error", "Could not synchronize with file. Indices out of range.")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete records: {e}")

    def go_to_selected_area(self):
        selected_indexes = self.table.selectedIndexes()
        if not selected_indexes:
            QMessageBox.warning(self, "No Selection", "Please select a record to go to.")
            return
            
        # Get the row index (use the first selected row if multiple)
        row = selected_indexes[0].row()
        
        # Helper to get text from a column
        def get_item_text(header_name):
            for c in range(self.table.columnCount()):
                h = self.table.horizontalHeaderItem(c).text()
                if h == header_name:
                    item = self.table.item(row, c)
                    return item.text() if item else ""
            return ""

        # 1. Location
        loc_str = get_item_text("Location")
        if not loc_str:
             QMessageBox.warning(self, "Error", "Location column not found or empty.")
             return
             
        geometry = self.parse_location_string(loc_str)
        if not geometry:
             QMessageBox.warning(self, "Error", "Invalid location format.")
             return

        # 2. Dates & Mode
        # Extract raw strings from table
        t_mode_str = get_item_text("Time Mode")
        start_date_str = get_item_text("Start Date")
        end_date_str = get_item_text("End Date")
        
        # Determine Mode
        mode = "range"
        if "Single" in t_mode_str:
            mode = "single"
            
        # Helper: Convert DD.MM.YYYY -> YYYY-MM-DD
        def to_iso(d_str):
            if not d_str or d_str == "-" or d_str == "": return None
            try:
                if "." in d_str:
                    parts = d_str.split(".")
                    if len(parts) == 3:
                        return f"{parts[2]}-{parts[1]}-{parts[0]}"
                return d_str # Fail-safe (maybe already ISO)
            except:
                return d_str

        date1 = to_iso(start_date_str)
        date2 = to_iso(end_date_str)
        
        # Logic for Single Mode:
        # In RecordsDialog/gui.py, for single mode, 'specific_date' is key.
        # Usually user selects a start date in single mode which acts as the specific date.
        # But 'saved_test.csv' creates "Start Date" column from date_start widget.
        # So date1 is likely our specific date.
        
        specific_date = None
        if mode == "single":
            specific_date = date1
            # date2 might be empty or same, irrelevant for map worker in single mode if specific_date is set
            
        record_data = {
            "geometry": geometry,
            "analysis_params": {
                "mode": mode,
                "date1": date1,
                "date2": date2,
                "specific_date": specific_date
            }
        }
        
        # Call Parent Method
        if isinstance(self.parent(), QWidget) and hasattr(self.parent(), 'load_saved_location'):
            self.parent().load_saved_location(record_data)
            self.close() # Close dialog to see map
        else:
             QMessageBox.warning(self, "Error", "Cannot access main application.")


    def parse_location_string(self, loc_str):
        """
        Parses string format: "(Lat, Lon); (Lat, Lon)"
        Returns GeoJSON dict: {"type": "Polygon", "coordinates": [[[Lon, Lat], ...]]}
        """
        if not loc_str or not loc_str.startswith("("):
            return None
            
        try:
            # Remove parentheses and split by semicolon
            parts = loc_str.split(";")
            coords = []
            for p in parts:
                p = p.strip().replace("(", "").replace(")", "")
                if "," in p:
                    lat, lon = map(float, p.split(","))
                    # GeoJSON is [Lon, Lat]
                    coords.append([lon, lat])
            
            # Check if it's a polygon (more than 2 points) or point
            if len(coords) > 2:
                # Ensure closed ring for Polygon
                if coords[0] != coords[-1]:
                    coords.append(coords[0])
                return {
                    "type": "Polygon",
                    "coordinates": [coords]
                }
            elif len(coords) == 1:
                 return {
                    "type": "Point",
                    "coordinates": coords[0]
                }
            return None
        except Exception as e:
            print(f"Parsing error: {e}")
            return None
