import streamlit as st
import pandas as pd
import plotly.express as px
from scripts.fetch_data import get_alarmas
from datetime import datetime, timedelta
from PIL import Image
import requests

# --- CONFIGURACIÓN INICIAL ---
img = Image.open("logo.png")
st.set_page_config(
    page_title="ADCE - Alarm Data Control Engine", 
    layout="wide", 
    page_icon=img, 
    initial_sidebar_state="expanded"
)

# --- TÍTULO ---
st.title("📊 ADCE ")
st.caption("Alarm Data Control Engine")

# Control de actualización automática
if "last_update" not in st.session_state:
    st.session_state.last_update = datetime.now() - timedelta(minutes=16)

# Funciones
def consultar_serial_api(serial, gestor):
    """Función para consultar la API según el gestor seleccionado"""
    try:
        # Determinar el endpoint según el gestor
        if gestor.lower() == "huawei":
            url = f"{ngrok_base_url}/consulta_serial?serial={serial}"
        elif gestor.lower() == "zte":
            url = f"{ngrok_base_url}/consulta_serial_zte?serial={serial}"
        else:
            return {"error": "Gestor no soportado"}
        
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

# --- CARGAR DATOS ---
if "data" not in st.session_state:
    actualizar_datos()

df = st.session_state.data

st.caption(f"🕒 Última actualización: {pd.to_datetime(df['HoraProceso'], errors='coerce').max():%d/%m/%Y %H:%M:%S} | Registros cargados ({len(df)} registros)")

if df.empty:
    st.error("No se pudieron cargar los datos 😢")
else:
    # --- FILTROS EN HOJA PRINCIPAL ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # FILTRO DE FECHAS
        if "HoraPeru" in df.columns:
            df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors="coerce", dayfirst=True)
            df = df.dropna(subset=["HoraPeru"])
            min_fecha = df["HoraPeru"].min().date()
            max_fecha = df["HoraPeru"].max().date()

            rango = st.date_input(
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

    with col2:
        # FILTRO POR GESTOR (CORREGIDO - SIN CAPTION)
        if "gestor_seleccionado" not in st.session_state:
            st.session_state.gestor_seleccionado = "Ambos"

        gestor_seleccionado = st.selectbox(
            "📡 Gestor",
            options=["Ambos", "HUAWEI", "ZTE"],
            index=["Ambos", "HUAWEI", "ZTE"].index(st.session_state.gestor_seleccionado if st.session_state.gestor_seleccionado in ["Ambos", "HUAWEI", "ZTE"] else "Ambos")
        )
        st.session_state.gestor_seleccionado = gestor_seleccionado

        # Aplicar filtro base según el gestor
        if gestor_seleccionado.lower() == "huawei":
            df_filtrado = df_filtrado[df_filtrado["Gestor"].str.lower() == "huawei"]
        elif gestor_seleccionado.lower() == "zte":
            df_filtrado = df_filtrado[df_filtrado["Gestor"].str.lower() == "zte"]

    with col3:
        # --- Filtros adicionales dinámicos ---
        if gestor_seleccionado.lower() == "huawei" and "TipoFinal" in df_filtrado.columns:
            tipo_final = st.multiselect(
                "📂 TipoFinal (HUAWEI)",
                options=sorted(df_filtrado["TipoFinal"].dropna().unique()),
                placeholder="Seleccionar tipos..."
            )
            if tipo_final:
                df_filtrado = df_filtrado[df_filtrado["TipoFinal"].isin(tipo_final)]

        elif gestor_seleccionado.lower() == "zte" and "strAckUserName" in df_filtrado.columns:
            str_name = st.multiselect(
                "🏷️ Tipo alarma (ZTE)",
                options=sorted(df_filtrado["strAckUserName"].dropna().unique()),
                placeholder="Seleccionar tipos..."
            )
            if str_name:
                df_filtrado = df_filtrado[df_filtrado["strAckUserName"].isin(str_name)]

    if df_filtrado.empty:
        st.warning("⚠️ No se encontraron datos con los filtros seleccionados.")

    # --- MOSTRAR RESULTADOS ---
    if not df_filtrado.empty:
        st.info(f"📡 Gestor seleccionado: {gestor_seleccionado.upper()} | Registros: {len(df_filtrado)}")

        if {"DEV", "Cliente_puerto", "SN", "PN", "HoraPeru", "SerialNo"}.issubset(df_filtrado.columns):
            # TABLA SIMPLIFICADA SIN COLUMNAS DE HORAS
            tabla_dinamica = df_filtrado.groupby(["DEV", "Cliente_puerto", "SN", "PN", "HoraPeru"]).size().reset_index(name='Total')
            tabla_dinamica = tabla_dinamica.sort_values(by="Total", ascending=False)
            
            # FILTRAR HUAWEI CON TOTAL > 3 SOLO CUANDO SE SELECCIONA "ALARMA POR CLIENTE"
            if (gestor_seleccionado.lower() == "huawei" and 
                'tipo_final' in locals() and tipo_final and 
                len(tipo_final) > 0 and
                "Alarma Parcial" in tipo_final):
                
                # Aplicar filtro solo para "Alarma por cliente"
                tabla_dinamica = tabla_dinamica[tabla_dinamica["Total"] >= 3]
            
            tabla_dinamica = tabla_dinamica.reset_index(drop=True)

            # --- SECCIÓN DE TARJETAS Y TABLA ---
            col_tabla, col_metricas = st.columns([3, 1])
            
            with col_tabla:
                st.dataframe(tabla_dinamica, use_container_width=True)

                st.download_button(
                    label="📥 Descargar tabla (.csv)",
                    data=tabla_dinamica.to_csv().encode("utf-8"),
                    file_name="tabla_dinamica.csv",
                    mime="text/csv"
                )

            with col_metricas:
                st.subheader("📊 Métricas")
                
                # --- MÉTRICAS DE ÚLTIMOS 30 MINUTOS (SIN FILTROS) ---
                ahora = datetime.now()
                hace_30_min = ahora - timedelta(minutes=30)
                df_ultimos_30min = df[df["HoraPeru"] >= hace_30_min]
                
                # Métrica 1: OLTs con caídas por puerto (sin condición de cantidad)
                df_puerto_30min = df_ultimos_30min[
                    ((df_ultimos_30min["Gestor"].str.lower() == "huawei") & 
                     (df_ultimos_30min["TipoFinal"] == "Alarma por puerto")) |
                    ((df_ultimos_30min["Gestor"].str.lower() == "zte") & 
                     (df_ultimos_30min["strAckUserName"] == "Alarmas Puerto"))
                ]
                
                olts_caidas_puerto = df_puerto_30min["DEV"].unique()
                nombres_olts_puerto = ", ".join(olts_caidas_puerto) if len(olts_caidas_puerto) > 0 else "Ninguna"
                
                st.metric(
                    "🏢 OLTs con caídas por puerto (30min)", 
                    len(olts_caidas_puerto),
                    help="OLTs con alarmas de puerto en los últimos 30 minutos"
                )
                st.caption(f"**OLTs:** {nombres_olts_puerto}")
                
                # Métrica 2: OLTs con caídas parciales (3+ alarmas en la misma hora)
                df_parciales_30min = df_ultimos_30min[
                    ((df_ultimos_30min["Gestor"].str.lower() == "huawei") & 
                     (df_ultimos_30min["TipoFinal"] == "Alarma Parcial")) |
                    ((df_ultimos_30min["Gestor"].str.lower() == "zte") & 
                     (df_ultimos_30min["strAckUserName"] == "Alarmas Parciales"))
                ]
                
                # Agrupar por DEV + HoraPeru y contar, filtrar solo >= 3
                agrupado_parciales = df_parciales_30min.groupby(["DEV", "HoraPeru"]).size().reset_index(name='Total')
                agrupado_parciales_filtrado = agrupado_parciales[agrupado_parciales["Total"] >= 3]
                
                olts_caidas_parciales = agrupado_parciales_filtrado["DEV"].unique()
                nombres_olts_parciales = ", ".join(olts_caidas_parciales) if len(olts_caidas_parciales) > 0 else "Ninguna"
                
                st.metric(
                    "🔴 OLTs con caídas parciales (30min)", 
                    len(olts_caidas_parciales),
                    help="OLTs con 3+ alarmas por cliente en la misma hora (últimos 30 min)"
                )
                st.caption(f"**OLTs:** {nombres_olts_parciales}")
            
            # --- DETALLE DE REGISTROS ---
            st.markdown("### 🔎 Detalle de registros")
            if not tabla_dinamica.empty:
                seleccion = st.selectbox(
                    "Selecciona una fila:",
                    tabla_dinamica.index,
                    format_func=lambda i: f"{tabla_dinamica.loc[i, 'DEV']} - {tabla_dinamica.loc[i, 'SN']}-{tabla_dinamica.loc[i, 'PN']} - Total: {tabla_dinamica.loc[i, 'Total']}"
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
                                if gestor_seleccionado.lower() == "huawei":
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

                                response = requests.get(url, params=params)

                                if response.status_code == 200:
                                    try:
                                        json_data = response.json()
                                        df_json = pd.json_normalize(json_data)

                                        try:
                                            df_clientes = pd.read_parquet("clientes_TDP.parquet")
                                        except Exception as e:
                                            st.error(f"⚠️ Error al cargar el archivo de clientes: {e}")
                                            df_clientes = None
                                        
                                        if gestor_seleccionado.lower() == "huawei":
                                            columnas_deseadas = ["ALIAS", "LSTDOWNTIME", "LSTUPTIME", "ONTID", "OperState"]
                                        else:
                                            columnas_deseadas = ["ONUID", "OperState", "AUTHINFO", "LASTOFFTIME"]
                                        
                                        columnas_existentes = [c for c in columnas_deseadas if c in df_json.columns]
                                        df_mostrar = df_json[columnas_existentes]

                                        # Hacer merge con el archivo de clientes para obtener el serial number
                                        if df_clientes is not None and 'ALIAS' in df_mostrar.columns:
                                            # Renombrar la columna para hacer el merge
                                            df_clientes_merge = df_clientes.rename(columns={'SUBSCRIPCION': 'ALIAS'}).astype(str)
                                            
                                            # Hacer el merge left para mantener todos los registros del JSON
                                            df_mostrar = df_mostrar.merge(
                                                df_clientes_merge[['ALIAS', 'SERIAL NUMBER']], 
                                                on='ALIAS', 
                                                how='left'
                                            )
                                            
                                            # Reordenar columnas para que el serial number esté visible
                                            column_order = ['SERIAL NUMBER'] + [col for col in df_mostrar.columns if col != 'SERIAL NUMBER']
                                            df_mostrar = df_mostrar[column_order]

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

            # --- CONSULTA MANUAL POR SERIAL ---
            if 'show_consultation' not in st.session_state:
                st.session_state.show_consultation = False
            if 'consultation_result' not in st.session_state:
                st.session_state.consultation_result = None
            
            if st.button("🔎 Consultar Estado de ONT", type="primary", use_container_width=True):
                st.session_state.show_consultation = True
                st.session_state.consultation_result = None

            if st.session_state.show_consultation:
                st.subheader("Consulta por Serial Number")
                
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
                
                if submit_btn and serial_input:
                    with st.spinner("🔍 Consultando información del ONT..."):
                        # Pasar el gestor_seleccionado a la función
                        resultado = consultar_serial_api(serial_input.strip(), gestor_seleccionado)
                        st.session_state.consultation_result = resultado
                        st.rerun()
                
                if cancel_btn:
                    st.session_state.show_consultation = False
                    st.session_state.consultation_result = None
                    st.rerun()

            if st.session_state.consultation_result:
                st.markdown("---")
                resultado = st.session_state.consultation_result
                
                if "error" in resultado:
                    st.error(f"❌ **Error en la consulta:** {resultado['error']}")
                else:
                    st.success("✅ **ONT encontrado exitosamente!**")
                    
                    col1, col2 = st.columns(2)
                    
                    # ====================================
                    # COLUMNA 1: Información del ONT/ONU
                    # ====================================
                    with col1:
                        st.subheader("📋 Información del Equipo")
                        
                        # Detectar si es Huawei o ZTE por la estructura del JSON
                        if "datos_ont" in resultado:  # HUAWEI
                            datos = resultado["datos_ont"]
                            st.metric("📟 Serial", resultado["serial_number"])
                            st.metric("🏷️ Alias", datos["alias"])
                            st.metric("🔢 ONT ID", datos["ontid"])
                            st.metric("📊 Perfil", datos["lineprof"])
                            st.write(f"**📍 Ubicación:** {datos['dev_completo']}")
                            
                        elif "datos_onu" in resultado:  # ZTE
                            datos = resultado["datos_onu"]
                            st.metric("📟 Serial", resultado["serial_number"])
                            st.metric("🏷️ Name", datos["name"])
                            st.metric("🔢 ONU ID", datos["onuno"])
                            st.metric("📍 PON ID", datos["ponid"])
                            st.write(f"**🌐 OLT ID:** {datos['oltid']}")
                            st.write(f"**🔗 OID:** {datos['oid']}")
                            
                            # Mostrar estado ONU (solo ZTE)
                            if "estado_onu" in resultado:
                                estado = resultado["estado_onu"]
                                st.write(f"**🟢 Admin State:** {estado['admin_state']}")
                                st.write(f"**📡 Oper State:** {estado['oper_state']}")
                                st.write(f"**⏰ Last Off Time:** {estado['last_off_time']}")
                    
                    # ====================================
                    # COLUMNA 2: Parámetros Ópticos
                    # ====================================
                    with col2:
                        st.subheader("📊 Estado Óptico")
                        opticos = resultado["parametros_opticos"]
                        
                        # RX Power con indicadores (igual para ambos)
                        rx_power = opticos['rx_power']
                        if rx_power != "--" and rx_power != "N/A":
                            try:
                                rx_value = float(rx_power.split()[0])
                                if rx_value >= -27:
                                    st.metric("📡 RX Power", rx_power, delta="Óptimo", delta_color="normal")
                                elif rx_value >= -30:
                                    st.metric("📡 RX Power", rx_power, delta="Aceptable", delta_color="off")
                                else:
                                    st.metric("📡 RX Power", rx_power, delta="Crítico", delta_color="inverse")
                            except:
                                st.metric("📡 RX Power", rx_power)
                        else:
                            st.metric("📡 RX Power", rx_power)
                        
                        # TX Power
                        st.metric("📤 TX Power", opticos['tx_power'])
                        
                        # Temperatura
                        st.metric("🌡️ Temperatura", opticos['temperature'])
                        
                        # Voltaje
                        st.metric("⚡ Voltaje", opticos['voltage'])
                        
                        # Corriente Bias (nombres diferentes)
                        bias_key = 'bias_current' if 'bias_current' in opticos else 'tx_bias'
                        st.metric("🔋 Corriente Bias", opticos[bias_key])
                        
                        # Ranging Distance (solo Huawei)
                        if 'ranging_distance' in opticos:
                            st.metric("📏 Distancia", opticos['ranging_distance'])
    
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

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style='text-align:center; font-size:14px; color:gray;'>
    Desarrollado con 💚 by <b>AJ</b> — 2025
</div>
""", unsafe_allow_html=True)