# import ee
# import os
#
# print("Eski yetki dosyalari kontrol ediliyor...")
#
# # 1. Bilgisayardaki eski yetki dosyasini bul ve sil (Temiz kurulum için sart)
# # Windows'ta genelde C:\Users\Kullanici\.config\earthengine\credentials yolundadir.
# credentials_path = os.path.expanduser("~/.config/earthengine/credentials")
#
# if os.path.exists(credentials_path):
#     try:
#         os.remove(credentials_path)
#         print(f"Eski yetki dosyasi silindi: {credentials_path}")
#     except Exception as e:
#         print(f"Dosya silinemedi: {e}")
# else:
#     print("Eski yetki dosyasi bulunamadi, temiz.")
#
# print("-" * 30)
# print("LUTFEN DIKKAT: Tarayici acildiginda Token'i kopyalayip buraya yapistirin.")
# print("-" * 30)
#
# # 2. force=True komutu ile yetkilendirmeyi ZORLA
# try:
#     ee.Authenticate(auth_mode='notebook', force=False)
#     print("\nBASARILI! Google Earth Engine yetkilendirmesi tamamlandi.")
# except Exception as e:
#     print(f"\nHata olustu: {e}")

# import ee
# import os
# import sys
# import builtins
# from PyQt5.QtWidgets import QApplication, QInputDialog, QMessageBox
#
#
# def gui_input(prompt=''):
#     """
#     Python'ın standart input() fonksiyonunun yerine geçecek olan
#     GUI tabanlı input fonksiyonu.
#     """
#     # Halihazırda çalışan bir QApplication var mı kontrol et
#     app = QApplication.instance()
#     if app is None:
#         app = QApplication(sys.argv)
#
#     # Token giriş penceresini aç
#     text, ok = QInputDialog.getText(
#         None,
#         "Google Earth Engine Yetkilendirme",
#         "Tarayıcıda açılan sayfadan kopyaladığınız Token'ı buraya yapıştırın ve OK'e basın:"
#     )
#
#     if ok and text:
#         return text.strip()
#     else:
#         # Kullanıcı iptal ederse boş string döndür veya hata fırlat
#         return ""
#
#
# def authenticate_with_gui():
#     print("Eski yetki dosyalari kontrol ediliyor...")
#
#     # 1. Eski yetki dosyasını temizle
#     credentials_path = os.path.expanduser("~/.config/earthengine/credentials")
#     if os.path.exists(credentials_path):
#         try:
#             os.remove(credentials_path)
#             print(f"Eski yetki dosyasi silindi: {credentials_path}")
#         except Exception as e:
#             print(f"Dosya silinemedi: {e}")
#     else:
#         print("Eski yetki dosyasi bulunamadi, temiz.")
#
#     print("-" * 30)
#     print("Tarayıcı açılıyor... Lütfen Token'ı açılan pencereye giriniz.")
#     print("-" * 30)
#
#     # --- SİHİRLİ KISIM ---
#     # Python'ın orjinal input fonksiyonunu yedekle
#     original_input = builtins.input
#
#     try:
#         # input fonksiyonunu bizim yazdığımız gui_input ile değiştir
#         builtins.input = gui_input
#
#         # Earth Engine yetkilendirmesini başlat
#         # force=True: Yeniden yetkilendirmeyi zorlar
#         # auth_mode='notebook': Genelde token akışını tetiklemek için en uygun moddur
#         ee.Authenticate(auth_mode='notebook', force=True)
#
#         # Başarı mesajı (GUI)
#         app = QApplication.instance()
#         if app is None: app = QApplication(sys.argv)
#         QMessageBox.information(None, "Başarılı", "Google Earth Engine yetkilendirmesi başarıyla tamamlandı!")
#         print("\nBASARILI! Google Earth Engine yetkilendirmesi tamamlandi.")
#
#     except Exception as e:
#         # Hata mesajı (GUI)
#         app = QApplication.instance()
#         if app is None: app = QApplication(sys.argv)
#         QMessageBox.critical(None, "Hata", f"Yetkilendirme sırasında hata oluştu:\n{str(e)}")
#         print(f"\nHata olustu: {e}")
#
#     finally:
#         # Ne olursa olsun orjinal input fonksiyonunu geri yükle
#         # (Uygulamanın geri kalanının bozulmaması için çok önemli)
#         builtins.input = original_input
#
#
# if __name__ == "__main__":
#     authenticate_with_gui()

# Dosya Adı: Yetkilendirme.py
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