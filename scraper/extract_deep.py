"""
Deep extraction reading full text files directly (not truncated records.jsonl).
Extracts structured data from adjudicaciones and inmuebles.
"""

import json
import re
from pathlib import Path
from collections import defaultdict, Counter

DATA_DIR = Path(__file__).parent.parent / "data"
TEXT_DIR = DATA_DIR / "text"
BULLETINS_FILE = DATA_DIR / "bulletins.json"

# ── Contract type normalisation ──────────────────────────────────────────────

LICIT_TYPE_RE = re.compile(
    r"(Licitaci[oó]n\s+P[uú]blica"
    r"|Licit(?:aci[oó]n)?\.?\s+P[uú]b(?:lica)?\.?"
    r"|Licitaci[oó]n\s+Privada"
    r"|Licit(?:aci[oó]n)?\.?\s+Priv(?:ada)?\.?"
    r"|Concurso\s+de\s+Precios"
    r"|Concurso\s+de\s+Precio"
    r"|Contrataci[oó]n\s+Directa"
    r"|Contrat(?:aci[oó]n)?\.?\s+Dir(?:ecta)?\.?"
    r")",
    re.I,
)
LICIT_NUM_RE = re.compile(
    r"(?:Licitaci[oó]n|Licit\.?)\s*(?:P[uú]b(?:lica)?\.?|Priv(?:ada)?\.?)"
    r"\s*N[°º]?\s*([\d/\-]+)",
    re.I,
)
CONTRAT_NUM_RE = re.compile(
    r"(?:Contrataci[oó]n|Contrat\.?)\s*(?:Directa|Dir\.?)"
    r"\s*N[°º]?\s*([\d/\-]+)", re.I
)
# Description after "para ..." in one-liner decrees
DESCRIPTION_RE = re.compile(r"\bpara\s+(?:la\s+|el\s+|los\s+|las\s+)?(.{10,120}?)[\.\n]", re.I)

def normalise_contract_type(text):
    m = LICIT_TYPE_RE.search(text)
    if not m:
        return "otro"
    t = (m.group(1).lower()
         .replace("ú","u").replace("á","a").replace("ó","o").replace("é","e").replace("í","i"))
    if "pub" in t:
        return "licitacion_publica"
    if "priv" in t:
        return "licitacion_privada"
    if "concurso" in t:
        return "concurso_de_precios"
    if "dir" in t:
        return "contratacion_directa"
    return "otro"

# ── Bidder / company extraction ───────────────────────────────────────────────

# "Perteneciente a la Firma X" / "Pertenece a la Firma X"
BIDDER_RE = re.compile(
    r"[Pp]ertenec(?:iente|e)\s+a\s+la\s+[Ff]irma\s+([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9\s\.,&\-]{3,60}?)"
    r"(?:\s+quien|\s+la\s+cual|\s*,|\s+por|\n)",
    re.I,
)

# "a la firma X" / "a favor de X" after adjudícase
ADJUDICA_TO_RE = re.compile(
    r"adjudic[aá]se?\s+(?:a\s+(?:favor\s+de\s+)?)?(?:la\s+[Ff]irma\s+)?"
    r"([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9\s\.,&\-]{3,60}?)"
    r"(?:\s+(?:por|la|el|para|los|las)\b|\s*,|\s*\n)",
    re.I,
)

# "la más conveniente" / "la mejor oferta" → what comes before is the winner
WINNER_RE = re.compile(
    r"([A-ZÁÉÍÓÚÜÑ][A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9\s\.,&\-]{3,60}?)"
    r"\s+(?:resulta ser|es la\s+)?(?:la más conveniente|la mejor oferta|resulta ser la más|resulta ser la mejor)",
    re.I,
)

# Amounts: "$143.880.000,00" (ARS format) or "$143,880,000.00"
AMOUNT_RE = re.compile(r"\$\s*([\d\.,]+(?:,\d{2}|\.\d{2})?)", re.I)

def parse_amount(raw):
    """Convert Argentine peso format to float."""
    s = raw.strip()
    # Format: 143.880.000,00 → 143880000.00
    if "," in s and s.rfind(",") > s.rfind("."):
        s = s.replace(".", "").replace(",", ".")
    return float(s.replace(",", "")) if s else None

# ── Document splitter ─────────────────────────────────────────────────────────

DOC_START_RE = re.compile(
    r"^\s*(?:Decreto|Ordenanza|Resoluci[oó]n)\s+N[°º]?\s*[\d]",
    re.I | re.MULTILINE,
)

def split_text_into_docs(text):
    """Split raw bulletin text into individual document blocks."""
    positions = [m.start() for m in DOC_START_RE.finditer(text)]
    if not positions:
        return [text]
    blocks = []
    for i, pos in enumerate(positions):
        end = positions[i + 1] if i + 1 < len(positions) else len(text)
        blocks.append(text[pos:end])
    return blocks

DOC_NUM_RE = re.compile(
    r"^\s*(?:Decreto|Ordenanza|Resoluci[oó]n)\s+N[°º]?\s*([\d/\-\.]+)",
    re.I | re.MULTILINE,
)
EXPTE_RE = re.compile(r"Expte\.?\s*N?[°º]?\s*([\d\-/]+)", re.I)
DOC_DATE_RE = re.compile(
    r"La Plata,\s+(\d{1,2}\s+de\s+\w+\s+de\s+\d{4}|\d{1,2}/\d{1,2}/\d{4})", re.I
)

# ── Inmueble patterns ─────────────────────────────────────────────────────────

INMUEBLE_RE = re.compile(r"\binmueble\b|\bparcela\b|\bterreno\b|\bdominio\b", re.I)

# A block must match at least one of these to be kept as an inmueble record
INMUEBLE_STRONG_RE = re.compile(
    r"uso\s+precario|transferencia\s+de\s+dominio|escritura\s+traslativa"
    r"|bien\s+inmueble|inmueble\s+municipal|inmueble\s+(?:fiscal|del\s+estado)"
    r"|[Cc]at[aá]logo\s+de\s+[Bb]ienes|espacio\s+verde"
    r"|[Bb]ien(?:es)?\s+(?:del\s+municipio|municipales?|fiscales?)"
    r"|[Cc]ircunscripci[oó]n\s+[IVXL\d]",
    re.I,
)

INMUEBLE_OP_RE = re.compile(
    r"\b(desafectaci[oó]n|desaf[eé]ct[aáeé](?:se?|ndo|n(?:se)?)?|desafecta"
    r"|cesi[oó]n(?:\s+de\s+uso)?|cedido|cede|c[eé]d[ao]se?"
    r"|escritura\s+traslativa|escritura[rs]?|escriturar|escrituraci[oó]n|escritúrese?"
    r"|comodato"
    r"|donaci[oó]n|dona\b"
    r"|permuta"
    r"|adjudicaci[oó]n|adjudica"
    r"|transferencia(?:\s+de\s+dominio)?|transfi[eé]r[ae]se?"
    r"|otorg(?:a(?:se?|miento|ndo)?|amiento|[uú]ese?))\b",
    re.I,
)

# "Autorizase al DE a efectuar la CESIÓN/ESCRITURA/..." — most common Argentine decree form
AUTORIZA_OP_RE = re.compile(
    r"autoriza(?:se|ndo|r)?\b.{0,120}?\b"
    r"(cesi[oó]n|escritura\s+traslativa|escritura|desafectaci[oó]n"
    r"|transferencia|donaci[oó]n|comodato|permuta)",
    re.I | re.DOTALL,
)
PARCELA_RE = re.compile(r"parcela\s+N[°º]?\s*([\w\-/]+)", re.I)
CIRC_RE = re.compile(r"[Cc]ircunscripci[oó]n\s+([IVXLCDM\d]+)", re.I)
SECC_RE = re.compile(r"[Ss]ecci[oó]n\s+([A-Z\d]+)", re.I)

BENEFICIARIO_RE = re.compile(
    r"(?:"
    r"a\s+t[ií]tulo\s+gratuito\s+al?\s+"
    r"|a\s+favor\s+de\s+(?:la\s+)?(?:Firma\s+)?"
    r"|a\s+la\s+(?:Asociaci[oó]n|Fundaci[oó]n|Cooperativa|Sociedad|Entidad|Escuela|Iglesia|Universidad)\s+"
    r"|al\s+(?:Club|Hospital|Instituto|Comedor|Municipio|Estado)\s+"
    r"|al?\s+(?:Sr\.|Se[nñ]or|Sra\.|Se[nñ]ora)\s+"
    r")"
    r"([A-ZÁÉÍÓÚÜÑ\"][A-ZÁÉÍÓÚÜÑa-záéíóúüñ0-9\s\.,&\-'\"]{3,80}?)"
    r"(?=,\s*(?:Personería|DNI|CUIT|con\s+domicilio|ubicad)|"
    r"\s+Personería|\s*\n)",
    re.I,
)

DIRECCION_RE = re.compile(
    r"(?:[Cc]alle|[Aa]v\.?\s+|[Aa]venida\s+|[Dd]iagonal\s+|[Bb]oulevard\s+|[Bb]v\.\s+)"
    r"([\d]+|[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+(?:\s+[A-Za-záéíóúüñ]+)?)"
    r"(?:\s+N[°º]?\s*(\d+))?"
    r"(?:\s+(?:e/|entre|y)\s+([\d]+(?:\s+y\s+[\d]+)?))?",
    re.I,
)


_BENEFICIARIO_FALSO = re.compile(
    r"^(la informaci[oó]n|del pago|que la indemnice|de la responsabilidad"
    r"|para su correspondiente|sea expresado|libre de|los adjudicatarios"
    r"|Provincial$|Nacional de La Plata$|este Municipio"
    r"|Municipalidad[\s,]|Secretar[ií]a\s+de|Gerente\s+de"
    r"|Provincia\s+de\s+Buenos\s+Aires\s+del)",
    re.I,
)
_BENEFICIARIO_BAD_SUFFIX = re.compile(r"\s+(del\s+pago|del\s+sector|y\s+en|en\s+el|en\s+su)\s*$", re.I)


def clean_beneficiario(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip().rstrip(".,- ")
    if len(raw) < 5 or len(raw) > 80:
        return None
    if raw[0].islower():
        return None
    if _BENEFICIARIO_FALSO.search(raw):
        return None
    if _BENEFICIARIO_BAD_SUFFIX.search(raw):
        return None
    return raw


def normalize_op(raw: str) -> str:
    r = (raw.lower()
         .replace("ó","o").replace("á","a").replace("é","e")
         .replace("í","i").replace("ú","u").strip())
    if r.startswith("desafect"):
        return "desafecta"
    if r.startswith("cesi") or r in ("cedido", "cede"):
        return "cede"
    if r.startswith("escritur"):
        return "escritura"
    if r.startswith("donaci") or r == "dona":
        return "donación"
    if r.startswith("transfer"):
        return "transfiere"
    if r.startswith("adjudic"):
        return "adjudica"
    if r.startswith("otorg"):
        return "otorga"
    return r  # comodato, permuta unchanged

# ── Extraction functions ──────────────────────────────────────────────────────

def extract_adjudicacion_doc(block, bulletin_meta):
    if not re.search(r"adjudic", block, re.I):
        return None

    m = DOC_NUM_RE.search(block)
    doc_number = m.group(1).strip() if m else None

    m = DOC_DATE_RE.search(block)
    doc_date = m.group(1).strip() if m else None

    m = EXPTE_RE.search(block)
    expediente = m.group(1).strip() if m else None

    contract_type = normalise_contract_type(block)

    m = LICIT_NUM_RE.search(block) or CONTRAT_NUM_RE.search(block)
    contract_number = m.group(1).strip() if m else None

    m = DESCRIPTION_RE.search(block)
    description = m.group(1).strip() if m else None

    # All bidders
    bidders = [m.group(1).strip().rstrip(".,") for m in BIDDER_RE.finditer(block)]

    # Winner
    winner = None
    m = WINNER_RE.search(block)
    if m:
        winner = m.group(1).strip().rstrip(".,")
    if not winner:
        m = ADJUDICA_TO_RE.search(block)
        if m:
            winner = m.group(1).strip().rstrip(".,")

    # Amounts — try to get the winning amount (last/largest $ near winner)
    amounts = []
    for m in AMOUNT_RE.finditer(block):
        try:
            amounts.append(parse_amount(m.group(1)))
        except Exception:
            pass
    awarded_amount = max(amounts) if amounts else None

    return {
        "bulletin_id":      bulletin_meta["bulletin_id"],
        "bulletin_date":    bulletin_meta["date"],
        "year":             int(bulletin_meta["date"].split("/")[2]) if "/" in bulletin_meta["date"] else None,
        "doc_number":       doc_number,
        "doc_date":         doc_date,
        "expediente":       expediente,
        "contract_type":    contract_type,
        "contract_number":  contract_number,
        "bidders":          bidders,
        "winner":           winner,
        "all_amounts":      amounts[:10],
        "awarded_amount":   awarded_amount,
        "n_bidders":        len(bidders),
        "description":      description,
        "text_snippet":     block[:400].replace("\n", " "),
    }

def extract_inmueble_doc(block, bulletin_meta):
    if not INMUEBLE_RE.search(block):
        return None

    m = DOC_NUM_RE.search(block)
    doc_number = m.group(1).strip() if m else None

    m = DOC_DATE_RE.search(block)
    doc_date = m.group(1).strip() if m else None

    ops_raw = set(normalize_op(m.group(1)) for m in INMUEBLE_OP_RE.finditer(block))
    m_auth = AUTORIZA_OP_RE.search(block)
    if m_auth:
        ops_raw.add(normalize_op(m_auth.group(1)))
    ops = list(ops_raw)

    m = PARCELA_RE.search(block)
    parcela = m.group(1) if m else None

    m = CIRC_RE.search(block)
    circ = m.group(1) if m else None

    m = SECC_RE.search(block)
    secc = m.group(1) if m else None

    amounts = []
    for m in AMOUNT_RE.finditer(block):
        try:
            amounts.append(parse_amount(m.group(1)))
        except Exception:
            pass

    m = BENEFICIARIO_RE.search(block)
    beneficiario = clean_beneficiario(m.group(1) if m else None)

    direccion = None
    m = DIRECCION_RE.search(block)
    if m:
        calle = m.group(1).strip()
        numero = m.group(2) or ""
        entre = m.group(3) or ""
        direccion = f"calle {calle}"
        if numero:
            direccion += f" Nº {numero}"
        if entre:
            direccion += f" e/ {entre}"

    # Drop records where "inmueble" appears only in passing (vehicle damage, parking, etc.)
    if not ops and not circ and not INMUEBLE_STRONG_RE.search(block):
        return None

    return {
        "bulletin_id":     bulletin_meta["bulletin_id"],
        "bulletin_date":   bulletin_meta["date"],
        "year":            int(bulletin_meta["date"].split("/")[2]) if "/" in bulletin_meta["date"] else None,
        "doc_number":      doc_number,
        "doc_date":        doc_date,
        "operations":      ops,
        "parcela":         parcela,
        "circunscripcion": circ,
        "seccion":         secc,
        "amounts":         amounts[:5],
        "beneficiario":    beneficiario,
        "direccion":       direccion,
        "text_snippet":    block[:500].replace("\n", " "),
    }

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    bulletins = json.loads(BULLETINS_FILE.read_text())
    id_to_meta = {b["bulletin_id"]: b for b in bulletins}

    adj_records = []
    inm_records = []
    processed = 0

    for txt_path in sorted(TEXT_DIR.glob("*.txt")):
        bid = int(txt_path.stem)
        meta = id_to_meta.get(bid)
        if not meta:
            continue

        text = txt_path.read_text(encoding="utf-8", errors="replace")
        blocks = split_text_into_docs(text)

        for block in blocks:
            rec = extract_adjudicacion_doc(block, meta)
            if rec:
                adj_records.append(rec)

            rec = extract_inmueble_doc(block, meta)
            if rec:
                inm_records.append(rec)

        processed += 1
        if processed % 20 == 0:
            print(f"Processed {processed}/132 bulletins | adj={len(adj_records)} inm={len(inm_records)}")

    # ── Reports ───────────────────────────────────────────────────────────────

    print(f"\n{'='*60}")
    print(f"ADJUDICACIONES: {len(adj_records)}")
    print(f"{'='*60}")

    print("\n--- Contract types ---")
    ct = Counter(r["contract_type"] for r in adj_records)
    for t, n in ct.most_common():
        print(f"  {t:30s} {n:5d}")

    print("\n--- By year ---")
    by_year = defaultdict(int)
    for r in adj_records:
        if r["year"]:
            by_year[r["year"]] += 1
    for yr in sorted(by_year):
        bar = "█" * (by_year[yr] // 15)
        print(f"  {yr}: {by_year[yr]:4d}  {bar}")

    print("\n--- Records with bidder data ---")
    with_bidders = [r for r in adj_records if r["bidders"]]
    print(f"  {len(with_bidders)} records have identified bidders")
    bidder_counts = Counter(b for r in with_bidders for b in r["bidders"])
    print("  Top 20 companies appearing as bidders:")
    for name, n in bidder_counts.most_common(20):
        print(f"  {n:3d}  {name}")

    print("\n--- Records with winner identified ---")
    with_winner = [r for r in adj_records if r["winner"]]
    print(f"  {len(with_winner)} records have winner extracted")
    winner_counts = Counter(r["winner"] for r in with_winner)
    print("  Top 20 winners:")
    for name, n in winner_counts.most_common(20):
        print(f"  {n:3d}  {name}")

    print("\n--- Largest contracts by amount ---")
    with_amount = [r for r in adj_records if r.get("awarded_amount")]
    with_amount.sort(key=lambda r: r["awarded_amount"], reverse=True)
    for r in with_amount[:15]:
        print(f"  [{r['bulletin_date']}] ${r['awarded_amount']:>20,.0f}  {r.get('contract_type','?')}")
        if r.get("winner"):
            print(f"    → {r['winner']}")
        if r.get("bidders"):
            print(f"    bidders: {', '.join(r['bidders'][:3])}")

    print(f"\n{'='*60}")
    print(f"BIENES INMUEBLES: {len(inm_records)}")
    print(f"{'='*60}")

    print("\n--- Operations ---")
    op_counts = Counter()
    for r in inm_records:
        for op in r["operations"]:
            op_counts[op] += 1
    for op, n in op_counts.most_common():
        print(f"  {op:25s} {n:3d}")

    print("\n--- By year ---")
    by_year = defaultdict(int)
    for r in inm_records:
        if r["year"]:
            by_year[r["year"]] += 1
    for yr in sorted(by_year):
        bar = "█" * (by_year[yr] // 2)
        print(f"  {yr}: {by_year[yr]:3d}  {bar}")

    print("\n--- Sample recent property records ---")
    recent = [r for r in inm_records if r.get("year", 0) >= 2023]
    for r in recent[:12]:
        print(f"\n  [{r['bulletin_date']}] {r['doc_number'] or '?'}")
        print(f"    ops={r['operations']}  parcela={r['parcela']}  circ={r['circunscripcion']}")
        if r.get("amounts"):
            print(f"    $ {r['amounts']}")
        print(f"    {r['text_snippet'][:250]}")

    # Save
    adj_out = DATA_DIR / "adjudicaciones.jsonl"
    inm_out = DATA_DIR / "inmuebles.jsonl"
    adj_out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in adj_records))
    inm_out.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in inm_records))
    print(f"\nSaved {len(adj_records)} → {adj_out}")
    print(f"Saved {len(inm_records)} → {inm_out}")

if __name__ == "__main__":
    main()
