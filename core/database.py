import requests
import uuid
import json
import os
from datetime import datetime, timedelta

class LicenseManager:
    def __init__(self):
        # Firebase Veritabanı URL'in (Sonunda / işareti olmasın)
        self.db_url = "https://trl-d-agroneo-default-rtdb.europe-west1.firebasedatabase.app/"
        # Kalıcı Kullanıcı ID Sistemi
        self.user_id = self.load_or_create_user_id()
        
        # Memory Cache
        self.cache_valid_until = None
        self.cached_response = None
        self.cached_credits = 0

    def load_or_create_user_id(self):
        """
        Kullanıcı ID'sini yerel bir dosyadan okur veya yoksa yeni oluşturur.
        Bu sayede MAC adresi değişse bile kullanıcı ID sabit kalır.
        """
        config_path = os.path.expanduser("~/.agroneo_id.json")
        
        # 1. Dosya varsa oku
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                    if 'user_id' in data:
                        return data['user_id']
            except Exception as e:
                print(f"Kimlik okuma hatası: {e}")

        # 2. Dosya yoksa veya okunamadıysa YENİ oluştur
        new_id = str(uuid.uuid4())
        try:
            with open(config_path, 'w') as f:
                json.dump({'user_id': new_id, 'created_at': str(datetime.now())}, f)
        except Exception as e:
            print(f"Kimlik kaydetme hatası: {e}")
            
        return new_id

    def check_access(self):
        """
        Checks if the user has permission.
        Returns: (True/False, Message)
        """
        # Cache Check (Valid for 5 minutes)
        if self.cached_response and self.cache_valid_until:
             if datetime.now() < self.cache_valid_until:
                 # Check credits locally
                 if self.cached_credits > 0:
                     return True, f"Remaining credits: {self.cached_credits} (Cached)"
                 else:
                     return False, "Trial period expired. (Cached)"

        try:
            # 1. Check if user exists in DB
            response = requests.get(f"{self.db_url}/users/{self.user_id}.json")
            user_data = response.json()

            # 2. Create if not exists (Give 15 credits to new user)
            if user_data is None:
                new_user = {
                    "credits": 15,
                    "role": "user",  # admin or user
                    "last_access": str(datetime.now())
                }
                requests.put(f"{self.db_url}/users/{self.user_id}.json", json=new_user)
                
                # Update Cache
                self.cached_credits = 15
                self.cached_response = True
                self.cache_valid_until = datetime.now() + timedelta(minutes=5)
                
                return True, "New User: 15 trial credits assigned."

            # 3. Admin Check
            if user_data.get("role") == "admin":
                self.cached_response = True
                self.cached_credits = 999
                self.cache_valid_until = datetime.now() + timedelta(minutes=60) # Admin cache longer
                return True, "Admin Access: Unlimited."

            # 4. Credit Check
            credits = user_data.get("credits", 0)
            
            # Update Cache
            self.cached_credits = credits
            self.cached_response = True
            self.cache_valid_until = datetime.now() + timedelta(minutes=5)
            
            if credits > 0:
                return True, f"Remaining credits: {credits}"
            else:
                return False, "Trial period expired. Please contact administrator."

        except Exception as e:
            # Fallback for connection issues
            print(f"License Error: {e}")
            # FALLBACK: Offline Mode (Allow Access)
            return True, "Server unreachable. Offline mode active."

    def decrement_credit(self):
        """
        Bir analiz yapıldığında krediyi 1 düşürür.
        """
        try:
            # Update local cache immediately for responsiveness
            if self.cached_credits > 0:
                self.cached_credits -= 1
            
            # Use request in background (or fire and forget logic? For now sync is ok as it's at end of analysis)
            # To avoid slow UI at end of analysis, we might want to thread this or trust local cache?
            # Let's keep it sync but optimize:
            
            # Only update DB if we have a valid user
            requests.patch(f"{self.db_url}/users/{self.user_id}.json", json={"credits": self.cached_credits})
            
        except Exception as e:
            print(f"Kredi düşme hatası: {e}")

    def get_user_id(self):
        return self.user_id