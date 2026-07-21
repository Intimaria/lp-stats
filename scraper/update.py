"""
Incremental update: fetch new bulletins from SIBOM and append to data files.
Designed to run daily in CI (GitHub Actions) or manually.
"""

import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from parse_bulletins import parse_bulletin
from extract_deep import (
    extract_adjudicacion_doc,
    extract_inmueble_doc,
    split_text_into_docs,
)

def _ensure_newline(f):
    """Guarantee the file ends with a newline before appending."""
    pos = f.seek(0, 2)
    if pos > 0:
        f.seek(pos - 1)
        if f.read(1) != "\n":
            f.write("\n")


BASE_URL = "https://sibom.slyt.gba.gob.ar"
CITY_ID = 66
HEADERS = {"User-Agent": "laplata-stats/0.1 civic-research (inti.tidball@mikroways.net)"}

DATA_DIR = Path(__file__).parent.parent / "data"
RECORDS_FILE = DATA_DIR / "records.jsonl"
ADJ_FILE = DATA_DIR / "adjudicaciones.jsonl"
IMM_FILE = DATA_DIR / "inmuebles.jsonl"


def get_known_ids():
    known = set()
    with open(RECORDS_FILE) as f:
        for line in f:
            r = json.loads(line)
            known.add(r["bulletin_id"])
    return known


def fetch_page(url, retries=3):
    for attempt in range(retries):
        time.sleep(1.5 + attempt * 2)
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            r.raise_for_status()
            return BeautifulSoup(r.text, "lxml")
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                print(f"  Timeout (intento {attempt + 1}/{retries}), reintentando...")
            else:
                raise
        except requests.exceptions.RequestException:
            raise


def fetch_recent_bulletins(known_ids, max_pages=10):
    """Fetch recent SIBOM pages, stopping when we hit already-known bulletins."""
    new = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/cities/{CITY_ID}?page={page}"
        print(f"Checking SIBOM page {page}...")
        soup = fetch_page(url)

        rows = soup.find_all("div", class_="bulletin")
        if not rows:
            break

        page_new = []
        for row in rows:
            title_el = row.find(class_="bulletin-title")
            date_el = row.find(class_="bulletin-date")
            form_el = row.find("form", class_="button_to")
            if not (title_el and date_el and form_el):
                continue
            import re
            m = re.search(r"(\d+)", title_el.get_text(strip=True))
            display_number = int(m.group(1)) if m else None
            action = form_el.get("action", "")
            m2 = re.search(r"/bulletins/(\d+)", action)
            if not m2:
                continue
            bulletin_id = int(m2.group(1))
            date_text = date_el.get_text(strip=True)

            if bulletin_id not in known_ids:
                page_new.append({"bulletin_id": bulletin_id, "display_number": display_number, "date": date_text})

        new.extend(page_new)

        if len(page_new) < len(rows):
            break  # hit known bulletins on this page, stop

    return new


def download_text(bulletin_id, tmp_dir):
    """Download PDF and extract text with pdftotext. Returns text or None."""
    pdf_path = tmp_dir / f"{bulletin_id}.pdf"
    txt_path = tmp_dir / f"{bulletin_id}.txt"

    url = f"{BASE_URL}/bulletins/{bulletin_id}.pdf"
    try:
        r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
        r.raise_for_status()
    except Exception as e:
        print(f"  Download failed: {e}")
        return None

    with open(pdf_path, "wb") as f:
        for chunk in r.iter_content(8192):
            f.write(chunk)

    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(txt_path)],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"  pdftotext failed for {bulletin_id}")
        return None

    return txt_path.read_text(encoding="utf-8", errors="replace")


def main():
    known_ids = get_known_ids()
    print(f"Already have {len(known_ids)} bulletins (max id: {max(known_ids)})")

    new_bulletins = fetch_recent_bulletins(known_ids)
    if not new_bulletins:
        print("No new bulletins. Nothing to do.")
        return

    print(f"\nFound {len(new_bulletins)} new bulletins to process")

    new_records = []
    new_adj = []
    new_imm = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)

        for b in sorted(new_bulletins, key=lambda x: x["bulletin_id"]):
            print(f"\nBulletin {b['bulletin_id']} ({b['date']})...")
            time.sleep(1)

            text = download_text(b["bulletin_id"], tmp_dir)
            if not text:
                continue

            meta = {"bulletin_id": b["bulletin_id"], "display_number": b["display_number"], "date": b["date"]}

            records = parse_bulletin(meta, text)
            new_records.extend(records)
            print(f"  {len(records)} records parsed")

            for block in split_text_into_docs(text):
                adj = extract_adjudicacion_doc(block, meta)
                if adj:
                    new_adj.append(adj)
                imm = extract_inmueble_doc(block, meta)
                if imm:
                    new_imm.append(imm)

    if new_records:
        with open(RECORDS_FILE, "a", encoding="utf-8") as f:
            _ensure_newline(f)
            for r in new_records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"\nAppended {len(new_records)} records → {RECORDS_FILE}")

    if new_adj:
        with open(ADJ_FILE, "a", encoding="utf-8") as f:
            _ensure_newline(f)
            for a in new_adj:
                f.write(json.dumps(a, ensure_ascii=False) + "\n")
        print(f"Appended {len(new_adj)} adjudicaciones")

    if new_imm:
        with open(IMM_FILE, "a", encoding="utf-8") as f:
            _ensure_newline(f)
            for i in new_imm:
                f.write(json.dumps(i, ensure_ascii=False) + "\n")
        print(f"Appended {len(new_imm)} inmuebles")

    print("\nDone.")


if __name__ == "__main__":
    main()
