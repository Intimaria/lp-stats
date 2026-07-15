import pandas as pd
from app.inmuebles import GLOSARIO
from app.db import get_inmuebles_por_año_y_tipo

DB_PATH = "data/laplata.duckdb"


def test_glosario_tiene_terminos_clave():
    assert "desafecta" in GLOSARIO
    assert "cede" in GLOSARIO
    assert "escritura" in GLOSARIO
    for termino, definicion in GLOSARIO.items():
        assert len(definicion) > 10


def test_inmuebles_por_año_y_tipo_shape():
    df = get_inmuebles_por_año_y_tipo(DB_PATH)
    assert isinstance(df, pd.DataFrame)
    assert "year" in df.columns
    assert "operacion" in df.columns
    assert "cantidad" in df.columns
    assert "Sin detalle publicado" in df["operacion"].values
    total = df["cantidad"].sum()
    assert total >= 154  # genuine property operations only
