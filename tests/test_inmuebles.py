import pandas as pd
from app.inmuebles import GLOSARIO

DB_PATH = "data/laplata.duckdb"


def test_glosario_tiene_terminos_clave():
    assert "desafecta" in GLOSARIO
    assert "cede" in GLOSARIO
    assert "escritura" in GLOSARIO
    for termino, definicion in GLOSARIO.items():
        assert len(definicion) > 10
