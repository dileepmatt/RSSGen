from config import PORT


def caps_xml():
    return """<?xml version="1.0" encoding="UTF-8"?>
<caps>
  <server title="RSSGen Torznab" />
  <limits max="100" default="50" />
  <searching>
    <search available="yes" supportedParams="q" />
    <movie-search available="yes" supportedParams="q" />
  </searching>
  <categories>
    <category id="2000" name="Movies">
      <subcat id="2010" name="Movies/Foreign" />
      <subcat id="2060" name="Movies/Bollywood" />
    </category>
  </categories>
</caps>"""


def error_xml(code, description):
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<error code="{code}" description="{description}" />"""


def results_xml(items):
    entries = ""
    for item in items:
        pub_date = item["date"].strftime("%a, %d %b %Y %H:%M:%S %z")
        title_escaped = item["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        link_escaped = item["link"].replace("&", "&amp;")
        magnet_escaped = item["magnet"].replace("&", "&amp;")

        entries += f"""    <item>
      <title>{title_escaped}</title>
      <link>{link_escaped}</link>
      <guid>{magnet_escaped}</guid>
      <pubDate>{pub_date}</pubDate>
      <size>{item["size"]}</size>
      <enclosure url="{magnet_escaped}" length="{item["size"]}" type="application/x-bittorrent;x-scheme-handler/magnet" />
      <torznab:attr name="category" value="{item["category"]}" />
      <torznab:attr name="magneturl" value="{magnet_escaped}" />
    </item>
"""

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:torznab="http://torznab.com/schemas/2015/feed">
  <channel>
    <title>RSSGen Torznab</title>
    <description>Magnet links from movie sources</description>
    <link>http://localhost:{PORT}</link>
    <response offset="0" total="{len(items)}" />
{entries}  </channel>
</rss>"""
