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


def parse_rows(table):
  """Extracts gallon tiers and prices from a specific price table."""
  rows = []
  for row in table.find_all("tr"):
    cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
    if len(cols) >= 2 and any(char.isdigit() for char in cols[1]):
      # Avoid header or duplicate label rows
      if "Gallons" not in cols[0]:
        rows.append((cols[0], cols[1]))
  return rows


def scrape_prices():
  response = requests.get(URL, headers=HEADERS)
  if response.status_code != 200:
    print(f"Failed to fetch page: Status {response.status_code}")
    return

  soup = BeautifulSoup(response.content, "html.parser")
  today = datetime.date.today().strftime("%Y-%m-%d")

  cash_rows = []
  cc_rows = []

  # Find all table tags on the page
  tables = soup.find_all("table")

  for table in tables:
    text = table.text.lower()

    # Match exact Cash block without grabbing nested credit card tables
    if "cash prices" in text and "credit card prices" not in text and not cash_rows:
      cash_rows = parse_rows(table)
    elif "credit card prices" in text and not cc_rows:
      cc_rows = parse_rows(table)

    if cash_rows and cc_rows:
      break

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
    print(f"[{today}] Updated feed.xml and CSV without duplicates.")
  else:
    print("Could not locate price tables.")


if __name__ == "__main__":
  scrape_prices()
