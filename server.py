import threading

from flask import Flask, request, Response

from config import API_KEY, SCRAPE_INTERVAL, PORT, logger
import store
from scraper import scrape_loop
from torznab import caps_xml, error_xml, results_xml

app = Flask(__name__)


@app.route("/api", methods=["GET"])
def torznab_api():
    apikey = request.args.get("apikey", "")
    if apikey != API_KEY:
        return Response(error_xml(100, "Incorrect API Key"), mimetype="application/xml", status=401)

    t = request.args.get("t", "")

    if t == "caps":
        return Response(caps_xml(), mimetype="application/xml")

    if t in ("search", "movie"):
        query = request.args.get("q", "").lower().strip()
        limit = int(request.args.get("limit", 50))

        with store.scrape_lock:
            results = list(store.scraped_items)

        if query:
            query_terms = query.split()
            results = [
                item for item in results
                if all(term in item["title"].lower() for term in query_terms)
            ]

        results = results[:limit]
        return Response(results_xml(results), mimetype="application/xml")

    return Response(error_xml(201, "Unknown function"), mimetype="application/xml", status=400)


@app.route("/status", methods=["GET"])
def status():
    with store.scrape_lock:
        count = len(store.scraped_items)
        last = store.last_scrape_time.isoformat() if store.last_scrape_time else "never"
    return {"items": count, "last_scrape": last, "interval_seconds": SCRAPE_INTERVAL}


if __name__ == "__main__":
    store.load_data()

    scrape_thread = threading.Thread(target=scrape_loop, daemon=True)
    scrape_thread.start()

    logger.info(f"Torznab server starting on http://localhost:{PORT}")
    logger.info(f"Add to Prowlarr/Jackett as: http://localhost:{PORT}/api  (API key: {API_KEY})")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
