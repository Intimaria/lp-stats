# app/empresas.py
import streamlit as st
import altair as alt
from app.db import get_empresas_stats


def calcular_pct_gap(sin_empresa: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round(sin_empresa * 100.0 / total, 1)


def render(db_path: str) -> None:
    st.header("Empresas — lo que dice y lo que omite el boletín")

    stats = get_empresas_stats(db_path)
    sin_empresa = stats["sin_empresa"]
    total = stats["total"]
    top = stats["top_empresas"]
    pct_gap = calcular_pct_gap(sin_empresa, total)

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Contratos sin empresa publicada",
                  f"{pct_gap:.0f}%",
                  help=f"{sin_empresa:,} de {total:,} contratos")
    with col2:
        st.metric("Contratos con empresa publicada",
                  f"{100 - pct_gap:.0f}%",
                  help="Solo en contratos con algún proceso competitivo")

    st.error(
        f"**El {pct_gap:.0f}% de los contratos no publica la empresa contratada.** "
        "El boletín registra que se contrató. No registra a quién ni cuánto se pagó. "
        "Esto incluye la mayoría de los contratos sin licitación."
    )

    st.divider()
    st.subheader("Empresas que aparecen en contratos con datos disponibles")
    st.caption(
        "Solo se muestran contratos donde el boletín publicó el adjudicatario. "
        "El grueso de las contrataciones directas no está incluido."
    )

    if len(top) > 0:
        chart = (
            alt.Chart(top)
            .mark_bar(color="#2C7BB6")
            .encode(
                x=alt.X("contratos:Q", title="Cantidad de contratos"),
                y=alt.Y("empresa:N", sort="-x", title=""),
                tooltip=[
                    alt.Tooltip("empresa:N", title="Empresa"),
                    alt.Tooltip("contratos:Q", title="Contratos"),
                    alt.Tooltip("primer_año:Q", title="Primer contrato"),
                    alt.Tooltip("ultimo_año:Q", title="Último contrato"),
                ],
            )
            .properties(height=400)
        )
        st.altair_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("Continuidad del padrón de proveedores")
    st.markdown("""
Las empresas ya registradas en el padrón municipal tienen ventaja burocrática:
sus certificaciones (AFIP, seguros, antecedentes) ya están aprobadas.
Este padrón tiende a mantenerse entre gestiones, independientemente de quién gobierne.

**Próximamente:** cruce con declaraciones juradas de funcionarios y registro ARBA.
""")
