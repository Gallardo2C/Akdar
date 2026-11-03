import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'water-refilling-system-secure-key-2026'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{os.path.join(BASE_DIR, "water_station.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # System Branding & Station Information
    SYSTEM_BRAND = "Water Refilling System"
    STATION_NAME = "Water Refilling System"
    STATION_SUBTITLE = "Commercial Station Management & Point of Sale"
    STATION_ADDRESS = "Poblacion Ward II, Minglanilla, Cebu, Philippines 6046"
    STATION_CONTACT = "+63 (032) 272-8819 / 0917-555-9283"
    STATION_EMAIL = "operations@waterrefillingsystem.com"
    RECEIPT_HEADER = "WATER REFILLING SYSTEM"
    RECEIPT_FOOTER = "Thank you for your business! Clean, pure, and safe water every day."
    
    # Official Minglanilla Barangays
    MINGLANILLA_BARANGAYS = [
        "Cadulawan",
        "Calajo-an",
        "Camp 7",
        "Camp 8",
        "Cuanos",
        "Guindaruhan",
        "Linao",
        "Lipata",
        "Manduang",
        "Pakigne",
        "Poblacion Ward I",
        "Poblacion Ward II",
        "Tubod",
        "Tulay",
        "Tungkil",
        "Tungkop",
        "Vito"
    ]
