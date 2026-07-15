import streamlit as st
from app.db import buscar

BADGE_COLORS = {
    "Contrato":  "#2C7BB6",
    "Inmueble":  "#4DAC26",
    "Decreto":   "#888888",
}


def formatear_tipo_badge(tipo: str) -> str:
    color = BADGE_COLORS.get(tipo, "#AAAAAA")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em">{tipo}</span>'


def render(db_path: str) -> None:
    st.header("Buscador")
    st.markdown(
        "Buscá una empresa, número de decreto, expediente o palabra clave "
        "en todos los registros del boletín oficial."
    )

    query = st.text_input(
        "",
        placeholder="empresa, decreto, expediente, barrio...",
        label_visibility="collapsed",
    )

    if not query:
        st.caption("Ingresá un término para comenzar la búsqueda.")
        return

    with st.spinner("Buscando..."):
        df = buscar(db_path, query)

    if len(df) == 0:
        st.warning(f"No se encontraron resultados para **{query}**.")
        return

    st.caption(f"{len(df)} resultado(s) para **{query}**")

    for _, row in df.iterrows():
        badge = formatear_tipo_badge(row["tipo"])
        st.markdown(
            f"{badge} &nbsp; **{row['doc_number'] or 'S/N'}** · {row['fecha']}",
            unsafe_allow_html=True,
        )
        contenido = (row["contenido"] or "")[:300]
        if query.lower() in contenido.lower():
            idx = contenido.lower().find(query.lower())
            start = max(0, idx - 60)
            end = min(len(contenido), idx + len(query) + 60)
            contenido = f"...{contenido[start:end]}..."
        st.caption(contenido)

        url = row["url_sibom"]
        st.markdown(f"[Ver en boletín oficial ↗]({url})")
        st.divider()
