import sys
from PyQt5.QtWidgets import QApplication

try:
    from gui import NeoAgroApp
    from utils import initialize_ee
except ImportError as e:
    print(f"\n[HATA] Gerekli kütüphaneler bulunamadı: {e}")
    print(f"[BİLGİ] Çalıştırılan Python Yolu: {sys.executable}")
    print("Lütfen bu Python ortamına kütüphaneleri yüklediğinizden veya IDE ayarlarından doğru Python yorumlayıcısını (Interpreter) seçtiğinizden emin olun.\n")
    print("Gerekli paketleri yüklemek için terminalde: pip install -r requirements.txt")
    sys.exit(1)

if __name__ == "__main__":
    # Earth Engine başlat
    initialize_ee()
    
    app = QApplication(sys.argv)
    window = NeoAgroApp()
    window.showMaximized()
    sys.exit(app.exec_())

def run_app():
    """External entry point for run.py"""
    initialize_ee()
    
    # Check if QApplication already exists (from Yetkilendirme)
    app = QApplication.instance()
    if not app:
        app = QApplication(sys.argv)
        
    window = NeoAgroApp()
    window.showMaximized()
    
    if app.exec_() != 0:
        sys.exit(1)

