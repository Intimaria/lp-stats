# tests/test_contrataciones.py
import pandas as pd
from app.contrataciones import agregar_anotaciones, orden_tipos

DB_PATH = "data/laplata.duckdb"


def test_orden_tipos_completo():
    assert "Sin licitación" in orden_tipos()
    assert "Licitación pública" in orden_tipos()
    assert len(orden_tipos()) == 5


def test_agregar_anotaciones_retorna_lista():
    anotaciones = agregar_anotaciones()
    assert isinstance(anotaciones, list)
    assert len(anotaciones) >= 2
    for a in anotaciones:
        assert "year" in a
        assert "texto" in a
        assert isinstance(a["year"], int)
