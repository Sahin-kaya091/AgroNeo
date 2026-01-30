import requests
import uuid
import json
from datetime import datetime

class LicenseManager:
    def __init__(self):
        # Firebase Veritabanı URL'in (Sonunda / işareti olmasın)
        self.db_url = "https://trl-d-agroneo-default-rtdb.europe-west1.firebasedatabase.app/"
        # Bilgisayarın benzersiz ID'sini al (Mac Adresinden üretilir)
        self.user_id = str(uuid.getnode())

    def check_access(self):
        """
        Kullanıcının izni var mı kontrol eder.
        Dönüş: (True/False, Mesaj)
        """
        try:
            # 1. Kullanıcı veritabanında var mı bak
            response = requests.get(f"{self.db_url}/users/{self.user_id}.json")
            user_data = response.json()

            # 2. Kullanıcı yoksa oluştur (Yeni Kullanıcıya 5 Hak Ver)
            if user_data is None:
                new_user = {
                    "credits": 15,
                    "role": "user",  # admin veya user
                    "last_access": str(datetime.now())
                }
                requests.put(f"{self.db_url}/users/{self.user_id}.json", json=new_user)
                return True, "Yeni kullanıcı: 15 deneme hakkı tanımlandı."

            # 3. Admin kontrolü
            if user_data.get("role") == "admin":
                return True, "Admin girişi: Sınırsız erişim."

            # 4. Kredi kontrolü
            credits = user_data.get("credits", 0)
            if credits > 0:
                return True, f"Kalan hakkınız: {credits}"
            else:
                return False, "Deneme süreniz doldu. Lütfen yönetici ile iletişime geçin."

        except Exception as e:
            # İnternet yoksa veya hata varsa güvenli tarafta kalıp izin vermeyebilirsin
            # ya da offline mod için geçici izin verebilirsin.
            print(f"Lisans Hatası: {e}")
            return False, "Lisans sunucusuna bağlanılamadı."

    def decrement_credit(self):
        """
        Bir analiz yapıldığında krediyi 1 düşürür.
        """
        try:
            # Önce kullanıcıyı çek
            response = requests.get(f"{self.db_url}/users/{self.user_id}.json")
            user_data = response.json()

            if user_data and user_data.get("role") != "admin":
                current_credits = user_data.get("credits", 0)
                if current_credits > 0:
                    new_credits = current_credits - 1
                    requests.patch(f"{self.db_url}/users/{self.user_id}.json", json={"credits": new_credits})
        except Exception as e:
            print(f"Kredi düşme hatası: {e}")

    def get_user_id(self):
        return self.user_id