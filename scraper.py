import datetime
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from bs4 import BeautifulSoup


def generate_rss(parsed_data, today):
  rss = ET.Element("rss", version="2.0")
  channel = ET.SubElement(rss, "channel")

  ET.SubElement(channel, "title").text = "Daily Heating Oil Prices"
  ET.SubElement(channel, "link").text = (
      "https://cashheatingoil.com/oak_ridge_nj_oil_prices/07438"
  )
  ET.SubElement(channel, "description").text = (
      "Daily scraped prices for Oak Ridge, NJ"
  )

  item = ET.SubElement(channel, "item")
  ET.SubElement(item, "title").text = f"Oil Prices for {today}"

  # Format the table rows as text inside the RSS feed item
  body_text = "\n".join([f"{row[0]}: {row[1]}" for row in parsed_data])
  ET.SubElement(item, "description").text = body_text
  ET.SubElement(item, "pubDate").text = datetime.datetime.utcnow().strftime(
      "%a, %d %b %Y %H:%M:%S GMT"
  )

  tree = ET.ElementTree(rss)
  tree.write("feed.xml", encoding="utf-8", xml_declaration=True)
