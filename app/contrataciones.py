# app/contrataciones.py
import altair as alt
import streamlit as st
from app.db import get_contrataciones_por_año, get_montos_por_año, get_pct_directa_por_año
from app.ipc import deflactar, get_ipc_anual

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
    st.subheader("El cambio de gestión en un número")

    df_tend = get_pct_directa_por_año(db_path)
    garro = df_tend[df_tend["year"].between(2019, 2023)]["pct_directa"].mean()
    alak = df_tend[df_tend["year"] >= 2024]["pct_directa"].mean()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Gestión anterior (2019–2023)", f"{garro:.0f}%",
                  help="Promedio anual de contratos adjudicados sin proceso licitatorio")
        st.caption("Promedio de contratos sin licitación por año")
    with col2:
        st.metric("Gestión actual (2024–hoy)", f"{alak:.0f}%",
                  delta=f"+{alak - garro:.0f} puntos",
                  delta_color="inverse",
                  help="Promedio anual de contratos adjudicados sin proceso licitatorio")
        st.caption("Promedio de contratos sin licitación por año")

    line = (
        alt.Chart(df_tend)
        .mark_line(point=True, strokeWidth=2.5)
        .encode(
            x=alt.X("year:O", title="Año", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("pct_directa:Q", title="% sin licitación", scale=alt.Scale(domain=[0, 100])),
            color=alt.condition(
                alt.datum.year >= 2024,
                alt.value("#D73027"),
                alt.value("#74ADD1"),
            ),
            tooltip=[
                alt.Tooltip("year:O", title="Año"),
                alt.Tooltip("directas:Q", title="Sin licitación"),
                alt.Tooltip("total:Q", title="Total contratos"),
                alt.Tooltip("pct_directa:Q", title="% sin licitación", format=".1f"),
            ],
        )
        .properties(height=300)
    )

    regla = (
        alt.Chart(alt.Data(values=[{"year": "2024"}]))
        .mark_rule(strokeDash=[6, 3], color="#888888")
        .encode(x=alt.X("year:O"))
    )

    st.altair_chart(line + regla, use_container_width=True)
    st.caption(
        "La línea punteada marca el cambio de intendente (diciembre 2023). "
        "2026 incluye solo los meses publicados hasta la fecha."
    )

    st.divider()
    st.subheader("¿Cuánto se adjudicó?")
    st.markdown(
        "Solo las **licitaciones públicas** publican el monto en el texto del boletín. "
        "El resto — contrataciones directas, licitaciones privadas, concursos — "
        "no incluye el importe adjudicado."
    )

    df_montos = get_montos_por_año(db_path)
    ipc = get_ipc_anual()
    ref_year = max(ipc.keys())
    deflactar(df_montos, "total_miles_millones", "total_real_mm", ipc, ref_year)

    nominal = st.checkbox("Ver valores nominales (sin ajuste por inflación)", value=False)
    y_col = "total_miles_millones" if nominal else "total_real_mm"
    y_label = "Miles de millones de pesos (nominal)" if nominal else f"Miles de millones de pesos ({ref_year})"
    tooltip_extra = (
        [alt.Tooltip("total_miles_millones:Q", title="Nominal ($M)", format=".1f")]
        if not nominal else []
    )

    bar_montos = (
        alt.Chart(df_montos)
        .mark_bar(color="#2C7BB6")
        .encode(
            x=alt.X("year:O", title="Año", axis=alt.Axis(labelAngle=0)),
            y=alt.Y(f"{y_col}:Q", title=y_label),
            tooltip=[
                alt.Tooltip("year:O", title="Año"),
                alt.Tooltip("contratos:Q", title="Licitaciones con monto"),
                alt.Tooltip(f"{y_col}:Q", title="Miles de millones $", format=".1f"),
                *tooltip_extra,
            ],
        )
        .properties(height=320)
    )
    st.altair_chart(bar_montos, use_container_width=True)

    total_nominal = df_montos["total_miles_millones"].sum()
    total_real = df_montos["total_real_mm"].sum()
    if nominal:
        st.caption(
            f"Total nominal 2018–2026: **${total_nominal:,.0f} miles de millones**. "
            "Los valores no son comparables entre años por la inflación."
        )
    else:
        st.caption(
            f"Total en pesos constantes de {ref_year}: **${total_real:,.0f} miles de millones** "
            f"(equivalente nominal: ${total_nominal:,.0f} MM). "
            f"Deflactado con IPC INDEC (base dic 2016). "
            "Solo licitaciones públicas con monto publicado."
        )
