# app.py
import streamlit as st
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "data" / "laplata.duckdb")


def _db_ready(path: str) -> bool:
    if not Path(path).exists():
        return False
    try:
        import duckdb
        con = duckdb.connect(path, read_only=True)
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        con.close()
        return {"adjudicaciones", "inmuebles", "records"}.issubset(tables)
    except Exception:
        return False


if not _db_ready(DB_PATH):
    import scraper.load_db as _load_db
    _load_db.main()

st.set_page_config(
    page_title="Estadísticas platenses",
    page_icon="📋",
    layout="wide",
)

PANELES = {
    "Inicio": "inicio",
    "Contrataciones": "contrataciones",
    "Empresas": "empresas",
    "Inmuebles": "inmuebles",
    "Buscador": "busqueda",
}

with st.sidebar:
    st.title("Estadísticas platenses")
    st.caption("Datos públicos de La Plata · 2018–2026")
    seleccion = st.radio("", list(PANELES.keys()), label_visibility="collapsed")
    st.divider()
    st.caption("Fuente: SIBOM · sibom.slyt.gba.gob.ar")
    st.caption(
        "Visualización de datos abiertos del Municipio de La Plata y la Provincia de Buenos Aires. "
        "Procesamiento automático: puede contener errores o estar incompleto. No es fuente oficial."
    )

panel = PANELES[seleccion]

if panel == "inicio":
    from app.cabecera import render
    render(DB_PATH)
elif panel == "contrataciones":
    from app.contrataciones import render
    render(DB_PATH)
elif panel == "empresas":
    from app.empresas import render
    render(DB_PATH)
elif panel == "inmuebles":
    from app.inmuebles import render
    render(DB_PATH)
elif panel == "busqueda":
    from app.busqueda import render
    render(DB_PATH)
