# app/contrataciones.py
import altair as alt
import streamlit as st
from app.db import get_contrataciones_por_año, get_montos_por_año

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

    st.altair_chart(chart, use_container_width=True)

    col_a, col_b = st.columns(2)
    with col_a:
        st.info("**2022–2023:** pico de contrataciones al final de la gestión anterior.")
    with col_b:
        st.info("**Desde 2024:** la mayoría de los contratos son sin licitación (rojo).")

    st.caption(
        "**Sin clasificar:** contratos donde el boletín no publica suficiente texto "
        "para identificar el tipo — el detalle está en el anexo escaneado del decreto."
    )

    st.divider()
    st.subheader("¿Cuánto se adjudicó?")
    st.markdown(
        "Solo las **licitaciones públicas** publican el monto en el texto del boletín. "
        "El resto — contrataciones directas, licitaciones privadas, concursos — "
        "no incluye el importe adjudicado. Los valores están en pesos nominales."
    )

    df_montos = get_montos_por_año(db_path)
    total_mm = df_montos["total_miles_millones"].sum()

    bar_montos = (
        alt.Chart(df_montos)
        .mark_bar(color="#2C7BB6")
        .encode(
            x=alt.X("year:O", title="Año", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("total_miles_millones:Q", title="Miles de millones de pesos (nominal)"),
            tooltip=[
                alt.Tooltip("year:O", title="Año"),
                alt.Tooltip("contratos:Q", title="Licitaciones con monto"),
                alt.Tooltip("total_miles_millones:Q", title="Miles de millones $", format=".1f"),
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(bar_montos, use_container_width=True)
    st.caption(
        f"Total registrado 2018–2026: **${total_mm:,.0f} miles de millones** en licitaciones públicas con monto publicado. "
        "No incluye contrataciones directas ni licitaciones privadas."
    )
