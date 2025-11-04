import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.fetch_data import get_alarmas
from datetime import datetime, timedelta
from PIL import Image
import requests

img=Image.open("logo.png")

st.set_page_config(page_title="Reporte", layout="wide",page_icon=img,initial_sidebar_state="collapsed")

st.title("📊 Reporte de Alarmas Huawei & ZTE")

# Control de actualización automática
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now() - timedelta(minutes=16)

def actualizar_datos():
    st.session_state.data = get_alarmas()
    st.session_state.last_update = datetime.now()

# Actualización automática cada 15 min
if datetime.now() - st.session_state.last_update > timedelta(minutes=15):
    actualizar_datos()


# Botón manual
if st.button("🔄 Actualizar datos ahora"):
    actualizar_datos()

# --- Selector de tema ---
if "tema" not in st.session_state:
    st.session_state.tema = "Claro"

tema = st.sidebar.radio("🎨 Tema:", ["Claro", "Oscuro"], index=0)

# Guarda el tema seleccionado
st.session_state.tema = tema

# Define colores según tema
if tema == "Oscuro":
    bg_color = "#0e1117"
    text_color = "#fafafa"
    accent = "#009EF7"
else:
    bg_color = "#F4FAFF"
    text_color = "#1E1E1E"
    accent = "#009EF7"

# --- Aplica estilo global ---
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
    }}
    div[data-testid="stSidebar"] {{
        background-color: {accent}22;  /* 22 → opacidad ligera */
    }}
    .css-1d391kg .stButton>button {{
        background-color: {accent};
        color: white;
    }}
    a {{
        color: {accent};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# Cargar datos si no existen aún
if "data" not in st.session_state:
    actualizar_datos()

df = st.session_state.data

st.caption(f"🕒 Última actualización: {pd.to_datetime(df['HoraProceso'], errors='coerce').max():%d/%m/%Y %H:%M:%S} | Registros cargados ({len(df)} registros)"  )

if df.empty:
    st.error("No se pudieron cargar los datos de Huawei/ZTE 😢")
else:
    
    # --- 🗓️ FILTRO DE FECHAS ---
    if "HoraPeru" in df.columns:
        df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors="coerce", dayfirst=True)
        df = df.dropna(subset=["HoraPeru"])

        min_fecha = df["HoraPeru"].min().date()
        max_fecha = df["HoraPeru"].max().date()

        col1, col2 = st.columns([1.2, 2.5])

        
        with col1:
            rango = st.date_input(
                "Selecciona rango de fechas",
                value=(min_fecha, max_fecha),
                min_value=min_fecha,
                max_value=max_fecha
            )

        if isinstance(rango, tuple) and len(rango) == 2:
            inicio, fin = rango
            df_filtrado = df[
                (df["HoraPeru"].dt.date >= inicio) &
                (df["HoraPeru"].dt.date <= fin)
            ]
            with col2:
                st.write(f"📆 Rango disponible: {min_fecha} → {max_fecha}")
                #st.info(f"🔍 Filtrado entre {inicio} y {fin}: {len(df_filtrado)} registros.")
        else:
            df_filtrado = df.copy()
    else:
        st.warning("⚠️ No existe la columna 'HoraPeru'.")
        df_filtrado = df.copy()

    # --- MOSTRAR TABLA Y GRÁFICO ---
    if not df_filtrado.empty:
        # --- FILTRO POR GESTOR ---
        st.subheader("🔍 Seleccione Gestor")

        # Inicializamos el estado del gestor si no existe
        if "gestor_seleccionado" not in st.session_state:
            st.session_state.gestor_seleccionado = "ambos"

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("📡 HUAWEI"):
                st.session_state.gestor_seleccionado = "huawei"

        with col2:
            if st.button("🛰️ ZTE"):
                st.session_state.gestor_seleccionado = "zte"

        with col3:
            if st.button("🌐 Ambos"):
                st.session_state.gestor_seleccionado = "ambos"

        # Ahora usamos el gestor recordado
        gestor_seleccionado = st.session_state.gestor_seleccionado

        # Aplicar filtro base según el gestor
        if gestor_seleccionado == "huawei":
            df_filtrado = df_filtrado[df_filtrado["Gestor"].str.lower() == "huawei"]
        elif gestor_seleccionado == "zte":
            df_filtrado = df_filtrado[df_filtrado["Gestor"].str.lower() == "zte"]

        st.info(f"📡 Gestor seleccionado: {gestor_seleccionado.upper()}")

        # --- Segmentadores adicionales según el Gestor seleccionado ---
        if gestor_seleccionado == "huawei" and "TipoFinal" in df_filtrado.columns:
            tipo_final = st.multiselect(
                "Filtrar por TipoFinal (Huawei):",
                options=sorted(df_filtrado["TipoFinal"].dropna().unique()),
                default=None,
            )
            if tipo_final:
                df_filtrado = df_filtrado[df_filtrado["TipoFinal"].isin(tipo_final)]

        elif gestor_seleccionado == "zte" and "strName" in df_filtrado.columns:
            str_name = st.multiselect(
                "Filtrar por strName (ZTE):",
                options=sorted(df_filtrado["strName"].dropna().unique()),
                default=None,
            )
            if str_name:
                df_filtrado = df_filtrado[df_filtrado["strName"].isin(str_name)]

        elif gestor_seleccionado == "ambos":
            col_a, col_b = st.columns(2)
            with col_a:
                tipo_final = st.multiselect(
                    "Filtrar por TipoFinal (Huawei):",
                    options=sorted(df_filtrado["TipoFinal"].dropna().unique()),
                    default=None,
                )
                if tipo_final:
                    df_filtrado = df_filtrado[df_filtrado["TipoFinal"].isin(tipo_final)]
            with col_b:
                str_name = st.multiselect(
                    "Filtrar por strName (ZTE):",
                    options=sorted(df_filtrado["strName"].dropna().unique()),
                    default=None,
                )
                if str_name:
                    df_filtrado = df_filtrado[df_filtrado["strName"].isin(str_name)]


        # --- Mostrar tabla y gráfico final ---
        #st.dataframe(df_filtrado[["DEV_2", "Cliente_puerto", "PORT TIME", "Gestor", "HoraPeru"]].head(500))

        if not df_filtrado.empty:
            st.subheader("📊 Incidencias registradas por hora")

            if {"DEV", "Cliente_puerto", "SN", "PN", "HoraPeru", "Hour", "SerialNo"}.issubset(df_filtrado.columns):
                tabla_dinamica = pd.pivot_table(
                    df_filtrado,
                    index=["DEV", "Cliente_puerto", "SN", "PN", "HoraPeru"],
                    columns="Hour",
                    values="SerialNo",
                    aggfunc="count",
                    fill_value=0,
                )
                tabla_dinamica["Total"] = tabla_dinamica.sum(axis=1)
                tabla_dinamica = tabla_dinamica.loc[:, (tabla_dinamica != 0).any(axis=0)]
                tabla_dinamica = tabla_dinamica.sort_values(by="Total", ascending=False)
                tabla_dinamica.columns = tabla_dinamica.columns.map(str)
                tabla_dinamica = tabla_dinamica.reset_index()

                st.dataframe(tabla_dinamica, use_container_width=True)

                st.download_button(
                    label="📥 Descargar tabla dinámica (.csv)",
                    data=tabla_dinamica.to_csv().encode("utf-8"),
                    file_name="tabla_dinamica.csv",
                    mime="text/csv"
                )

                # --- 🔍 Agregar sección de detalle ---
                st.markdown("### 🔎 Detalle de registros")

                # Selector seguro para elegir fila
                seleccion = st.selectbox(
                    "Selecciona una fila para ver detalles:",
                    tabla_dinamica.index,
                    format_func=lambda i: f"{tabla_dinamica.loc[i, 'DEV']} - {tabla_dinamica.loc[i, 'Cliente_puerto']}"
                )

                if seleccion is not None:
                    fila = tabla_dinamica.loc[seleccion]
                    dev_sel = fila["DEV"]
                    cliente_sel = fila["Cliente_puerto"]
                    sn_sel = fila["SN"]
                    pn_sel = fila["PN"]
                    hora_sel = fila["HoraPeru"]

                    # Filtrar df_filtrado para mostrar detalles
                    columnas_detalle = ["DEV", "Cliente_puerto", "SN", "PN", "HoraPeru", "AditionalInfo", "SerialNumber_TDP"]
                    columnas_existentes = [c for c in columnas_detalle if c in df_filtrado.columns]

                    detalle = df_filtrado[
                        (df_filtrado["DEV"] == dev_sel) &
                        (df_filtrado["Cliente_puerto"] == cliente_sel) &
                        (df_filtrado["SN"] == sn_sel) &
                        (df_filtrado["PN"] == pn_sel) &
                        (df_filtrado["HoraPeru"] == hora_sel)
                    ][columnas_existentes]

                    st.dataframe(detalle, use_container_width=True)

                    ngrok_base_url = "https://leilani-thimblelike-lucklessly.ngrok-free.dev"

                    col1, col2 = st.columns(2)
                    with col2:
                        st.download_button(
                            label="📥 Descargar detalle (.csv)",
                            data=detalle.to_csv(index=False).encode("utf-8"),
                            file_name=f"detalle_{dev_sel}.csv",
                            mime="text/csv"
                        )
                    with col1:
                        if st.button("👓 Consultar en Tiempo Real"):
                            try:
                                # Construir la URL de consulta
                                sn_val = int(float(sn_sel)) if str(sn_sel).replace('.', '', 1).isdigit() else sn_sel
                                pn_val = int(float(pn_sel)) if str(pn_sel).replace('.', '', 1).isdigit() else pn_sel
                                params = {
                                    "dev": dev_sel,
                                    "fn": 0,
                                    "sn": sn_val,
                                    "pn": pn_val
                                }
                                url = f"{ngrok_base_url}/consulta"
                                
                                response = requests.get(url, params=params)

                                if response.status_code == 200:
                                    try:
                                        json_data = response.json()
                                        df_json = pd.json_normalize(json_data)

                                        # Filtrar columnas deseadas
                                        columnas_deseadas = ["ALIAS", "LSTDOWNTIME", "LSTUPTIME", "ONTID", "OperState"]
                                        columnas_existentes = [c for c in columnas_deseadas if c in df_json.columns]
                                        df_mostrar = df_json[columnas_existentes]

                                        if not df_mostrar.empty:
                                            st.success("✅ Consulta exitosa")
                                            st.dataframe(df_mostrar, use_container_width=True)
                                        else:
                                            st.warning("⚠️ No se encontraron columnas esperadas en la respuesta.")
                                            st.write(df_json.head())  # Muestra algo de respaldo
                                    except Exception as e:
                                        st.error(f"⚠️ Respuesta no es JSON válido: {e}")
                                        st.text(response.text)
                                else:
                                    st.error(f"❌ Error {response.status_code}: {response.text}")

                            except Exception as e:
                                st.error(f"⚠️ Error al conectar con ngrok: {e}")

                    

            else:
                faltantes = {"DEV", "Cliente_puerto", "SN", "PN", "HoraPeru", "Hour", "SerialNo"} - set(df_filtrado.columns)
                st.warning(f"⚠️ Faltan columnas necesarias para la tabla dinámica: {faltantes}")


        # --- GRÁFICO DE TOP OLT ---
        if "DEV" in df_filtrado.columns:
            top_olts = (
                df_filtrado.groupby("DEV")["DEV"]
                .count()
                .reset_index(name="Cantidad")
                .sort_values(by="Cantidad", ascending=False)
            )
            top_olts = top_olts.head(10)

            grafico = px.bar(
                top_olts,
                x="DEV",
                y="Cantidad",
                color="DEV",
                title="Top OLT (filtrado)"
            )
            st.plotly_chart(grafico, use_container_width=True)
    else:
        st.warning("😶 No hay registros en el rango seleccionado.")


st.markdown(f"""
<hr style='margin-top: 40px; border-color:{accent};'>
<div style='text-align:center; font-size:14px; color:{text_color};'>
    Desarrollado con 💚 by <b>AJ</b> — 2025
</div>
""", unsafe_allow_html=True)