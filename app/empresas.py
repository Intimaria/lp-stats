import streamlit as st
import altair as alt
import pandas as pd
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
    top = stats["top_empresas"].copy()
    pct_gap = calcular_pct_gap(sin_empresa, total)
    con_empresa = total - sin_empresa

    # Gap donut
    gap_df = pd.DataFrame([
        {"estado": "Sin empresa publicada", "cantidad": sin_empresa},
        {"estado": "Con empresa publicada", "cantidad": con_empresa},
    ])

    donut = (
        alt.Chart(gap_df)
        .mark_arc(innerRadius=70, outerRadius=140)
        .encode(
            theta=alt.Theta("cantidad:Q"),
            color=alt.Color(
                "estado:N",
                scale=alt.Scale(
                    domain=["Sin empresa publicada", "Con empresa publicada"],
                    range=["#BDBDBD", "#2C7BB6"],
                ),
                legend=alt.Legend(title=""),
            ),
            tooltip=[
                alt.Tooltip("estado:N", title=""),
                alt.Tooltip("cantidad:Q", title="Contratos"),
            ],
        )
        .properties(height=300)
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        st.altair_chart(donut, use_container_width=True)
    with col2:
        st.metric("Sin empresa publicada", f"{pct_gap:.0f}%",
                  help=f"{sin_empresa:,} de {total:,} contratos")
        st.metric("Con empresa publicada", f"{100 - pct_gap:.0f}%",
                  help=f"{con_empresa:,} contratos")
        st.markdown("""
El boletín registra que se contrató.
**No registra a quién ni cuánto se pagó.**

Esto incluye casi todos los contratos sin licitación.
""")

    st.divider()
    st.subheader("Las empresas que sí aparecen")
    st.caption(
        f"Solo {con_empresa:,} contratos publican el adjudicatario. "
        "El grueso de las contrataciones directas no está incluido."
    )

    if len(top) > 0:
        top["años_activos"] = top["años"].apply(
            lambda ys: " · ".join(str(y) for y in sorted(ys)) if ys else ""
        )

        bar = (
            alt.Chart(top)
            .mark_bar(color="#2C7BB6")
            .encode(
                x=alt.X("contratos:Q", title="Contratos publicados"),
                y=alt.Y("empresa:N", sort="-x", title=""),
                tooltip=[
                    alt.Tooltip("empresa:N", title="Empresa"),
                    alt.Tooltip("contratos:Q", title="Contratos"),
                    alt.Tooltip("años_activos:N", title="Años con contratos"),
                ],
            )
            .properties(height=420)
        )
        st.altair_chart(bar, use_container_width=True)

        display = top[["empresa", "contratos", "años_activos"]].rename(columns={
            "empresa": "Empresa",
            "contratos": "Contratos",
            "años_activos": "Años con contratos",
        })
        st.dataframe(display, use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Continuidad del padrón de proveedores")
    st.markdown("""
Las empresas registradas en el padrón municipal tienen ventaja burocrática:
sus certificaciones (AFIP, seguros, antecedentes) ya están aprobadas.
Este padrón tiende a mantenerse entre gestiones, independientemente de quién gobierne.

**Próximamente:** cruce con declaraciones juradas de funcionarios y registro ARBA.
""")
