import requests
from datetime import datetime
from PyQt5.QtCore import QObject, pyqtSignal, QThread

class WeatherWorker(QThread):
    finished = pyqtSignal(dict)
    
    def __init__(self, lat, lon, start_date, end_date=None):
        super().__init__()
        self.lat = lat
        self.lon = lon
        self.start_date = start_date
        self.end_date = end_date

    def run(self):
        result = self.fetch_weather()
        self.finished.emit(result)

    def fetch_weather(self):
        try:
            # Open-Meteo Archive API
            url = "https://archive-api.open-meteo.com/v1/archive"
            
            # If dates are missing or invalid, fail gracefully
            if not self.start_date:
                return {"error": "No Date"}

            params = {
                "latitude": self.lat,
                "longitude": self.lon,
                "start_date": self.start_date,
                "end_date": self.end_date if self.end_date else self.start_date,
                "daily": "weathercode,temperature_2m_max,precipitation_sum",
                "timezone": "auto"
            }

            response = requests.get(url, params=params, timeout=10)
            if response.status_code != 200:
                print(f"Weather API Error: {response.text}")
                return {"error": "API Error"}
            
            data = response.json()
            
            if 'daily' not in data:
                return {"error": "No Data"}

            daily = data['daily']
            if not daily.get('temperature_2m_max'):
                return {"error": "Empty Data"}

            # Calculate Averages/Sums
            temps = [t for t in daily['temperature_2m_max'] if t is not None]
            precips = [p for p in daily['precipitation_sum'] if p is not None]
            codes = [c for c in daily['weathercode'] if c is not None]

            if not temps:
                return {"error": "No Data"}

            avg_temp = sum(temps) / len(temps)
            total_precip = sum(precips)
            
            # Most common weather code (simple approach)
            most_common_code = max(set(codes), key=codes.count) if codes else 0
            
            condition, icon = self.get_weather_desc(most_common_code)

            return {
                "error": None,
                "temp": f"{avg_temp:.1f}°C",
                "precip": f"{total_precip:.1f} mm",
                "condition": condition,
                "icon": icon
            }

        except Exception as e:
            print(f"Weather Fetch Exception: {e}")
            return {"error": str(e)}

    def get_weather_desc(self, code):
        # WMO Weather interpretation codes (WW)
        # 0: Clear sky
        # 1, 2, 3: Mainly clear, partly cloudy, and overcast
        # 45, 48: Fog
        # 51, 53, 55: Drizzle
        # 61, 63, 65: Rain
        # 71, 73, 75: Snow
        # 95: Thunderstorm
        
        if code == 0: return "Clear Sky", "☀️"
        if code in [1, 2]: return "Partly Cloudy", "⛅"
        if code == 3: return "Overcast", "☁️"
        if code in [45, 48]: return "Foggy", "🌫️"
        if code in [51, 53, 55]: return "Drizzle", "🌦️"
        if code in [61, 63, 65, 80, 81, 82]: return "Rainy", "🌧️"
        if code in [71, 73, 75, 85, 86]: return "Snowy", "❄️"
        if code >= 95: return "Thunderstorm", "⛈️"
        
        return "Unknown", "🌡️"
