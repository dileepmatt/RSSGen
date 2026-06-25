import os

SCRAPE_INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", 3600))
API_KEY = os.environ.get("API_KEY", "rssgen123")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", 500))
BASE_SITE = os.environ.get("BASE_SITE", "https://www.5movierulz.house").rstrip("/")
PORT = int(os.environ.get("PORT", 6945))

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "data.json")

CATEGORY_PATHS = [
    "/category/malayalam-featured",
    # "/category/bollywood-featured",
    # "/category/telugu-featured",
    # "/category/tamil-featured",
]
