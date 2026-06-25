import re
import time
from datetime import datetime, timezone

from config import BASE_SITE, CATEGORY_PATHS, SCRAPE_INTERVAL
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
    import undetected_chromedriver as uc
    from bs4 import BeautifulSoup

    print(f"[{datetime.now()}] Starting scrape...")
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    driver = uc.Chrome(options=options)

    source_urls = build_paginated_urls(BASE_URLS)
    items = []
    movie_pattern = r'-20\d{2}-.*\.html$'

    try:
        movie_urls_pool = []
        for idx, source_url in enumerate(source_urls):
            print(f"  [{idx+1}/{len(source_urls)}] Index page: {source_url}")
            try:
                driver.get(source_url)
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        href = BASE_SITE + href
                    if re.search(movie_pattern, href.lower()):
                        if 'dvdscr' not in href.lower() and href not in movie_urls_pool:
                            movie_urls_pool.append(href)
            except Exception as e:
                print(f"  Skipping {source_url}: {e}")

        print(f"  Found {len(movie_urls_pool)} movie pages")

        for idx, movie_url in enumerate(movie_urls_pool):
            print(f"  [{idx+1}/{len(movie_urls_pool)}] Scraping: {movie_url}")
            try:
                driver.get(movie_url)
                time.sleep(4)
                movie_soup = BeautifulSoup(driver.page_source, 'html.parser')
                magnets = movie_soup.find_all('a', href=re.compile(r'^magnet:\?'))

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

                    size_match = re.search(r'xl=(\d+)', magnet_link)
                    size = int(size_match.group(1)) if size_match else 0

                    items.append({
                        "title": clean_title,
                        "magnet": magnet_link,
                        "link": movie_url,
                        "size": size,
                        "date": datetime.now(timezone.utc),
                        "category": "2000",
                    })
            except Exception as e:
                print(f"  Failed {movie_url}: {e}")

    finally:
        try:
            driver.quit()
        except:
            pass

    new_count, expired_count = add_items(items)
    print(f"[{datetime.now()}] Scrape complete. {new_count} new, {expired_count} expired, {len(items)} scraped.")


def scrape_loop():
    while True:
        try:
            scrape_magnets()
        except Exception as e:
            print(f"Scrape loop error: {e}")
        time.sleep(SCRAPE_INTERVAL)
