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
        df = pd.read_csv(data, low_memory=False, dtype_backend='numpy_nullable')
        
        return df
    except Exception as e:
        print(f"❌ Error al descargar {url}: {e}")
        return pd.DataFrame()


def parsear_fecha_multiple_formato(fecha_serie):
    """
    Intenta parsear fechas en múltiples formatos comunes.
    Formatos probados:
    - %d/%m/%Y %H:%M:%S (01/12/2025 15:30:45)
    - %Y-%m-%d %H:%M:%S (2025-12-01 15:30:45)
    - %d-%m-%Y %H:%M:%S (01-12-2025 15:30:45)
    - ISO 8601 (auto-detectado por pandas)
    """
    if fecha_serie.isna().all():
        return fecha_serie
    
    # Lista de formatos a probar en orden
    formatos = [
        "%d/%m/%Y %H:%M:%S",  # 01/12/2025 15:30:45
        "%Y-%m-%d %H:%M:%S",  # 2025-12-01 15:30:45
        "%d-%m-%Y %H:%M:%S",  # 01-12-2025 15:30:45
        "%d/%m/%Y %H:%M",     # 01/12/2025 15:30
        "%Y-%m-%d %H:%M",     # 2025-12-01 15:30
        "%d/%m/%Y",           # 01/12/2025
        "%Y-%m-%d",           # 2025-12-01
    ]
    
    resultado = pd.Series([pd.NaT] * len(fecha_serie), index=fecha_serie.index)
    pendientes = fecha_serie.copy()
    
    # Probar cada formato
    for formato in formatos:
        if pendientes.notna().sum() == 0:
            break
            
        try:
            parseadas = pd.to_datetime(pendientes, format=formato, errors='coerce')
            validas = parseadas.notna()
            resultado[validas] = parseadas[validas]
            pendientes[validas] = pd.NA
        except:
            continue
    
    # Último intento: dejar que pandas infiera el formato
    if pendientes.notna().sum() > 0:
        try:
            parseadas = pd.to_datetime(pendientes, errors='coerce', infer_datetime_format=True)
            validas = parseadas.notna()
            resultado[validas] = parseadas[validas]
        except:
            pass
    
    return resultado

    
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
    """Convierte números con decimales a enteros (2.0 → 2) y mantiene texto."""
    if pd.isna(x):
        return "?"
    try:
        val_float = float(x)
        if val_float.is_integer():
            return str(int(val_float))
        return str(val_float)
    except (ValueError, TypeError):
        return str(x).strip() if str(x).strip() else "?"


@st.cache_data(ttl=14400)
def get_alarmas_historicas():
    """Descarga SOLO alarmas históricas con caché de 4 horas."""
    print("🔄 Descargando alarmas históricas...")
    historicas_df = download_csv(URL_HISTORICAS)
    
    if not historicas_df.empty:
        if "Gestor" not in historicas_df.columns:
            historicas_df["Gestor"] = "Histórico"
        
        historicas_df["_Origen"] = "Histórico"
    
    print(f"✅ Históricas cargadas: {len(historicas_df):,} registros")
    return historicas_df


@st.cache_data(ttl=900)
def get_alarmas_actuales():
    """Descarga SOLO alarmas actuales (Huawei y ZTE) con caché de 15 minutos."""
    print("🔄 Descargando alarmas actuales (Huawei + ZTE)...")
    
    huawei_df = download_csv(URL_HUAWEI)
    zte_df = download_csv(URL_ZTE)

    if not huawei_df.empty:
        huawei_df["Gestor"] = "Huawei"
        huawei_df["_Origen"] = "Actual_Huawei"
        
    if not zte_df.empty:
        zte_df["Gestor"] = "ZTE"
        zte_df["_Origen"] = "Actual_ZTE"

    actuales = pd.concat([huawei_df, zte_df], ignore_index=True)
    
    print(f"✅ Actuales cargadas: {len(actuales):,} registros (Huawei: {len(huawei_df)}, ZTE: {len(zte_df)})")
    return actuales


@st.cache_data(ttl=900)
def get_alarmas():
    """Combina alarmas actuales e históricas + procesa datos de clientes."""
    
    inicio = datetime.now()
    
    # Obtener alarmas con cachés diferenciados
    alarmas_actuales = get_alarmas_actuales()
    alarmas_historicas = get_alarmas_historicas()
    
    # Combinar todas las alarmas
    alarmas = pd.concat([alarmas_actuales, alarmas_historicas], ignore_index=True)
    
    if alarmas.empty:
        print("⚠️ No se encontraron alarmas")
        return alarmas

    print(f"📊 Total combinado ANTES de procesamiento: {len(alarmas):,} alarmas")

    # --- 🔹 Cargar clientes activos ---
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
            alarmas["DEV"].fillna("?").astype(str) + "-" +
            alarmas["FN"].apply(limpiar_num) + "-" +
            alarmas["SN"].apply(limpiar_num) + "-" +
            alarmas["PN"].apply(limpiar_num)
        )
    
    if "NAME_ALARM" not in alarmas.columns and "FaultID" in alarmas.columns:
        alarmas["NAME_ALARM"] = alarmas["FaultID"].apply(map_name_alarm)

    # --- 🔹 Merge con clientes ---
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
        clientes_tdp["SUBSCRIPCION"] = clientes_tdp["SUBSCRIPCION"].astype(str).str.strip()
        alarmas["AditionalInfo"] = alarmas["AditionalInfo"].astype(str).str.strip()

        alarmas = alarmas.merge(
            clientes_tdp[["SUBSCRIPCION", "SERIAL NUMBER"]],
            left_on="AditionalInfo",
            right_on="SUBSCRIPCION",
            how="left"
        )

        alarmas = alarmas.rename(columns={"SERIAL NUMBER": "SerialNumber_TDP"})
        alarmas = alarmas.drop(columns=["SUBSCRIPCION"], errors="ignore")
        print(f"✅ Cruce con clientes_TDP completado")
    except Exception as e:
        print(f"⚠️ Error al cruzar con clientes_TDP.parquet: {e}")

    # --- 🔹 PROCESAMIENTO CRÍTICO DE FECHAS (MEJORADO) ---
    print("\n🔍 Iniciando parseo de fechas con múltiples formatos...")
    
    if "HoraPeru" in alarmas.columns:
        # Guardar formato original para diagnóstico (solo primeros valores para no saturar memoria)
        alarmas["_HoraPeru_Original"] = alarmas["HoraPeru"].astype(str)
        
        # Guardar una muestra de formatos originales para debug
        muestra_fechas = alarmas["HoraPeru"].dropna().head(10).tolist()
        print(f"📅 Muestra de fechas originales: {muestra_fechas[:3]}")
        
        # Aplicar parseo múltiple formato
        alarmas["HoraPeru"] = parsear_fecha_multiple_formato(alarmas["HoraPeru"])
        
        # Estadísticas de parseo
        total_registros = len(alarmas)
        fechas_validas = alarmas["HoraPeru"].notna().sum()
        fechas_invalidas = alarmas["HoraPeru"].isna().sum()
        tasa_exito = (fechas_validas / total_registros * 100) if total_registros > 0 else 0
        
        print(f"✅ Parseo completado:")
        print(f"   - Fechas válidas: {fechas_validas:,} ({tasa_exito:.1f}%)")
        print(f"   - Fechas inválidas: {fechas_invalidas:,} ({100-tasa_exito:.1f}%)")
        
        # CRÍTICO: Solo eliminar si el % de pérdida es aceptable
        if fechas_invalidas > 0:
            porcentaje_perdida = (fechas_invalidas / total_registros * 100)
            
            if porcentaje_perdida > 50:
                print(f"\n⚠️⚠️⚠️ ALERTA: {porcentaje_perdida:.1f}% de datos sin fecha!")
                print("⚠️ Revisa el formato de fecha en tu archivo histórico")
                print("⚠️ Se mantendrán todos los registros para investigación")
                # NO eliminar datos si hay mucha pérdida
            else:
                print(f"ℹ️ Eliminando {fechas_invalidas:,} registros sin fecha válida")
                alarmas = alarmas.dropna(subset=["HoraPeru"])
    else:
        print("⚠️ Columna 'HoraPeru' no encontrada en los datos")
    
    # --- 🔹 Calcular tiempo de procesamiento ---
    tiempo_total = (datetime.now() - inicio).total_seconds()
    
    # --- 🔹 Estadísticas finales ---
    print("\n" + "="*60)
    print(f"⏱️  TIEMPO DE PROCESAMIENTO: {tiempo_total:.2f} segundos")
    print(f"📊 TOTAL DE ALARMAS PROCESADAS: {len(alarmas):,}")
    
    print(f"\n📦 DISTRIBUCIÓN POR ORIGEN:")
    if "_Origen" in alarmas.columns:
        print(alarmas["_Origen"].value_counts().to_string())
    
    print(f"\n📊 DISTRIBUCIÓN POR GESTOR:")
    print(alarmas["Gestor"].value_counts().to_string())
    
    if len(alarmas) > 0 and "HoraPeru" in alarmas.columns:
        alarmas_con_fecha = alarmas["HoraPeru"].notna()
        if alarmas_con_fecha.sum() > 0:
            print(f"\n📅 RANGO DE FECHAS ({alarmas_con_fecha.sum():,} registros con fecha):")
            print(f"   - Más antigua: {alarmas.loc[alarmas_con_fecha, 'HoraPeru'].min()}")
            print(f"   - Más reciente: {alarmas.loc[alarmas_con_fecha, 'HoraPeru'].max()}")
    
    if not clientes.empty and "DEV_2" in alarmas.columns:
        coincidencias = alarmas["DEV_2"].isin(clientes["DEV_2"]).sum()
        print(f"\n✅ Coincidencias con clientes: {coincidencias:,} / {len(alarmas):,} ({coincidencias/len(alarmas)*100:.1f}%)")
    
    print("="*60 + "\n")

    return alarmas


def limpiar_cache():
    """Limpia el caché de Streamlit para forzar recarga de datos."""
    st.cache_data.clear()
    print("🗑️ Caché limpiado")