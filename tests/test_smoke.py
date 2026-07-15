# tests/test_smoke.py
"""Verifica que todos los módulos importan y las queries no explotan."""
import pytest

DB_PATH = "data/laplata.duckdb"


def test_db_cabecera_smoke():
    from app.db import get_stats_cabecera
    stats = get_stats_cabecera(DB_PATH)
    assert stats is not None


def test_db_contrataciones_smoke():
    from app.db import get_contrataciones_por_año
    df = get_contrataciones_por_año(DB_PATH)
    assert len(df) > 0


def test_db_empresas_smoke():
    from app.db import get_empresas_stats
    stats = get_empresas_stats(DB_PATH)
    assert stats["total"] > 5000


def test_db_inmuebles_smoke():
    from app.db import get_inmuebles_todos
    assert len(get_inmuebles_todos(DB_PATH)) > 0


def test_db_buscar_smoke():
    from app.db import buscar
    df = buscar(DB_PATH, "licitacion")
    assert len(df) > 0


def test_todos_los_paneles_importan():
    import app.cabecera
    import app.contrataciones
    import app.empresas
    import app.inmuebles
    import app.busqueda
