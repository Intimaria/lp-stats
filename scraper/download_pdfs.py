"""
Step 2: Download all bulletin PDFs and extract text with pdftotext.
Skips already-downloaded files so it's safe to re-run.
"""

import json
import subprocess
import time
from pathlib import Path
import requests

BASE_URL = "https://sibom.slyt.gba.gob.ar"
DATA_DIR = Path(__file__).parent.parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
TEXT_DIR = DATA_DIR / "text"
BULLETINS_FILE = DATA_DIR / "bulletins.json"

HEADERS = {
    "User-Agent": "laplata-stats/0.1 civic-research (inti.tidball@mikroways.net)",
}

def download_pdf(bulletin_id, out_path):
    url = f"{BASE_URL}/bulletins/{bulletin_id}.pdf"
    r = requests.get(url, headers=HEADERS, timeout=60, stream=True)
    r.raise_for_status()
    with open(out_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

def extract_text(pdf_path, text_path):
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(text_path)],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0

def main():
    PDF_DIR.mkdir(parents=True, exist_ok=True)
    TEXT_DIR.mkdir(parents=True, exist_ok=True)

    bulletins = json.loads(BULLETINS_FILE.read_text())
    total = len(bulletins)

    for i, b in enumerate(bulletins, 1):
        bid = b["bulletin_id"]
        display = b["display_number"]
        date = b["date"]

        pdf_path = PDF_DIR / f"{bid}.pdf"
        text_path = TEXT_DIR / f"{bid}.txt"

        prefix = f"[{i:3d}/{total}] {display}º ({date}) id={bid}"

        if text_path.exists():
            print(f"{prefix}  ✓ already done")
            continue

        # Download
        if not pdf_path.exists():
            try:
                print(f"{prefix}  downloading...", end="", flush=True)
                download_pdf(bid, pdf_path)
                print(f" {pdf_path.stat().st_size // 1024}KB", end="")
                time.sleep(1.0)
            except Exception as e:
                print(f" FAILED: {e}")
                continue
        else:
            print(f"{prefix}  pdf exists, extracting...", end="", flush=True)

        # Extract text
        ok = extract_text(pdf_path, text_path)
        if ok:
            size = text_path.stat().st_size
            print(f" → {size // 1024}KB text")
        else:
            print(" pdftotext failed")

    print("\nDone.")
    done = sum(1 for b in bulletins if (TEXT_DIR / f"{b['bulletin_id']}.txt").exists())
    print(f"{done}/{total} bulletins have extracted text")

if __name__ == "__main__":
    main()
