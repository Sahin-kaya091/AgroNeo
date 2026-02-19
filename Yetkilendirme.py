
import ee
import os
import sys
import builtins
from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox


# GUI Input fonksiyonu aynı kalıyor
def gui_input(prompt=''):
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    text, ok = QInputDialog.getText(None, "Google Earth Engine Yetkilendirme",
                                    "Tarayıcıda açılan sayfadan kopyaladığınız Token'ı buraya yapıştırın:")
    if ok and text:
        return text.strip()
    return ""


def authenticate_with_gui():
    """
    Bu fonksiyon artık işlem sonucunu (True/False) döndürüyor.
    """
    print("Eski yetki dosyalari kontrol ediliyor...")
    credentials_path = os.path.expanduser("~/.config/earthengine/credentials")
    if os.path.exists(credentials_path):
        try:
            os.remove(credentials_path)
        except Exception:
            pass

    original_input = builtins.input
    try:
        builtins.input = gui_input
        # Yetkilendirme
        ee.Authenticate(auth_mode='notebook', force=True)

        # Eğer buraya kadar hata vermediyse başarılıdır
        ee.Initialize()  # Test etmek için initialize et

        # Başarılı mesajı
        app = QApplication.instance()
        if app is None: app = QApplication(sys.argv)
        QMessageBox.information(None, "Başarılı", "Yetkilendirme Başarılı! Uygulama başlatılıyor...")
        return True  # BAŞARILI DÖN

    except Exception as e:
        app = QApplication.instance()
        if app is None: app = QApplication(sys.argv)
        QMessageBox.critical(None, "Hata", f"Yetkilendirme hatası:\n{str(e)}")
        return False  # BAŞARISIZ DÖN

    finally:
        builtins.input = original_input


if __name__ == "__main__":
    authenticate_with_gui()