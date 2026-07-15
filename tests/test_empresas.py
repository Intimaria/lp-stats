# tests/test_empresas.py
import pandas as pd
from app.empresas import calcular_pct_gap

DB_PATH = "data/laplata.duckdb"


def test_calcular_pct_gap_basico():
    pct = calcular_pct_gap(sin_empresa=4809, total=5033)
    assert 90 <= pct <= 100


def test_calcular_pct_gap_cero_total():
    pct = calcular_pct_gap(sin_empresa=0, total=0)
    assert pct == 0
