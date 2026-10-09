import datetime
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


def scrape_prices():
  response = requests.get(URL, headers=HEADERS)
  if response.status_code != 200:
    print(f"Failed to fetch page: Status {response.status_code}")
    return

  soup = BeautifulSoup(response.content, "html.parser")
  today = datetime.date.today().strftime("%Y-%m-%d")

  # Find all tables containing oil options
  rows = soup.find_all("tr")
  parsed_data = []

  for row in rows:
    cols = [ele.text.strip() for ele in row.find_all(["td", "th"])]
    if len(cols) == 2 and any(char.isdigit() for char in cols[1]):
      parsed_data.append(cols)

  if parsed_data:
    df = pd.DataFrame(parsed_data, columns=["Gallon Tier", "Price"])
    df["Date"] = today

    # Save daily snapshot
    file_name = f"prices_{today}.csv"
    df.to_csv(file_name, index=False)
    print(f"Successfully saved {file_name}")
  else:
    print("No price data extracted.")


if __name__ == "__main__":
  scrape_prices()
