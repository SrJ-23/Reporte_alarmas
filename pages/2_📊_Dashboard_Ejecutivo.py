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
# 🆕 Botón de actualización en el header
col_header1, col_header2, col_header3 = st.columns([3, 1, 1])

with col_header1:
    st.write("")  # Espaciado

with col_header2:
    # Mostrar última actualización
    from scripts.fetch_data import get_info_cache
    info_cache = get_info_cache()
    
    if info_cache['timestamp_procesamiento']:
        tiempo_transcurrido = datetime.now() - info_cache['timestamp_procesamiento']
        minutos = int(tiempo_transcurrido.total_seconds() / 60)
        
        if minutos < 1:
            tiempo_str = "Hace menos de 1 min"
        elif minutos < 60:
            tiempo_str = f"Hace {minutos} min"
        else:
            horas = minutos // 60
            tiempo_str = f"Hace {horas}h {minutos % 60}min"
        
        st.caption(f"🕐 {tiempo_str}")
    else:
        st.caption("🕐 Sin información")

with col_header3:
    if st.button("🔄 Actualizar", type="primary", use_container_width=True, key="update_header"):
        with st.spinner("Actualizando datos desde Google Sheets..."):
            # Limpiar session_state
            if 'data' in st.session_state:
                del st.session_state.data
            if 'drill_olt_selected' in st.session_state:
                del st.session_state.drill_olt_selected
            if 'drill_dev2_selected' in st.session_state:
                del st.session_state.drill_dev2_selected
            
            # Recargar con forzar_recarga=True
            raw_data = get_alarmas(forzar_recarga=True)
            st.session_state.data = raw_data
            
            st.success("✅ Datos actualizados correctamente")
            st.rerun()

# Cargar datos normalmente si no están en session_state
if "data" not in st.session_state:
    with st.spinner("Cargando histórico de alarmas..."):
        raw_data = get_alarmas(forzar_recarga=False)
        st.session_state.data = raw_data

df_original = st.session_state.data.copy()

# --- INFORMACIÓN RÁPIDA DE DATOS CARGADOS ---
col_info1, col_info2, col_info3 = st.columns([2, 1, 1])

with col_info1:
    st.success(f"✅ {len(df_original):,} registros cargados correctamente")

with col_info2:
    info_cache = get_info_cache()
    if info_cache['timestamp_actuales']:
        st.caption(f"📡 Actuales: {info_cache['timestamp_actuales'].strftime('%H:%M:%S')}")

with col_info3:
    if info_cache['timestamp_historicas']:
        st.caption(f"📚 Históricas: {info_cache['timestamp_historicas'].strftime('%H:%M:%S')}")

# --- DECISIÓN: ¿FILTRAR O NO POR GESTOR? ---
st.info("💡 **Importante**: Este dashboard ahora muestra TODAS las alarmas. Usa el filtro de 'Gestor' para ver específicamente Huawei, ZTE o Histórico.")

# --- USAR TODOS LOS DATOS (SIN FILTRAR POR GESTOR) ---
df = df_original.copy()

if df.empty:
    st.error("No se encontraron datos históricos 😢")
    st.stop()

# --- PREPROCESAMIENTO ---
df['Fecha'] = df['HoraPeru'].dt.date

# Asegurar TipoFinal
if 'TipoFinal' not in df.columns:
    st.error("⚠️ **CRÍTICO**: Columna 'TipoFinal' no existe en los datos")
    st.write("Columnas disponibles:", df.columns.tolist())
    
    if 'Severity' in df.columns:
        st.info("Usando 'Severity' como tipo de alarma temporal")
        df['TipoFinal'] = df['Severity'].fillna('Otros')
    else:
        df['TipoFinal'] = 'Desconocido'
else:
    # Corregir encoding
    df['TipoFinal'] = df['TipoFinal'].astype(str).str.encode('latin1', errors='ignore').str.decode('utf-8', errors='ignore')
    
    tipos_unicos = df['TipoFinal'].nunique()
    tipos_null = df['TipoFinal'].isna().sum()
    
    if tipos_unicos == 0 or tipos_null == len(df):
        st.error(f"⚠️ **CRÍTICO**: TipoFinal está vacío en todas las filas")
        df['TipoFinal'] = 'Sin clasificar'
    elif tipos_null > 0:
        df['TipoFinal'] = df['TipoFinal'].fillna('Otros')

# Verificar fechas válidas
fechas_validas = df['HoraPeru'].notna().sum()
fechas_invalidas = df['HoraPeru'].isna().sum()

if fechas_invalidas > 0:
    st.warning(f"⚠️ {fechas_invalidas:,} alarmas sin fecha válida. Mostrando solo {fechas_validas:,} registros con fecha.")
    df = df.dropna(subset=["HoraPeru"])

# --- FILTROS UNIFICADOS ---
with st.container():
    st.subheader("🔍 Filtros de Visualización")
    
    # Botón para resetear filtros
    col_reset1, col_reset2, col_reset3 = st.columns([2, 1, 1])
    with col_reset2:
        if st.button("🔄 Resetear Filtros", type="secondary", key="reset_filters"):
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
    
    col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
    
    with col1:
        # Filtro de Gestor
        gestores_disponibles = sorted(df['Gestor'].dropna().unique().tolist())
        
        if 'gestores_seleccionados' not in st.session_state:
            st.session_state.gestores_seleccionados = gestores_disponibles
        
        gestor_filtro = st.multiselect(
            "Filtrar por Gestor",
            gestores_disponibles,
            default=st.session_state.gestores_seleccionados,
            key='multiselect_gestores',
            help="Selecciona Huawei, ZTE, Histórico, etc."
        )
        
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
        # Filtro por Tipo de Alarma
        tipos_disponibles = sorted(df['TipoFinal'].dropna().unique().tolist())
        tipo_con_conteo = df['TipoFinal'].value_counts().to_dict()
        
        st.write("**Filtrar Tipo de Alarma:**")
        
        with st.expander("📊 Ver distribución de tipos", expanded=False):
            for tipo in tipos_disponibles:
                cantidad = tipo_con_conteo.get(tipo, 0)
                st.write(f"- **{tipo}**: {cantidad:,} alarmas")
        
        if 'tipos_seleccionados' not in st.session_state:
            st.session_state.tipos_seleccionados = tipos_disponibles
        
        tipo_filtro_temp = st.multiselect(
            f"Selecciona tipos ({len(tipos_disponibles)} disponibles)",
            tipos_disponibles,
            default=st.session_state.tipos_seleccionados,
            key='multiselect_tipos',
            help="Deselecciona para filtrar por tipos específicos"
        )
        
        if tipo_filtro_temp:
            st.session_state.tipos_seleccionados = tipo_filtro_temp
            tipo_filtro = tipo_filtro_temp
        else:
            tipo_filtro = tipos_disponibles
            st.session_state.tipos_seleccionados = tipos_disponibles
            st.info("ℹ️ Sin selección → mostrando todos los tipos")
        
        st.caption(f"Seleccionados: {len(tipo_filtro)}/{len(tipos_disponibles)} tipos")

    with col4:
        # Selector de Rango de Fechas
        fecha_min_df = df["Fecha"].min()
        fecha_max_df = df["Fecha"].max()
        
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
    (df['Gestor'].isin(gestor_filtro))
)

if olt_seleccionada != "Todas":
    mask = mask & (df['DEV'] == olt_seleccionada)

df_filtered = df[mask].copy()

# --- RESUMEN EJECUTIVO DE FILTRADO ---
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

# Validación de datos filtrados
if len(df_filtered) == 0:
    st.error("❌ **No hay datos** con los filtros actuales. Por favor, ajusta los filtros.")
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
        title=f'<b>Tendencia de Alarmas</b><br><sup>{title_suffix}</sup>',
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
st.plotly_chart(crear_grafico_combo(df_filtered, olt_seleccionada), use_container_width=True)

# --- 🔍 ANÁLISIS DRILL-DOWN INTERACTIVO: OLT → DEV_2 → TIPO ALARMA ---
st.divider()
st.subheader("🔍 Análisis Drill-Down Interactivo")

# Inicializar variables de navegación en session_state
if 'drill_olt_selected' not in st.session_state:
    st.session_state.drill_olt_selected = None
if 'drill_dev2_selected' not in st.session_state:
    st.session_state.drill_dev2_selected = None

# Botón para resetear navegación
col_reset_drill, col_space = st.columns([1, 5])
with col_reset_drill:
    if st.button("🔄 Resetear Vista", key="reset_drill"):
        st.session_state.drill_olt_selected = None
        st.session_state.drill_dev2_selected = None
        st.rerun()

# --- NIVEL 1: VISTA POR OLT ---
st.markdown("### 📡 Nivel 1: Alarmas por OLT")

if not df_filtered.empty and 'DEV' in df_filtered.columns:
    # Agrupar por OLT
    alarmas_por_olt = df_filtered.groupby('DEV').size().reset_index(name='Total_Alarmas')
    alarmas_por_olt = alarmas_por_olt.sort_values('Total_Alarmas', ascending=False).head(20)
    
    # Gráfico de barras por OLT
    fig_olt = px.bar(
        alarmas_por_olt,
        x='DEV',
        y='Total_Alarmas',
        text='Total_Alarmas',
        color='Total_Alarmas',
        color_continuous_scale='Reds',
        title=f"Distribución de Alarmas por OLT ({len(alarmas_por_olt)} OLTs)"
    )
    fig_olt.update_traces(textposition='outside')
    fig_olt.update_layout(
        xaxis_title="OLT",
        yaxis_title="Cantidad de Alarmas",
        height=400,
        showlegend=False
    )
    
    st.plotly_chart(fig_olt, use_container_width=True)
    
    # Selector manual de OLT
    olt_seleccionada_drill = st.selectbox(
        "👉 Selecciona una OLT para análisis detallado:",
        ["Ninguna"] + alarmas_por_olt['DEV'].tolist(),
        index=0 if st.session_state.drill_olt_selected is None else 
              alarmas_por_olt['DEV'].tolist().index(st.session_state.drill_olt_selected) + 1 
              if st.session_state.drill_olt_selected in alarmas_por_olt['DEV'].tolist() else 0,
        key="select_olt_drill"
    )
    
    if olt_seleccionada_drill != "Ninguna":
        st.session_state.drill_olt_selected = olt_seleccionada_drill
        
        # --- NIVEL 2: VISTA POR DEV_2 (SLOT-PUERTO) ---
        st.markdown(f"### 🔌 Nivel 2: Puertos de OLT `{olt_seleccionada_drill}`")
        
        df_olt_filtrada = df_filtered[df_filtered['DEV'] == olt_seleccionada_drill]
        
        if 'DEV_2' in df_olt_filtrada.columns:
            alarmas_por_dev2 = df_olt_filtrada.groupby('DEV_2').size().reset_index(name='Total_Alarmas')
            alarmas_por_dev2 = alarmas_por_dev2.sort_values('Total_Alarmas', ascending=False).head(20)
            
            fig_dev2 = px.bar(
                alarmas_por_dev2,
                x='DEV_2',
                y='Total_Alarmas',
                text='Total_Alarmas',
                color='Total_Alarmas',
                color_continuous_scale='Oranges',
                title=f"Top 20 Puertos (DEV_2) con más alarmas en {olt_seleccionada_drill}"
            )
            fig_dev2.update_traces(textposition='outside')
            fig_dev2.update_layout(
                xaxis_title="Puerto (Slot-Puerto)",
                yaxis_title="Cantidad de Alarmas",
                height=400,
                showlegend=False,
                xaxis_tickangle=-45
            )
            
            st.plotly_chart(fig_dev2, use_container_width=True)
            
            # Selector manual de DEV_2
            dev2_seleccionado_drill = st.selectbox(
                "👉 Selecciona un Puerto para ver detalles:",
                ["Ninguno"] + alarmas_por_dev2['DEV_2'].tolist(),
                index=0 if st.session_state.drill_dev2_selected is None else
                      alarmas_por_dev2['DEV_2'].tolist().index(st.session_state.drill_dev2_selected) + 1
                      if st.session_state.drill_dev2_selected in alarmas_por_dev2['DEV_2'].tolist() else 0,
                key="select_dev2_drill"
            )
            
            if dev2_seleccionado_drill != "Ninguno":
                st.session_state.drill_dev2_selected = dev2_seleccionado_drill
                
                # --- NIVEL 3: ANÁLISIS DETALLADO DEL PUERTO ---
                st.markdown(f"### 📊 Nivel 3: Análisis Detallado de `{dev2_seleccionado_drill}`")
                
                df_puerto = df_filtered[
                    (df_filtered['DEV'] == olt_seleccionada_drill) &
                    (df_filtered['DEV_2'] == dev2_seleccionado_drill)
                ]
                
                if not df_puerto.empty:
                    st.info(f"🔍 {len(df_puerto):,} alarmas encontradas en este puerto")
                    
                    col_graph, col_table = st.columns([2, 1])
                    
                    with col_graph:
                        # Gráfico temporal de evolución
                        st.markdown("**📈 Evolución Temporal**")
                        daily_puerto = df_puerto.groupby('Fecha').size().reset_index(name='Cantidad')
                        
                        fig_evol = px.line(
                            daily_puerto,
                            x='Fecha',
                            y='Cantidad',
                            markers=True,
                            title=f"Alarmas diarias en {dev2_seleccionado_drill}"
                        )
                        fig_evol.update_layout(height=300)
                        st.plotly_chart(fig_evol, use_container_width=True)
                        
                        # Mapa de calor: Hora vs Tipo de Alarma
                        st.markdown("**⏰ Mapa de Calor: Hora vs Tipo de Alarma**")
                        df_puerto_heat = df_puerto.copy()
                        df_puerto_heat['Hora'] = df_puerto_heat['HoraPeru'].dt.hour
                        
                        heatmap_puerto = df_puerto_heat.groupby(['Hora', 'TipoFinal']).size().reset_index(name='Conteo')
                        
                        if not heatmap_puerto.empty:
                            fig_heat_puerto = px.density_heatmap(
                                heatmap_puerto,
                                x='Hora',
                                y='TipoFinal',
                                z='Conteo',
                                nbinsx=24,
                                color_continuous_scale='Viridis',
                                title=f"Concentración horaria de alarmas"
                            )
                            fig_heat_puerto.update_xaxes(dtick=1)
                            fig_heat_puerto.update_layout(height=300)
                            st.plotly_chart(fig_heat_puerto, use_container_width=True)
                        else:
                            st.info("Sin suficientes datos para mapa de calor")

                    with col_table:
                        # Tabla resumen por tipo de alarma
                        st.markdown("**📋 Tipos de Alarma**")
                        tipos_puerto = df_puerto['TipoFinal'].value_counts().reset_index()
                        tipos_puerto.columns = ['Tipo', 'Cantidad']
                        st.dataframe(tipos_puerto, hide_index=True, height=200)
                        
                        # Top Clientes por SerialNumber
                        if 'SerialNumber_TDP' in df_puerto.columns:
                            st.markdown("**🎯 Top Clientes (SerialNumber)**")
                            clientes_puerto = df_puerto['SerialNumber_TDP'].value_counts().head(10).reset_index()
                            clientes_puerto.columns = ['SerialNumber', 'Alarmas']
                            st.dataframe(clientes_puerto, hide_index=True, height=250)
                        
                        # Severidad
                        if 'Severity' in df_puerto.columns:
                            st.markdown("**⚠️ Severidad**")
                            severity_puerto = df_puerto['Severity'].value_counts().reset_index()
                            severity_puerto.columns = ['Severidad', 'Cantidad']
                            st.dataframe(severity_puerto, hide_index=True, height=150)
                    

                    
                    # Tabla detallada expandible
                    with st.expander("📂 Ver Detalle Completo de Alarmas", expanded=False):
                        cols_detalle = [
                            c for c in ['HoraPeru', 'TipoFinal', 'Severity', 'ProbableCause', 
                                       'Cliente_puerto', 'SerialNumber_TDP']
                            if c in df_puerto.columns
                        ]
                        st.dataframe(
                            df_puerto[cols_detalle].sort_values('HoraPeru', ascending=False),
                            use_container_width=True,
                            height=400
                        )
                else:
                    st.warning("No hay alarmas para este puerto en el rango seleccionado")
        else:
            st.warning("⚠️ Columna 'DEV_2' no disponible en los datos")
else:
    st.info("Selecciona filtros para comenzar el análisis")

# --- 🏆 TOP 20 PUERTOS PROBLEMÁTICOS (VISTA GLOBAL) ---
st.divider()
st.subheader("🏆 Top 20 Puertos Problemáticos (Vista Global)")

if not df_filtered.empty and 'DEV_2' in df_filtered.columns:
    top_puertos_global = df_filtered['DEV_2'].value_counts().head(20).reset_index()
    top_puertos_global.columns = ['Puerto', 'Total_Alarmas']
    
    # Agregar columna de OLT
    if 'DEV' in df_filtered.columns:
        olt_por_puerto = df_filtered.groupby('DEV_2')['DEV'].first().to_dict()
        top_puertos_global['OLT'] = top_puertos_global['Puerto'].map(olt_por_puerto)
    
    col_top1, col_top2 = st.columns([2, 1])
    
    with col_top1:
        fig_top = px.bar(
            top_puertos_global,
            x='Puerto',
            y='Total_Alarmas',
            text='Total_Alarmas',
            color='Total_Alarmas',
            color_continuous_scale='RdYlGn_r',
            title="Top 20 Puertos con Más Alarmas",
            hover_data=['OLT'] if 'OLT' in top_puertos_global.columns else None
        )
        fig_top.update_traces(textposition='outside')
        fig_top.update_layout(
            xaxis_tickangle=-45,
            height=400,
            showlegend=False
        )
        st.plotly_chart(fig_top, use_container_width=True)
    
    with col_top2:
        st.dataframe(
            top_puertos_global,
            hide_index=True,
            height=400,
            use_container_width=True
        )
else:
    st.info("No hay datos disponibles para mostrar el ranking de puertos")

# --- 🔄 INFORMACIÓN DE ACTUALIZACIÓN ---
st.divider()
st.subheader("📊 Información del Sistema")

col_info_sys1, col_info_sys2, col_info_sys3, col_info_sys4 = st.columns(4)

info_cache = get_info_cache()

with col_info_sys1:
    if info_cache['timestamp_procesamiento']:
        st.metric(
            "⏱️ Última Actualización",
            info_cache['timestamp_procesamiento'].strftime('%H:%M:%S'),
            delta=f"{info_cache['tiempo_procesamiento']:.1f}s procesamiento" if info_cache['tiempo_procesamiento'] else None
        )
    else:
        st.metric("⏱️ Última Actualización", "N/A")

with col_info_sys2:
    if info_cache['timestamp_actuales']:
        tiempo_actuales = datetime.now() - info_cache['timestamp_actuales']
        minutos_actuales = int(tiempo_actuales.total_seconds() / 60)
        st.metric(
            "📡 Alarmas Actuales",
            "Cacheadas",
            delta=f"Hace {minutos_actuales} min" if minutos_actuales < 60 else f"Hace {minutos_actuales//60}h"
        )
    else:
        st.metric("📡 Alarmas Actuales", "No cargadas")

with col_info_sys3:
    if info_cache['timestamp_historicas']:
        tiempo_historicas = datetime.now() - info_cache['timestamp_historicas']
        horas_historicas = int(tiempo_historicas.total_seconds() / 3600)
        st.metric(
            "📚 Alarmas Históricas",
            "Cacheadas",
            delta=f"Hace {horas_historicas}h" if horas_historicas > 0 else "Reciente"
        )
    else:
        st.metric("📚 Alarmas Históricas", "No cargadas")

with col_info_sys4:
    st.metric(
        "🔄 Auto-refresh",
        "5 min (actuales)",
        delta="24h (históricas)"
    )

st.info(
    "ℹ️ **Sistema de Caché Inteligente:**\n"
    "- **Alarmas Actuales** (Huawei/ZTE): Se actualizan automáticamente cada 5 minutos\n"
    "- **Alarmas Históricas**: Se actualizan cada 24 horas (datos más estables)\n"
    "- Usa el botón 🔄 **Actualizar** en el header para forzar recarga inmediata"
)

# --- TABLA DE DATOS ---
st.divider()
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