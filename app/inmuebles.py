import streamlit as st
import altair as alt
from app.db import get_inmuebles_por_año_y_tipo

GLOSARIO = {
    "desafecta": (
        "Saca el inmueble del catálogo de bienes públicos protegidos. "
        "Es el paso previo a cualquier venta, cesión o cambio de uso. "
        "Una desafectación no es una venta, pero habilita el camino."
    ),
    "cede": (
        "Transfiere el uso a un tercero — persona, organización o empresa — "
        "sin transferir la propiedad. El municipio sigue siendo dueño. "
        "El boletín a veces no especifica quién recibe ni por cuánto tiempo."
    ),
    "escritura": (
        "Formaliza la transferencia de dominio: el inmueble pasa legalmente "
        "a manos de otro. Es la operación más difícil de revertir."
    ),
    "comodato": (
        "Préstamo de uso gratuito por plazo determinado. "
        "Al vencimiento, el inmueble vuelve al municipio."
    ),
    "donación": (
        "El municipio cede la propiedad definitivamente. "
        "Requiere ordenanza del Concejo Deliberante."
    ),
    "otorga": (
        "Término genérico para una concesión o autorización de uso. "
        "El alcance exacto depende del decreto."
    ),
}

COLORES = {
    "Sin detalle publicado": "#BDBDBD",
    "escritura":             "#D73027",
    "donación":              "#FC8D59",
    "desafecta":             "#FEE090",
    "cede":                  "#74ADD1",
    "comodato":              "#4DAC26",
    "otorga":                "#91BFDB",
    "adjudica":              "#A6D96A",
    "permuta":               "#E0F3F8",
}


def render(db_path: str) -> None:
    st.header("Suelo público — ¿qué hace el municipio con sus inmuebles?")
    st.markdown("""
El municipio puede ceder, escriturar, desafectar o transferir inmuebles mediante decreto.
Cada operación debe publicarse en el boletín oficial. Entre 2018 y 2026 hay **475 registros**.
""")

    st.warning(
        "**El 89% de los registros no incluye el tipo de operación publicado en texto digital.** "
        "El detalle figura en el anexo escaneado del decreto — no procesable sin OCR. "
        "Lo que se muestra abajo es el registro de que *algo ocurrió*, no siempre *qué*."
    )

    df = get_inmuebles_por_año_y_tipo(db_path)

    tipos = df["operacion"].unique().tolist()
    orden = ["Sin detalle publicado"] + [t for t in GLOSARIO if t in tipos]
    orden += [t for t in tipos if t not in orden]
    colores_dom = [COLORES.get(t, "#CCCCCC") for t in orden]

    chart = (
        alt.Chart(df)
        .mark_bar()
        .encode(
            x=alt.X("year:O", title="Año", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("cantidad:Q", title="Operaciones registradas", stack="zero"),
            color=alt.Color(
                "operacion:N",
                scale=alt.Scale(domain=orden, range=colores_dom),
                legend=alt.Legend(title="Tipo de operación"),
            ),
            order=alt.Order("operacion:N", sort="ascending"),
            tooltip=[
                alt.Tooltip("year:O", title="Año"),
                alt.Tooltip("operacion:N", title="Tipo"),
                alt.Tooltip("cantidad:Q", title="Cantidad"),
            ],
        )
        .properties(height=360)
    )
    st.altair_chart(chart, use_container_width=True)

    st.caption(
        "Gris = registro sin tipo identificable. Rojo = escritura (transferencia de dominio). "
        "Amarillo = desafectación (retiro de protección pública)."
    )

    st.divider()
    st.subheader("Por qué importa")
    st.markdown("""
El suelo público es el activo municipal más valioso. Lo que el municipio hace con él
determina qué servicios, espacios y oportunidades quedan en manos públicas.

Una operación puede ser completamente legítima — una cesión a un comedor comunitario,
una escritura para regularizar viviendas sociales, un comodato a una escuela.
O puede no serlo. **El boletín registra que ocurrió. Rara vez dice quién se benefició.**

La operación más sensible es la **desafectación**: saca un inmueble del catálogo de bienes
protegidos y habilita su transferencia o cambio de uso. Si tu barrio perdió una plaza,
un espacio verde o un edificio público, el decreto de desafectación estuvo antes.
""")

    st.divider()
    st.subheader("Glosario")
    for termino, definicion in GLOSARIO.items():
        with st.expander(f"**{termino.capitalize()}**"):
            st.write(definicion)

    st.divider()
    st.info(
        "**Próximamente:** mapa de La Plata con puntos por operación, "
        "cruce con ARBA (titular actual de cada parcela) y "
        "cruce con declaraciones juradas de funcionarios."
    )
