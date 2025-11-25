import pandas as pd
import requests
from io import StringIO
import streamlit as st
from datetime import datetime, timedelta

# URLs de tus CSV publicados en Google Sheets
URL_HUAWEI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTign5FwsuyQIprayFCmuNAmDexWqKZUYM7tN5i0a5rAU_0UprfZWQUSxX4bJ2m5cIP7YzMiFou75CW/pub?gid=0&single=true&output=csv"
URL_ZTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRY5_ja1U1Ny4KWCefOi6zV1WFDUqQdo8_MyDlGLSSIUYnW3LI3fN7qzT7gKs2xOfu4IrLt7OcVnNzm/pub?gid=0&single=true&output=csv"
URL_HISTORICAS = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSlxDn5R_fj9uqy2FmFVWXWJBFvwOobDPby-CEW_GgScpimkgY6sAmnIPSGQm9OuIVR9b9aMiYycqEZ/pub?gid=0&single=true&output=csv"


def download_csv(url):
    """Descarga CSV desde URL pública de Google Sheets."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        data = StringIO(response.text)
        df = pd.read_csv(data)  
        
        return df
    except Exception as e:
        print(f"Error al descargar {url}: {e}")
        return pd.DataFrame()

    
def map_name_alarm(code):
    """Mapea códigos de alarma a descripciones."""
    mapping = {
        1014: "The link between the server and the NE is broken",
        400123: "Card Offline",
        35273: "[GPON Alarm] PON LOS (Loss of signal)",
        430660006: "[GPON Alarm] PON LOS (ONU Dropped)",
        351130000: "[GPON Alarm] ONU LOS (Loss of Signal)",
        722445000: "[GPON Alarm] ONU LOS (Loss of Signal)"
    }
    return mapping.get(code, "")


def limpiar_num(x):
    try:
        # Convertir 2.0 -> 2 y mantener texto normal
        return str(int(float(x))) if str(x).replace('.', '', 1).isdigit() else str(x)
    except:
        return str(x)


@st.cache_data(ttl=14400)  # 4 horas de caché para históricas (se actualiza 2-3 veces al día)
def get_alarmas_historicas():
    """Descarga SOLO alarmas históricas con caché de 4 horas."""
    print("🔄 Descargando alarmas históricas...")
    historicas_df = download_csv(URL_HISTORICAS)
    
    if not historicas_df.empty:
        if "Gestor" not in historicas_df.columns:
            historicas_df["Gestor"] = "Histórico"
    
    print(f"✅ Históricas cargadas: {len(historicas_df):,} registros")
    return historicas_df


@st.cache_data(ttl=900)  # 15 minutos de caché para alarmas actuales
def get_alarmas_actuales():
    """Descarga SOLO alarmas actuales (Huawei y ZTE) con caché de 15 minutos."""
    print("🔄 Descargando alarmas actuales (Huawei + ZTE)...")
    
    huawei_df = download_csv(URL_HUAWEI)
    zte_df = download_csv(URL_ZTE)

    if not huawei_df.empty:
        huawei_df["Gestor"] = "Huawei"
    if not zte_df.empty:
        zte_df["Gestor"] = "ZTE"

    actuales = pd.concat([huawei_df, zte_df], ignore_index=True)
    
    print(f"✅ Actuales cargadas: {len(actuales):,} registros (Huawei: {len(huawei_df)}, ZTE: {len(zte_df)})")
    return actuales


@st.cache_data(ttl=900)  # 15 minutos para el procesamiento completo
def get_alarmas():
    """Combina alarmas actuales e históricas + procesa datos de clientes."""
    
    inicio = datetime.now()
    
    # Obtener alarmas con cachés diferenciados
    alarmas_actuales = get_alarmas_actuales()
    alarmas_historicas = get_alarmas_historicas()
    
    # Combinar todas las alarmas
    alarmas = pd.concat([alarmas_actuales, alarmas_historicas], ignore_index=True)
    
    # Si no hay alarmas, devolvemos vacío
    if alarmas.empty:
        print("⚠️ No se encontraron alarmas")
        return alarmas

    print(f"📊 Total combinado: {len(alarmas):,} alarmas")

    # --- 🔹 Cargar clientes activos desde Parquet (caché automático por @st.cache_data) ---
    try:
        clientes = pd.read_parquet("clientes_activos.parquet")
        if "Etiquetas de fila" in clientes.columns:
            clientes = clientes.rename(columns={"Etiquetas de fila": "DEV_2"})
        print(f"✅ Clientes activos: {len(clientes):,} registros")
    except Exception as e:
        print(f"⚠️ No se pudo cargar clientes_activos.parquet: {e}")
        clientes = pd.DataFrame()

    # --- 🔹 Crear columnas extra ---
    if all(col in alarmas.columns for col in ["DEV", "FN", "SN", "PN"]):
        alarmas["DEV_2"] = (
            alarmas["DEV"].astype(str) + "-" +
            alarmas["FN"].apply(limpiar_num) + "-" +
            alarmas["SN"].apply(limpiar_num) + "-" +
            alarmas["PN"].apply(limpiar_num)
        )
    
    if "NAME_ALARM" not in alarmas.columns and "FaultID" in alarmas.columns:
        alarmas["NAME_ALARM"] = alarmas["FaultID"].apply(map_name_alarm)

    # --- 🔹 Buscar cliente por DEV_2 ---
    if not clientes.empty and "DEV_2" in clientes.columns:
        alarmas = alarmas.merge(
            clientes[["DEV_2", "Total general"]],
            on="DEV_2", how="left"
        )
        alarmas = alarmas.rename(columns={"Total general": "Cliente_puerto"})
        print(f"✅ Merge con clientes completado")

    # --- 🔹 Cruce con clientes TDP ---
    try:
        clientes_tdp = pd.read_parquet("clientes_TDP.parquet")

        # Asegurar tipos compatibles
        clientes_tdp["SUBSCRIPCION"] = clientes_tdp["SUBSCRIPCION"].astype(str)
        alarmas["AditionalInfo"] = alarmas["AditionalInfo"].astype(str)

        # Hacer merge: AditionalInfo ↔ SUBSCRIPCION
        alarmas = alarmas.merge(
            clientes_tdp[["SUBSCRIPCION", "SERIAL NUMBER"]],
            left_on="AditionalInfo",
            right_on="SUBSCRIPCION",
            how="left"
        )

        # Renombrar columna resultante para mayor claridad
        alarmas = alarmas.rename(columns={"SERIAL NUMBER": "SerialNumber_TDP"})

        # Ya no necesitamos la columna SUBSCRIPCION duplicada del parquet
        alarmas = alarmas.drop(columns=["SUBSCRIPCION"], errors="ignore")

        print(f"✅ Cruce con clientes_TDP completado")

    except Exception as e:
        print(f"⚠️ Error al cruzar con clientes_TDP.parquet: {e}")

    # --- 🔹 Procesar fechas ---
    alarmas["HoraPeru"] = pd.to_datetime(alarmas["HoraPeru"], format="%d/%m/%Y %H:%M:%S", errors="coerce")
    
    # Eliminar filas con fechas inválidas
    alarmas = alarmas.dropna(subset=["HoraPeru"])
    
    # --- 🔹 Calcular tiempo de procesamiento ---
    tiempo_total = (datetime.now() - inicio).total_seconds()
    
    # --- 🔹 Estadísticas finales ---
    print("\n" + "="*60)
    print(f"⏱️  TIEMPO DE PROCESAMIENTO: {tiempo_total:.2f} segundos")
    print(f"📊 TOTAL DE ALARMAS: {len(alarmas):,}")
    print(f"   - Actuales: {len(alarmas_actuales):,}")
    print(f"   - Históricas: {len(alarmas_historicas):,}")
    
    if len(alarmas) > 0:
        print(f"\n📅 RANGO DE FECHAS:")
        print(f"   - Más antigua: {alarmas['HoraPeru'].min()}")
        print(f"   - Más reciente: {alarmas['HoraPeru'].max()}")
    
    print(f"\n📊 DISTRIBUCIÓN POR GESTOR:")
    print(alarmas["Gestor"].value_counts().to_string())
    
    if not clientes.empty:
        coincidencias = alarmas["DEV_2"].isin(clientes["DEV_2"]).sum()
        print(f"\n✅ Coincidencias con clientes: {coincidencias:,} / {len(alarmas):,} ({coincidencias/len(alarmas)*100:.1f}%)")
    
    print("="*60 + "\n")

    return alarmas


# Función auxiliar para limpiar caché manualmente si es necesario
def limpiar_cache():
    """Limpia el caché de Streamlit para forzar recarga de datos."""
    st.cache_data.clear()
    print("🗑️ Caché limpiado")