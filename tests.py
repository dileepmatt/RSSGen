import os
import json
import tempfile
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

os.environ["BASE_SITE"] = "https://test.example.com"
os.environ["API_KEY"] = "testkey"

import config
config.DATA_DIR = tempfile.mkdtemp()
config.DATA_FILE = os.path.join(config.DATA_DIR, "data.json")

import store
import torznab
from scraper import build_paginated_urls
from server import app


def test_build_paginated_urls_category():
    urls = build_paginated_urls(["https://test.example.com/category/malayalam-featured"], pages=3)
    assert len(urls) == 3
    assert urls[0] == "https://test.example.com/category/malayalam-featured"
    assert urls[1] == "https://test.example.com/category/malayalam-featured/page/2"
    assert urls[2] == "https://test.example.com/category/malayalam-featured/page/3"
    print("PASS: test_build_paginated_urls_category")


def test_build_paginated_urls_movies_query():
    urls = build_paginated_urls(["https://test.example.com/movies?sort=featured"], pages=2)
    assert len(urls) == 2
    assert urls[0] == "https://test.example.com/movies?sort=featured"
    assert urls[1] == "https://test.example.com/movies/page/2?sort=featured"
    print("PASS: test_build_paginated_urls_movies_query")


def test_store_add_items_dedup():
    store.scraped_items = []
    store.seen_magnets = set()

    items = [
        {"title": "Movie A", "magnet": "magnet:?xt=urn:a", "link": "http://a", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Movie B", "magnet": "magnet:?xt=urn:b", "link": "http://b", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Movie A dup", "magnet": "magnet:?xt=urn:a", "link": "http://a", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]

    new_count, expired_count = store.add_items(items)
    assert new_count == 2
    assert len(store.scraped_items) == 2
    print("PASS: test_store_add_items_dedup")


def test_store_expiry():
    store.scraped_items = []
    store.seen_magnets = set()

    old_date = datetime.now(timezone.utc) - timedelta(weeks=5)
    items = [
        {"title": "Old Movie", "magnet": "magnet:?xt=urn:old", "link": "http://old", "size": 0, "date": old_date, "category": "2000"},
        {"title": "New Movie", "magnet": "magnet:?xt=urn:new", "link": "http://new", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]

    new_count, expired_count = store.add_items(items)
    assert new_count == 2
    assert expired_count == 1
    assert len(store.scraped_items) == 1
    assert store.scraped_items[0]["title"] == "New Movie"
    print("PASS: test_store_expiry")


def test_store_persistence():
    store.scraped_items = []
    store.seen_magnets = set()

    items = [
        {"title": "Persist Me", "magnet": "magnet:?xt=urn:persist", "link": "http://p", "size": 1234, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.add_items(items)

    assert os.path.exists(config.DATA_FILE)
    with open(config.DATA_FILE) as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["title"] == "Persist Me"

    store.scraped_items = []
    store.seen_magnets = set()
    store.load_data()
    assert len(store.scraped_items) == 1
    assert store.scraped_items[0]["title"] == "Persist Me"
    print("PASS: test_store_persistence")


def test_torznab_caps_xml():
    xml = torznab.caps_xml()
    assert '<?xml version="1.0"' in xml
    assert "Movies" in xml
    assert 'supportedParams="q"' in xml
    print("PASS: test_torznab_caps_xml")


def test_torznab_results_xml():
    items = [
        {"title": "Test & Movie <1>", "magnet": "magnet:?xt=urn:test&dn=foo", "link": "http://link", "size": 500, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    xml = torznab.results_xml(items)
    assert "&amp;" in xml
    assert "&lt;1&gt;" in xml
    assert "magnet:?xt=urn:test&amp;dn=foo" in xml
    print("PASS: test_torznab_results_xml")


def test_api_caps():
    with app.test_client() as client:
        resp = client.get("/api?t=caps&apikey=testkey")
        assert resp.status_code == 200
        assert b"Movies" in resp.data
    print("PASS: test_api_caps")


def test_api_bad_key():
    with app.test_client() as client:
        resp = client.get("/api?t=caps&apikey=wrong")
        assert resp.status_code == 401
    print("PASS: test_api_bad_key")


def test_api_search():
    store.seen_magnets = set()
    store.scraped_items = [
        {"title": "Malayalam Movie 2024 720p", "magnet": "magnet:?xt=urn:m1", "link": "http://m1", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Bollywood Film 2024 1080p", "magnet": "magnet:?xt=urn:m2", "link": "http://m2", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.seen_magnets = {"magnet:?xt=urn:m1", "magnet:?xt=urn:m2"}

    with app.test_client() as client:
        resp = client.get("/api?t=search&q=malayalam&apikey=testkey")
        assert resp.status_code == 200
        assert b"Malayalam Movie" in resp.data
        assert b"Bollywood" not in resp.data

        resp = client.get("/api?t=search&q=&apikey=testkey")
        assert resp.status_code == 200
        assert b"Malayalam" in resp.data
        assert b"Bollywood" in resp.data
    print("PASS: test_api_search")


def test_status_endpoint():
    with app.test_client() as client:
        resp = client.get("/status")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "items" in data
        assert "last_scrape" in data
    print("PASS: test_status_endpoint")


def test_build_paginated_urls_single_page():
    urls = build_paginated_urls(["https://test.example.com/category/tamil-featured"], pages=1)
    assert len(urls) == 1
    assert urls[0] == "https://test.example.com/category/tamil-featured"
    print("PASS: test_build_paginated_urls_single_page")


def test_build_paginated_urls_trailing_slash():
    urls = build_paginated_urls(["https://test.example.com/category/test/"], pages=2)
    assert urls[1] == "https://test.example.com/category/test/page/2"
    print("PASS: test_build_paginated_urls_trailing_slash")


def test_build_paginated_urls_empty():
    urls = build_paginated_urls([], pages=3)
    assert urls == []
    print("PASS: test_build_paginated_urls_empty")


def test_store_max_items_cap():
    store.scraped_items = []
    store.seen_magnets = set()

    items = [
        {"title": f"Movie {i}", "magnet": f"magnet:?xt=urn:{i}", "link": f"http://{i}", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"}
        for i in range(600)
    ]
    store.add_items(items)
    assert len(store.scraped_items) <= config.MAX_ITEMS
    print("PASS: test_store_max_items_cap")


def test_store_dedup_across_runs():
    store.scraped_items = []
    store.seen_magnets = set()

    batch1 = [
        {"title": "Movie A", "magnet": "magnet:?xt=urn:aaa", "link": "http://a", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Movie B", "magnet": "magnet:?xt=urn:bbb", "link": "http://b", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.add_items(batch1)

    batch2 = [
        {"title": "Movie A again", "magnet": "magnet:?xt=urn:aaa", "link": "http://a", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Movie C", "magnet": "magnet:?xt=urn:ccc", "link": "http://c", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    new_count, _ = store.add_items(batch2)
    assert new_count == 1
    assert len(store.scraped_items) == 3
    print("PASS: test_store_dedup_across_runs")


def test_store_empty_items():
    store.scraped_items = []
    store.seen_magnets = set()

    new_count, expired_count = store.add_items([])
    assert new_count == 0
    assert expired_count == 0
    assert len(store.scraped_items) == 0
    print("PASS: test_store_empty_items")


def test_store_load_corrupted_file():
    store.scraped_items = []
    store.seen_magnets = set()

    with open(config.DATA_FILE, "w") as f:
        f.write("not valid json{{{")

    store.load_data()
    assert store.scraped_items == []
    print("PASS: test_store_load_corrupted_file")


def test_store_newest_first():
    store.scraped_items = []
    store.seen_magnets = set()

    items = [
        {"title": "First", "magnet": "magnet:?xt=urn:first", "link": "http://1", "size": 0, "date": datetime.now(timezone.utc) - timedelta(hours=2), "category": "2000"},
    ]
    store.add_items(items)

    items2 = [
        {"title": "Second", "magnet": "magnet:?xt=urn:second", "link": "http://2", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.add_items(items2)

    assert store.scraped_items[0]["title"] == "Second"
    assert store.scraped_items[1]["title"] == "First"
    print("PASS: test_store_newest_first")


def test_api_search_multi_word():
    store.scraped_items = [
        {"title": "Malayalam Action Movie 2024 720p", "magnet": "magnet:?xt=urn:s1", "link": "http://s1", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Malayalam Romance 2024 1080p", "magnet": "magnet:?xt=urn:s2", "link": "http://s2", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
        {"title": "Telugu Action Movie 2024", "magnet": "magnet:?xt=urn:s3", "link": "http://s3", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.seen_magnets = {"magnet:?xt=urn:s1", "magnet:?xt=urn:s2", "magnet:?xt=urn:s3"}

    with app.test_client() as client:
        resp = client.get("/api?t=search&q=malayalam+action&apikey=testkey")
        assert b"Malayalam Action" in resp.data
        assert b"Romance" not in resp.data
        assert b"Telugu" not in resp.data
    print("PASS: test_api_search_multi_word")


def test_api_search_case_insensitive():
    store.scraped_items = [
        {"title": "UPPERCASE MOVIE Title", "magnet": "magnet:?xt=urn:upper", "link": "http://u", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.seen_magnets = {"magnet:?xt=urn:upper"}

    with app.test_client() as client:
        resp = client.get("/api?t=search&q=uppercase+movie&apikey=testkey")
        assert b"UPPERCASE MOVIE" in resp.data
    print("PASS: test_api_search_case_insensitive")


def test_api_search_limit():
    store.scraped_items = [
        {"title": f"Movie {i}", "magnet": f"magnet:?xt=urn:lim{i}", "link": f"http://l{i}", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"}
        for i in range(20)
    ]
    store.seen_magnets = {f"magnet:?xt=urn:lim{i}" for i in range(20)}

    with app.test_client() as client:
        resp = client.get("/api?t=search&q=&limit=5&apikey=testkey")
        assert resp.data.count(b"<item>") == 5
    print("PASS: test_api_search_limit")


def test_api_search_no_results():
    store.scraped_items = [
        {"title": "Some Movie", "magnet": "magnet:?xt=urn:none", "link": "http://n", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.seen_magnets = {"magnet:?xt=urn:none"}

    with app.test_client() as client:
        resp = client.get("/api?t=search&q=nonexistent&apikey=testkey")
        assert resp.status_code == 200
        assert b"<item>" not in resp.data
        assert b'total="0"' in resp.data
    print("PASS: test_api_search_no_results")


def test_api_movie_search_type():
    store.scraped_items = [
        {"title": "Test Film", "magnet": "magnet:?xt=urn:movie", "link": "http://m", "size": 0, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    store.seen_magnets = {"magnet:?xt=urn:movie"}

    with app.test_client() as client:
        resp = client.get("/api?t=movie&q=test&apikey=testkey")
        assert resp.status_code == 200
        assert b"Test Film" in resp.data
    print("PASS: test_api_movie_search_type")


def test_api_unknown_function():
    with app.test_client() as client:
        resp = client.get("/api?t=bogus&apikey=testkey")
        assert resp.status_code == 400
        assert b"Unknown function" in resp.data
    print("PASS: test_api_unknown_function")


def test_api_missing_apikey():
    with app.test_client() as client:
        resp = client.get("/api?t=caps")
        assert resp.status_code == 401
    print("PASS: test_api_missing_apikey")


def test_torznab_results_xml_empty():
    xml = torznab.results_xml([])
    assert 'total="0"' in xml
    assert "<item>" not in xml
    print("PASS: test_torznab_results_xml_empty")


def test_torznab_error_xml():
    xml = torznab.error_xml(100, "Bad key")
    assert 'code="100"' in xml
    assert "Bad key" in xml
    print("PASS: test_torznab_error_xml")


def test_torznab_results_xml_size():
    items = [
        {"title": "Big Movie", "magnet": "magnet:?xt=urn:big", "link": "http://big", "size": 1500000000, "date": datetime.now(timezone.utc), "category": "2000"},
    ]
    xml = torznab.results_xml(items)
    assert "<size>1500000000</size>" in xml
    assert 'length="1500000000"' in xml
    print("PASS: test_torznab_results_xml_size")


if __name__ == "__main__":
    test_build_paginated_urls_category()
    test_build_paginated_urls_movies_query()
    test_build_paginated_urls_single_page()
    test_build_paginated_urls_trailing_slash()
    test_build_paginated_urls_empty()
    test_store_add_items_dedup()
    test_store_expiry()
    test_store_persistence()
    test_store_max_items_cap()
    test_store_dedup_across_runs()
    test_store_empty_items()
    test_store_load_corrupted_file()
    test_store_newest_first()
    test_torznab_caps_xml()
    test_torznab_results_xml()
    test_torznab_results_xml_empty()
    test_torznab_error_xml()
    test_torznab_results_xml_size()
    test_api_caps()
    test_api_bad_key()
    test_api_missing_apikey()
    test_api_search()
    test_api_search_multi_word()
    test_api_search_case_insensitive()
    test_api_search_limit()
    test_api_search_no_results()
    test_api_movie_search_type()
    test_api_unknown_function()
    test_status_endpoint()
    print("\nAll tests passed!")
