import json
import re
import threading
from datetime import datetime, timezone, timedelta

from config import DATA_FILE, MAX_ITEMS, logger


def magnet_id(magnet_link):
    match = re.search(r'btih:([a-fA-F0-9]+)', magnet_link)
    return match.group(1).lower() if match else magnet_link

scraped_items = []
seen_magnets = set()
last_scrape_time = None
scrape_lock = threading.Lock()


def save_data():
    data = [
        {**item, "date": item["date"].isoformat()}
        for item in scraped_items
    ]
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)


def load_data():
    global scraped_items, seen_magnets
    import os
    if not os.path.exists(DATA_FILE):
        return
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        deduped = []
        for item in data:
            item["date"] = datetime.fromisoformat(item["date"])
            mid = magnet_id(item["magnet"])
            if mid not in seen_magnets:
                seen_magnets.add(mid)
                deduped.append(item)
        scraped_items = deduped
        if len(deduped) < len(data):
            logger.info(f"Removed {len(data) - len(deduped)} duplicates from disk.")
            save_data()
        logger.info(f"Loaded {len(scraped_items)} items from disk.")
    except Exception as e:
        logger.error(f"Failed to load data.json: {e}")


def add_items(items):
    global scraped_items, last_scrape_time
    with scrape_lock:
        new_count = 0
        for item in items:
            mid = magnet_id(item["magnet"])
            if mid not in seen_magnets:
                seen_magnets.add(mid)
                scraped_items.insert(0, item)
                new_count += 1

        cutoff = datetime.now(timezone.utc) - timedelta(weeks=4)
        expired = [i for i in scraped_items if i["date"] < cutoff]
        for r in expired:
            seen_magnets.discard(magnet_id(r["magnet"]))
        scraped_items = [i for i in scraped_items if i["date"] >= cutoff]

        if len(scraped_items) > MAX_ITEMS:
            removed = scraped_items[MAX_ITEMS:]
            for r in removed:
                seen_magnets.discard(magnet_id(r["magnet"]))
            scraped_items = scraped_items[:MAX_ITEMS]

        last_scrape_time = datetime.now(timezone.utc)
        save_data()

    return new_count, len(expired)
