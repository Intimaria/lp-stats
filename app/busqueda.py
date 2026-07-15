import streamlit as st
from app.db import buscar, buscar_empresa

BADGE_COLORS = {
    "Contrato":  "#2C7BB6",
    "Inmueble":  "#4DAC26",
    "Decreto":   "#888888",
}

SIBOM_BASE = "https://sibom.slyt.gba.gob.ar/bulletins"


def formatear_tipo_badge(tipo: str) -> str:
    color = BADGE_COLORS.get(tipo, "#AAAAAA")
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:4px;font-size:0.8em">{tipo}</span>'


def render_perfil_empresa(perfil: dict) -> None:
    st.subheader(f"Empresa: {perfil['empresa']}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Licitaciones ganadas", perfil["contratos"])
    with col2:
        if perfil["total_millones"]:
            st.metric("Total adjudicado", f"${perfil['total_millones']:,}M")
        else:
            st.metric("Total adjudicado", "Sin dato")
    with col3:
        rango = (
            str(perfil["primer_año"])
            if perfil["primer_año"] == perfil["ultimo_año"]
            else f"{perfil['primer_año']}–{perfil['ultimo_año']}"
        )
        st.metric("Período", rango)

    df = perfil["detalle"].copy()
    df["Año"] = df["year"]
    df["Decreto"] = df["doc_number"]
    df["Tipo"] = df["tipo_label"]
    df["Descripción"] = df["description"].fillna("—").str[:80]
    df["Monto ($M)"] = df["awarded_amount"].apply(
        lambda x: f"{x/1e6:,.0f}" if x and x > 0 else "—"
    )
    df["Fuente"] = df["url"]

    st.dataframe(
        df[["Año", "Decreto", "Tipo", "Descripción", "Monto ($M)", "Fuente"]],
        column_config={"Fuente": st.column_config.LinkColumn("Fuente", display_text="Ver ↗")},
        use_container_width=True,
        hide_index=True,
    )
    st.divider()


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
        perfil = buscar_empresa(db_path, query)
        df = buscar(db_path, query)

    if perfil:
        render_perfil_empresa(perfil)

    if len(df) == 0 and not perfil:
        st.warning(f"No se encontraron resultados para **{query}**.")
        return

    if len(df) > 0:
        st.caption(f"{len(df)} resultado(s) en el boletín para **{query}**")
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
            st.markdown(f"[Ver en boletín oficial ↗]({row['url_sibom']})")
            st.divider()
