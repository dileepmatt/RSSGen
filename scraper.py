import gc
import re
import time
from datetime import datetime, timezone

from config import BASE_SITE, CATEGORY_PATHS, SCRAPE_INTERVAL, logger
import store as store_module
from store import add_items


BASE_URLS = [f"{BASE_SITE}{path}" for path in CATEGORY_PATHS]


def build_paginated_urls(base_urls, pages=3):
    source_urls = []
    for url in base_urls:
        url = url.strip()
        for page in range(1, pages + 1):
            if page == 1:
                source_urls.append(url)
            else:
                if "/movies?" in url or url.endswith("/movies"):
                    base_part = url.split("?")[0].rstrip('/')
                    query_part = url.split("?")[1] if "?" in url else ""
                    if query_part:
                        source_urls.append(f"{base_part}/page/{page}?{query_part}")
                    else:
                        source_urls.append(f"{base_part}/page/{page}")
                else:
                    source_urls.append(f"{url.rstrip('/')}/page/{page}")
    return source_urls


def scrape_magnets():
    from seleniumbase import Driver
    from bs4 import BeautifulSoup

    logger.info("Starting scrape...")
    driver = Driver(uc=True, headless=True)
    driver.set_page_load_timeout(30)

    source_urls = build_paginated_urls(BASE_URLS)
    movie_pattern = r'-20\d{2}-.*\.html$'

    try:
        movie_urls_pool = []
        for idx, source_url in enumerate(source_urls):
            logger.info(f"[{idx+1}/{len(source_urls)}] Index page: {source_url}")
            try:
                driver.get(source_url)
                time.sleep(3)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        href = BASE_SITE + href
                    if re.search(movie_pattern, href.lower()):
                        if 'dvdscr' not in href.lower() and href not in movie_urls_pool:
                            movie_urls_pool.append(href)
                del soup
            except Exception as e:
                logger.warning(f"Skipping {source_url}: {e}")

        logger.info(f"Found {len(movie_urls_pool)} movie pages")

        with store_module.scrape_lock:
            already_scraped = {item["link"] for item in store_module.scraped_items}

        for idx, movie_url in enumerate(movie_urls_pool):
            if movie_url in already_scraped:
                logger.info(f"[{idx+1}/{len(movie_urls_pool)}] Skipping (already scraped): {movie_url}")
                continue
            logger.info(f"[{idx+1}/{len(movie_urls_pool)}] Scraping: {movie_url}")
            try:
                driver.get(movie_url)
                time.sleep(3)
                movie_soup = BeautifulSoup(driver.page_source, 'html.parser')
                magnets = movie_soup.find_all('a', href=re.compile(r'^magnet:\?'))

                movie_items = []
                for magnet in magnets:
                    magnet_link = magnet['href']
                    if 'dvdscr' in magnet_link.lower():
                        continue

                    dn_match = re.search(r'dn=([^&]+)', magnet_link)
                    if dn_match:
                        file_name = dn_match.group(1).replace('%20', ' ').replace('%28', '(').replace('%29', ')')
                        clean_title = file_name.replace('www.5MovieRulz.software - ', '').replace('www.5MovieRulz.co - ', '').strip()
                        if clean_title.lower().endswith(('.mkv', '.mp4', '.torrent')):
                            clean_title = clean_title.rsplit('.', 1)[0]
                    else:
                        title_tag = movie_soup.find('h1') or movie_soup.find('h2')
                        base_title = title_tag.get_text(strip=True) if title_tag else "Unknown Movie"
                        quality_text = magnet.get_text(strip=True).replace('\U0001f9f2', '').replace('GET THIS TORRENT', '').strip()
                        clean_title = f"{base_title} [{quality_text}]"

                    clean_title = re.sub(r'\s*-?\s*ESub\b', '', clean_title, flags=re.IGNORECASE).strip()

                    size_match = re.search(r'xl=(\d+)', magnet_link)
                    size = int(size_match.group(1)) if size_match else 0

                    movie_items.append({
                        "title": clean_title,
                        "magnet": magnet_link,
                        "link": movie_url,
                        "size": size,
                        "date": datetime.now(timezone.utc),
                        "category": "2000",
                    })

                if movie_items:
                    add_items(movie_items)
                    logger.info(f"  Got {len(movie_items)} magnets, saved to disk")
                else:
                    logger.warning(f"  No magnets found, skipping: {movie_url}")
                del movie_soup
                gc.collect()
            except Exception as e:
                logger.error(f"Failed {movie_url}: {e}")

    finally:
        try:
            driver.quit()
        except:
            pass

    with store_module.scrape_lock:
        total = len(store_module.scraped_items)
    logger.info(f"Scrape complete. {total} total items in store.")


def scrape_loop():
    while True:
        try:
            scrape_magnets()
        except Exception as e:
            logger.error(f"Scrape loop error: {e}")
        time.sleep(SCRAPE_INTERVAL)
