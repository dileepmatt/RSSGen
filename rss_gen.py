import sys
import os

# 1. TRICK THE SYSTEM: Force stderr to ignore that specific WinError 6 on exit
class WinError6Suppressor:
    def __init__(self, original_stderr):
        self.original_stderr = original_stderr

    def write(self, message):
        # If the incoming error text contains the buggy traceback keywords, swallow it
        if "Exception ignored while calling deallocator" in message or "WinError 6" in message:
            return
        self.original_stderr.write(message)

    def flush(self):
        self.original_stderr.flush()

# Redirect standard error to our filter wrapper immediately
sys.stderr = WinError6Suppressor(sys.stderr)

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import re
from feedgen.feed import FeedGenerator

def scrape_deep_magnets():
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    
    driver = uc.Chrome(options=options, version_main=149)
    
    base_urls = [
        "https://www.5movierulz.house/category/malayalam-featured",
        # "https://www.5movierulz.house/category/bollywood-featured",
        # "https://www.5movierulz.house/category/telugu-featured/",
        # "https://www.5movierulz.house/category/tamil-featured",
        # "https://www.5movierulz.house/movies?sort=featured"
    ]
    
    source_urls = []
    for url in base_urls:
        url = url.strip()
        for page in range(1, 4):
            if page == 1:
                source_urls.append(url)
            else:
                if "/movies?" in url or url.endswith("/movies"):
                    base_part = url.split("?")[0].rstrip('/')
                    query_part = url.split("?")[1] if "?" in url else ""
                    if query_part:
                        paged_url = f"{base_part}/page/{page}?{query_part}"
                    else:
                        paged_url = f"{base_part}/page/{page}"
                else:
                    paged_url = f"{url.rstrip('/')}/page/{page}"
                source_urls.append(paged_url)

    fg = FeedGenerator()
    fg.title('MovieRulz Direct Magnet Feed')
    fg.link(href=base_urls[0])
    fg.description('Deep scraped magnet links for Jackett integration')
    
    try:
        movie_urls_pool = []
        movie_pattern = r'-20\d{2}-.*\.html$'
        
        print(f"Step 1: Harvesting movie links across {len(source_urls)} total index pages...")
        for idx, source_url in enumerate(source_urls):
            print(f"[{idx+1}/{len(source_urls)}] Gathering items from: {source_url}")
            try:
                driver.get(source_url)
                time.sleep(5)
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if href.startswith('/'):
                        href = "https://www.5movierulz.house".rstrip('/') + href
                    if re.search(movie_pattern, href.lower()):
                        if 'dvdscr' not in href.lower() and href not in movie_urls_pool:
                            movie_urls_pool.append(href)
            except Exception as page_err:
                print(f"Skipping index page {source_url} due to connection error: {page_err}")
                        
        print(f"\nTotal unique, non-DVDSCR movie pages collected in pool: {len(movie_urls_pool)}")
        print("---")
        
        print("Step 2: Deep scraping individual pages for magnets...")
        max_depth = min(len(movie_urls_pool), 5)
        
        for idx, movie_url in enumerate(movie_urls_pool[:max_depth]):
            print(f"[{idx+1}/{max_depth}] Deep scraping: {movie_url}")
            try:
                driver.get(movie_url)
                time.sleep(4)
                movie_soup = BeautifulSoup(driver.page_source, 'html.parser')
                magnets = movie_soup.find_all('a', href=re.compile(r'^magnet:\?'))
                
                for m_idx, magnet in enumerate(magnets):
                    magnet_link = magnet['href']
                    if 'dvdscr' in magnet_link.lower():
                        continue
                    
                    dn_match = re.search(r'dn=([^&]+)', magnet_link)
                    if dn_match:
                        file_name = dn_match.group(1).replace('%20', ' ').replace('%28', '(').replace('%29', ')')
                        clean_title = file_name.replace('www.5MovieRulz.software - ', '').replace('www.5MovieRulz.co - ', '').strip()
                        if clean_title.lower().endswith(('.mkv', '.mp4', '.torrent')):
                            clean_title = clean_title.rsplit('.', 1)[0]
                        full_item_title = clean_title
                    else:
                        title_tag = movie_soup.find('h1') or movie_soup.find('h2')
                        base_title = title_tag.get_text(strip=True) if title_tag else "Unknown Movie"
                        quality_text = magnet.get_text(strip=True).replace('🧲', '').replace('GET THIS TORRENT', '').strip()
                        full_item_title = f"{base_title} [{quality_text}]"
                    
                    fe = fg.add_entry()
                    fe.title(full_item_title)
                    fe.link(href=magnet_link, rel='enclosure', type='application/x-bittorrent')
                    fe.id(magnet_link)
            except Exception as scrape_err:
                print(f"Failed to cleanly process content from {movie_url}: {scrape_err}")
        
        fg.rss_file('movierulz_magnets.xml')
        print("\nSuccess! 'movierulz_magnets.xml' is ready with deep-scraped links.")
        
    except Exception as e:
        print(f"Scraping routine failed: {e}")
        
    finally:
        # Standard release attempt
        try:
            driver.quit()
        except:
            pass

if __name__ == "__main__":
    scrape_deep_magnets()
    # Force close the stream cleanly right now before python tries to look up unallocated garbage
    print("Execution finalized cleanly.")
    os._exit(0)