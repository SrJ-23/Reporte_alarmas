import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.fetch_data import get_alarmas
from datetime import datetime, timedelta
from PIL import Image
import requests

# --- CONFIGURACIÓN INICIAL ---
img = Image.open("logo.png")
st.set_page_config(page_title="ADCE", layout="wide", page_icon=img, initial_sidebar_state="expanded")

st.title("📊 ADCE ")
st.caption ("Alarm Data Control Engine")
# Control de actualización automática
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now() - timedelta(minutes=16)

#Funciones

def consultar_serial_api(serial):
    """Función para consultar la API"""
    try:
        url = f"{ngrok_base_url}/consulta_serial?serial={serial}"
        response = requests.get(url, timeout=20)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error en la API: {response.status_code}"}
    except Exception as e:
        return {"error": f"Error de conexión: {str(e)}"}

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


# --- CARGAR DATOS ---
if "data" not in st.session_state:
    actualizar_datos()

df = st.session_state.data

st.caption(f"🕒 Última actualización: {pd.to_datetime(df['HoraProceso'], errors='coerce').max():%d/%m/%Y %H:%M:%S} | Registros cargados ({len(df)} registros)")

if df.empty:
    st.error("No se pudieron cargar los datos 😢")
else:
# --- FILTROS EN SIDEBAR ---
    st.sidebar.header("🧭 Filtros")

    # FILTRO DE FECHAS
    if "HoraPeru" in df.columns:
        df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors="coerce", dayfirst=True)
        df = df.dropna(subset=["HoraPeru"])
        min_fecha = df["HoraPeru"].min().date()
        max_fecha = df["HoraPeru"].max().date()

        rango = st.sidebar.date_input(
            "📅 Rango de fechas",
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
        else:
            df_filtrado = df.copy()
    else:
        st.warning("⚠️ No existe la columna 'HoraPeru'.")
        df_filtrado = df.copy()

    # FILTRO POR GESTOR (radio/selección en sidebar)
    st.sidebar.subheader("📡 Gestor")
    if "gestor_seleccionado" not in st.session_state:
        st.session_state.gestor_seleccionado = "Ambos"

    # usamos selectbox (o radio) y actualizamos session_state correctamente
    gestor_seleccionado = st.sidebar.selectbox(
        "Seleccionar Gestor:",
        options=["Ambos", "HUAWEI", "ZTE"],
        index=["Ambos", "HUAWEI", "ZTE"].index(st.session_state.gestor_seleccionado if st.session_state.gestor_seleccionado in ["Ambos", "HUAWEI", "ZTE"] else "Ambos")
    )
    # guardar en sesión para persistencia
    st.session_state.gestor_seleccionado = gestor_seleccionado

    # Aplicar filtro base según el gestor (normalizamos a lower)
    if gestor_seleccionado.lower() == "huawei":
        df_filtrado = df_filtrado[df_filtrado["Gestor"].str.lower() == "huawei"]
    elif gestor_seleccionado.lower() == "zte":
        df_filtrado = df_filtrado[df_filtrado["Gestor"].str.lower() == "zte"]

    # --- Filtros adicionales dinámicos ---
    if gestor_seleccionado.lower() == "huawei" and "TipoFinal" in df_filtrado.columns:
        tipo_final = st.sidebar.multiselect(
            "📂 TipoFinal (HUAWEI)",
            options=sorted(df_filtrado["TipoFinal"].dropna().unique())
        )
        if tipo_final:
            df_filtrado = df_filtrado[df_filtrado["TipoFinal"].isin(tipo_final)]

    elif gestor_seleccionado.lower() == "zte" and "strAckUserName" in df_filtrado.columns:
        str_name = st.sidebar.multiselect(
            "🏷️ Tipo alarma (ZTE)",
            options=sorted(df_filtrado["strAckUserName"].dropna().unique())
        )
        if str_name:
            df_filtrado = df_filtrado[df_filtrado["strAckUserName"].isin(str_name)]
    if df_filtrado.empty:
        st.warning("⚠️ No se encontraron datos con los filtros seleccionados.")

    # --- Tema (lista desplegable al final del sidebar) ---
    st.sidebar.markdown("---")
    st.sidebar.header("🎨 Tema")
    if "tema" not in st.session_state:
        st.session_state.tema = "Claro"

    tema = st.sidebar.selectbox("Selecciona tema", options=["Claro", "Oscuro"], index=0)
    st.session_state.tema = tema


    # --- MOSTRAR RESULTADOS ---
    if not df_filtrado.empty:
        st.info(f"📡 Gestor seleccionado: {gestor_seleccionado.upper()} | Registros: {len(df_filtrado)}")

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
                label="📥 Descargar tabla (.csv)",
                data=tabla_dinamica.to_csv().encode("utf-8"),
                file_name="tabla_dinamica.csv",
                mime="text/csv"
            )

            # --- DETALLE DE REGISTROS ---
            st.markdown("### 🔎 Detalle de registros")
            seleccion = st.selectbox(
                "Selecciona una fila:",
                tabla_dinamica.index,
                format_func=lambda i: f"{tabla_dinamica.loc[i, 'DEV']} - {tabla_dinamica.loc[i, 'SN']}-{tabla_dinamica.loc[i, 'PN']}"
            )

            if seleccion is not None:
                fila = tabla_dinamica.loc[seleccion]
                dev_sel = fila["DEV"]
                cliente_sel = fila["Cliente_puerto"]
                sn_sel = fila["SN"]
                pn_sel = fila["PN"]
                hora_sel = fila["HoraPeru"]

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
                            # Detectar gestor y construir URL apropiada
                            if gestor_seleccionado.lower() == "huawei":
                                # Huawei - formato actual
                                sn_val = int(float(sn_sel)) if str(sn_sel).replace('.', '', 1).isdigit() else sn_sel
                                pn_val = int(float(pn_sel)) if str(pn_sel).replace('.', '', 1).isdigit() else pn_sel
                                params = {
                                    "dev": dev_sel,
                                    "fn": 0,
                                    "sn": sn_val,
                                    "pn": pn_val
                                }
                                url = f"{ngrok_base_url}/consulta"
                                
                            elif gestor_seleccionado.lower() == "zte":
                                # ZTE - buscar en datos originales para obtener IP y ONTID
                                zte_match = df[
                                    (df["DEV"] == dev_sel) & 
                                    (df["Cliente_puerto"] == cliente_sel) &
                                    (df["SN"] == sn_sel) & 
                                    (df["PN"] == pn_sel)
                                ].iloc[0] if not df[
                                    (df["DEV"] == dev_sel) & 
                                    (df["Cliente_puerto"] == cliente_sel) &
                                    (df["SN"] == sn_sel) & 
                                    (df["PN"] == pn_sel)
                                ].empty else None
                                
                                
                                sn_val = int(float(sn_sel)) if str(sn_sel).replace('.', '', 1).isdigit() else sn_sel
                                pn_val = int(float(pn_sel)) if str(pn_sel).replace('.', '', 1).isdigit() else pn_sel
                                if zte_match is not None and "DID" in zte_match and "ONTID" in zte_match:
                                    olt_ip = zte_match["DID"]
                                    ontid = zte_match["ONTID"]
                                    ontid_val = int(float(ontid)) if str(ontid).replace('.', '', 1).isdigit() else ontid
                                    ponid = f"1-{ontid_val}-{sn_val}-{pn_val}"
                                    
                                    params = {
                                        "oltid": olt_ip,
                                        "ponid": ponid
                                    }
                                    url = f"{ngrok_base_url}/pruebazte"
                                else:
                                    st.error("❌ No se encontraron datos necesarios (DID u ONTID) para consulta ZTE")
                                    st.stop()
                            else:
                                st.error("❌ Gestor no soportado")
                                st.stop()

                            # Realizar consulta (código existente)
                            response = requests.get(url, params=params)

                            if response.status_code == 200:
                                try:
                                    json_data = response.json()
                                    df_json = pd.json_normalize(json_data)
                                    
                                    # Columnas según gestor
                                    if gestor_seleccionado.lower() == "huawei":
                                        columnas_deseadas = ["ALIAS", "LSTDOWNTIME", "LSTUPTIME", "ONTID", "OperState"]
                                    else:
                                        columnas_deseadas = ["ONUID", "OperState", "AUTHINFO", "LASTOFFTIME"]
                                    
                                    columnas_existentes = [c for c in columnas_deseadas if c in df_json.columns]
                                    df_mostrar = df_json[columnas_existentes]

                                    if not df_mostrar.empty:
                                        st.success("✅ Consulta exitosa")
                                        st.dataframe(df_mostrar, use_container_width=True)
                                    else:
                                        st.warning("⚠️ No se encontraron columnas esperadas en la respuesta.")
                                        st.write(df_json.head())
                                except Exception as e:
                                    st.error(f"⚠️ Respuesta no es JSON válido: {e}")
                                    st.text(response.text)
                            else:
                                st.error(f"❌ Error {response.status_code}: {response.text}")
                        except Exception as e:
                            st.error(f"⚠️ Error al conectar: {e}")

        # Inicializar estado de sesión
        if 'show_consultation' not in st.session_state:
            st.session_state.show_consultation = False
        if 'consultation_result' not in st.session_state:
            st.session_state.consultation_result = None
        
        if st.button("🔎 Consultar Estado de ONT", type="primary", use_container_width=True):
            st.session_state.show_consultation = True
            st.session_state.consultation_result = None

        # Mostrar formulario de consulta si está activo
        if st.session_state.show_consultation:
            st.subheader("Consulta por Serial Number")
            
            # Formulario para ingresar serial
            with st.form("serial_consultation_form"):
                serial_input = st.text_input(
                    "📋 Serial Number del ONT:",
                    placeholder="Ej: MSTC0940DFDA",
                    help="Ingrese el serial number del equipo ONT",
                    key="serial_input"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    submit_btn = st.form_submit_button("🚀 Ejecutar Consulta", type="primary", use_container_width=True)
                with col2:
                    cancel_btn = st.form_submit_button("❌ Cancelar", use_container_width=True)
            
            # Procesar formulario
            if submit_btn and serial_input:
                with st.spinner("🔍 Consultando información del ONT..."):
                    resultado = consultar_serial_api(serial_input.strip())
                    st.session_state.consultation_result = resultado
                    st.rerun()
            
            if cancel_btn:
                st.session_state.show_consultation = False
                st.session_state.consultation_result = None
                st.rerun()

        # Mostrar resultados si existen
        if st.session_state.consultation_result:
            st.markdown("---")
            resultado = st.session_state.consultation_result
            
            if "error" in resultado:
                st.error(f"❌ **Error en la consulta:** {resultado['error']}")
            else:
                st.success("✅ **ONT encontrado exitosamente!**")
                
                # Crear pestañas para organizar la información
                tab1, tab2, tab3 = st.tabs(["📊 Resumen", "🔧 Datos Técnicos", "📁 Raw Data"])
                
                with tab1:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📋 Información del ONT")
                        datos_ont = resultado["datos_ont"]
                        
                        st.metric("📟 Serial", resultado["serial_number"])
                        st.metric("🏷️ Alias", datos_ont["alias"])
                        st.metric("🔢 ONT ID", datos_ont["ontid"])
                        st.metric("📊 Perfil", datos_ont["lineprof"])
                        
                        st.write(f"**📍 Ubicación:** {datos_ont['dev_completo']}")
                    
                    with col2:
                        st.subheader("📊 Estado Óptico")
                        opticos = resultado["parametros_opticos"]
                        
                        # Mostrar RX Power con color según calidad
                        rx_power = opticos['rx_power']
                        if rx_power != "--":
                            rx_value = float(rx_power.split()[0])
                            if rx_value >= -27:
                                st.metric("📡 RX Power", rx_power, delta="Óptimo", delta_color="normal")
                            elif rx_value >= -30:
                                st.metric("📡 RX Power", rx_power, delta="Aceptable", delta_color="off")
                            else:
                                st.metric("📡 RX Power", rx_power, delta="Crítico", delta_color="inverse")
                        else:
                            st.metric("📡 RX Power", rx_power)
                        
                        st.metric("📤 TX Power", opticos['tx_power'])
                        st.metric("📏 Distancia", opticos['ranging_distance'])
                        st.metric("🌡️ Temperatura", opticos['temperature'])
                        st.metric("⚡ Voltaje", opticos['voltage'])
                        st.metric("🔋 Corriente Bias", opticos['bias_current'])
                
                with tab2:
                    st.subheader("🔧 Datos Técnicos Completos")
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Configuración OLT:**")
                        datos_ont = resultado["datos_ont"]
                        st.json({
                            "DEV": datos_ont["dev"],
                            "Frame": datos_ont["fn"],
                            "Slot": datos_ont["sn"],
                            "Port": datos_ont["pn"],
                            "ONT ID": datos_ont["ontid"],
                            "Alias": datos_ont["alias"],
                            "Line Profile": datos_ont["lineprof"]
                        })
                    
                    with col2:
                        st.write("**Parámetros Ópticos Detallados:**")
                        opticos = resultado["parametros_opticos"]
                        st.json({
                            "RX Power": opticos["rx_power"],
                            "TX Power": opticos["tx_power"], 
                            "Bias Current": opticos["bias_current"],
                            "Temperature": opticos["temperature"],
                            "Voltage": opticos["voltage"],
                            "Ranging Distance": opticos["ranging_distance"]
                        })
                
                with tab3:
                    st.subheader("📁 Respuesta Cruda de la API")
                    st.json(resultado)
            
            # Botón para nueva consulta
            st.markdown("---")
            if st.button("🔄 Realizar Nueva Consulta", use_container_width=True):
                st.session_state.show_consultation = True
                st.session_state.consultation_result = None
                st.rerun()
                
        # --- GRÁFICO DE TOP OLT ---
        if "DEV" in df_filtrado.columns:
            top_olts = (
                df_filtrado.groupby("DEV")["DEV"]
                .count()
                .reset_index(name="Cantidad")
                .sort_values(by="Cantidad", ascending=False)
            )
            grafico = px.bar(top_olts.head(10), x="DEV", y="Cantidad", color="DEV", title="Top 10 OLT (filtrado)")
            st.plotly_chart(grafico, use_container_width=True)
    else:
        st.warning("😶 No hay registros en el rango seleccionado.")

#-----------------------------------------------

# Inicializar estado de sesión
if 'show_consultation' not in st.session_state:
    st.session_state.show_consultation = False
if 'consultation_result' not in st.session_state:
    st.session_state.consultation_result = None


# --- 🎨 Tema oscuro de lujo (corregido y completo) ---
if tema == "Oscuro":
    bg_color = "#F8DD65"        # Fondo principal negro profundo
    panel_color = "#F9FC79"     # Sidebar azul noche
    card_color = "#E6EE79"      # Cajas/tablas
    text_color = "#E8ECF2"      # Blanco azulado suave
    accent = "#00AEEF"          # Azul eléctrico
    accent_hover = "#33CFFF"    # Azul más claro
    border_color = "#1C2B3A"    # Bordes discretos
else:
    bg_color = "#F4FAFF"
    panel_color = "#FFFFFF"
    card_color = "#FFFFFF"
    text_color = "#1E1E1E"
    accent = "#009EF7"
    accent_hover = "#38B6FF"
    border_color = "#DDDDDD"

# --- 💅 Estilo global y de componentes ---
st.markdown(f"""
    <style>
    /* === FONDO GENERAL === */
    .stApp {{
        background-color: {bg_color};
        color: {text_color};
        font-family: 'Segoe UI', sans-serif;
    }}

    /* === SIDEBAR === */
    div[data-testid="stSidebar"] {{
        background-color: {panel_color};
        border-right: 1px solid {border_color};
        color: {text_color};
    }}

    /* === TÍTULOS === */
    h1, h2, h3, h4, h5 {{
        color: {accent};
        font-weight: 600;
        text-shadow: 0px 0px 8px {accent}33;
    }}

    /* === LINKS === */
    a {{
        color: {accent};
        text-decoration: none;
        font-weight: 500;
    }}
    a:hover {{
        color: {accent_hover};
        text-decoration: underline;
    }}

    /* === BOTONES Streamlit === */
    div[data-testid="stButton"] > button {{
        background: linear-gradient(90deg, {accent}, {accent_hover}) !important;
        color: white !important;
        border-radius: 10px !important;
        border: none !important;
        font-weight: 600 !important;
        transition: all 0.3s ease-in-out;
        box-shadow: 0px 0px 10px {accent}55 !important;
    }}
    div[data-testid="stButton"] > button:hover {{
        transform: scale(1.03);
        box-shadow: 0px 0px 15px {accent_hover}99 !important;
        background: linear-gradient(90deg, {accent_hover}, {accent}) !important;
        color: white !important;
    }}

    /* === INPUTS Y SELECTORES === */
    div[data-baseweb="select"] > div, input, textarea {{
        background-color: {card_color} !important;
        color: {text_color} !important;
        border-radius: 8px !important;
        border: 1px solid {border_color} !important;
    }}
    div[data-baseweb="select"] > div:hover, input:hover, textarea:hover {{
        border-color: {accent} !important;
        box-shadow: 0px 0px 8px {accent}44 !important;
    }}

    /* === TABLAS (st.dataframe y st.table) === */
    .stDataFrame, .stTable {{
        background-color: {card_color} !important;
        color: {text_color} !important;
        border-radius: 12px !important;
        border: 1px solid {border_color} !important;
        box-shadow: 0px 0px 12px {accent}11 !important;
    }}
    .stDataFrame [data-testid="stTable"] td, .stDataFrame [data-testid="stTable"] th {{
        background-color: {card_color} !important;
        color: {text_color} !important;
    }}

    /* === PLOTLY (Gráficos) === */
    div[data-testid="stPlotlyChart"] > div {{
        background-color: {card_color} !important;
        border-radius: 10px !important;
        padding: 10px !important;
    }}
    .plotly .main-svg {{
        background-color: {card_color} !important;
    }}

    /* === SCROLLBAR === */
    ::-webkit-scrollbar {{
        width: 10px;
        height: 10px;
    }}
    ::-webkit-scrollbar-thumb {{
        background: {accent}44;
        border-radius: 8px;
    }}
    ::-webkit-scrollbar-thumb:hover {{
        background: {accent_hover}77;
    }}

    /* === ALERTAS, INFO, WARNINGS === */
    div[data-testid="stNotification"], div[data-testid="stAlert"] {{
        background-color: {card_color} !important;
        border-left: 4px solid {accent} !important;
        color: {text_color} !important;
    }}

    /* === BOTÓN DE DESCARGA === */
    .stDownloadButton button {{
        background: linear-gradient(90deg, {accent}, {accent_hover}) !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
        box-shadow: 0px 0px 8px {accent}55 !important;
    }}
    .stDownloadButton button:hover {{
        background: linear-gradient(90deg, {accent_hover}, {accent}) !important;
        transform: scale(1.03);
        box-shadow: 0px 0px 12px {accent_hover}77 !important;
    }}
    </style>
""", unsafe_allow_html=True)

st.markdown(f"""
<hr style='margin-top: 40px; border-color:{accent};'>
<div style='text-align:center; font-size:14px; color:{text_color};'>
    Desarrollado con 💚 by <b>AJ</b> — 2025
</div>
""", unsafe_allow_html=True)
