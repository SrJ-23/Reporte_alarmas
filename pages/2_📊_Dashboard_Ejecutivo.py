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
    </style>
""", unsafe_allow_html=True)

st.title("📉 Dashboard Histórico de Alarmas ")
st.markdown("**Gestor:** Huawei | **Alcance:** Datos históricos y tendencias por Tipo de Alarma")

# --- CARGA DE DATOS ---
if "data" not in st.session_state:
    with st.spinner("Cargando histórico de alarmas Huawei..."):
        raw_data = get_alarmas()
        # Filtrar explícitamente por Huawei
        if 'Gestor' in raw_data.columns:
            raw_data = raw_data[raw_data['Gestor'].astype(str).str.contains('Huawei', case=False, na=False)]
        st.session_state.data = raw_data

df = st.session_state.data.copy()

if df.empty:
    st.error("No se encontraron datos históricos de Huawei 😢")
    st.stop()

# --- PREPROCESAMIENTO ---
df["HoraPeru"] = pd.to_datetime(df["HoraPeru"], errors="coerce")
df = df.dropna(subset=["HoraPeru"])
df['Fecha'] = df['HoraPeru'].dt.date

# Asegurar que exista TipoFinal (Rellenar si es nulo para evitar errores en el gráfico)
if 'TipoFinal' not in df.columns:
    df['TipoFinal'] = 'Desconocido'
else:
    df['TipoFinal'] = df['TipoFinal'].fillna('Otros')

# --- FILTROS UNIFICADOS ---
with st.container():
    st.subheader("🔍 Filtros de Visualización")
    
    col1, col2, col3 = st.columns([1, 1, 2])
    
    with col1:
        # Filtro de OLT
        olts_disponibles = sorted(df['DEV'].dropna().unique().tolist())
        olt_seleccionada = st.selectbox(
            "Seleccionar OLT",
            ["Todas"] + olts_disponibles,
            index=0,
            help="Selecciona 'Todas' para ver el Top 5 global, o una específica para detalle."
        )

    with col2:
        # Filtro por TIPO FINAL (Ajustado según requerimiento)
        tipos_disponibles = sorted(df['TipoFinal'].unique().tolist())
        tipo_filtro = st.multiselect("Filtrar Tipo de Alarma", tipos_disponibles, default=tipos_disponibles)

    with col3:
        # Selector de Rango de Fechas
        fecha_min_df = df["Fecha"].min()
        fecha_max_df = df["Fecha"].max()
        
        fechas_seleccionadas = st.date_input(
            "Rango de Fechas",
            value=(fecha_max_df - timedelta(days=7), fecha_max_df),
            min_value=fecha_min_df,
            max_value=fecha_max_df
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
    (df['TipoFinal'].isin(tipo_filtro))
)

if olt_seleccionada != "Todas":
    mask = mask & (df['DEV'] == olt_seleccionada)

df_filtered = df[mask].copy()

# --- KPIs METRICS ---
def mostrar_kpis(df_kpi, df_total_hist):
    col1, col2, col3, col4 = st.columns(4)
    
    total_alarmas = len(df_kpi)
    n_olts = df_kpi['DEV'].nunique()
    
    # Comparativa temporal simple
    dias_rango = (end_date - start_date).days + 1
    prev_start = start_date - timedelta(days=dias_rango)
    # Filtramos el histórico total para la comparativa
    df_prev = df_total_hist[(df_total_hist['Fecha'] >= prev_start) & (df_total_hist['Fecha'] < start_date)]
    
    delta_alarmas = total_alarmas - len(df_prev)
    
    # Tipo más frecuente en el rango
    tipo_top = df_kpi['TipoFinal'].mode()[0] if not df_kpi.empty else "N/A"

    with col1:
        st.metric("Total Alarmas (Rango)", f"{total_alarmas:,}", delta=f"{delta_alarmas} vs periodo ant.")
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
    """
    Gráfico Combinado:
    1. Barras Apiladas: Cantidad por TipoFinal.
    2. Líneas: Evolución de Top 5 OLTs (si 'Todas') o la OLT seleccionada.
    """
    if df_in.empty:
        return go.Figure().add_annotation(text="Sin datos en el rango seleccionado", showarrow=False)

    fig = go.Figure()
    
    # --- PARTE 1: BARRAS APILADAS (Por TipoFinal) ---
    # Agrupar por fecha y TipoFinal
    daily_tipo = df_in.groupby(['Fecha', 'TipoFinal']).size().reset_index(name='Count')
    
    # Obtener tipos únicos presentes en el filtro
    tipos_presentes = daily_tipo['TipoFinal'].unique()
    
    # Paleta de colores para tipos (Plotly qualitative colors)
    colors = px.colors.qualitative.Plotly
    
    for i, tipo in enumerate(tipos_presentes):
        subset = daily_tipo[daily_tipo['TipoFinal'] == tipo]
        color_idx = i % len(colors)
        
        fig.add_trace(go.Bar(
            x=subset['Fecha'],
            y=subset['Count'],
            name=str(tipo), # Nombre en leyenda
            marker_color=colors[color_idx],
            opacity=0.4,  # Transparencia para que resalten las líneas
            hoverinfo='y+name'
        ))

    # --- PARTE 2: LÍNEAS (Evolución por OLT) ---
    
    if olt_sel == "Todas":
        # Top 5 OLTs en el periodo
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
        # Línea de la OLT seleccionada
        title_suffix = f"Evolución: {olt_sel}"
        daily_olt = df_in.groupby('Fecha').size().reset_index(name='Count')
        
        fig.add_trace(go.Scatter(
            x=daily_olt['Fecha'],
            y=daily_olt['Count'],
            mode='lines+markers',
            name=f'Tendencia {olt_sel}',
            line=dict(width=4, color='#2c3e50'), # Color oscuro para resaltar sobre barras
            marker=dict(size=8)
        ))

    # Layout
    fig.update_layout(
        title=f'<b>Tendencia de Alarmas Huawei</b><br><sup>{title_suffix}</sup>',
        xaxis_title='Fecha',
        yaxis_title='Cantidad de Alarmas',
        barmode='stack', # Apilar las barras de TipoFinal
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        height=500,
        template="plotly_white"
    )
    
    return fig

st.subheader("📊 Evolutivo Principal")
st.plotly_chart(crear_grafico_combo(df_filtered, olt_seleccionada), use_container_width=True)

# --- GRÁFICOS SECUNDARIOS ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("🔌 Top Recurrencia (DEV-SN-PN)")
    
    if not df_filtered.empty:
        df_concatenado = df_filtered.copy()
        
        cols_necesarias = ['DEV', 'SN', 'PN']
        
        # Verificar si existen todas las columnas
        if all(col in df_concatenado.columns for col in cols_necesarias):
            
            # --- PASO CLAVE: Limpieza de decimales (.0) en SN y PN ---
            for col in ['SN', 'PN']:
                # 1. Convertir a numérico forzado (errores se vuelven NaN)
                df_concatenado[col] = pd.to_numeric(df_concatenado[col], errors='coerce')
                # 2. Rellenar vacíos con -1, convertir a Entero (quita el .0) y luego a Texto
                df_concatenado[col] = df_concatenado[col].fillna(-1).astype(int).astype(str)
                # 3. Opcional: Reemplazar el -1 por '?' si prefieres ver un signo de interrogación en datos faltantes
                df_concatenado[col] = df_concatenado[col].replace('-1', '?')

            # Limpiar DEV (asegurar texto)
            df_concatenado['DEV'] = df_concatenado['DEV'].fillna('?').astype(str)
            
            # --- Concatenación ---
            df_concatenado['Identificador'] = (
                df_concatenado['DEV'] + "-" + 
                df_concatenado['SN'] + "-" + 
                df_concatenado['PN']
            )
            
            # Filtrar datos sucios (ej. ?-?-?)
            df_concatenado = df_concatenado[~df_concatenado['Identificador'].str.contains(r'\?-\?-\?')]
            
            if not df_concatenado.empty:
                # Contar ocurrencias
                top_dev_sn_pn = df_concatenado['Identificador'].value_counts().head(10).reset_index()
                top_dev_sn_pn.columns = ['Identificador', 'Cantidad']
                
                # Gráfico
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
                st.plotly_chart(fig_p, use_container_width=True)
            else:
                st.info("No hay datos válidos de DEV-SN-PN en la selección.")
        else:
            st.warning(f"Faltan columnas en los datos: {[c for c in cols_necesarias if c not in df_concatenado.columns]}")
    else:
        st.info("Sin datos para mostrar con los filtros actuales.")
        
with col_right:
    st.subheader("⏰ Mapa de Calor: Hora vs Tipo")
    if not df_filtered.empty:
        df_heat = df_filtered.copy()
        df_heat['Hora'] = df_heat['HoraPeru'].dt.hour
        
        # Heatmap usando TipoFinal en lugar de Severity
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
        st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.info("Sin datos para mapa de calor.")

# --- TABLA DE DATOS ---
with st.expander("📂 Ver Datos Detallados (Últimas 100)"):
    cols_to_show = [c for c in ['HoraPeru', 'DEV', 'TipoFinal', 'Severity', 'ProbableCause'] if c in df_filtered.columns]
    st.dataframe(
        df_filtered[cols_to_show].sort_values('HoraPeru', ascending=False).head(100),
        use_container_width=True
    )

st.markdown("---")
st.caption(f"Dashboard generado el {datetime.now().strftime('%d/%m/%Y %H:%M')} | Huawei Datos Históricos")