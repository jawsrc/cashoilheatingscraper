import datetime
import xml.etree.ElementTree as ET
import pandas as pd
import requests
from bs4 import BeautifulSoup

URL = "https://www.cashheatingoil.com/oak_ridge_nj_oil_prices/07438"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML,"
        " like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def generate_rss(parsed_data, today):
  """Generates an RSS XML feed (feed.xml) from extracted oil price rows."""
  rss = ET.Element("rss", version="2.0")
  channel = ET.SubElement(rss, "channel")

  ET.SubElement(channel, "title").text = "Daily Heating Oil Prices - Oak Ridge"
  ET.SubElement(channel, "link").text = URL
  ET.SubElement(channel, "description").text = (
      f"Daily heating oil prices updated on {today}"
  )

  item = ET.SubElement(channel, "item")
  ET.SubElement(item, "title").text = f"Oil Prices for {today}"

  # Format extracted prices into readable text inside the RSS feed item
  body_lines = [f"{row[0]}: {row[1]}" for row in parsed_data]
  ET.SubElement(item, "description").text = "\n".join(body_lines)
  ET.SubElement(item, "pubDate").text = datetime.datetime.utcnow().strftime(
      "%a, %d %b %Y %H:%M:%S GMT"
  )

  tree = ET.ElementTree(rss)
  tree.write("feed.xml", encoding="utf-8", xml_declaration=True)


def scrape_prices():
  response = requests.get(URL, headers=HEADERS)
  if response.status_code != 200:
    print(f"Failed to fetch page: Status {response.status_code}")
    return

  soup = BeautifulSoup(response.content, "html.parser")
  today = datetime.date.today().strftime("%Y-%m-%d")

  rows = soup.find_all("tr")
  parsed_data = []

  for row in rows:
    cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
    if len(cols) == 2 and any(char.isdigit() for char in cols[1]):
      parsed_data.append(cols)

  if parsed_data:
    # 1. Save CSV
    df = pd.DataFrame(parsed_data, columns=["Gallon Tier", "Price"])
    df["Date"] = today
    file_name = f"prices_{today}.csv"
    df.to_csv(file_name, index=False)
    print(f"Successfully saved {file_name}")

    # 2. Save RSS Feed (feed.xml)
    generate_rss(parsed_data, today)
    print("Successfully generated feed.xml")
  else:
    print("No price data extracted.")


if __name__ == "__main__":
  scrape_prices()
