"""
Step 1: Map all La Plata bulletin IDs from SIBOM.
Produces data/bulletins.json — the index of everything we'll scrape.
"""

import json
import time
import re
from pathlib import Path
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://sibom.slyt.gba.gob.ar"
CITY_ID = 66  # La Plata
OUT_FILE = Path(__file__).parent.parent / "data" / "bulletins.json"

HEADERS = {
    "User-Agent": "laplata-stats/0.1 civic-research (inti.tidball@mikroways.net)",
}

def fetch_page(url, delay=1.0):
    time.sleep(delay)
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    return BeautifulSoup(r.text, "lxml")

def parse_bulletin_row(row):
    """Extract (display_number, bulletin_id, date) from a bulletin row div."""
    title_el = row.find(class_="bulletin-title")
    date_el = row.find(class_="bulletin-date")
    form_el = row.find("form", class_="button_to")

    if not (title_el and date_el and form_el):
        return None

    # "1283º de La Plata" → 1283
    title_text = title_el.get_text(strip=True)
    m = re.search(r"(\d+)", title_text)
    display_number = int(m.group(1)) if m else None

    # "Publicado el 08/06/2026" → "08/06/2026"
    date_text = date_el.get_text(strip=True).replace("Publicado el", "").strip()

    # form action="/bulletins/15068" → 15068
    action = form_el.get("action", "")
    m = re.search(r"/bulletins/(\d+)", action)
    bulletin_id = int(m.group(1)) if m else None

    return {
        "display_number": display_number,
        "bulletin_id": bulletin_id,
        "date": date_text,
    }

def main():
    bulletins = []
    page = 1

    while True:
        url = f"{BASE_URL}/cities/{CITY_ID}?page={page}"
        print(f"Fetching page {page}: {url}")
        soup = fetch_page(url)

        rows = soup.find_all("div", class_="bulletin")
        if not rows:
            print(f"No bulletins on page {page}, stopping.")
            break

        for row in rows:
            entry = parse_bulletin_row(row)
            if entry:
                bulletins.append(entry)
                print(f"  {entry['display_number']}º  id={entry['bulletin_id']}  date={entry['date']}")

        # Check if there's a next page
        pagination = soup.find("ul", class_="pagination")
        if not pagination:
            break
        next_links = [a for a in pagination.find_all("a") if "»" in a.get_text()]
        if not next_links:
            break  # last page
        page += 1

    bulletins.sort(key=lambda x: x["bulletin_id"])
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(bulletins, indent=2, ensure_ascii=False))
    print(f"\nSaved {len(bulletins)} bulletins to {OUT_FILE}")
    if bulletins:
        print(f"Range: {bulletins[0]['date']} → {bulletins[-1]['date']}")

if __name__ == "__main__":
    main()
