import pandas as pd
import requests
from io import StringIO
import streamlit as st  
# URLs de tus CSV publicados en Google Sheets
URL_HUAWEI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTign5FwsuyQIprayFCmuNAmDexWqKZUYM7tN5i0a5rAU_0UprfZWQUSxX4bJ2m5cIP7YzMiFou75CW/pub?gid=0&single=true&output=csv"
URL_ZTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vRY5_ja1U1Ny4KWCefOi6zV1WFDUqQdo8_MyDlGLSSIUYnW3LI3fN7qzT7gKs2xOfu4IrLt7OcVnNzm/pub?gid=0&single=true&output=csv"



def download_csv(url):
    """Descarga CSV desde URL pública de Google Sheets."""
    try:
        response = requests.get(url)
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

def get_alarmas():
    """Descarga y combina alarmas de Huawei y ZTE + une datos de clientes activos."""
    
    # Descargar alarmas
    huawei_df = download_csv(URL_HUAWEI)
    zte_df = download_csv(URL_ZTE)

    if not huawei_df.empty:
        huawei_df["Gestor"] = "Huawei"
    if not zte_df.empty:
        zte_df["Gestor"] = "ZTE"

    alarmas = pd.concat([huawei_df, zte_df], ignore_index=True)

    # Si no hay alarmas, devolvemos vacío
    if alarmas.empty:
        return alarmas

    # --- 🔹 Cargar clientes activos desde Parquet ---
    try:
        clientes = pd.read_parquet("clientes_activos.parquet")
        if "Etiquetas de fila" in clientes.columns:
            clientes = clientes.rename(columns={"Etiquetas de fila": "DEV_2"})
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
        clientes = clientes.rename(columns={"Etiquetas de fila": "DEV_2"})
        
        # Traer la columna "Total general" como "Cliente_puerto"
        alarmas = alarmas.merge(
            clientes[["DEV_2", "Total general"]],
            on="DEV_2", how="left"
        )
        alarmas = alarmas.rename(columns={"Total general": "Cliente_puerto"})
    print("🔎 Ejemplo de DEV_2 en alarmas:")
    print(alarmas["DEV_2"].dropna().head(5).to_list())

    if not clientes.empty:
        print("📋 Ejemplo de Etiquetas de fila en clientes:")
        print(clientes["DEV_2"].dropna().head(5).to_list())

        # Verificamos coincidencias reales
        coincidencias = alarmas["DEV_2"].isin(clientes["DEV_2"]).sum()
        print(f"✅ Coincidencias encontradas: {coincidencias} / {len(alarmas)} filas")
    else:
        print("⚠️ Clientes está vacío")

    return alarmas