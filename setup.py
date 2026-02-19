import sys
from cx_Freeze import setup, Executable

# --- AYARLAR ---

build_exe_options = {
    # 1. Gerekli paketler
    "packages": [
        "os", "sys",
        "ee",
        "geemap", "folium",
        "branca", "jinja2",
        "PyQt5",
        "numpy", "bqplot",
        "googleapiclient",
        "google_auth_httplib2",
        "requests",
        "urllib3",
        "http",
        "ssl",
        "uuid",
        "json",
        "pydoc",
        "webbrowser",
        "xml",
        "email",
        "geopy",
        "matplotlib",
        "idna",
        "certifi",
        "charset_normalizer",
        "shapely",
        "simplejson",
        # --- EKLENEN YENİ PAKETLER ---
        "pandas",       # Veri analizi için kritik
        "shutil",       # Dosya/Klasör kopyalama (Export için)
        "csv",          # CSV işlemleri
        "shapefile",    # pyshp (Shapefile desteği için gerekebilir)
        # Matplotlib Backend'i açıkça belirtmek gerekebilir
        "matplotlib.backends.backend_qt5agg", 
        "ac51d50a4f4b6d748b8c__mypyc" # Kullanıcının orijinal listesinde vardı, koruyoruz.
    ],

    # 2. Dahil edilen dosyalar
    "include_files": [
        ("utils.py", "utils.py"),
        ("worker.py", "worker.py"),
        ("gui.py", "gui.py"),
        ("dialogs.py", "dialogs.py"),
        ("Yetkilendirme.py", "Yetkilendirme.py"),
        ("weather_service.py","weather_service.py"),
        ("cache_utils.py","cache_utils.py"),
        ("database.py","database.py"),
        ("debug_map.py","debug_map.py"),
        ("geo_utils.py","geo_utils.py"),
        ("historical_analysis.py","historical_analysis.py"),
        ("main.py","main.py"),
        ("map_utils.py","map_utils.py"),
        ("result_utils.py","result_utils.py")
        # Varsa resimlerinizi buraya ekleyin: ("logo.png", "logo.png"),
    ],

    # 3. Hariç tutulanlar
    "excludes": [
        "tkinter",
        "unittest",
        "PyQt5.QtQml"
    ],

    # 4. Gereksiz DLL uyarılarını susturmak için
    "bin_excludes": [
        "libpq.dll",
        "api-ms-win-core-path-l1-1-0.dll",
        "api-ms-win-core-winrt-l1-1-0.dll",
        "api-ms-win-crt-conio-l1-1-0.dll",
    ],

    "include_msvcr": True
}

# Hataları görmek için konsol penceresini açık bırakıyoruz (base = None)
base = None
# if sys.platform == "win32":
#     base = "Win32GUI" # Hata ayıklama bittiğinde bunu açabilirsiniz.

setup(
    name="AdvancedAgroNeo",
    version="1.1", # Version updated
    description="Advanced Agro Neo Application",
    options={"build_exe": build_exe_options},
    executables=[Executable("run.py", base=base, target_name="AdvancedAgroNeo.exe")]
)