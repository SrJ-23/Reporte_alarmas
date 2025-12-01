import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scripts.fetch_data import get_alarmas
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(page_title="Dashboard Histórico Huawei - ADCE", layout="wide", page_icon="📉")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #e0e0e0;
    }
    .audit-box {
        background-color: #e8f4f8;
        padding: 12px;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📉 Dashboard Histórico de Alarmas")
st.markdown("**Alcance:** Análisis histórico completo - Todos los gestores")

# --- CARGA DE DATOS ---
if "data" not in st.session_state:
    with st.spinner("Cargando histórico de alarmas..."):
        raw_data = get_alarmas()
        st.session_state.data = raw_data

df_original = st.session_state.data.copy()

# --- AUDITORÍA DE DATOS (CRÍTICA) ---
with st.expander("📊 Auditoría de Carga de Datos (TODOS los registros crudos)", expanded=True):
    st.markdown('<div class="audit-box">', unsafe_allow_html=True)
    
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    
    with col_a1:
        st.metric("Total Registros Crudos", f"{len(df_original):,}")
        
    with col_a2:
        if "_Origen" in df_original.columns:
            st.write("**Por Origen:**")
            st.dataframe(
                df_original["_Origen"].value_counts().reset_index(),
                column_config={
                    "_Origen": "Origen",
                    "count": "Cantidad"
                },
                hide_index=True,
                width=300
            )
    
    with col_a3:
        if "Gestor" in df_original.columns:
            st.write("**Por Gestor:**")
            gestor_counts = df_original["Gestor"].value_counts().reset_index()
            gestor_counts.columns = ['Gestor', 'Cantidad']
            st.dataframe(gestor_counts, hide_index=True, width=300)
            
            # 🔍 CRÍTICO: Mostrar qué se perdería si filtramos solo Huawei
            registros_huawei = df_original[df_original['Gestor'].astype(str).str.contains('Huawei', case=False, na=False)]
            st.warning(f"⚠️ Si filtramos solo 'Huawei': {len(registros_huawei):,} alarmas ({len(registros_huawei)/len(df_original)*100:.1f}%)")
    
    with col_a4:
        # Verificar estado de fechas
        if "HoraPeru" in df_original.columns:
            con_fecha = df_original["HoraPeru"].notna().sum()
            sin_fecha = df_original["HoraPeru"].isna().sum()
            st.write("**Estado de Fechas:**")
            st.metric("Con fecha válida", f"{con_fecha:,}")
            st.metric("Sin fecha válida", f"{sin_fecha:,}", 
                     delta=f"-{sin_fecha/len(df_original)*100:.1f}%" if sin_fecha > 0 else "0%",
                     delta_color="inverse")
    
    st.markdown('</div>', unsafe_allow_html=True)

# --- DECISIÓN: ¿FILTRAR O NO POR GESTOR? ---
st.info("💡 **Importante**: Este dashboard ahora muestra TODAS las alarmas. Usa el filtro de 'Gestor' para ver específicamente Huawei, ZTE o Histórico.")

# --- USAR TODOS LOS DATOS (SIN FILTRAR POR GESTOR) ---
df = df_original.copy()

if df.empty:
    st.error("No se encontraron datos históricos 😢")
    st.stop()

# --- PREPROCESAMIENTO ---
# Las fechas ya vienen parseadas desde fetch_data.py
df['Fecha'] = df['HoraPeru'].dt.date

# Asegurar TipoFinal
if 'TipoFinal' not in df.columns:
    st.error("⚠️ **CRÍTICO**: Columna 'TipoFinal' no existe en los datos")
    st.write("Columnas disponibles:", df.columns.tolist())
    
    # Intentar usar otra columna como fallback
    if 'Severity' in df.columns:
        st.info("Usando 'Severity' como tipo de alarma temporal")
        df['TipoFinal'] = df['Severity'].fillna('Otros')
    else:
        df['TipoFinal'] = 'Desconocido'
else:
    # 🔧 CORREGIR ENCODING (energÃ­a → energía)
    df['TipoFinal'] = df['TipoFinal'].astype(str).str.encode('latin1', errors='ignore').str.decode('utf-8', errors='ignore')
    
    # Verificar si TipoFinal está vacío
    tipos_unicos = df['TipoFinal'].nunique()
    tipos_null = df['TipoFinal'].isna().sum()
    
    if tipos_unicos == 0 or tipos_null == len(df):
        st.error(f"⚠️ **CRÍTICO**: TipoFinal está vacío en todas las filas")
        st.write("Asignando valor por defecto...")
        df['TipoFinal'] = 'Sin clasificar'
    elif tipos_null > 0:
        st.warning(f"⚠️ {tipos_null:,} registros sin TipoFinal, rellenando con 'Otros'")
        df['TipoFinal'] = df['TipoFinal'].fillna('Otros')
    else:
        st.success(f"✅ TipoFinal OK: {tipos_unicos} tipos únicos ({len(df):,} alarmas)")

# Verificar si hay fechas válidas
fechas_validas = df['HoraPeru'].notna().sum()
fechas_invalidas = df['HoraPeru'].isna().sum()

if fechas_invalidas > 0:
    st.warning(f"⚠️ {fechas_invalidas:,} alarmas sin fecha válida. Mostrando solo {fechas_validas:,} registros con fecha.")
    # Eliminar solo para visualización en este dashboard
    df = df.dropna(subset=["HoraPeru"])
else:
    st.success(f"✅ Dataset Huawei: {len(df):,} alarmas con fecha válida")

# 🔍 DIAGNÓSTICO: Mostrar rango de fechas disponible
if not df.empty:
    fecha_min_total = df['Fecha'].min()
    fecha_max_total = df['Fecha'].max()
    
    col_diag1, col_diag2, col_diag3 = st.columns(3)
    with col_diag1:
        st.metric("📅 Fecha más antigua", str(fecha_min_total))
    with col_diag2:
        st.metric("📅 Fecha más reciente", str(fecha_max_total))
    with col_diag3:
        dias_disponibles = (fecha_max_total - fecha_min_total).days
        st.metric("📊 Días de historial", f"{dias_disponibles:,}")

# --- FILTROS UNIFICADOS ---
with st.container():
    st.subheader("🔍 Filtros de Visualización")
    
    # Botón para resetear filtros
    col_reset1, col_reset2, col_reset3 = st.columns([2, 1, 1])
    with col_reset2:
        if st.button("🔄 Resetear Filtros", type="secondary", key="reset_filters"):
            # Resetear session state
            if 'tipos_seleccionados' in st.session_state:
                del st.session_state.tipos_seleccionados
            if 'gestores_seleccionados' in st.session_state:
                del st.session_state.gestores_seleccionados
            st.rerun()
    
    with col_reset3:
        if st.button("✅ Seleccionar Todos", type="primary", key="select_all"):
            tipos_disponibles_reset = sorted(df['TipoFinal'].dropna().unique().tolist())
            gestores_disponibles_reset = sorted(df['Gestor'].dropna().unique().tolist())
            st.session_state.tipos_seleccionados = tipos_disponibles_reset
            st.session_state.gestores_seleccionados = gestores_disponibles_reset
            st.rerun()
    
    # 🔍 DIAGNÓSTICO PRE-FILTRO (mejorado)
    expandir_diagnostico = len(df) < 50000
    
    with st.expander("🔧 Diagnóstico de Datos Pre-Filtro", expanded=expandir_diagnostico):
        st.write(f"**Total alarmas disponibles:** {len(df):,}")
        
        col_d1, col_d2 = st.columns(2)
        with col_d1:
            st.write("**Top 10 Tipos de Alarma:**")
            if 'TipoFinal' in df.columns:
                tipos_df = df['TipoFinal'].value_counts().head(10).reset_index()
                tipos_df.columns = ['Tipo', 'Cantidad']
                
                # Verificar si está vacío
                if tipos_df.empty:
                    st.error("⚠️ No hay tipos de alarma (tabla vacía)")
                    st.write(f"TipoFinal nulos: {df['TipoFinal'].isna().sum()}")
                    st.write(f"TipoFinal únicos: {df['TipoFinal'].nunique()}")
                    st.write("**Muestra de valores en TipoFinal:**")
                    st.code(df['TipoFinal'].head(20).tolist())
                else:
                    st.dataframe(tipos_df, hide_index=True, height=300)
            else:
                st.error("⚠️ Columna 'TipoFinal' no existe")
        
        with col_d2:
            st.write("**Distribución Temporal (últimos 30 días):**")
            fecha_corte = df['Fecha'].max() - timedelta(days=30)
            df_recientes = df[df['Fecha'] >= fecha_corte]
            st.metric("Alarmas últimos 30 días", f"{len(df_recientes):,}")
            
            if not df_recientes.empty:
                daily_count = df_recientes.groupby('Fecha').size().reset_index(name='Cantidad')
                st.line_chart(daily_count.set_index('Fecha'))
            
            st.write("**Top 5 OLTs con más alarmas:**")
            if 'DEV' in df.columns:
                top_olts = df['DEV'].value_counts().head(5).reset_index()
                top_olts.columns = ['OLT', 'Cantidad']
                st.dataframe(top_olts, hide_index=True)
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        # 🆕 FILTRO DE GESTOR
        gestores_disponibles = sorted(df['Gestor'].dropna().unique().tolist())
        
        # Inicializar session state para gestores
        if 'gestores_seleccionados' not in st.session_state:
            st.session_state.gestores_seleccionados = gestores_disponibles
        
        gestor_filtro = st.multiselect(
            "Filtrar por Gestor",
            gestores_disponibles,
            default=st.session_state.gestores_seleccionados,
            key='multiselect_gestores',
            help="Selecciona Huawei, ZTE, Histórico, etc."
        )
        
        # Actualizar session state
        if gestor_filtro:
            st.session_state.gestores_seleccionados = gestor_filtro
        else:
            gestor_filtro = gestores_disponibles
            st.session_state.gestores_seleccionados = gestores_disponibles
        
        st.caption(f"Gestores: {len(gestor_filtro)}/{len(gestores_disponibles)}")

    with col2:
        # Filtro de OLT
        olts_disponibles = sorted(df['DEV'].dropna().unique().tolist())
        olt_seleccionada = st.selectbox(
            "Seleccionar OLT",
            ["Todas"] + olts_disponibles,
            index=0,
            help="Selecciona 'Todas' para ver el Top 5 global, o una específica para detalle."
        )

    with col3:
        # Filtro por TIPO FINAL - VERSIÓN CON SESSION STATE
        tipos_disponibles = sorted(df['TipoFinal'].dropna().unique().tolist())
        tipo_con_conteo = df['TipoFinal'].value_counts().to_dict()
        
        st.write("**Filtrar Tipo de Alarma:**")
        
        # Mostrar información de tipos disponibles
        with st.expander("📊 Ver distribución de tipos", expanded=False):
            for tipo in tipos_disponibles:
                cantidad = tipo_con_conteo.get(tipo, 0)
                st.write(f"- **{tipo}**: {cantidad:,} alarmas")
        
        # 🔥 INICIALIZAR SESSION STATE para asegurar que todos estén seleccionados
        if 'tipos_seleccionados' not in st.session_state:
            st.session_state.tipos_seleccionados = tipos_disponibles
        
        # Multiselect con key y session_state
        tipo_filtro_temp = st.multiselect(
            f"Selecciona tipos ({len(tipos_disponibles)} disponibles)",
            tipos_disponibles,
            default=st.session_state.tipos_seleccionados,
            key='multiselect_tipos',
            help="Deselecciona para filtrar por tipos específicos"
        )
        
        # Actualizar session state
        if tipo_filtro_temp:
            st.session_state.tipos_seleccionados = tipo_filtro_temp
            tipo_filtro = tipo_filtro_temp
        else:
            # Si está vacío, usar todos y resetear session state
            tipo_filtro = tipos_disponibles
            st.session_state.tipos_seleccionados = tipos_disponibles
            st.info("ℹ️ Sin selección → mostrando todos los tipos")
        
        # Mostrar resumen de selección
        st.caption(f"Seleccionados: {len(tipo_filtro)}/{len(tipos_disponibles)} tipos")

    with col4:
        # Selector de Rango de Fechas
        fecha_min_df = df["Fecha"].min()
        fecha_max_df = df["Fecha"].max()
        
        # 🔍 CORRECCIÓN: Rango por defecto más amplio (últimos 30 días)
        fecha_inicio_default = max(fecha_max_df - timedelta(days=30), fecha_min_df)
        
        fechas_seleccionadas = st.date_input(
            f"Rango de Fechas (disponible: {fecha_min_df} a {fecha_max_df})",
            value=(fecha_inicio_default, fecha_max_df),
            min_value=fecha_min_df,
            max_value=fecha_max_df,
            help=f"Datos disponibles desde {fecha_min_df} hasta {fecha_max_df}"
        )

# Manejo de fechas
if isinstance(fechas_seleccionadas, tuple):
    if len(fechas_seleccionadas) == 2:
        start_date, end_date = fechas_seleccionadas
    elif len(fechas_seleccionadas) == 1:
        start_date = end_date = fechas_seleccionadas[0]
    else:
        start_date, end_date = fecha_min_df, fecha_max_df
else:
    start_date, end_date = fechas_seleccionadas, fechas_seleccionadas

# --- APLICAR FILTROS ---
mask = (
    (df['Fecha'] >= start_date) & 
    (df['Fecha'] <= end_date) &
    (df['TipoFinal'].isin(tipo_filtro)) &
    (df['Gestor'].isin(gestor_filtro))  # 🆕 Filtro de gestor
)

if olt_seleccionada != "Todas":
    mask = mask & (df['DEV'] == olt_seleccionada)

df_filtered = df[mask].copy()

# 🔍 RESUMEN EJECUTIVO DE FILTRADO
st.markdown("---")
col_sum1, col_sum2, col_sum3, col_sum4 = st.columns(4)

with col_sum1:
    st.metric(
        "📊 Alarmas Filtradas", 
        f"{len(df_filtered):,}",
        delta=f"{len(df_filtered) - len(df):,} vs total"
    )

with col_sum2:
    pct_filtrado = (len(df_filtered) / len(df) * 100) if len(df) > 0 else 0
    st.metric(
        "📈 % del Dataset", 
        f"{pct_filtrado:.1f}%"
    )

with col_sum3:
    st.metric(
        "📅 Días Analizados",
        f"{(end_date - start_date).days + 1}"
    )

with col_sum4:
    st.metric(
        "🔧 Tipos Activos",
        f"{len(tipo_filtro)}/{len(df['TipoFinal'].unique())}"
    )

# 🔍 DIAGNÓSTICO POST-FILTRO (mejorado)
if len(df_filtered) < 100:
    st.warning(f"⚠️ **Solo {len(df_filtered):,} alarmas** después de aplicar filtros.")
    
    with st.expander("🔍 ¿Por qué tan pocas alarmas? Haz clic para diagnosticar", expanded=True):
        st.write("### Posibles causas:")
        
        # Verificar rango de fechas
        alarmas_fuera_rango = df[~((df['Fecha'] >= start_date) & (df['Fecha'] <= end_date))]
        st.write(f"1. **Rango de fechas**: {len(alarmas_fuera_rango):,} alarmas están fuera del rango {start_date} a {end_date}")
        
        # Verificar tipos filtrados
        alarmas_tipo_excluido = df[~df['TipoFinal'].isin(tipo_filtro)]
        st.write(f"2. **Tipos de alarma**: {len(alarmas_tipo_excluido):,} alarmas tienen tipos NO seleccionados")
        
        # Verificar OLT
        if olt_seleccionada != "Todas":
            alarmas_otras_olts = df[df['DEV'] != olt_seleccionada]
            st.write(f"3. **OLT seleccionada**: {len(alarmas_otras_olts):,} alarmas son de otras OLTs")
        
        st.info("💡 **Sugerencia**: Amplía el rango de fechas o selecciona 'Todas' las OLTs")
        
elif len(df_filtered) == 0:
    st.error("❌ **No hay datos** con los filtros actuales.")
    
    with st.expander("🔧 Información de depuración", expanded=True):
        st.write("**Filtros aplicados:**")
        st.write(f"- Rango de fechas: `{start_date}` a `{end_date}` ({(end_date - start_date).days + 1} días)")
        st.write(f"- Tipos seleccionados: {len(tipo_filtro)} de {len(df['TipoFinal'].unique())}")
        st.write(f"- OLT seleccionada: `{olt_seleccionada}`")
        
        st.write("\n**Datos disponibles:**")
        st.write(f"- Total Huawei: {len(df):,} alarmas")
        st.write(f"- Rango disponible: `{df['Fecha'].min()}` a `{df['Fecha'].max()}`")
        st.write(f"- Tipos disponibles: {sorted(df['TipoFinal'].unique())}")
    
    st.stop()

st.markdown("---")

# --- KPIs METRICS ---
def mostrar_kpis(df_kpi, df_total_hist):
    col1, col2, col3, col4 = st.columns(4)
    
    total_alarmas = len(df_kpi)
    n_olts = df_kpi['DEV'].nunique()
    
    # Comparativa temporal
    dias_rango = (end_date - start_date).days + 1
    prev_start = start_date - timedelta(days=dias_rango)
    df_prev = df_total_hist[(df_total_hist['Fecha'] >= prev_start) & (df_total_hist['Fecha'] < start_date)]
    
    delta_alarmas = total_alarmas - len(df_prev)
    
    # Tipo más frecuente
    tipo_top = df_kpi['TipoFinal'].mode()[0] if not df_kpi.empty else "N/A"

    with col1:
        st.metric("Total Alarmas (Rango)", f"{total_alarmas:,}", delta=f"{delta_alarmas:+,} vs anterior")
    with col2:
        st.metric("OLTs Afectadas", n_olts)
    with col3:
        st.metric("Tipo Más Frecuente", tipo_top)
    with col4:
        st.metric("Promedio Diario", f"{total_alarmas/max(dias_rango, 1):.0f}")

st.divider()
mostrar_kpis(df_filtered, df)
st.divider()

# --- GRÁFICO PRINCIPAL (COMBO: BARRAS TIPO FINAL + LÍNEAS OLT) ---
def crear_grafico_combo(df_in, olt_sel):
    """Gráfico Combinado: Barras Apiladas por TipoFinal + Líneas de OLTs"""
    if df_in.empty:
        return go.Figure().add_annotation(text="Sin datos en el rango seleccionado", showarrow=False)

    fig = go.Figure()
    
    # --- PARTE 1: BARRAS APILADAS (Por TipoFinal) ---
    daily_tipo = df_in.groupby(['Fecha', 'TipoFinal']).size().reset_index(name='Count')
    tipos_presentes = daily_tipo['TipoFinal'].unique()
    colors = px.colors.qualitative.Plotly
    
    for i, tipo in enumerate(tipos_presentes):
        subset = daily_tipo[daily_tipo['TipoFinal'] == tipo]
        color_idx = i % len(colors)
        
        fig.add_trace(go.Bar(
            x=subset['Fecha'],
            y=subset['Count'],
            name=str(tipo),
            marker_color=colors[color_idx],
            opacity=0.4,
            hoverinfo='y+name'
        ))

    # --- PARTE 2: LÍNEAS (Evolución por OLT) ---
    if olt_sel == "Todas":
        top_olts = df_in['DEV'].value_counts().nlargest(5).index.tolist()
        title_suffix = "Top 5 OLTs + Tipos de Alarma"
        
        for olt in top_olts:
            df_olt = df_in[df_in['DEV'] == olt]
            daily_olt = df_olt.groupby('Fecha').size().reset_index(name='Count')
            
            fig.add_trace(go.Scatter(
                x=daily_olt['Fecha'],
                y=daily_olt['Count'],
                mode='lines+markers',
                name=f'OLT: {olt}',
                line=dict(width=3),
                marker=dict(size=6)
            ))
    else:
        title_suffix = f"Evolución: {olt_sel}"
        daily_olt = df_in.groupby('Fecha').size().reset_index(name='Count')
        
        fig.add_trace(go.Scatter(
            x=daily_olt['Fecha'],
            y=daily_olt['Count'],
            mode='lines+markers',
            name=f'Tendencia {olt_sel}',
            line=dict(width=4, color='#2c3e50'),
            marker=dict(size=8)
        ))

    fig.update_layout(
        title=f'<b>Tendencia de Alarmas Huawei</b><br><sup>{title_suffix}</sup>',
        xaxis_title='Fecha',
        yaxis_title='Cantidad de Alarmas',
        barmode='stack',
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
        template="plotly_white"
    )
    
    return fig

st.subheader("📊 Evolutivo Principal")
st.plotly_chart(crear_grafico_combo(df_filtered, olt_seleccionada), width='stretch')

# --- GRÁFICOS SECUNDARIOS ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔌 Top Recurrencia (DEV-SN-PN)")
    
    if not df_filtered.empty:
        df_concatenado = df_filtered.copy()
        
        cols_necesarias = ['DEV', 'SN', 'PN']
        
        if all(col in df_concatenado.columns for col in cols_necesarias):
            
            # Limpieza robusta de IDs
            def limpiar_id(x):
                if pd.isna(x):
                    return "?"
                try:
                    val = float(x)
                    return str(int(val)) if val.is_integer() else str(val)
                except:
                    return str(x).strip() if str(x).strip() else "?"
            
            df_concatenado['DEV'] = df_concatenado['DEV'].apply(limpiar_id)
            df_concatenado['SN'] = df_concatenado['SN'].apply(limpiar_id)
            df_concatenado['PN'] = df_concatenado['PN'].apply(limpiar_id)
            
            df_concatenado['Identificador'] = (
                df_concatenado['DEV'] + "-" + 
                df_concatenado['SN'] + "-" + 
                df_concatenado['PN']
            )
            
            # Filtrar identificadores inválidos
            df_concatenado = df_concatenado[
                ~df_concatenado['Identificador'].isin(['?-?-?', '?--', '-?-?'])
            ]
            
            if not df_concatenado.empty:
                top_dev_sn_pn = df_concatenado['Identificador'].value_counts().head(10).reset_index()
                top_dev_sn_pn.columns = ['Identificador', 'Cantidad']
                
                fig_p = px.bar(
                    top_dev_sn_pn, 
                    y='Identificador', 
                    x='Cantidad', 
                    orientation='h',
                    text='Cantidad',
                    color='Cantidad',
                    color_continuous_scale='Reds',
                    labels={'Identificador': 'Origen (DEV-SN-PN)'}
                )
                
                fig_p.update_layout(
                    yaxis={'categoryorder': 'total ascending'},
                    height=400,
                    margin=dict(l=0, r=0, t=30, b=0)
                )
                st.plotly_chart(fig_p, width='stretch')
            else:
                st.info("No hay datos válidos de DEV-SN-PN en la selección.")
        else:
            faltantes = [c for c in cols_necesarias if c not in df_concatenado.columns]
            st.warning(f"Faltan columnas: {faltantes}")
    else:
        st.info("Sin datos para mostrar con los filtros actuales.")
        
with col_right:
    st.subheader("⏰ Mapa de Calor: Hora vs Tipo")
    if not df_filtered.empty:
        df_heat = df_filtered.copy()
        df_heat['Hora'] = df_heat['HoraPeru'].dt.hour
        
        heatmap_data = df_heat.groupby(['Hora', 'TipoFinal']).size().reset_index(name='Conteo')
        
        fig_h = px.density_heatmap(
            heatmap_data, 
            x='Hora', 
            y='TipoFinal', 
            z='Conteo', 
            nbinsx=24,
            color_continuous_scale='Viridis',
            title="Concentración de Tipos de Alarma por Hora"
        )
        fig_h.update_xaxes(dtick=1)
        st.plotly_chart(fig_h, width='stretch')
    else:
        st.info("Sin datos para mapa de calor.")

# --- 🔍 DRILL-DOWN: TOP PUERTOS CON PROBLEMAS ---
st.divider()
st.subheader("🔍 Drill-Down: Top Puertos con Problemas")

if not df_filtered.empty and 'DEV_2' in df_filtered.columns:
    # Contar alarmas por puerto (DEV_2)
    top_puertos = df_filtered['DEV_2'].value_counts().head(20).reset_index()
    top_puertos.columns = ['Puerto', 'Total_Alarmas']
    
    col_drill1, col_drill2 = st.columns([1, 3])
    
    with col_drill1:
        st.write("**Top 20 Puertos Problemáticos:**")
        st.dataframe(top_puertos, hide_index=True, height=400)
    
    with col_drill2:
        puerto_seleccionado = st.selectbox(
            "Selecciona un puerto para ver su historial completo:",
            top_puertos['Puerto'].tolist(),
            help="El historial mostrará TODAS las alarmas de este puerto (independiente del filtro de Tipo)"
        )
        
        if puerto_seleccionado:
            # Opción para ver histórico absoluto o respetar fechas
            ver_historico_completo = st.checkbox(
                "Ver histórico absoluto (ignorar rango de fechas)",
                value=False
            )
            
            if ver_historico_completo:
                df_puerto = df[df['DEV_2'] == puerto_seleccionado].copy()
            else:
                # Respetar rango de fechas pero ignorar tipo
                df_puerto = df[
                    (df['DEV_2'] == puerto_seleccionado) &
                    (df['Fecha'] >= start_date) & 
                    (df['Fecha'] <= end_date)
                ].copy()
            
            if not df_puerto.empty:
                st.info(f"📊 {len(df_puerto):,} alarmas encontradas para {puerto_seleccionado}")
                
                cols_mostrar = [
                    c for c in ['HoraPeru', 'DEV', 'TipoFinal', 'Severity', 
                                'ProbableCause', 'Cliente_puerto', 'SerialNumber_TDP']
                    if c in df_puerto.columns
                ]
                
                st.dataframe(
                    df_puerto[cols_mostrar].sort_values('HoraPeru', ascending=False),
                    width='stretch',
                    height=400
                )
                
                # Gráfico de tendencia del puerto
                daily_puerto = df_puerto.groupby('Fecha').size().reset_index(name='Count')
                fig_puerto = px.line(
                    daily_puerto,
                    x='Fecha',
                    y='Count',
                    markers=True,
                    title=f"Evolución de Alarmas - {puerto_seleccionado}"
                )
                st.plotly_chart(fig_puerto, width='stretch')
            else:
                st.warning("No hay datos para este puerto en el rango seleccionado")
else:
    st.info("Columna 'DEV_2' no disponible para drill-down")

# --- TABLA DE DATOS ---
with st.expander("📂 Ver Datos Detallados (Últimas 100)"):
    cols_to_show = [
        c for c in ['HoraPeru', 'DEV', 'DEV_2', 'TipoFinal', 'Severity', 
                    'ProbableCause', 'Cliente_puerto']
        if c in df_filtered.columns
    ]
    st.dataframe(
        df_filtered[cols_to_show].sort_values('HoraPeru', ascending=False).head(100),
        width='stretch'
    )

st.markdown("---")
st.caption(f"Dashboard generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Huawei Datos Históricos")