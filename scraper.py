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


def generate_rss(cash_rows, cc_rows, today):
  """Generates formatted RSS XML feed with separate Cash and Credit Card sections."""
  rss = ET.Element("rss", version="2.0")
  channel = ET.SubElement(rss, "channel")

  ET.SubElement(channel, "title").text = "Daily Heating Oil Prices - Oak Ridge"
  ET.SubElement(channel, "link").text = URL
  ET.SubElement(channel, "description").text = (
      f"Daily heating oil prices updated on {today}"
  )

  item = ET.SubElement(channel, "item")
  ET.SubElement(item, "title").text = f"Oil Prices for {today}"

  description_lines = []

  if cash_rows:
    description_lines.append("cash prices")
    for qty, price in cash_rows:
      description_lines.append(f"{qty}: {price}")

  if cc_rows:
    if description_lines:
      description_lines.append("")  # Blank line separator
    description_lines.append("credit card prices")
    for qty, price in cc_rows:
      description_lines.append(f"{qty}: {price}")

  ET.SubElement(item, "description").text = "\n".join(description_lines)
  ET.SubElement(item, "pubDate").text = datetime.datetime.utcnow().strftime(
      "%a, %d %b %Y %H:%M:%S GMT"
  )

  tree = ET.ElementTree(rss)
  tree.write("feed.xml", encoding="utf-8", xml_declaration=True)


def extract_table_data(heading_element):
  """Finds the closest table right after a header element and extracts quantity/price rows."""
  if not heading_element:
    return []

  # Find the container/table immediately associated with this header
  parent_tr = heading_element.find_parent("tr")
  if not parent_tr:
    return []

  # Find the price rows table right below the header row
  next_table = parent_tr.find_next("table")
  if not next_table:
    return []

  data = []
  for row in next_table.find_all("tr"):
    cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
    if len(cols) >= 2 and any(char.isdigit() for char in cols[1]):
      if "Gallons" not in cols[0]:
        data.append((cols[0], cols[1]))

  return data


def scrape_prices():
  response = requests.get(URL, headers=HEADERS)
  if response.status_code != 200:
    print(f"Failed to fetch page: Status {response.status_code}")
    return

  soup = BeautifulSoup(response.content, "html.parser")
  today = datetime.date.today().strftime("%Y-%m-%d")

  # Find the first 'Cash Prices' header element
  cash_heading = soup.find(
      lambda tag: tag.name in ["td", "th", "font", "b"]
      and "cash prices" in tag.text.lower()
  )

  # Find the first 'Credit Card Prices' header element
  cc_heading = soup.find(
      lambda tag: tag.name in ["td", "th", "font", "b"]
      and "credit card prices" in tag.text.lower()
  )

  cash_rows = extract_table_data(cash_heading)
  cc_rows = extract_table_data(cc_heading)

  if cash_rows or cc_rows:
    # 1. Save CSV
    combined = [("Cash", qty, price) for qty, price in cash_rows] + [
        ("Credit Card", qty, price) for qty, price in cc_rows
    ]
    df = pd.DataFrame(combined, columns=["Payment Type", "Gallon Tier", "Price"])
    df["Date"] = today
    df.to_csv(f"prices_{today}.csv", index=False)

    # 2. Save RSS
    generate_rss(cash_rows, cc_rows, today)
    print(f"[{today}] Updated feed.xml and CSV cleanly.")
  else:
    print("Could not locate price tables.")


if __name__ == "__main__":
  scrape_prices()
