"""
IPC (Índice de Precios al Consumidor) from INDEC via datos.gob.ar Series API.
Used to deflate nominal peso amounts to constant pesos.
"""
from collections import defaultdict

import requests
import streamlit as st

_SERIES_ID = "148.3_INIVELNAL_DICI_M_26"
_API_URL = "https://apis.datos.gob.ar/series/api/series/"

# Annual averages (base dic 2016=100) — fallback if API is unreachable
_IPC_FALLBACK = {
    2017: 113.0,
    2018: 151.0,
    2019: 233.0,
    2020: 330.0,
    2021: 490.0,
    2022: 846.0,
    2023: 1975.0,
    2024: 6317.0,
    2025: 8966.0,
    2026: 11167.0,
}


@st.cache_data(ttl=86400)
def get_ipc_anual() -> dict[int, float]:
    """Returns {year: avg_ipc} fetched from INDEC API. Falls back to hardcoded values."""
    try:
        r = requests.get(
            _API_URL,
            params={"ids": _SERIES_ID, "limit": 200, "format": "json"},
            timeout=5,
        )
        r.raise_for_status()
        by_year: dict[int, list] = defaultdict(list)
        for date_str, value in r.json()["data"]:
            by_year[int(date_str[:4])].append(value)
        return {y: sum(v) / len(v) for y, v in by_year.items()}
    except Exception:
        return _IPC_FALLBACK.copy()


def deflactar(df, col_nominal: str, col_real: str, ipc: dict[int, float], ref_year: int) -> None:
    """Add a deflated column to df in-place. ref_year determines the constant-peso base."""
    ipc_ref = ipc.get(ref_year, max(ipc.values()))
    df[col_real] = df.apply(
        lambda r: r[col_nominal] * ipc_ref / ipc[r["year"]]
        if r["year"] in ipc else None,
        axis=1,
    )
