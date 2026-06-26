from config import PORT


def caps_xml():
    return '<?xml version="1.0" encoding="UTF-8"?>\n<caps>\n  <server title="RSSGen Torznab" />\n  <limits max="100" default="50" />\n  <searching>\n    <search available="yes" supportedParams="q" />\n    <movie-search available="yes" supportedParams="q" />\n  </searching>\n  <categories>\n    <category id="2000" name="Movies">\n      <subcat id="2010" name="Movies/Foreign" />\n      <subcat id="2060" name="Movies/Bollywood" />\n    </category>\n  </categories>\n</caps>'


def error_xml(code, description):
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<error code="{code}" description="{description}" />'


def results_xml(items):
    entries = ""
    for item in items:
        pub_date = item["date"].strftime("%a, %d %b %Y %H:%M:%S %z")
        title_escaped = item["title"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        link_escaped = item["link"].replace("&", "&amp;")
        magnet_escaped = item["magnet"].replace("&", "&amp;")

        seeders = item.get("seeders", 5000)
        peers = item.get("peers", 5020)

        entries += f"""    <item>
      <title>{title_escaped}</title>
      <link>{link_escaped}</link>
      <guid>{magnet_escaped}</guid>
      <pubDate>{pub_date}</pubDate>
      <size>{item["size"]}</size>
      <enclosure url="{magnet_escaped}" length="{item["size"]}" type="application/x-bittorrent;x-scheme-handler/magnet" />
      <torznab:attr name="category" value="{item["category"]}" />
      <torznab:attr name="magneturl" value="{magnet_escaped}" />
      <torznab:attr name="seeders" value="{seeders}" />
      <torznab:attr name="peers" value="{peers}" />
      <torznab:attr name="downloadvolumefactor" value="0" />
      <torznab:attr name="uploadvolumefactor" value="1" />
      <torznab:attr name="flags" value="33" />
    </item>
"""

    xml = f'<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:torznab="http://torznab.com/schemas/2015/feed">\n'
    xml += '  <channel>\n'
    xml += '    <title>RSSGen Torznab</title>\n'
    xml += '    <description>Magnet links from movie sources</description>\n'
    xml += f'    <link>http://localhost:{PORT}</link>\n'
    xml += f'    <torznab:response offset="0" total="{len(items)}" />\n'
    xml += entries
    xml += '  </channel>\n'
    xml += '</rss>'
    return xml
