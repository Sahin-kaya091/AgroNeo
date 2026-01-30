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
        "ac51d50a4f4b6d748b8c__mypyc"
    ],

    # 2. Dahil edilen dosyalar
    "include_files": [
        ("utils.py", "utils.py"),
        ("worker.py", "worker.py"),
        ("gui.py", "gui.py"),
        ("dialogs.py", "dialogs.py"),
        ("Yetkilendirme.py", "Yetkilendirme.py"),
        # Varsa resimlerinizi buraya ekleyin: ("logo.png", "logo.png"),
    ],

    # 3. Hariç tutulanlar (Sorunlu modülü buraya ekledik!)
    "excludes": [
        "tkinter",
        "unittest",
        "PyQt5.QtQml"
          # <--- BU SATIR HATAYI ÇÖZECEK
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
#     base = "Win32GUI"

setup(
    name="AdvancedAgroNeo",
    version="1.0",
    description="Advanced Agro Neo Application",
    options={"build_exe": build_exe_options},
    executables=[Executable("run.py", base=base, target_name="AdvancedAgroNeo.exe")]
)