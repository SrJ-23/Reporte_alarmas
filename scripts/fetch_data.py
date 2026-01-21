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

# ================= FUNCIONES BASE =================

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

# ================= FUNCIONES DE CARGA =================

@st.cache_data(ttl=300, show_spinner="Cargando alarmas actuales...")
def get_alarmas_actuales():
    """
    Carga SOLO alarmas actuales desde Google Sheets (Huawei + ZTE)
    Cache: 5 minutos
    """
    print("🔄 Descargando alarmas actuales desde Google Sheets...")
    
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


@st.cache_data(ttl=86400, show_spinner="Cargando alarmas históricas...")
def get_alarmas_historicas(start_date, end_date):
    """
    Carga SOLO alarmas históricas desde Supabase con filtro de rango
    Cache: 24 horas por combinación de fechas
    
    Args:
        start_date: fecha inicio (date o datetime)
        end_date: fecha fin (date o datetime)
    """
    print(f"📚 Cargando históricas desde Supabase: {start_date} a {end_date}")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        response = supabase.rpc(
            "get_alarmas_historico_por_rango",
            {
                "p_start_date": str(start_date),
                "p_end_date": str(end_date)
            }
        ).execute()

        df = pd.DataFrame(response.data)

        if not df.empty:
            df["Gestor"] = df.get("Gestor", "Histórico")
            df["_Origen"] = "Supabase_Histórico"
            df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors="coerce")
            
            st.session_state['timestamp_historicas'] = datetime.now()
        
        print(f"✅ Cargadas {len(df):,} alarmas históricas")
        return df
    
    except Exception as e:
        print(f"❌ Error al cargar históricas: {e}")
        st.error(f"Error al cargar alarmas históricas: {e}")
        return pd.DataFrame()


def get_alarmas_completas(start_date, end_date, incluir_actuales=True):
    """
    Combina alarmas históricas del rango + alarmas actuales (opcional)
    
    Args:
        start_date: fecha inicio del rango
        end_date: fecha fin del rango
        incluir_actuales: si True, incluye alarmas actuales de Google Sheets
    
    Returns:
        DataFrame combinado y procesado
    """
    print(f"🔄 Cargando alarmas completas (actuales={incluir_actuales})")
    
    inicio = datetime.now()
    
    # 1. Cargar históricas del rango
    alarmas_historicas = get_alarmas_historicas(start_date, end_date)
    
    # 2. Cargar actuales si se solicita
    if incluir_actuales:
        alarmas_actuales = get_alarmas_actuales()
    else:
        alarmas_actuales = pd.DataFrame()
    
    # 3. Combinar
    if not alarmas_actuales.empty and not alarmas_historicas.empty:
        alarmas = pd.concat([alarmas_actuales, alarmas_historicas], ignore_index=True)
        print(f"📊 Combinadas: {len(alarmas_actuales):,} actuales + {len(alarmas_historicas):,} históricas = {len(alarmas):,} total")
    elif not alarmas_historicas.empty:
        alarmas = alarmas_historicas.copy()
        print(f"📊 Solo históricas: {len(alarmas):,}")
    elif not alarmas_actuales.empty:
        alarmas = alarmas_actuales.copy()
        print(f"📊 Solo actuales: {len(alarmas):,}")
    else:
        print("⚠️ No se cargaron datos")
        return pd.DataFrame()
    
    # 4. Procesar datos
    alarmas = procesar_alarmas(alarmas)
    
    # 5. Guardar metadata
    st.session_state['timestamp_procesamiento'] = datetime.now()
    st.session_state['tiempo_procesamiento'] = (datetime.now() - inicio).total_seconds()
    
    print(f"✅ Procesamiento completo en {st.session_state['tiempo_procesamiento']:.2f}s")
    
    return alarmas


# ================= PROCESAMIENTO UNIFICADO =================

def procesar_alarmas(df):
    """
    Aplica todas las transformaciones a un DataFrame de alarmas
    """
    if df.empty:
        return df
    
    # --- Columnas Calculadas ---
    if all(col in df.columns for col in ["DEV", "FN", "SN", "PN"]):
        df["DEV_2"] = (
            df["DEV"].fillna("?").astype(str) + "-" +
            df["FN"].apply(limpiar_num) + "-" +
            df["SN"].apply(limpiar_num) + "-" +
            df["PN"].apply(limpiar_num)
        )
    
    if "NAME_ALARM" not in df.columns and "FaultID" in df.columns:
        df["NAME_ALARM"] = df["FaultID"].apply(map_name_alarm)

    # --- Cruces con Parquets (Si existen) ---
    try:
        clientes = pd.read_parquet("clientes_activos.parquet")
        if "Etiquetas de fila" in clientes.columns:
            clientes = clientes.rename(columns={"Etiquetas de fila": "DEV_2"})
        if "DEV_2" in df.columns:
            df = df.merge(clientes[["DEV_2", "Total general"]], on="DEV_2", how="left")
            df = df.rename(columns={"Total general": "Cliente_puerto"})
    except:
        pass

    try:
        clientes_tdp = pd.read_parquet("clientes_TDP.parquet")
        # Asegurar tipos string para cruce
        df["AditionalInfo"] = df["AditionalInfo"].astype(str).str.strip()
        clientes_tdp["SUBSCRIPCION"] = clientes_tdp["SUBSCRIPCION"].astype(str).str.strip()
        
        df = df.merge(
            clientes_tdp[["SUBSCRIPCION", "SERIAL NUMBER"]],
            left_on="AditionalInfo", right_on="SUBSCRIPCION", how="left"
        )
        df = df.rename(columns={"SERIAL NUMBER": "SerialNumber_TDP"})
    except:
        pass

    # --- CORRECCIÓN FINAL DE FECHAS (Aquí estaba el error) ---
    if "HoraPeru" in df.columns:
        # 1. Convertimos la columna mixta (Object) a Datetime REAL
        # 'utc=True' es vital para que entienda tanto los textos de Sheets como las fechas de Supabase
        df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors='coerce', utc=True)
        
        # 2. Ahora que YA es datetime, podemos usar .dt sin que explote
        df["HoraPeru"] = df["HoraPeru"].dt.tz_localize(None)
        
        # 3. Creamos columna Fecha y ordenamos
        df['Fecha'] = df['HoraPeru'].dt.date
        df = df.sort_values("HoraPeru", ascending=False)

    return df
# ================= WRAPPER DE COMPATIBILIDAD =================

def get_alarmas(start_date=None, end_date=None, forzar_recarga=False):
    """
    Función de compatibilidad con código legacy
    
    Si NO se pasan fechas: retorna solo alarmas actuales
    Si SÍ se pasan fechas: retorna completas (históricas + actuales)
    """
    if forzar_recarga:
        st.cache_data.clear()
    
    # Sin fechas = solo actuales (comportamiento original de app.py)
    if start_date is None and end_date is None:
        alarmas = get_alarmas_actuales()
        return procesar_alarmas(alarmas)
    
    # Con fechas = completas (para Dashboard Ejecutivo)
    else:
        return get_alarmas_completas(start_date, end_date, incluir_actuales=True)


# ================= METADATA =================

def get_info_cache():
    """Retorna información sobre el estado del caché"""
    return {
        'timestamp_actuales': st.session_state.get('timestamp_actuales'),
        'timestamp_historicas': st.session_state.get('timestamp_historicas'),
        'timestamp_procesamiento': st.session_state.get('timestamp_procesamiento'),
        'tiempo_procesamiento': st.session_state.get('tiempo_procesamiento')
    }