import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Consulta Tiempo Real - ADCE", layout="wide")

st.title("🔍 Consulta en Tiempo Real")
st.caption("Consultas manuales directas a la API - Sin filtros heredados")

# Configuración de la API
ngrok_base_url = "https://leilani-thimblelike-lucklessly.ngrok-free.dev"

# Listas predefinidas de OLTs
HUAWEI_OLTS = [
    "OLT_MA5600T_CAJAMARCA_62", "OLT_MA5600T_CHINCHAALTA_40", "OLT_MA5600T_PUCALLPA_52", 
    "OLT_MA5600T_PUNO_43", "OLT_MA5800_ABANCAY_25", "OLT_MA5800_AREQUIPA_44", 
    "OLT_MA5800_AYAVIRI_7", "OLT_MA5800_BAMBAMARCA_4", "OLT_MA5800_BANOS_DEL_INCA_5", 
    "OLT_MA5800_BARRANCA_16", "OLT_MA5800_BARRANCO_24", "OLT_MA5800_BARRANCO_26", 
    "OLT_MA5800_CAJAMARCA_62_F2", "OLT_MA5800_CALLAO_52", "OLT_MA5800_CANETE_10", 
    "OLT_MA5800_CARABAYLLO_33", "OLT_MA5800_CASA_GRANDE_7", "OLT_MA5800_CAYMA_19", 
    "OLT_MA5800_CEDROS_DE_VILLA_2", "OLT_MA5800_CHINCHA_ALTA_42", "OLT_MA5800_CHORRILLOS_33", 
    "OLT_MA5800_CHORRILLOS_SG_34_F1", "OLT_MA5800_CHOTA_6", "OLT_MA5800_CHULUCANAS_8", 
    "OLT_MA5800_CIUDAD_NUEVA_12", "OLT_MA5800_CONO_SUR_14", "OLT_MA5800_CUSCO_66", 
    "OLT_MA5800_CUTERVO_8", "OLT_MA5800_EL_CERCADO_19", "OLT_MA5800_EL_PINO_2", 
    "OLT_MA5800_EL_RETABLO_21", "OLT_MA5800_HIGUERETA_39", "OLT_MA5800_HIGUERETA_41_F1", 
    "OLT_MA5800_HIGUERETA_41_F2", "OLT_MA5800_HIGUERETA_CQ_40_F1", "OLT_MA5800_HIGUERETA_CQ_40_F2", 
    "OLT_MA5800_HUACHO_45", "OLT_MA5800_HUACHO_46", "OLT_MA5800_HUANUCO_50", 
    "OLT_MA5800_HUARAL_30", "OLT_MA5800_HUARAZ_40", "OLT_MA5800_HUARAZ_40_F2", 
    "OLT_MA5800_HUAURA_9", "OLT_MA5800_ILAVE_4", "OLT_MA5800_ILO_18", "OLT_MA5800_IMPERIAL_8", 
    "OLT_MA5800_JAEN_17", "OLT_MA5800_LA_MOLINA_21", "OLT_MA5800_LA_MOLINA_22_F1", 
    "OLT_MA5800_LA_VICTORIA_42", "OLT_MA5800_LAS_CASUARINAS_7", "OLT_MA5800_LAS_FLORES_3", 
    "OLT_MA5800_LAS_GARDENIAS_13", "OLT_MA5800_LAS_LAGUNAS_17", "OLT_MA5800_LAS_LAGUNAS_18_F1", 
    "OLT_MA5800_LINCE_31", "OLT_MA5800_LOS_FICUS_23", "OLT_MA5800_LOS_OLIVOS_47", 
    "OLT_MA5800_LOS_ORGANOS_3", "OLT_MA5800_LURIN_11", "OLT_MA5800_MACARENA_4", 
    "OLT_MA5800_MAGDALENA_49", "OLT_MA5800_MAGDALENA_50_F1", "OLT_MA5800_MAGDALENA_50_F2", 
    "OLT_MA5800_MAGDALENA_51", "OLT_MA5800_MANCORA_8", "OLT_MA5800_MAQUETA_X7", 
    "OLT_MA5800_MIRAFLORES_66", "OLT_MA5800_MIRAFLORES_67", "OLT_MA5800_MIRAFLORES_68_F1", 
    "OLT_MA5800_MONTERRICO_53", "OLT_MA5800_MONTERRICO_55_F1", "OLT_MA5800_MONTERRICO_LC_54_F1", 
    "OLT_MA5800_NUEVA_CAJAMARCA_4", "OLT_MA5800_PAIJAN_5", "OLT_MA5800_PAITA_12", 
    "OLT_MA5800_PAMPAINALAMBRICA_13", "OLT_MA5800_PARAMONGA_7", "OLT_MA5800_PATIVILCA_5", 
    "OLT_MA5800_PIURA_59", "OLT_MA5800_PUCALLPA_52_F2", "OLT_MA5800_PUENTE_PIEDRA_3", 
    "OLT_MA5800_PUERTO_NUEVO_CL_1_F1", "OLT_MA5800_PUNO_47", "OLT_MA5800_QUERECOTILLO_4", 
    "OLT_MA5800_QUILLABAMBA_7", "OLT_MA5800_RIMAC_3", "OLT_MA5800_RIOJA_5", 
    "OLT_MA5800_SAGITARIO_10", "OLT_MA5800_SAN_BORJA_38", "OLT_MA5800_SAN_BORJA_39_F1", 
    "OLT_MA5800_SAN_BORJA_39_F2", "OLT_MA5800_SAN_BORJA_40", "OLT_MA5800_SAN_BORJA_41_F1", 
    "OLT_MA5800_SAN_ISIDRO_44_F1", "OLT_MA5800_SAN_ISIDRO_44_F2", "OLT_MA5800_SAN_ISIDRO_46", 
    "OLT_MA5800_SAN_ISIDRO_47_F1", "OLT_MA5800_SAN_ISIDRO_47_F2", "OLT_MA5800_SAN_JOSE_55", 
    "OLT_MA5800_SAN_JUAN_51", "OLT_MA5800_SAN_MIGUEL_17", "OLT_MA5800_SAN_ROQUE_20", 
    "OLT_MA5800_SANISIDRO_43", "OLT_MA5800_SANTA_CLARA_25", "OLT_MA5800_SANTA_PATRICIA_2", 
    "OLT_MA5800_SECHURA_4", "OLT_MA5800_SULLANA_48", "OLT_MA5800_SULLANA_48_F2", 
    "OLT_MA5800_TACNA_48", "OLT_MA5800_TALARA_23", "OLT_MA5800_TARAPOTO_46", 
    "OLT_MA5800_TINGO_MARIA_12", "OLT_MA5800_TRUJILLO_60", "OLT_MA5800_TUMBES_30", 
    "OLT_MA5800_URUBAMBA_6", "OLT_MA5800_VITARTE_44", "OLT_MA5800_WASHINGTON_58", 
    "OLT_MA5800_WASHINGTON_59_F1", "OLT_MA5800_WASHINGTON_59_F2", "OLT_MA5800_X17_MAQUETA", 
    "OLT_MA5800_YARINACOCHA_8", "OLT_MA5800_YUNGUYO_4", "OLT_MA5800_ZARUMILLA_9"
]

ZTE_OLTS = [
    "OLT_C610_RODRIGUEZ_DE_MENDOZA_5", "OLT_C300_ANDAHUAYLAS_10", "OLT_C300_AYACUCHO_44_F1", 
    "OLT_C300_AYACUCHO_44_F2", "OLT_C300_AZANGARO_6", "OLT_C300_BAGUA_CHICA_9", 
    "OLT_C300_BAGUA_GRANDE_5", "OLT_C300_CAJABAMBA_5", "OLT_C300_CAMANA_13", 
    "OLT_C300_CASMA_5", "OLT_C300_CERRO_DE_PASCO_10", "OLT_C300_CHACHAPOYAS_6", 
    "OLT_C300_CHANCAY_10", "OLT_C300_CHEPEN_14", "OLT_C300_DESAGUADERO_4", 
    "OLT_C300_GUADALUPE_5", "OLT_C300_HUAMACHUCO_07", "OLT_C300_HUANTA_8", 
    "OLT_C300_HUARMEY_10", "OLT_C300_JULI_4", "OLT_C300_JULIACA_54_F1", 
    "OLT_C300_JULIACA_54_F2", "OLT_C300_LA_MERCED_6", "OLT_C300_MAZAMARI_2", 
    "OLT_C300_MOQUEGUA_15", "OLT_C300_MOYOBAMBA_14", "OLT_C300_NAZCA_12", 
    "OLT_C300_OLMOS_5", "OLT_C300_PACASMAYO_15", "OLT_C300_PISCO_24", 
    "OLT_C300_PUERTO_MALDONADO_22", "OLT_C300_SATIPO_7", "OLT_C300_SICUANI_9", 
    "OLT_C300_TAMBO_GRANDE_5", "OLT_C300_TARAPOTO_46", "OLT_C300_TARMA_12", 
    "OLT_C300_TOCACHE_2", "OLT_C300_VIRU_6", "OLT_C300_YURIMAGUAS_8", 
    "OLT_C600_BARRANCO_25_F1", "OLT_C600_CHICLAYO_81", "OLT_C600_CHORRILLOS_35_F1", 
    "OLT_C600_LINCE_32", "OLT_C600_MAGDALENA_52_F1", "OLT_C600_PANDO-2", 
    "OLT_C600_ROSA_TORO_5", "OLT_C600_SAN_JOSE_56", "OLT_C600_WASHINGTON_60", 
    "OLT_C610_ACOBAMBA_2", "OLT_C610_ACOMAYO_1", "OLT_C610_AGUAYTIA_7", 
    "OLT_C610_AIJA_3", "OLT_C610_ANTABAMBA_2", "OLT_C610_AYABACA_3", 
    "OLT_C610_BOLIVAR", "OLT_C610_CABANA_2", "OLT_C610_CAJATAMBO_1", 
    "OLT_C610_CANDARAVE_1", "OLT_C610_CANGALLO_2", "OLT_C610_CARAZ_6", 
    "OLT_C610_CASCAS_1", "OLT_C610_CASTROVIRREYNA_2", "OLT_C610_CELENDIN_6", 
    "OLT_C610_CHACAS_1", "OLT_C610_CHALHUANCA_2", "OLT_C610_CHAVINILLO_1", 
    "OLT_C610_CHINCHEROS_2", "OLT_C610_CHIQUIAN_4", "OLT_C610_CHIVAY_3", 
    "OLT_C610_CHUQUIBAMBA_4", "OLT_C610_CHUQUIBAMBILLA_2", "OLT_C610_CHURCAMPA_3", 
    "OLT_C610_CONTUMAZA_1", "OLT_C610_CORONGO_2", "OLT_C610_COTAHUASI_2", 
    "OLT_C610_HUACAYBAMBA_1", "OLT_C610_HUACRACHUCO_1", "OLT_C610_HUANCA_SANCOS_2", 
    "OLT_C610_HUANCABAMBA_4", "OLT_C610_HUANCANE_5", "OLT_C610_HUARI_4", 
    "OLT_C610_HUAYTARA_2", "OLT_C610_INAPARI_1", "OLT_C610_IZCUCHACA_4", 
    "OLT_C610_JESUS_HUANUCO_1", "OLT_C610_JULCAN_1", "OLT_C610_JUMBILLA_1", 
    "OLT_C610_JUNIN_7", "OLT_C610_LA_JOLLA_AS_1_F1", "OLT_C610_LA_UNION_HUANUCO_2", 
    "OLT_C610_LAMPA_2", "OLT_C610_LAMUD_1", "OLT_C610_LIRCAY_6", "OLT_C610_LLAMELLIN_1", 
    "OLT_C610_LLATA_2", "OLT_C610_MACUSANI_2", "OLT_C610_MOHO_2", "OLT_C610_OCROS_1", 
    "OLT_C610_OMATE_1", "OLT_C610_OYON_3", "OLT_C610_PAMPAS_4", "OLT_C610_PANAO_1", 
    "OLT_C610_PARURO_1", "OLT_C610_PAUCARTAMBO_2", "OLT_C610_PAUSA_2", 
    "OLT_C610_PICOTA_1", "OLT_C610_PISCOBAMBA_1", "OLT_C610_POMABAMBA_3", 
    "OLT_C610_PUERTO_INCA_2", "OLT_C610_PUQUIO_2", "OLT_C610_PUTINA_2", 
    "OLT_C610_SAN_IGNACIO_6", "OLT_C610_SAN_JOSE_DE_SISA_1", "OLT_C610_SAN_LUIS_ANCASH_1", 
    "OLT_C610_SAN_MARCOS_CAJ_1", "OLT_C610_SAN_MIGUEL_CAJ_2", "OLT_C610_SAN_PABLO_4", 
    "OLT_C610_SANDIA_2", "OLT_C610_SANTIAGO_DE_CHUCO_1", "OLT_C610_SANTO_TOMAS_1", 
    "OLT_C610_SIHUAS_4", "OLT_C610_SUCCHUBAMBA_4", "OLT_C610_TAMBOBAMBA_2", 
    "OLT_C610_TARATA_1", "OLT_C610_TAYABAMBA_1", "OLT_C610_URCOS_4", 
    "OLT_C610_VILCAS_HUAMAN_2", "OLT_C610_YANAHUANCA_2", "OLT_C610_YANAOCA_1", 
    "OLT_C610_YAURI_4", "OLT_C610_YAUYOS_1", "OLT_C600_SURQUILLO_PRO", 
    "OLT_C300_SURQUILLO_LAB", "OLT_C610_AMBO_2", "OLT_C610_BELLAVISTA_1", 
    "OLT_C610_JUANJUI_1", "OLT_C610_LAMAS_1", "OLT_C610_SAPOSOA_1", 
    "OLT_C610_SAN_MIGUEL_AYA_1", "OLT_C610_CANTA_1", "OLT_C610_CALCA_1", 
    "OLT_C610_CARAVELI_1", "OLT_C610_CORACORA_2", "OLT_C610_CARHUAZ_1", 
    "OLT_C610_APLAO_1", "OLT_C610_OTUZCO_1", "OLT_C610_FERREÑAFE_1", 
    "OLT_C610_HUANCAPI_2", "OLT_C610_QUILLABAMBA_8", "C610_MAQUETA_SURQUILLO", 
    "OLT_C610_QUEROBAMBA_2", "OLT_C600_MAQUETA_LURIN", "OLT_C600_JULIACA_55", 
    "OLT_C600_TARAPOTO_48", "OLT_C600_AYACUCHO_46", "OLT_C600_TARMA_13", 
    "OLT_C600_HIGUERETA_42", "OLT_C600_CHORRILLOS_36", "OLT_C600_LA_MOLINA_23", 
    "OLT_C600_RIMAC_50", "OLT_C600_MAQUETA_FTTM"
]

# Diccionario de IPs para ZTE (usando los datos proporcionados)
ZTE_IP_MAPPING = {
    "OLT_C610_RODRIGUEZ_DE_MENDOZA_5": "10.227.123.94",
    "OLT_C300_ANDAHUAYLAS_10": "10.227.117.122",
    "OLT_C300_AYACUCHO_44_F1": "10.227.114.246",
    "OLT_C300_AYACUCHO_44_F2": "10.227.114.248",
    "OLT_C300_AZANGARO_6": "10.227.130.149",
    "OLT_C300_BAGUA_CHICA_9": "10.227.123.200",
    "OLT_C300_BAGUA_GRANDE_5": "10.227.123.124",
    "OLT_C300_CAJABAMBA_5": "10.227.96.198",
    "OLT_C300_CAMANA_13": "10.227.118.124",
    "OLT_C300_CASMA_5": "10.227.123.185",
    "OLT_C300_CERRO_DE_PASCO_10": "10.227.121.147",
    "OLT_C300_CHACHAPOYAS_6": "10.227.96.234",
    "OLT_C300_CHANCAY_10": "10.227.126.195",
    "OLT_C300_CHEPEN_14": "10.227.123.181",
    "OLT_C300_DESAGUADERO_4": "10.227.130.155",
    "OLT_C300_GUADALUPE_5": "10.227.123.203",
    "OLT_C300_HUAMACHUCO_07": "10.227.96.197",
    "OLT_C300_HUANTA_8": "10.227.114.249",
    "OLT_C300_HUARMEY_10": "10.227.123.178",
    "OLT_C300_JULI_4": "10.227.130.143",
    "OLT_C300_JULIACA_54_F1": "10.227.130.54",
    "OLT_C300_JULIACA_54_F2": "10.227.130.94",
    "OLT_C300_LA_MERCED_6": "10.227.121.72",
    "OLT_C300_MAZAMARI_2": "10.227.121.148",
    "OLT_C300_MOQUEGUA_15": "10.227.118.113",
    "OLT_C300_MOYOBAMBA_14": "10.227.121.216",
    "OLT_C300_NAZCA_12": "10.227.115.173",
    "OLT_C300_OLMOS_5": "10.227.119.69",
    "OLT_C300_PACASMAYO_15": "10.227.123.191",
    "OLT_C300_PISCO_24": "10.227.115.168",
    "OLT_C300_PUERTO_MALDONADO_22": "10.227.130.109",
    "OLT_C300_SATIPO_7": "10.227.121.209",
    "OLT_C300_SICUANI_9": "10.227.117.49",
    "OLT_C300_TAMBO_GRANDE_5": "10.227.120.231",
    "OLT_C300_TARAPOTO_46": "10.227.121.191",
    "OLT_C300_TARMA_12": "10.227.121.226",
    "OLT_C300_TOCACHE_2": "10.227.81.203",
    "OLT_C300_VIRU_6": "10.227.123.220",
    "OLT_C300_YURIMAGUAS_8": "10.227.121.221",
    "OLT_C600_BARRANCO_25_F1": "10.227.103.105",
    "OLT_C600_CHICLAYO_81": "10.227.119.66",
    "OLT_C600_CHORRILLOS_35_F1": "10.227.103.106",
    "OLT_C600_LINCE_32": "10.227.128.64",
    "OLT_C600_MAGDALENA_52_F1": "10.227.128.61",
    "OLT_C600_PANDO-2": "10.227.111.45",
    "OLT_C600_ROSA_TORO_5": "10.227.106.216",
    "OLT_C600_SAN_JOSE_56": "10.227.111.71",
    "OLT_C600_WASHINGTON_60": "10.227.126.199",
    # ... (puedes agregar más mapeos según sea necesario)
}

# --- SELECTOR DE GESTOR ---
st.subheader("📡 Seleccionar Gestor")

gestor = st.selectbox(
    "Tipo de Gestor:",
    ["HUAWEI", "ZTE"],
    help="Seleccione el tipo de gestor para la consulta"
)

st.markdown("---")

# ============================================================
# TAB 1: CONSULTA POR PARÁMETROS MANUALES
# ============================================================
tab1, tab2 = st.tabs(["🔧 Consulta por Parámetros", "🔎 Consulta por Serial Number"])

with tab1:
    st.subheader(f"Consulta Manual - {gestor}")
    
    # ====================================
    # FORMULARIO PARA HUAWEI
    # ====================================
    if gestor == "HUAWEI":
        st.info("**Parámetros requeridos para Huawei:** DEV, FN, SN, PN")
        
        with st.form("huawei_form"):
            # Campo DEV con autocompletado
            dev = st.selectbox(
                "📍 DEV (Nombre de OLT):",
                options=HUAWEI_OLTS,
                help="Seleccione o escriba para buscar la OLT",
                index=None,
                placeholder="Seleccione o escriba para buscar..."
            )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                fn = st.number_input(
                    "🔢 FN (Frame):",
                    min_value=0,
                    value=0,
                    step=1,
                    help="Frame number (usualmente 0)"
                )
            
            with col2:
                sn = st.number_input(
                    "🔢 SN (Slot):",
                    min_value=0,
                    value=0,
                    step=1,
                    help="Slot number"
                )
            
            with col3:
                pn = st.number_input(
                    "🔢 PN (Port):",
                    min_value=0,
                    value=0,
                    step=1,
                    help="Port number"
                )
            
            submitted = st.form_submit_button("🚀 Ejecutar Consulta", type="primary", use_container_width=True)
            
            if submitted:
                if not dev:
                    st.error("❌ El campo DEV es obligatorio")
                else:
                    with st.spinner("🔍 Consultando datos en Huawei..."):
                        try:
                            params = {
                                "dev": dev,
                                "fn": int(fn),
                                "sn": int(sn),
                                "pn": int(pn)
                            }
                            url = f"{ngrok_base_url}/consulta"
                            response = requests.get(url, params=params, timeout=20)
                            
                            if response.status_code == 200:
                                json_data = response.json()
                                
                                # Verificar si hay error en la respuesta
                                if isinstance(json_data, dict) and "error" in json_data:
                                    st.error(f"❌ Error: {json_data['error']}")
                                elif isinstance(json_data, dict) and "mensaje" in json_data:
                                    st.warning(f"⚠️ {json_data['mensaje']}")
                                else:
                                    st.success("✅ Consulta exitosa")
                                    
                                    # Convertir a DataFrame si es una lista
                                    if isinstance(json_data, list):
                                        df_result = pd.DataFrame(json_data)
                                        
                                        # Mostrar resultados
                                        st.dataframe(df_result, use_container_width=True)
                                        
                                        # Botón de descarga
                                        st.download_button(
                                            label="📥 Descargar resultados (.csv)",
                                            data=df_result.to_csv(index=False).encode("utf-8"),
                                            file_name=f"huawei_{dev}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                            mime="text/csv"
                                        )
                                    else:
                                        st.json(json_data)
                            else:
                                st.error(f"❌ Error {response.status_code}: {response.text}")
                        
                        except requests.exceptions.Timeout:
                            st.error("❌ Timeout: La consulta tardó demasiado")
                        except Exception as e:
                            st.error(f"❌ Error de conexión: {str(e)}")
    
    # ====================================
    # FORMULARIO PARA ZTE
    # ====================================
    else:  # ZTE
        st.info("**Parámetros requeridos para ZTE:** OLTID (IP), PONID (Formato: 1-FN-SN-PN)")
        
        with st.form("zte_form"):
            # Campo OLT con autocompletado
            olt_name = st.selectbox(
                "🌐 OLT (Nombre de OLT):",
                options=ZTE_OLTS,
                help="Seleccione o escriba para buscar la OLT ZTE",
                index=None,
                placeholder="Seleccione o escriba para buscar..."
            )
            
            # Mostrar IP automáticamente si está en el mapeo
            olt_ip = ""
            if olt_name and olt_name in ZTE_IP_MAPPING:
                olt_ip = ZTE_IP_MAPPING[olt_name]
                st.info(f"**IP de la OLT:** {olt_ip}")
            elif olt_name:
                st.warning("⚠️ IP no encontrada en la base de datos. Ingrese manualmente.")
                olt_ip = st.text_input(
                    "🌐 OLTID (IP de OLT):",
                    placeholder="Ej: 10.227.118.124",
                    help="Dirección IP de la OLT ZTE"
                )
            else:
                olt_ip = st.text_input(
                    "🌐 OLTID (IP de OLT):",
                    placeholder="Ej: 10.227.118.124",
                    help="Dirección IP de la OLT ZTE"
                )
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                fn_zte = st.number_input(
                    "🔢 FN (Frame):",
                    min_value=1,
                    value=1,
                    step=1,
                    help="Frame number (usualmente 1)"
                )
            
            with col2:
                sn_zte = st.number_input(
                    "🔢 SN (Slot):",
                    min_value=1,
                    value=1,
                    step=1,
                    help="Slot number"
                )
            
            with col3:
                pn_zte = st.number_input(
                    "🔢 PN (Port):",
                    min_value=1,
                    value=1,
                    step=1,
                    help="Port number"
                )
            
            # Generar PONID automáticamente en formato 1-FN-SN-PN
            ponid = f"1-{fn_zte}-{sn_zte}-{pn_zte}"
            st.info(f"**PONID generado:** `{ponid}`")
            
            st.caption("💡 **Formato PONID:** 1-FN-SN-PN donde el primer '1' es fijo y FN usualmente es 1")
            
            submitted = st.form_submit_button("🚀 Ejecutar Consulta", type="primary", use_container_width=True)
            
            if submitted:
                if not olt_ip or not ponid:
                    st.error("❌ Todos los campos son obligatorios")
                else:
                    with st.spinner("🔍 Consultando datos en ZTE..."):
                        try:
                            params = {
                                "oltid": olt_ip,
                                "ponid": ponid
                            }
                            url = f"{ngrok_base_url}/pruebazte"
                            response = requests.get(url, params=params, timeout=20)
                            
                            if response.status_code == 200:
                                json_data = response.json()
                                
                                # Verificar si hay error en la respuesta
                                if isinstance(json_data, dict) and "error" in json_data:
                                    st.error(f"❌ Error: {json_data['error']}")
                                elif isinstance(json_data, dict) and "mensaje" in json_data:
                                    st.warning(f"⚠️ {json_data['mensaje']}")
                                else:
                                    st.success("✅ Consulta exitosa")
                                    
                                    # Convertir a DataFrame si es una lista
                                    if isinstance(json_data, list):
                                        df_result = pd.DataFrame(json_data)
                                        
                                        # Mostrar resultados
                                        st.dataframe(df_result, use_container_width=True)
                                        
                                        # Botón de descarga
                                        st.download_button(
                                            label="📥 Descargar resultados (.csv)",
                                            data=df_result.to_csv(index=False).encode("utf-8"),
                                            file_name=f"zte_{olt_ip}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                                            mime="text/csv"
                                        )
                                    else:
                                        st.json(json_data)
                            else:
                                st.error(f"❌ Error {response.status_code}: {response.text}")
                        
                        except requests.exceptions.Timeout:
                            st.error("❌ Timeout: La consulta tardó demasiado")
                        except Exception as e:
                            st.error(f"❌ Error de conexión: {str(e)}")

# ============================================================
# TAB 2: CONSULTA POR SERIAL NUMBER
# ============================================================
with tab2:
    st.subheader(f"Consulta por Serial Number - {gestor}")
    
    st.info(f"**Gestor seleccionado:** {gestor} - La consulta se realizará en este gestor")
    
    with st.form("serial_form"):
        serial_input = st.text_input(
            "📋 Serial Number:",
            placeholder="Ej: MSTC0940DFDA",
            help="Ingrese el serial number del equipo ONT/ONU"
        )
        
        submitted_serial = st.form_submit_button("🚀 Ejecutar Consulta", type="primary", use_container_width=True)
        
        if submitted_serial:
            if not serial_input:
                st.error("❌ El serial number es obligatorio")
            else:
                with st.spinner(f"🔍 Consultando serial en {gestor}..."):
                    try:
                        # Determinar endpoint según gestor
                        if gestor == "HUAWEI":
                            url = f"{ngrok_base_url}/consulta_serial?serial={serial_input.strip()}"
                        else:  # ZTE
                            url = f"{ngrok_base_url}/consulta_serial_zte?serial={serial_input.strip()}"
                        
                        response = requests.get(url, timeout=20)
                        
                        if response.status_code == 200:
                            resultado = response.json()
                            
                            if "error" in resultado:
                                st.error(f"❌ **Error en la consulta:** {resultado['error']}")
                            else:
                                st.success("✅ **ONT/ONU encontrado exitosamente!**")
                                
                                col1, col2 = st.columns(2)
                                
                                # ====================================
                                # COLUMNA 1: Información del ONT/ONU
                                # ====================================
                                with col1:
                                    st.subheader("📋 Información del Equipo")
                                    
                                    # Detectar si es Huawei o ZTE
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
                                    
                                    # RX Power con indicadores
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
                                    
                                    # Corriente Bias
                                    bias_key = 'bias_current' if 'bias_current' in opticos else 'tx_bias'
                                    st.metric("🔋 Corriente Bias", opticos[bias_key])
                                    
                                    # Ranging Distance (solo Huawei)
                                    if 'ranging_distance' in opticos:
                                        st.metric("📏 Distancia", opticos['ranging_distance'])
                        else:
                            st.error(f"❌ Error {response.status_code}: {response.text}")
                    
                    except requests.exceptions.Timeout:
                        st.error("❌ Timeout: La consulta tardó demasiado")
                    except Exception as e:
                        st.error(f"❌ Error de conexión: {str(e)}")

# --- INFORMACIÓN DE AYUDA ---
st.markdown("---")
st.subheader("ℹ️ Información de Uso")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **🔧 Consulta por Parámetros (Huawei):**
    - **DEV:** Nombre completo de la OLT (con autocompletado)
    - **FN:** Frame Number (usualmente 0)
    - **SN:** Slot Number
    - **PN:** Port Number
    
    **Ejemplo:** 
    - DEV: `OLT_MA5800_SAN_ISIDRO_47_F1`
    - FN: `0`, SN: `4`, PN: `10`
    """)

with col2:
    st.markdown("""
    **🔧 Consulta por Parámetros (ZTE):**
    - **OLT:** Nombre de OLT (con autocompletado e IP automática)
    - **PONID:** Formato **1-FN-SN-PN** (automático)
    
    **Ejemplo:**
    - OLT: `OLT_C300_CAMANA_13`
    - PONID generado: `1-1-3-1`
    
    💡 En ZTE, el primer '1' es fijo y FN usualmente es `1`
    """)

# --- ESTADO DE LA API ---
st.markdown("---")
st.subheader("🟢 Estado de Conexión")

col1, col2 = st.columns(2)

with col1:
    st.success(f"""
    **API Base URL:**  
    `{ngrok_base_url}`
    
    ✅ Configuración cargada
    """)

with col2:
    st.info("""
    **Endpoints Disponibles:**
    - `/consulta` (Huawei)
    - `/pruebazte` (ZTE)
    - `/consulta_serial` (Huawei)
    - `/consulta_serial_zte` (ZTE)
    """)

# --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style='text-align:center; font-size:14px; color:gray;'>
    Consultas en Tiempo Real - ADCE | Desarrollado con 💚 by <b>AJ</b> — 2025
</div>
""", unsafe_allow_html=True)