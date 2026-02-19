import sys
import os
import ee

# Initialize Earth Engine at the very beginning to avoid hangs in env
try:
    ee.Initialize()
    EE_INITIALIZED = True
except Exception:
    EE_INITIALIZED = False

from PyQt5.QtWidgets import QApplication, QMessageBox

# Import modules directly to avoid subprocess issues in frozen exe
import Yetkilendirme
import main as app_main

def resource_path(relative_path):
    """ PyInstaller ile paketlenmiş dosya yollarını bulur """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def check_auth():
    """
    Google Earth Engine yetkilendirmesi olup olmadığını kontrol eder.
    """
    # If already initialized successfully at top level
    if EE_INITIALIZED:
        return True
    
    # Try initializing again if it failed previously
    try:
        ee.Initialize()
        return True
    except Exception:
        return False

def start():
    print("Sistem kontrol ediliyor...")

    # Auth check
    if check_auth():
        print("Earth Engine yetkilendirmesi bulundu.")
    else:
        print("Earth Engine yetkilendirmesi bulunamadı.")
        print("Yetkilendirme sihirbazı başlatılıyor...")
        
        success = Yetkilendirme.authenticate_with_gui()
        if not success:
            print("Yetkilendirme başarısız veya iptal edildi. Uygulama kapatılıyor.")
            sys.exit(0)
            
        print("Yetkilendirme başarılı.")

    print("Ana uygulama başlatılıyor...")
    try:
        app_main.run_app()
    except Exception as e:
        print(f"Uygulama hatası: {e}")
        # Show error in GUI if possible
        app = QApplication.instance()
        if not app: app = QApplication(sys.argv)
        QMessageBox.critical(None, "Kritik Hata", f"Uygulama başlatılamadı:\n{e}")

if __name__ == "__main__":
    start()
