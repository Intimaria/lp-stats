# app/db.py
import duckdb
import pandas as pd

SIBOM_BASE = "https://sibom.slyt.gba.gob.ar/bulletins"

TIPO_LABELS = {
    "licitacion_publica": "Licitación pública",
    "licitacion_privada": "Licitación privada",
    "concurso_de_precios": "Concurso de precios",
    "contratacion_directa": "Sin licitación",
    "otro": "Sin clasificar",
}


def _connect(db_path: str) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(db_path, read_only=True)


def get_stats_cabecera(db_path: str) -> dict:
    con = _connect(db_path)
    row = con.execute("""
        SELECT
            COUNT(*) FILTER (WHERE contract_type = 'contratacion_directa') * 100.0 / COUNT(*),
            COUNT(*)
        FROM adjudicaciones WHERE year >= 2024
    """).fetchone()
    pct_directa, total = row

    n_excep = con.execute("""
        SELECT COUNT(*) FROM adjudicaciones
        WHERE year = 2025
          AND contract_type = 'contratacion_directa'
          AND text_snippet LIKE '%Excepcional%'
    """).fetchone()[0]

    row2 = con.execute("""
        SELECT
            COUNT(*) FILTER (WHERE winner IS NULL AND len(bidders) = 0) * 100.0 / COUNT(*)
        FROM adjudicaciones
    """).fetchone()
    pct_sin_empresa = row2[0]

    con.close()
    return {
        "pct_directa_reciente": round(pct_directa, 1),
        "total_reciente": total,
        "n_excepcionales": n_excep,
        "pct_sin_empresa": round(pct_sin_empresa, 1),
    }


def get_contrataciones_por_año(db_path: str) -> pd.DataFrame:
    con = _connect(db_path)
    df_wide = con.execute("""
        SELECT year,
            COUNT(*) FILTER (WHERE contract_type = 'licitacion_publica')   AS licitacion_publica,
            COUNT(*) FILTER (WHERE contract_type = 'licitacion_privada')   AS licitacion_privada,
            COUNT(*) FILTER (WHERE contract_type = 'concurso_de_precios')  AS concurso_de_precios,
            COUNT(*) FILTER (WHERE contract_type = 'contratacion_directa') AS contratacion_directa,
            COUNT(*) FILTER (WHERE contract_type = 'otro')                 AS otro
        FROM adjudicaciones
        WHERE year IS NOT NULL
        GROUP BY year ORDER BY year
    """).df()
    con.close()

    cols = ["licitacion_publica", "licitacion_privada", "concurso_de_precios",
            "contratacion_directa", "otro"]
    df_long = df_wide.melt(id_vars="year", value_vars=cols,
                            var_name="tipo_raw", value_name="cantidad")
    df_long["tipo"] = df_long["tipo_raw"].map(TIPO_LABELS)
    return df_long[["year", "tipo", "cantidad"]].copy()


def get_empresas_stats(db_path: str) -> dict:
    con = _connect(db_path)
    row = con.execute("""
        SELECT
            COUNT(*) FILTER (WHERE winner IS NULL AND len(bidders) = 0),
            COUNT(*)
        FROM adjudicaciones
    """).fetchone()
    sin_empresa, total = row

    top = con.execute("""
        SELECT winner AS empresa,
               COUNT(*) AS contratos,
               MIN(year) AS primer_año,
               MAX(year) AS ultimo_año
        FROM adjudicaciones
        WHERE winner IS NOT NULL AND winner != ''
        GROUP BY winner
        ORDER BY contratos DESC
        LIMIT 15
    """).df()
    con.close()
    return {"sin_empresa": sin_empresa, "total": total, "top_empresas": top}


def get_inmuebles_por_año(db_path: str) -> pd.DataFrame:
    con = _connect(db_path)
    df = con.execute("""
        SELECT year, COUNT(*) AS cantidad
        FROM inmuebles
        WHERE year IS NOT NULL
        GROUP BY year ORDER BY year
    """).df()
    con.close()
    return df


def get_inmuebles_ops(db_path: str) -> pd.DataFrame:
    con = _connect(db_path)
    df = con.execute("""
        SELECT op AS operacion, COUNT(*) AS cantidad
        FROM (SELECT unnest(operations) AS op FROM inmuebles) t
        GROUP BY op ORDER BY cantidad DESC
    """).df()
    con.close()
    return df


def get_inmuebles_por_año_y_tipo(db_path: str) -> pd.DataFrame:
    con = _connect(db_path)
    df = con.execute("""
        SELECT year, op AS operacion, COUNT(*) AS cantidad
        FROM (
            SELECT year, unnest(operations) AS op
            FROM inmuebles WHERE len(operations) > 0
            UNION ALL
            SELECT year, 'Sin detalle publicado' AS op
            FROM inmuebles WHERE len(operations) = 0
        ) t
        WHERE year IS NOT NULL
        GROUP BY year, op ORDER BY year, cantidad DESC
    """).df()
    con.close()
    return df


def buscar(db_path: str, query: str, limit: int = 50) -> pd.DataFrame:
    if not query or not query.strip():
        return pd.DataFrame(columns=["tipo", "fecha", "doc_number",
                                      "contenido", "bulletin_id", "url_sibom"])
    con = _connect(db_path)
    q = f"%{query.strip()}%"
    df = con.execute("""
        SELECT 'Contrato' AS tipo, bulletin_id, bulletin_date AS fecha,
               doc_number, COALESCE(description, text_snippet) AS contenido,
               winner
        FROM adjudicaciones
        WHERE text_snippet ILIKE ?
           OR description ILIKE ?
           OR winner ILIKE ?
           OR expediente ILIKE ?
        UNION ALL
        SELECT 'Inmueble' AS tipo, bulletin_id, bulletin_date AS fecha,
               doc_number, text_snippet AS contenido, NULL AS winner
        FROM inmuebles
        WHERE text_snippet ILIKE ?
           OR parcela ILIKE ?
        UNION ALL
        SELECT 'Decreto' AS tipo, bulletin_id, bulletin_date AS fecha,
               doc_number, text AS contenido, NULL AS winner
        FROM records
        WHERE text ILIKE ?
           OR expediente ILIKE ?
        ORDER BY fecha DESC
        LIMIT ?
    """, [q, q, q, q, q, q, q, q, limit]).df()
    con.close()
    df["url_sibom"] = df["bulletin_id"].apply(
        lambda bid: f"{SIBOM_BASE}/{bid}"
    )
    return df
