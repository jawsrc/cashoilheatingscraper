import datetime
import glob
import json
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


def update_history_json(today, cash_rows, cc_rows):
  """Appends daily minimum prices to a master history.json file for web charts."""
  history_file = "history.json"
  history_data = []

  if os.path.exists(history_file):
    try:
      with open(history_file, "r") as f:
        history_data = json.load(f)
    except Exception:
      history_data = []

  # Parse lowest cash and credit card prices
  lowest_cash = (
      min([float(price.replace("$", "").strip()) for _, price in cash_rows])
      if cash_rows
      else None
  )
  lowest_cc = (
      min([float(price.replace("$", "").strip()) for _, price in cc_rows])
      if cc_rows
      else None
  )

  # Overwrite today's entry if re-run on the same day
  history_data = [item for item in history_data if item.get("date") != today]

  history_data.append({
      "date": today,
      "lowest_cash": lowest_cash,
      "lowest_cc": lowest_cc,
  })

  # Keep entries sorted chronologically
  history_data.sort(key=lambda x: x["date"])

  with open(history_file, "w") as f:
    json.dump(history_data, f, indent=2)


def get_lowest_price_history(days=7):
  """Reads the master history.json file and returns the lowest price log for the last N days."""
  history_file = "history.json"
  if not os.path.exists(history_file):
    return []

  try:
    with open(history_file, "r") as f:
      history_data = json.load(f)

    # Grab the last `days` entries (newest last in list)
    recent_entries = history_data[-days:]
    history_logs = []

    # Format from newest to oldest for the feed
    for entry in reversed(recent_entries):
      date_str = entry.get("date", "")
      # Pick the lowest of cash or credit card price for that date
      prices = [
          p
          for p in [entry.get("lowest_cash"), entry.get("lowest_cc")]
          if p is not None
      ]
      if prices:
        min_price = min(prices)
        history_logs.append(f"{date_str}: ${min_price:.2f}")

    return history_logs
  except Exception as e:
    print(f"Error reading {history_file}: {e}")
    return []


def add_rss_item(channel, title, description, pub_date, guid_str, link_url):
  """Appends an individual <item> tag to the RSS feed."""
  item = ET.SubElement(channel, "item")
  ET.SubElement(item, "title").text = title
  ET.SubElement(item, "link").text = link_url
  ET.SubElement(item, "description").text = description

  guid = ET.SubElement(item, "guid", isPermaLink="false")
  guid.text = guid_str

  ET.SubElement(item, "pubDate").text = pub_date


def generate_rss(cash_rows, cc_rows, today):
  """Generates feed.xml containing Today's Prices and the 7-Day History Log."""
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

  # Item 2: 7-Day Lowest Price History Log
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
  """Extracts gallon tier and price columns from HTML tables."""
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
    # 1. Save detailed daily CSV
    combined = [("Cash", qty, price) for qty, price in cash_rows] + [
        ("Credit Card", qty, price) for qty, price in cc_rows
    ]
    df = pd.DataFrame(
        combined, columns=["Payment Type", "Gallon Tier", "Price"]
    )
    df["Date"] = today
    df.to_csv(f"prices_{today}.csv", index=False)

    # 2. Save master history.json for web dashboard
    update_history_json(today, cash_rows, cc_rows)

    # 3. Generate RSS feed for Protopage
    generate_rss(cash_rows, cc_rows, today)
    print(f"[{today}] Scrape complete: Saved CSV, history.json, and feed.xml")
  else:
    print("Could not locate price tables.")


if __name__ == "__main__":
  scrape_prices()
