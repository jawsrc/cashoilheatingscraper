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


def add_rss_item(channel, title_text, pub_date, item_id, today):
  """Appends an individual <item> with a date-stamped GUID."""
  item = ET.SubElement(channel, "item")
  ET.SubElement(item, "title").text = title_text

  guid = ET.SubElement(item, "guid", isPermaLink="false")
  guid.text = f"oil-price-{today}-{item_id}"

  ET.SubElement(item, "pubDate").text = pub_date


def generate_rss(cash_rows, cc_rows, today):
  """Generates RSS feed where each line has a unique timestamp and GUID."""
  rss = ET.Element("rss", version="2.0")
  channel = ET.SubElement(rss, "channel")

  ET.SubElement(channel, "title").text = "Daily Heating Oil Prices - Oak Ridge"
  ET.SubElement(channel, "link").text = URL
  ET.SubElement(channel, "description").text = (
      f"Daily heating oil prices updated on {today}"
  )

  base_time = datetime.datetime.now(datetime.timezone.utc)
  item_counter = 0

  # 1. Cash Prices Section
  if cash_rows:
    item_time = (base_time + datetime.timedelta(seconds=item_counter)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    add_rss_item(channel, "cash prices", item_time, item_counter, today)
    item_counter += 1

    for qty, price in cash_rows:
      item_time = (
          base_time + datetime.timedelta(seconds=item_counter)
      ).strftime("%a, %d %b %Y %H:%M:%S GMT")
      add_rss_item(channel, f"{qty}: {price}", item_time, item_counter, today)
      item_counter += 1

  # 2. Credit Card Prices Section
  if cc_rows:
    item_time = (base_time + datetime.timedelta(seconds=item_counter)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    add_rss_item(channel, "credit card prices", item_time, item_counter, today)
    item_counter += 1

    for qty, price in cc_rows:
      item_time = (
          base_time + datetime.timedelta(seconds=item_counter)
      ).strftime("%a, %d %b %Y %H:%M:%S GMT")
      add_rss_item(channel, f"{qty}\t{price}", item_time, item_counter, today)
      item_counter += 1

  tree = ET.ElementTree(rss)
  tree.write("feed.xml", encoding="utf-8", xml_declaration=True)


def extract_table_data(heading_element):
  """Finds the closest table right after a header element and extracts quantity/price rows."""
  if not heading_element:
    return []

  parent_tr = heading_element.find_parent("tr")
  if not parent_tr:
    return []

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

  cash_heading = soup.find(
      lambda tag: tag.name in ["td", "th", "font", "b"]
      and "cash prices" in tag.text.lower()
  )

  cc_heading = soup.find(
      lambda tag: tag.name in ["td", "th", "font", "b"]
      and "credit card prices" in tag.text.lower()
  )

  cash_rows = extract_table_data(cash_heading)
  cc_rows = extract_table_data(cc_heading)

  if cash_rows or cc_rows:
    combined = [("Cash", qty, price) for qty, price in cash_rows] + [
        ("Credit Card", qty, price) for qty, price in cc_rows
    ]
    df = pd.DataFrame(combined, columns=["Payment Type", "Gallon Tier", "Price"])
    df["Date"] = today
    df.to_csv(f"prices_{today}.csv", index=False)

    generate_rss(cash_rows, cc_rows, today)
    print(f"[{today}] Generated individual RSS items in feed.xml")
  else:
    print("Could not locate price tables.")


if __name__ == "__main__":
  scrape_prices()
