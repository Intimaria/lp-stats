import streamlit as st
import altair as alt
from app.db import get_inmuebles_por_año, get_inmuebles_ops

GLOSARIO = {
    "desafecta": (
        "Saca un inmueble del uso público. Puede ser el paso previo "
        "a una venta o cesión. No implica irregularidad, pero vale registrarlo."
    ),
    "cede": (
        "Transfiere el uso del inmueble a un tercero: persona, organización o empresa. "
        "El municipio sigue siendo propietario."
    ),
    "escritura": (
        "Formaliza una transferencia de dominio. El inmueble pasa legalmente "
        "a manos de otra persona u organización."
    ),
    "comodato": (
        "Préstamo de uso gratuito por un plazo determinado. "
        "El inmueble vuelve al municipio al vencimiento."
    ),
    "donación": (
        "El municipio dona el inmueble a un tercero. "
        "Requiere ordenanza del Concejo Deliberante."
    ),
    "permuta": (
        "Intercambio de un inmueble municipal por otro bien. "
        "Requiere valuación fiscal previa."
    ),
}


def render(db_path: str) -> None:
    st.header("Tierra municipal — operaciones registradas")
    st.markdown("""
El municipio puede ceder, escriturar, desafectar o transferir inmuebles mediante decreto.
Cada operación debe publicarse en el boletín oficial.
A continuación, el registro de **475 operaciones** entre 2018 y 2026.
""")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Operaciones por año")
        df_año = get_inmuebles_por_año(db_path)
        chart_año = (
            alt.Chart(df_año)
            .mark_bar(color="#4DAC26")
            .encode(
                x=alt.X("year:O", title="Año", axis=alt.Axis(labelAngle=0)),
                y=alt.Y("cantidad:Q", title="Operaciones"),
                tooltip=[
                    alt.Tooltip("year:O", title="Año"),
                    alt.Tooltip("cantidad:Q", title="Operaciones"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_año, use_container_width=True)

    with col2:
        st.subheader("Por tipo de operación")
        df_ops = get_inmuebles_ops(db_path)
        chart_ops = (
            alt.Chart(df_ops)
            .mark_bar(color="#4DAC26")
            .encode(
                x=alt.X("cantidad:Q", title="Cantidad"),
                y=alt.Y("operacion:N", sort="-x", title=""),
                tooltip=[
                    alt.Tooltip("operacion:N", title="Operación"),
                    alt.Tooltip("cantidad:Q", title="Cantidad"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart_ops, use_container_width=True)

    st.divider()
    st.subheader("Glosario de términos")
    st.caption(
        "Estas operaciones no implican irregularidad. "
        "El municipio puede legítimamente ceder o transferir inmuebles. "
        "El valor está en que queden registradas y sean consultables."
    )
    for termino, definicion in GLOSARIO.items():
        with st.expander(f"**{termino.capitalize()}**"):
            st.write(definicion)

    st.divider()
    st.info(
        "**Próximamente:** mapa de La Plata con puntos por operación, "
        "cruce con ARBA (titular actual de cada parcela) y "
        "cruce con declaraciones juradas de funcionarios."
    )
