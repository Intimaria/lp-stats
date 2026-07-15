# app/contrataciones.py
import altair as alt
import streamlit as st
from app.db import get_contrataciones_por_año

COLORES = {
    "Licitación pública":   "#2C7BB6",
    "Licitación privada":   "#74ADD1",
    "Concurso de precios":  "#FEE090",
    "Sin licitación":       "#D73027",
    "Sin clasificar":       "#BDBDBD",
}


def orden_tipos() -> list:
    return [
        "Licitación pública",
        "Licitación privada",
        "Concurso de precios",
        "Sin licitación",
        "Sin clasificar",
    ]


def agregar_anotaciones() -> list:
    return [
        {"year": 2023, "texto": "Pico pre-electoral"},
        {"year": 2025, "texto": "Mayoría sin licitación"},
    ]


def render(db_path: str) -> None:
    st.header("Cómo contrata la municipalidad")
    st.markdown("""
Cada contrato adjudicado debe publicarse en el boletín oficial.
La ley establece cuándo se requiere licitación pública, privada o concurso de precios.
**"Sin licitación"** agrupa los contratos donde no hubo proceso competitivo.
""")

    df = get_contrataciones_por_año(db_path)

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title="Año", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("cantidad:Q", title="Contratos publicados",
                    stack="zero"),
            color=alt.Color(
                "tipo:N",
                scale=alt.Scale(
                    domain=orden_tipos(),
                    range=[COLORES[t] for t in orden_tipos()],
                ),
                legend=alt.Legend(title="Tipo de contratación"),
            ),
            order=alt.Order("tipo:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("year:O", title="Año"),
                alt.Tooltip("tipo:N", title="Tipo"),
                alt.Tooltip("cantidad:Q", title="Contratos"),
            ],
        )
        .properties(height=400)
    )

    anotaciones = agregar_anotaciones()
    for a in anotaciones:
        chart = chart + alt.Chart(
            alt.Data(values=[{"year": str(a["year"]), "y": 0}])
        ).mark_text(
            text=f"← {a['texto']}",
            align="left",
            baseline="bottom",
            dy=-5,
            color="#333333",
            fontSize=11,
        ).encode(
            x=alt.X("year:O"),
            y=alt.value(10),
        )

    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "**Sin clasificar:** contratos donde el boletín no publica suficiente texto "
        "para identificar el tipo — el detalle está en el anexo escaneado del decreto."
    )
