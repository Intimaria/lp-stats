# app/cabecera.py
import streamlit as st
from app.db import get_stats_cabecera


def render(db_path: str) -> None:
    stats = get_stats_cabecera(db_path)

    st.title("📋 Boletín Oficial de La Plata")
    st.subheader("Lo que dicen los registros públicos del municipio")

    st.markdown("""
La Municipalidad de La Plata obtiene **puntaje perfecto** en transparencia fiscal
según la Provincia de Buenos Aires. Este sitio muestra qué hay adentro del boletín oficial.
""")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Contratos sin licitación (desde 2024)",
            f"{stats['pct_directa_reciente']:.0f}%",
            help=f"Del total de {stats['total_reciente']:,} contratos publicados desde 2024"
        )
    with col2:
        st.metric(
            "Contratos de 'emergencia' en 2025",
            f"{stats['n_excepcionales']:,}",
            help="Servicios cotidianos (parques, enfermería, cementerio) aprobados como excepción"
        )
    with col3:
        st.metric(
            "Contratos sin empresa publicada",
            f"{stats['pct_sin_empresa']:.0f}%",
            help="El boletín registra que se contrató, pero no publica a quién ni cuánto"
        )

    st.divider()
    st.markdown("""
> En 2024, el **{}% de los contratos municipales** se adjudicaron sin licitación pública.
> En diciembre de ese año, **{:,} contratos** para servicios cotidianos —mantenimiento de
> parques, enfermería, limpieza de cementerio, vía pública— fueron aprobados como
> "excepción de emergencia".
>
> El boletín oficial registra que ocurrió. **No registra quién cobró ni cuánto.**
""".format(
        int(stats['pct_directa_reciente']),
        stats['n_excepcionales']
    ))
