import os
import logging
from logging.handlers import RotatingFileHandler

SCRAPE_INTERVAL = int(os.environ.get("SCRAPE_INTERVAL", 3600))
API_KEY = os.environ.get("API_KEY", "rssgen123")
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", 500))
BASE_SITE = os.environ.get("BASE_SITE", "https://www.5movierulz.house").rstrip("/")
PORT = int(os.environ.get("PORT", 6945))

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
DATA_FILE = os.path.join(DATA_DIR, "data.json")
LOG_FILE = os.path.join(DATA_DIR, "rssgen.log")

logger = logging.getLogger("rssgen")
logger.setLevel(logging.INFO)

file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(file_handler)

console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
logger.addHandler(console_handler)

CATEGORY_PATHS = [
    "/category/malayalam-featured",
    # "/category/bollywood-featured",
    # "/category/telugu-featured",
    # "/category/tamil-featured",
]
