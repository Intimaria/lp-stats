import streamlit as st
import altair as alt
import pandas as pd
from app.db import get_inmuebles_resumen, get_inmuebles_por_año_y_tipo, get_inmuebles_todos

GLOSARIO = {
    "prescripción": (
        "El municipio adquiere un inmueble abandonado por prescripción administrativa: "
        "cuando un propietario no paga tasas durante años o abandona el bien, "
        "el Estado puede declarar que el inmueble pasa a su dominio. "
        "Es la forma en que el municipio recupera terrenos para uso público."
    ),
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
    "prescripción":          "#7B2D8B",
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

    resumen = get_inmuebles_resumen(db_path)
    total = resumen["total"]
    pct_sin = int(resumen["pct_sin_tipo"])

    st.markdown(f"""
El municipio puede ceder, escriturar, desafectar o transferir inmuebles mediante decreto.
Cada operación debe publicarse en el boletín oficial. Entre 2018 y 2026 hay **{total} registros de operaciones sobre suelo público**.
""")

    if pct_sin > 0:
        st.warning(
            f"**El {pct_sin}% de los registros aún no tiene tipo de operación extraído.** "
            "El municipio publicó el detalle en el boletín, pero en formatos que el sistema "
            "aún no puede leer completamente."
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
    st.subheader("Todos los registros")
    st.caption(
        "Cada fila es una operación detectada en el boletín oficial. "
        "Tipo vacío = el decreto menciona el inmueble pero no publicó el detalle de la operación. "
        "Los datos de dirección y beneficiario son extraídos automáticamente — pueden tener errores."
    )

    SIBOM_BASE = "https://sibom.slyt.gba.gob.ar/bulletins"
    df_todos = get_inmuebles_todos(db_path)
    df_todos["Fuente"] = df_todos["bulletin_id"].apply(lambda bid: f"{SIBOM_BASE}/{bid}")
    display = df_todos[["year", "doc_number", "operacion", "direccion", "beneficiario", "Fuente"]].rename(columns={
        "year": "Año", "doc_number": "Decreto/Ord.",
        "operacion": "Tipo", "direccion": "Dirección", "beneficiario": "Beneficiario",
    })
    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fuente": st.column_config.LinkColumn("Fuente", display_text="ver ↗"),
        },
    )

    st.divider()
    with st.expander("¿Y los decretos sobre vehículos?"):
        st.markdown("""
El boletín también registra otro tipo de decretos que mencionan bienes en la vía pública.
En los registros municipales hay dos categorías principales:

**Indemnizaciones por daños a vehículos (~430 decretos)**
Cuando un vehículo o infraestructura municipal daña un auto particular — un colectivo
que choca, una zanja sin señalizar, un árbol que cae — el municipio tramita una
indemnización. El decreto aprueba el pago y lo publica en el boletín.
El municipio **paga** en estos casos.

**Remoción de vehículos abandonados**
El municipio contrata empresas para retirar autos abandonados o siniestrados de la vía pública.
El propietario paga multa y estadía para recuperar el vehículo. En el período analizado
aparecen contrataciones directas para este servicio.

Estos registros no son operaciones sobre suelo público, por eso no aparecen en esta sección.
Podés buscarlos en el buscador con las palabras "indemnización vehículo" o "remoción vehículos".
""")

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
