# tests/test_db.py
import pytest
import pandas as pd
from app.db import (
    get_stats_cabecera,
    get_contrataciones_por_año,
    get_empresas_stats,
    get_inmuebles_por_año,
    get_inmuebles_ops,
    buscar,
)

DB_PATH = "data/laplata.duckdb"


def test_stats_cabecera_keys():
    stats = get_stats_cabecera(DB_PATH)
    assert "pct_directa_reciente" in stats
    assert "total_reciente" in stats
    assert "n_excepcionales" in stats
    assert "pct_sin_empresa" in stats
    assert isinstance(stats["pct_directa_reciente"], float)


def test_stats_cabecera_valores_plausibles():
    stats = get_stats_cabecera(DB_PATH)
    assert 50 <= stats["pct_directa_reciente"] <= 100
    assert stats["n_excepcionales"] > 100
    assert stats["pct_sin_empresa"] > 80


def test_contrataciones_por_año_shape():
    df = get_contrataciones_por_año(DB_PATH)
    assert isinstance(df, pd.DataFrame)
    assert "year" in df.columns
    assert "tipo" in df.columns
    assert "cantidad" in df.columns
    assert set(df["year"].unique()) >= {2018, 2019, 2023, 2025}


def test_contrataciones_por_año_tipos():
    df = get_contrataciones_por_año(DB_PATH)
    tipos = set(df["tipo"].unique())
    assert "Sin licitación" in tipos
    assert "Licitación pública" in tipos


def test_empresas_stats_keys():
    stats = get_empresas_stats(DB_PATH)
    assert "sin_empresa" in stats
    assert "total" in stats
    assert "top_empresas" in stats
    assert isinstance(stats["top_empresas"], pd.DataFrame)


def test_inmuebles_por_año_shape():
    df = get_inmuebles_por_año(DB_PATH)
    assert isinstance(df, pd.DataFrame)
    assert "year" in df.columns
    assert "cantidad" in df.columns
    assert len(df) > 0


def test_inmuebles_ops_shape():
    df = get_inmuebles_ops(DB_PATH)
    assert isinstance(df, pd.DataFrame)
    assert "operacion" in df.columns
    assert "cantidad" in df.columns


def test_buscar_retorna_dataframe():
    df = buscar(DB_PATH, "mantenimiento")
    assert isinstance(df, pd.DataFrame)
    assert len(df) > 0
    assert "tipo" in df.columns
    assert "bulletin_id" in df.columns
    assert "fecha" in df.columns
    assert "url_sibom" in df.columns


def test_buscar_termino_vacio_retorna_vacio():
    df = buscar(DB_PATH, "")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 0


def test_buscar_url_sibom_format():
    df = buscar(DB_PATH, "licitacion")
    if len(df) > 0:
        assert df["url_sibom"].iloc[0].startswith("https://sibom.slyt.gba.gob.ar/bulletins/")
