
import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta

CACHE_FILE = os.path.join(os.getcwd(), 'analysis_cache.db')

class AnalysisCache:
    def __init__(self):
        self.conn = sqlite3.connect(CACHE_FILE, check_same_thread=False)
        self.create_table()

    def create_table(self):
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    key TEXT PRIMARY KEY,
                    data TEXT,
                    timestamp DATETIME
                )
            """)

    def _generate_key(self, geometry, date1, date2, mode, analysis_type):
        """
        Generates a unique hash key based on inputs.
        geometry: dict or ee.Geometry (we use str representation)
        """
        # Convert inputs to string for hashing
        raw_str = f"{str(geometry)}_{date1}_{date2}_{mode}_{analysis_type}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    def get(self, geometry, date1, date2, mode, analysis_type="area"):
        key = self._generate_key(geometry, date1, date2, mode, analysis_type)
        cursor = self.conn.cursor()
        cursor.execute("SELECT data, timestamp FROM results WHERE key = ?", (key,))
        row = cursor.fetchone()
        
        if row:
            data_json, timestamp_str = row
            # Optional: Check expiry (e.g. 24 hours)
            # stored_time = datetime.fromisoformat(timestamp_str)
            # if datetime.now() - stored_time > timedelta(hours=24):
            #     return None
            
            try:
                return json.loads(data_json)
            except:
                return None
        return None

    def set(self, geometry, date1, date2, mode, data, analysis_type="area"):
        key = self._generate_key(geometry, date1, date2, mode, analysis_type)
        
        # Serialize data (handle EE objects if any remain, but mostly we store dicts of numbers/strings)
        # We assume 'data' is the final 'stats' dict which is JSON serializable
        try:
            data_json = json.dumps(data)
            timestamp = datetime.now().isoformat()
            
            with self.conn:
                self.conn.execute("""
                    INSERT OR REPLACE INTO results (key, data, timestamp)
                    VALUES (?, ?, ?)
                """, (key, data_json, timestamp))
        except Exception as e:
            print(f"Cache Set Error: {e}")

    def clear_old(self, days=7):
        # Cleanup old entries
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        with self.conn:
            self.conn.execute("DELETE FROM results WHERE timestamp < ?", (cutoff,))

# Global instance
cache_manager = AnalysisCache()
