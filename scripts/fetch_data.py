import pandas as pd
import numpy as np
import requests
from io import StringIO
import streamlit as st
from datetime import datetime, timedelta
from supabase import create_client, Client

# ================= CONFIGURACIÓN =================
URL_HUAWEI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTign5FwsuyQIprayFCmuNAmDexWqKZUYM7tN5i0a5rAU_0UprfZWQUSxX4bJ2m5cIP7YzMiFou75CW/pub?gid=0&single=true&output=csv"
URL_ZTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRY5_ja1U1Ny4KWCefOi6zV1WFDUqQdo8_MyDlGLSSIUYnW3LI3fN7qzT7gKs2xOfu4IrLt7OcVnNzm/pub?gid=0&single=true&output=csv"

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]

# ================= FUNCIONES BASE (SHEETS) =================

def download_csv(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = StringIO(response.text)
        return pd.read_csv(data, low_memory=False, dtype_backend='numpy_nullable')
    except Exception as e:
        print(f"❌ Error al descargar {url}: {e}")
        return pd.DataFrame()

def limpiar_num(x):
    if pd.isna(x): return "?"
    try:
        val_float = float(x)
        return str(int(val_float)) if val_float.is_integer() else str(val_float)
    except: return str(x).strip() if str(x).strip() else "?"

def map_name_alarm(code):
    mapping = {
        1014: "The link between the server and the NE is broken",
        400123: "Card Offline",
        35273: "[GPON Alarm] PON LOS (Loss of signal)",
        430660006: "[GPON Alarm] PON LOS (ONU Dropped)",
        351130000: "[GPON Alarm] ONU LOS (Loss of Signal)",
        722445000: "[GPON Alarm] ONU LOS (Loss of Signal)"
    }
    return mapping.get(code, "")

# ================= CARGA DE ACTUALES (GOOGLE SHEETS) =================

@st.cache_data(ttl=300, show_spinner="Cargando alarmas actuales...")
def get_alarmas_actuales():
    """
    Carga SOLO alarmas actuales desde Google Sheets.
    """
    print("🔄 Descargando alarmas actuales desde Google Sheets...")
    try: 
        huawei_df = download_csv(URL_HUAWEI)
        zte_df = download_csv(URL_ZTE)

        if not huawei_df.empty:
            huawei_df["Gestor"] = "Huawei"
            huawei_df["_Origen"] = "Actual_Huawei"
        
        if not zte_df.empty:
            zte_df["Gestor"] = "ZTE"
            zte_df["_Origen"] = "Actual_ZTE"

        actuales = pd.concat([huawei_df, zte_df], ignore_index=True)
        
        if not actuales.empty:
            st.session_state['timestamp_actuales'] = datetime.now()
        
        return actuales
    except:
        return pd.DataFrame()

# ================= CARGA DE HISTÓRICAS (SUPABASE) =================

@st.cache_data(ttl=86400, show_spinner="Cargando Histórico Blindado...")
def get_alarmas_historicas(start_date, end_date):
    """
    Carga histórica robusta. Baja datos día por día.
    """
    print(f"📚 Iniciando carga SQL Blindada: {start_date} a {end_date}")
    
    # --- CAMBIO: Usamos el cliente estándar sin opciones complejas ---
    # Al bajar día por día, el timeout por defecto es suficiente.
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    all_data = []
    
    if isinstance(start_date, datetime): start_date = start_date.date()
    if isinstance(end_date, datetime): end_date = end_date.date()
    
    # BLOCK SIZE = 1 (Día por día para máxima seguridad)
    block_size = 3 
    current_start = start_date
    
    # Barra de progreso
    progress_text = "Conectando a base de datos..."
    my_bar = st.progress(0, text=progress_text)
    total_days = (end_date - start_date).days + 1
    steps_done = 0

    try:
        while current_start <= end_date:
            current_end = min(current_start + timedelta(days=block_size - 1), end_date)
            
            pct = min(steps_done / total_days, 1.0)
            my_bar.progress(pct, text=f"📥 Descargando: {current_start}")
            
            try:
                response = supabase.rpc(
                    "get_alarmas_historico_por_rango",
                    {
                        "p_start_date": str(current_start),
                        "p_end_date": str(current_end)
                    }
                ).execute()
                
                if response.data:
                    all_data.extend(response.data)
            except Exception as e:
                print(f"   ⚠️ Error en día {current_start}: {e}")
            
            current_start = current_end + timedelta(days=1)
            steps_done += 1
            
        my_bar.empty()

        if not all_data:
            return pd.DataFrame()

        df = pd.DataFrame(all_data)
        df["_Origen"] = "Supabase_Histórico"
        df["Gestor"] = df.get("Gestor", "Histórico")

        # Limpieza de fechas
        if "HoraPeru" in df.columns:
            df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors="coerce")
            df["HoraPeru"] = df["HoraPeru"].dt.tz_localize(None)
            
        st.session_state['timestamp_historicas'] = datetime.now()
        print(f"✅ Cargadas {len(df):,} alarmas históricas")
        return df
    
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        return pd.DataFrame()

# ================= COORDINADOR =================

def get_alarmas_completas(start_date, end_date, incluir_actuales=True):
    """
    Coordinador de cargas.
    """
    inicio = datetime.now()
    
    # 1. Históricas
    alarmas_historicas = get_alarmas_historicas(start_date, end_date)
    
    # 2. Actuales (si se pide)
    if incluir_actuales:
        alarmas_actuales = get_alarmas_actuales()
    else:
        alarmas_actuales = pd.DataFrame()
    
    # 3. Combinar
    if not alarmas_actuales.empty and not alarmas_historicas.empty:
        alarmas = pd.concat([alarmas_actuales, alarmas_historicas], ignore_index=True)
    elif not alarmas_historicas.empty:
        alarmas = alarmas_historicas.copy()
    elif not alarmas_actuales.empty:
        alarmas = alarmas_actuales.copy()
    else:
        return pd.DataFrame()
    
    # 4. Procesar
    alarmas = procesar_alarmas(alarmas)
    
    st.session_state['timestamp_procesamiento'] = datetime.now()
    st.session_state['tiempo_procesamiento'] = (datetime.now() - inicio).total_seconds()
    
    return alarmas

# ================= PROCESAMIENTO =================

def procesar_alarmas(df):
    if df.empty: return df
    
    # Columnas Calculadas
    if all(col in df.columns for col in ["DEV", "FN", "SN", "PN"]):
        df["DEV_2"] = (
            df["DEV"].fillna("?").astype(str) + "-" +
            df["FN"].apply(limpiar_num) + "-" +
            df["SN"].apply(limpiar_num) + "-" +
            df["PN"].apply(limpiar_num)
        )
    
    if "NAME_ALARM" not in df.columns and "FaultID" in df.columns:
        df["NAME_ALARM"] = df["FaultID"].apply(map_name_alarm)

    # Cruces (con manejo de errores por si faltan archivos)
    try:
        clientes = pd.read_parquet("clientes_activos.parquet")
        if "Etiquetas de fila" in clientes.columns:
            clientes = clientes.rename(columns={"Etiquetas de fila": "DEV_2"})
        if "DEV_2" in df.columns:
            df = df.merge(clientes[["DEV_2", "Total general"]], on="DEV_2", how="left")
            df = df.rename(columns={"Total general": "Cliente_puerto"})
    except: pass

    try:
        clientes_tdp = pd.read_parquet("clientes_TDP.parquet")
        df["AditionalInfo"] = df["AditionalInfo"].astype(str).str.strip()
        clientes_tdp["SUBSCRIPCION"] = clientes_tdp["SUBSCRIPCION"].astype(str).str.strip()
        df = df.merge(
            clientes_tdp[["SUBSCRIPCION", "SERIAL NUMBER"]],
            left_on="AditionalInfo", right_on="SUBSCRIPCION", how="left"
        )
        df = df.rename(columns={"SERIAL NUMBER": "SerialNumber_TDP"})
    except: pass

    # Fechas
    if "HoraPeru" in df.columns:
        df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors='coerce', utc=True)
        df["HoraPeru"] = df["HoraPeru"].dt.tz_localize(None)
        df['Fecha'] = df['HoraPeru'].dt.date
        df = df.sort_values("HoraPeru", ascending=False)

    return df

# ================= METADATA =================
def get_info_cache():
    return {
        'timestamp_actuales': st.session_state.get('timestamp_actuales'),
        'timestamp_historicas': st.session_state.get('timestamp_historicas'),
        'timestamp_procesamiento': st.session_state.get('timestamp_procesamiento'),
        'tiempo_procesamiento': st.session_state.get('tiempo_procesamiento')
    }