import sys
import os
import ee
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
        
        # Run Auth GUI
        # Yetkilendirme.authenticate_with_gui returns True/False based on our previous logic (if we updated it, check below)
        # Note: In Step 58, Yetkilendirme.py was NOT updated yet to return True/False reliably in all blocks, 
        # but the code I read had a "Modified" comment. 
        # Wait, the read tool showed: 
        # def authenticate_with_gui(): ... return True ... return False
        # So it DOES return boolean.
        
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
