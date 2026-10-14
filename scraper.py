import datetime
import glob
import os
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


def get_lowest_price_history(days=7):
  """Reads saved daily CSV files and extracts the lowest price for each of the last `days` days."""
  csv_files = sorted(glob.glob("prices_*.csv"))
  history = []

  # Process CSV files from newest to oldest
  for file_path in reversed(csv_files):
    try:
      df = pd.read_csv(file_path)
      if "Price" in df.columns and "Date" in df.columns:
        # Clean price column to extract numeric float values
        df["Price_Numeric"] = (
            df["Price"]
            .astype(str)
            .str.replace("$", "", regex=False)
            .str.strip()
            .astype(float)
        )
        min_row = df.loc[df["Price_Numeric"].idxmin()]
        date_str = str(min_row["Date"])
        min_price = f"${min_row['Price_Numeric']:.2f}"

        # Formats cleanly as 'YYYY-MM-DD: $X.XX' without extra details
        history.append(f"{date_str}: {min_price}")

        if len(history) == days:
          break
    except Exception as e:
      print(f"Error parsing {file_path}: {e}")

  return history

def add_rss_item(channel, title, description, pub_date, guid_str, link_url):
  """Helper function to create an RSS <item> tag with unique link and guid."""
  item = ET.SubElement(channel, "item")
  ET.SubElement(item, "title").text = title
  ET.SubElement(item, "link").text = link_url
  ET.SubElement(item, "description").text = description

  guid = ET.SubElement(item, "guid", isPermaLink="false")
  guid.text = guid_str

  ET.SubElement(item, "pubDate").text = pub_date

def generate_rss(cash_rows, cc_rows, today):
  """Generates RSS feed with distinct links, timestamps, and GUIDs for Protopage compatibility."""
  rss = ET.Element("rss", version="2.0")
  channel = ET.SubElement(rss, "channel")

  ET.SubElement(channel, "title").text = "Daily Heating Oil Prices - Oak Ridge"
  ET.SubElement(channel, "link").text = URL
  ET.SubElement(channel, "description").text = (
      f"Daily heating oil prices updated on {today}"
  )

  base_time = datetime.datetime.now(datetime.timezone.utc)

  # Item 1: Today's Full Price Breakdown
  parts = []
  if cash_rows:
    parts.append(
        "CASH: " + " • ".join([f"{qty}: {price}" for qty, price in cash_rows])
    )
  if cc_rows:
    parts.append(
        "CREDIT CARD: "
        + " • ".join([f"{qty}: {price}" for qty, price in cc_rows])
    )

  item1_desc = "  |  ".join(parts)
  item1_time = base_time.strftime("%a, %d %b %Y %H:%M:%S GMT")
  add_rss_item(
      channel,
      title=f"Today's Prices ({today})",
      description=item1_desc,
      pub_date=item1_time,
      guid_str=f"oil-price-{today}-today",
      link_url=f"{URL}#today-{today}",
  )

  # Item 2: 7-Day Lowest Price Log
  history_logs = get_lowest_price_history(days=7)
  if history_logs:
    item2_desc = "  •  ".join(history_logs)
    item2_time = (base_time - datetime.timedelta(seconds=60)).strftime(
        "%a, %d %b %Y %H:%M:%S GMT"
    )
    add_rss_item(
        channel,
        title="7-Day Lowest Price Log",
        description=item2_desc,
        pub_date=item2_time,
        guid_str=f"oil-price-{today}-history",
        link_url=f"{URL}#history-{today}",
    )

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
    df = pd.DataFrame(
        combined, columns=["Payment Type", "Gallon Tier", "Price"]
    )
    df["Date"] = today
    df.to_csv(f"prices_{today}.csv", index=False)

    generate_rss(cash_rows, cc_rows, today)
    print(
        f"[{today}] Generated feed.xml with today's breakdown and 7-day history"
        " log."
    )
  else:
    print("Could not locate price tables.")


if __name__ == "__main__":
  scrape_prices()
