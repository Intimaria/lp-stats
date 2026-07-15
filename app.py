# app.py
import streamlit as st
from pathlib import Path

DB_PATH = str(Path(__file__).parent / "data" / "laplata.duckdb")

if not Path(DB_PATH).exists():
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
