"""
Step 3: Parse extracted bulletin text into structured records.
Produces data/records.jsonl — one JSON object per document item.

Each record:
  bulletin_id, bulletin_display, bulletin_date,
  doc_type (ordenanza|decreto|resolucion|other),
  doc_number, doc_date, expediente, full_text,
  tags (list of detected content types)
"""

import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
TEXT_DIR = DATA_DIR / "text"
BULLETINS_FILE = DATA_DIR / "bulletins.json"
OUT_FILE = DATA_DIR / "records.jsonl"

# Section markers in the PDF text layout
SECTION_HEADERS = {
    "ordenanza": re.compile(r"^\s*ORDENANZAS?\s*$", re.I),
    "decreto": re.compile(r"^\s*DECRETOS? DE\s*$", re.I),
    "resolucion": re.compile(r"^\s*RESOLUCIONES? DE\s*$", re.I),
}

# Document header patterns
DOC_PATTERNS = {
    "ordenanza": re.compile(
        r"Ordenanza\s+N[°º]?\s*(\d[\d./\-]*)", re.I
    ),
    "decreto": re.compile(
        r"Decreto\s+N[°º]?\s*(\d[\d./\-]*)", re.I
    ),
    "resolucion": re.compile(
        r"Resoluci[oó]n\s+N[°º]?\s*(\d[\d./\-]*)", re.I
    ),
}

EXPEDIENTE_RE = re.compile(r"Expte\.?\s*([\d\-/]+)", re.I)
DATE_RE = re.compile(r"La Plata,\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})", re.I)
DATE_SHORT_RE = re.compile(r"La Plata,\s+(\d{1,2}/\d{1,2}/\d{4})", re.I)
EXTRACTADA_RE = re.compile(r"versi[oó]n extractada", re.I)
AMOUNT_RE = re.compile(r"\$\s*([\d.,]+)", re.I)

# Content classifiers — what kind of thing is this decreto about?
TAG_PATTERNS = [
    ("adjudicacion",    re.compile(r"\badjudica(r|do|ci[oó]n)?\b", re.I)),
    ("licitacion",      re.compile(r"\blicitaci[oó]n\b", re.I)),
    ("contratacion_directa", re.compile(r"\bcontrataci[oó]n directa\b", re.I)),
    ("subsidio",        re.compile(r"\bsubsidio\b", re.I)),
    ("transferencia",   re.compile(r"\btransferencia\b", re.I)),
    ("bien_inmueble",   re.compile(r"\binmueble\b|\bparcela\b|\bterreno\b|\bcesion\b", re.I)),
    ("obra_publica",    re.compile(r"\bobra p[uú]blica\b|\bobras?\b.*\bvial\b", re.I)),
    ("personal",        re.compile(r"\bdesignaci[oó]n\b|\bcese\b|\bjubilaci[oó]n\b|\brenuncia\b|\blicencia\b", re.I)),
    ("convenio",        re.compile(r"\bconvenio\b", re.I)),
    ("multa_cobro",     re.compile(r"\bmulta\b|\bcobro\b.*\bdeuda\b|\bjuicio\b.*\bfiscal\b", re.I)),
    ("concesion",       re.compile(r"\bconcesi[oó]n\b|\bpermiso\s+de\s+uso\b", re.I)),
    ("presupuesto",     re.compile(r"\bpresupuesto\b|\bmodificaci[oó]n presupuestaria\b", re.I)),
    ("emergencia",      re.compile(r"\bemergencia\b", re.I)),
]

def detect_tags(text):
    return [tag for tag, pat in TAG_PATTERNS if pat.search(text)]

def extract_amounts(text):
    """Extract all peso amounts mentioned in text."""
    return [m.group(1).replace(".", "").replace(",", ".") for m in AMOUNT_RE.finditer(text)]

def split_into_documents(text):
    """
    Split a bulletin's full text into individual document chunks.
    Each chunk is the text of one ordenanza/decreto/resolución.
    Returns list of (doc_type, raw_text).
    """
    lines = text.splitlines()
    docs = []
    current_section = "other"
    current_lines = []
    current_doc_type = None

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect section change
        for dtype, pat in SECTION_HEADERS.items():
            if pat.match(line):
                current_section = dtype
                i += 1
                break
        else:
            # Detect start of a new document within section
            new_doc_type = None
            for dtype, pat in DOC_PATTERNS.items():
                if pat.search(line):
                    new_doc_type = dtype
                    break

            if new_doc_type and current_lines:
                # Save previous doc
                docs.append((current_doc_type or current_section, "\n".join(current_lines).strip()))
                current_lines = []

            if new_doc_type:
                current_doc_type = new_doc_type

            current_lines.append(line)
            i += 1

    # Save last doc
    if current_lines:
        docs.append((current_doc_type or current_section, "\n".join(current_lines).strip()))

    return [(dt, txt) for dt, txt in docs if txt and len(txt) > 30]

def extract_doc_number(doc_type, text):
    pat = DOC_PATTERNS.get(doc_type)
    if not pat:
        return None
    m = pat.search(text)
    return m.group(1).strip() if m else None

def extract_expediente(text):
    m = EXPEDIENTE_RE.search(text)
    return m.group(1).strip() if m else None

def extract_date(text):
    m = DATE_RE.search(text) or DATE_SHORT_RE.search(text)
    return m.group(1).strip() if m else None

def parse_bulletin(bulletin_meta, text):
    docs = split_into_documents(text)
    records = []
    for doc_type, raw in docs:
        records.append({
            "bulletin_id":      bulletin_meta["bulletin_id"],
            "bulletin_display": bulletin_meta["display_number"],
            "bulletin_date":    bulletin_meta["date"],
            "doc_type":         doc_type,
            "doc_number":       extract_doc_number(doc_type, raw),
            "doc_date":         extract_date(raw),
            "expediente":       extract_expediente(raw),
            "tags":             detect_tags(raw),
            "is_extractada":    bool(EXTRACTADA_RE.search(raw)),
            "amounts":          extract_amounts(raw),
            "text":             raw[:2000],      # cap stored text for now
            "text_length":      len(raw),
        })
    return records

def main():
    bulletins = {b["bulletin_id"]: b for b in json.loads(BULLETINS_FILE.read_text())}
    total = len(bulletins)
    processed = 0
    total_records = 0

    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for bid, meta in sorted(bulletins.items()):
            text_path = TEXT_DIR / f"{bid}.txt"
            if not text_path.exists():
                continue

            text = text_path.read_text(encoding="utf-8", errors="replace")
            records = parse_bulletin(meta, text)

            for r in records:
                out.write(json.dumps(r, ensure_ascii=False) + "\n")

            total_records += len(records)
            processed += 1
            if processed % 10 == 0:
                print(f"Parsed {processed}/{total} bulletins, {total_records} records so far")

    print(f"\nDone: {processed} bulletins → {total_records} records → {OUT_FILE}")

if __name__ == "__main__":
    main()
