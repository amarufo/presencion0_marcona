"""
Centro Cultural Marcona -- Dashboard de Analisis
=================================================
Aplicacion Streamlit para justificar la propuesta tecnica
del Centro Cultural Marcona como proyecto multiproposito.
"""

import streamlit as st
import pandas as pd
import numpy as np
import json
import folium
from streamlit_folium import st_folium
import plotly.graph_objects as go
from pathlib import Path

# =============================================
# CONFIGURACION DE PAGINA
# =============================================
st.set_page_config(
    page_title="CENTRO CULTURAL MARCONA - Dashboard Económico",
    page_icon=str(Path(__file__).parent / "assets" / "tactical.jpg"),
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).parent


# =============================================
# CARGA DE DATOS
# =============================================
@st.cache_data
def load_inversiones():
    return pd.read_csv(BASE_DIR / "data" / "inversiones_mapav2.csv")


@st.cache_data
def load_motor():
    with open(BASE_DIR / "data" / "resultado_motor.json", "r", encoding="utf-8") as f:
        return json.load(f)


df = load_inversiones()
motor = load_motor()

# -- Constantes de poblacion (Metodo 2 - INEI) --
MET2 = motor["estadisticas"]["Método 2 (INEI + Proporciones Censo)"]
POB_2026 = MET2["Población total inicial"]       # 21,409
POB_2038 = MET2["Población total final"]          # 30,214
TASA_CRECIMIENTO = MET2["Tasa de crecimiento anual (%)"] / 100  # 0.0291
ANIO_BASE = MET2["Año inicial"]                   # 2026
ANIO_FIN = MET2["Año final"]                      # 2038
POB_0_14 = MET2["Población 0-14 años inicial"]    # 5,364


def proyectar_poblacion(pob_base, anio_base, anio_destino, tasa):
    """Proyeccion geometrica de poblacion."""
    t = anio_destino - anio_base
    return int(round(pob_base * (1 + tasa) ** t))


# -- Separacion Marcona vs otros --
marcona_row = df[df["es_marcona"] == True]
otros = df[df["es_marcona"] == False]


# =============================================
# MODELO DE DIMENSIONAMIENTO
# =============================================
BENCHMARKS = {
    "Lima Metropolitana": {"pob": 10_400_000, "aforo": 1_500, "nombre": "Gran Teatro Nacional"},
    "Ica":                {"pob": 150_000,    "aforo": 230,   "nombre": "Auditorio Ica"},
    "Nasca":              {"pob": 30_000,     "aforo": 200,   "nombre": "Auditorio Nasca (ref.)"},
}


def enfoque_educativo(mayor_alumnos, tasa_part=0.15, ratio_m2=1.0, factor_multi=0.15):
    """
    Enfoque basado en la demanda del colegio mayor, con un factor de multifuncionalidad.
    Args:
        - mayor_alumnos: Numero de alumnos del colegio mayor (ej. 587)
        - tasa_part: Porcentaje de alumnos que participarian (ej. 15%)
        - ratio_m2: Metros cuadrados por persona (ej. 1.0 m2/persona)
        - factor_multi: Incremento porcentual por uso multifuncional (ej. 15% = +15% de demanda)
    """
    demanda_base = int(mayor_alumnos * tasa_part)
    demanda_multi = int(demanda_base * (1 + factor_multi))
    limite_minedu = 300
    aforo = min(demanda_multi, limite_minedu)
    return {
        "enfoque": "A - Educativo (MINEDU)",
        "aforo": aforo,
        "area_m2": aforo * ratio_m2,
        "detalle": (
            f"{tasa_part:.0%} de {mayor_alumnos} alumnos = {demanda_base}, "
            f"+{factor_multi:.0%} multi = {demanda_multi}, "
            f"tope MINEDU = {limite_minedu}"
        ),
    }


def enfoque_poblacional(horizonte_anios=12, ratio_asistencia=0.01, ratio_m2=1.0):
    anio_h = ANIO_BASE + horizonte_anios
    pob_proy = proyectar_poblacion(POB_2026, ANIO_BASE, anio_h, TASA_CRECIMIENTO)
    aforo = int(round(pob_proy * ratio_asistencia))
    return {
        "enfoque": "B - Poblacional",
        "aforo": aforo,
        "area_m2": aforo * ratio_m2,
        "pob_proyectada": pob_proy,
        "anio_horizonte": anio_h,
        "detalle": f"{ratio_asistencia:.1%} de {pob_proy:,.0f} hab. ({anio_h})",
    }


def enfoque_benchmark(aforo_propuesto=450, horizonte_anios=12, ratio_m2=1.0):
    anio_h = ANIO_BASE + horizonte_anios
    pob_proy = proyectar_poblacion(POB_2026, ANIO_BASE, anio_h, TASA_CRECIMIENTO)
    pob_nasca, af_nasca = 30_000, 200
    pob_ica, af_ica = 150_000, 400
    log_pob = np.log(pob_proy)
    log_nasca = np.log(pob_nasca)
    log_ica = np.log(pob_ica)
    aforo_interp = af_nasca + (af_ica - af_nasca) * (log_pob - log_nasca) / (log_ica - log_nasca)
    aforo_interp = int(round(max(aforo_interp, 50)))
    limite_3pct = pob_proy * 0.03
    penalizado = aforo_propuesto > limite_3pct
    score = 1.0 if not penalizado else max(0.3, limite_3pct / aforo_propuesto)
    aforo_bench = int(round(aforo_interp * score))
    return {
        "enfoque": "C - Benchmark",
        "aforo": aforo_bench,
        "area_m2": aforo_bench * ratio_m2,
        "penalizado": penalizado,
        "score": score,
        "detalle": (
            f"Interpolado: {aforo_interp} (log Nasca-Ica), "
            f"Limite 3%={int(limite_3pct)}, "
            f"Score={'ALERTA ' if penalizado else 'OK '}{score:.2f}"
        ),
    }


def calcular_dimensionamiento(
    mayor_alumnos, tasa_part, ratio_m2, horizonte, factor_multi,
    ratio_asistencia, aforo_propuesto
):
    r_edu = enfoque_educativo(mayor_alumnos, tasa_part, ratio_m2, factor_multi)
    r_pob = enfoque_poblacional(horizonte, ratio_asistencia, ratio_m2)
    r_bch = enfoque_benchmark(aforo_propuesto, horizonte, ratio_m2)

    aforos = [r_edu["aforo"], r_pob["aforo"], r_bch["aforo"]]
    rango_min = min(aforos)
    rango_max = max(aforos)
    punto_eq = int(round(np.mean(aforos)))
    area_eq = punto_eq * ratio_m2

    anio_h = ANIO_BASE + horizonte
    pob_proy = proyectar_poblacion(POB_2026, ANIO_BASE, anio_h, TASA_CRECIMIENTO)

    alertas = []
    if aforo_propuesto > 500:
        alertas.append(
            "ALERTA: El aforo excede estandares de sostenibilidad para un distrito "
            "de ~20k habitantes. Riesgo de infraestructura subutilizada."
        )
    if aforo_propuesto > pob_proy * 0.03:
        alertas.append(
            f"ADVERTENCIA: El aforo ({aforo_propuesto}) supera el 3% de la poblacion "
            f"proyectada ({pob_proy:,.0f}). Revisar justificacion."
        )

    return {
        "enfoques": [r_edu, r_pob, r_bch],
        "rango_min": rango_min,
        "rango_max": rango_max,
        "punto_equilibrio": punto_eq,
        "area_equilibrio": area_eq,
        "aforo_propuesto": aforo_propuesto,
        "anio_horizonte": anio_h,
        "pob_proyectada": pob_proy,
        "alertas": alertas,
    }


# =============================================
# ESTILOS PERSONALIZADOS
# =============================================
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Inter', sans-serif;
        font-weight: 700;
        letter-spacing: -0.02em;
    }
    
    .main-title {
        background: linear-gradient(135deg, #0d47a1 0%, #1565c0 50%, #1976d2 100%);
        padding: 20px 30px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    
    .main-title h1 {
        color: white;
        margin: 0;
        font-size: 28px;
        font-weight: 700;
    }
    
    .main-title p {
        color: #bbdefb;
        margin: 5px 0 0 0;
        font-size: 14px;
        font-weight: 400;
    }
    
    .metric-card {
        background: white;
        padding: 15px;
        border-radius: 8px;
        border-left: 4px solid #1565c0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    
    .section-header {
        font-size: 16px;
        font-weight: 600;
        color: #0d47a1;
        margin: 20px 0 10px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #e3f2fd;
    }
    
    .stPlotlyChart {
        background: white;
        border-radius: 8px;
        padding: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
</style>
""", unsafe_allow_html=True)


# =============================================
# TITULO PRINCIPAL
# =============================================
st.markdown("""
<div class="main-title">
    <h1>Centro Cultural Marcona - Dashboard Técnico</h1>
    <p>Análisis comparativo de ratios de inversión en tipología biblioteca | Distrito de Marcona, Ica</p>
</div>
""", unsafe_allow_html=True)


# =============================================
# LAYOUT PRINCIPAL - UNA SOLA PANTALLA
# =============================================

# PANEL DE CONTROL INTERACTIVO
st.markdown('<p class="section-header">⚙️ Parámetros del Proyecto Marcona</p>', unsafe_allow_html=True)

col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3, gap="medium")

with col_ctrl1:
    monto_proyecto = st.number_input(
        "💰 Monto Total del Proyecto (S/)",
        min_value=1_000_000,
        max_value=200_000_000,
        value=int(marcona_row.iloc[0]["monto_viable"]) if not marcona_row.empty else 90_000_000,
        step=1_000_000,
        help="Costo total estimado de inversión del Centro Cultural Marcona",
        format="%d"
    )

with col_ctrl2:
    poblacion_proyecto = st.number_input(
        "👥 Población Beneficiaria Proyectada",
        min_value=5_000,
        max_value=50_000,
        value=int(marcona_row.iloc[0]["poblacion_ref"]) if not marcona_row.empty else 21_409,
        step=500,
        help="Población proyectada del distrito de Marcona al 2026",
        format="%d"
    )

with col_ctrl3:
    # Cálculo automático del ratio
    ratio_calculado = monto_proyecto / poblacion_proyecto
    st.metric(
        "📊 Ratio Costo Calculado",
        f"S/ {ratio_calculado:,.0f}",
        help="Costo por beneficiario = Monto Total / Población"
    )

# Actualizar datos de Marcona con valores interactivos
if not marcona_row.empty:
    marcona_actualizado = marcona_row.copy()
    marcona_actualizado.loc[marcona_actualizado.index[0], "monto_viable"] = monto_proyecto
    marcona_actualizado.loc[marcona_actualizado.index[0], "poblacion_ref"] = poblacion_proyecto
    marcona_actualizado.loc[marcona_actualizado.index[0], "ratio_costo"] = ratio_calculado
    
    # Recalcular ratio_costo_norm
    min_ratio = otros["ratio_costo"].min()
    max_ratio = otros["ratio_costo"].max()
    marcona_actualizado.loc[marcona_actualizado.index[0], "ratio_costo_norm"] = (
        (ratio_calculado - min_ratio) / (max_ratio - min_ratio) if max_ratio > min_ratio else 0.5
    )
    
    mr = marcona_actualizado.iloc[0]
else:
    mr = None

st.markdown("---")

# FILA 1: Mapa + Indicadores Clave
col_mapa, col_stats = st.columns([6, 4], gap="medium")

with col_mapa:
    st.markdown('<p class="section-header">📍 Proyectos bibliotecarios a nivel nacional</p>', unsafe_allow_html=True)
    
    # Crear mapa con leyenda
    m = folium.Map(
        location=[-9.19, -75.015],
        zoom_start=5,
        tiles="CartoDB positron",
    )
    
    # Agregar marcadores
    for idx, row in df.iterrows():
        if pd.isna(row["latitud"]) or pd.isna(row["longitud"]):
            continue
        es_m = bool(row.get("es_marcona", False))
        
        popup_html = f"""
        <div style="width: 300px; font-family: 'Inter', Arial, sans-serif;">
            <h4 style="color: {'#c62828' if es_m else '#1565c0'}; 
                       margin-bottom: 10px; font-size: 14px; font-weight: 600;">
                {row['entidad']}
            </h4>
            <table style="font-size: 12px; width: 100%; border-collapse: collapse;">
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 4px 0; font-weight: 600;">Población proyectada el 2026:</td>
                    <td style="padding: 4px 0;">{row['poblacion_ref']:,.0f} hab.</td>
                </tr>
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 4px 0; font-weight: 600;">Ratio Costo:</td>
                    <td style="padding: 4px 0;">S/ {row['ratio_costo']:,.0f} /hab</td>
                </tr>
                <tr>
                    <td style="padding: 4px 0; font-weight: 600;">Tipo:</td>
                    <td style="padding: 4px 0;">{row['tipo']}</td>
                </tr>
            </table>
        </div>
        """
        
        if es_m:
            folium.Marker(
                [row["latitud"], row["longitud"]],
                popup=folium.Popup(popup_html, max_width=350),
                tooltip="<b>CENTRO CULTURAL MARCONA</b> (Propuesta)",
                icon=folium.Icon(color="red", icon="star", prefix="fa"),
            ).add_to(m)
        else:
            ratio_norm = row.get("ratio_costo_norm", 0.5)
            
            if ratio_norm < 0.1:
                color = "#42a5f5"
            elif ratio_norm < 0.5:
                color = "#ffa726"
            else:
                color = "#ef5350"
            
            radius = 6 + ratio_norm * 8
            
            folium.CircleMarker(
                [row["latitud"], row["longitud"]],
                radius=radius,
                popup=folium.Popup(popup_html, max_width=350),
                tooltip=f"<b>{row['entidad'][:60]}</b><br>Ratio: S/ {row['ratio_costo']:,.0f}/hab",
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.75,
                weight=2,
            ).add_to(m)
    
    # Agregar leyenda al mapa
    from branca.element import MacroElement
    from jinja2 import Template
    
    template = """
    {% macro html(this, kwargs) %}
    <div style="position: fixed; 
                bottom: 50px; right: 50px; 
                background-color: white;
                border: 2px solid #1565c0;
                border-radius: 8px;
                padding: 10px;
                font-family: 'Inter', Arial, sans-serif;
                font-size: 11px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
                z-index: 9999;">
        <p style="margin: 0 0 8px 0; font-weight: bold; color: #0d47a1;">
            Ratio Costo/Beneficiario
        </p>
        <div style="margin: 4px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; 
                         background: #42a5f5; border-radius: 50%; margin-right: 6px;"></span>
            Bajo (&lt; percentil 33)
        </div>
        <div style="margin: 4px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; 
                         background: #ffa726; border-radius: 50%; margin-right: 6px;"></span>
            Medio (percentil 33-66)
        </div>
        <div style="margin: 4px 0;">
            <span style="display: inline-block; width: 12px; height: 12px; 
                         background: #ef5350; border-radius: 50%; margin-right: 6px;"></span>
            Alto (&gt; percentil 66)
        </div>
        <div style="margin: 8px 0 4px 0;">
            <span style="color: #c62828; font-size: 14px; margin-right: 6px;">★</span>
            <b>Centro Cultural Marcona</b>
        </div>
    </div>
    {% endmacro %}
    """
    
    macro = MacroElement()
    macro._template = Template(template)
    m.get_root().add_child(macro)
    
    st_folium(m, width=None, height=450, returned_objects=[])

with col_stats:
    st.markdown('<p class="section-header">📊 Indicadores clave del proyecto</p>', unsafe_allow_html=True)
    
    if mr is not None:
        promedio_ratio = otros["ratio_costo"].mean()
        mediana_ratio = otros["ratio_costo"].median()
        percentil = (otros["ratio_costo"] < mr["ratio_costo"]).sum() / len(otros) * 100
        
        # Indicadores en cards
        st.markdown(f"""
        <div class="metric-card">
            <h5 style="color: #1565c0; margin: 0 0 0 0; font-size: 14px;">Promedio típico de costo por habitante</h5>
            <p style="font-size: 28px; font-weight: 700; color: #0d47a1; margin: 0;">
                S/ {mediana_ratio:,.0f}
            </p>
            <p style="font-size: 12px; color: #666; margin: 1px 0 0 0;">
                Es el costo por habitante más representativo entre los proyectos analizados (mediana)
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="metric-card">
            <h5 style="color: #1565c0; margin: 0 0 0 0; font-size: 14px;">¿Qué población se espera en el 2036?</h5>
            <p style="font-size: 28px; font-weight: 700; color: #0d47a1; margin: 0;">
                {mr["poblacion_ref"]:,.0f}
            </p>
            <p style="font-size: 12px; color: #666; margin: 1px 0 0 0;">
                Población beneficiaria actual del proyecto según parámetros configurados.
            </p>
        </div>
        """, unsafe_allow_html=True)        
        
        costo_referencial = mediana_ratio * mr["poblacion_ref"]
        diferencia_costo = ((mr["monto_viable"] / costo_referencial - 1) * 100) if costo_referencial > 0 else 0
        
        st.markdown(f"""
        <div class="metric-card">
            <h5 style="color: #1565c0; margin: 0 0 0 0; font-size: 14px;">¿Cuánto debería costar idealmente?</h5>
            <p style="font-size: 28px; font-weight: 700; color: {'#d32f2f' if diferencia_costo > 50 else '#388e3c' if diferencia_costo < 0 else '#f57c00'}; margin: 0;">
                S/ {costo_referencial:,.0f}
            </p>
            <p style="font-size: 12px; color: #666; margin: 1px 0 0 0;">
                Basado en ratio típico (S/ {mediana_ratio:,.0f}/hab). 
                <b style="color: {'#d32f2f' if diferencia_costo > 0 else '#388e3c'};">
                {diferencia_costo:+.1f}%</b> vs monto actual
            </p>
        </div>
        """, unsafe_allow_html=True)

# FILA 2: Gráficos Comparativos
st.markdown('<p class="section-header">📈 Análisis Comparativo de Ratios</p>', unsafe_allow_html=True)

col_g1, col_g2, col_g3 = st.columns(3, gap="medium")

with col_g1:
    # Distribución de ratios con marcona destacado
    fig_hist = go.Figure()
    
    fig_hist.add_trace(go.Histogram(
        x=otros["ratio_costo"],
        name="Otros Proyectos",
        marker_color="#64b5f6",
        opacity=0.75,
        nbinsx=25,
        hovertemplate="<b>Rango:</b> %{x}<br><b>Frecuencia:</b> %{y}<extra></extra>",
    ))
    
    if mr is not None:
        fig_hist.add_vline(
            x=mr["ratio_costo"],
            line_dash="solid",
            line_color="#c62828",
            line_width=3,
            annotation_text=f"<b>Marcona</b><br>S/ {mr['ratio_costo']:,.0f}",
            annotation_position="top",
            annotation=dict(font=dict(size=11, color="#c62828")),
        )
        
        # Agregar punto en la línea vertical
        fig_hist.add_trace(go.Scatter(
            x=[mr["ratio_costo"]],
            y=[5],
            mode="markers",
            marker=dict(size=14, color="#c62828", symbol="star", line=dict(color="white", width=2)),
            showlegend=False,
            hovertemplate=f"<b>Centro Cultural Marcona</b><br>Ratio: S/ {mr['ratio_costo']:,.0f}/hab<br>Monto: S/ {mr['monto_viable']:,.0f}<br>Población: {mr['poblacion_ref']:,.0f}<extra></extra>",
        ))
    
    fig_hist.update_layout(
        title=dict(
            text="<b>Distribución de Ratios Costo/Beneficiario</b>",
            font=dict(size=14, family="Inter"),
        ),
        xaxis_title="Ratio (S/. por habitante)",
        yaxis_title="Número de Proyectos",
        template="plotly_white",
        height=300,
        margin=dict(t=50, b=40, l=40, r=20),
        showlegend=False,
        font=dict(family="Inter", size=11),
    )
    st.plotly_chart(fig_hist, width="stretch", key="fig_hist_ratio")

with col_g2:
    # Box plot por tipo con Marcona
    fig_box = go.Figure()
    
    for tipo in df["tipo"].unique():
        df_tipo = otros[otros["tipo"] == tipo]
        fig_box.add_trace(go.Box(
            y=df_tipo["ratio_costo"],
            name=tipo,
            marker_color="#66bb6a",
            boxmean="sd",
            hovertemplate="<b>" + tipo + "</b><br>Ratio: S/ %{y:,.0f}/hab<extra></extra>",
        ))
    
    if mr is not None:
        fig_box.add_trace(go.Scatter(
            x=[mr["tipo"]],
            y=[mr["ratio_costo"]],
            mode="markers",
            marker=dict(size=16, color="#c62828", symbol="star", line=dict(color="white", width=2)),
            name="Marcona",
            hovertemplate=f"<b>Marcona</b><br>Tipo: {mr['tipo']}<br>Ratio: S/ {mr['ratio_costo']:,.0f}/hab<br>Monto: S/ {mr['monto_viable']:,.0f}<br>Población: {mr['poblacion_ref']:,.0f}<extra></extra>",
        ))
    
    fig_box.update_layout(
        title=dict(
            text="<b>Ratios por Tipo de Proyecto</b>",
            font=dict(size=14, family="Inter"),
        ),
        yaxis_title="Ratio (S/. por habitante)",
        template="plotly_white",
        height=300,
        margin=dict(t=50, b=40, l=40, r=20),
        showlegend=False,
        font=dict(family="Inter", size=11),
    )
    st.plotly_chart(fig_box, key="fig_box_tipo")

with col_g3:
    # Scatter: Población vs Ratio
    fig_scatter = go.Figure()
    
    fig_scatter.add_trace(go.Scatter(
        x=otros["pob_dist"],
        y=otros["ratio_costo"],
        mode="markers",
        marker=dict(
            size=8,
            color=otros["ratio_costo_norm"] if "ratio_costo_norm" in otros.columns else otros["ratio_costo"],
            colorscale="RdYlBu_r",
            showscale=False,
            line=dict(color="white", width=0.5),
        ),
        name="Otros",
        text=otros["nombre_pip"].str[:40],
        hovertemplate="<b>%{text}</b><br>Población: %{x:,.0f} hab<br>Ratio: S/ %{y:,.0f}/hab<extra></extra>",
    ))
    
    if mr is not None:
        fig_scatter.add_trace(go.Scatter(
            x=[mr["pob_dist"]],
            y=[mr["ratio_costo"]],
            mode="markers",
            marker=dict(size=20, color="#c62828", symbol="star", line=dict(color="white", width=2)),
            name="Marcona",
            hovertemplate=f"<b>Centro Cultural Marcona</b><br>Población: {mr['pob_dist']:,.0f} hab<br>Ratio: S/ {mr['ratio_costo']:,.0f}/hab<br>Monto: S/ {mr['monto_viable']:,.0f}<extra></extra>",
        ))
    
    fig_scatter.update_layout(
        title=dict(
            text="<b>Población Distrital vs Ratio</b>",
            font=dict(size=14, family="Inter"),
        ),
        xaxis_title="Población Distrital (habitantes)",
        yaxis_title="Ratio (S/. por habitante)",
        template="plotly_white",
        height=300,
        margin=dict(t=50, b=40, l=40, r=20),
        showlegend=False,
        font=dict(family="Inter", size=11),
        xaxis=dict(type="log"),
    )
    st.plotly_chart(fig_scatter, key="fig_scatter_pob")

# FILA 3: Recomendaciones Estratégicas
st.markdown('<p class="section-header">💡 Recomendaciones Estratégicas</p>', unsafe_allow_html=True)

st.markdown("""
<div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 12px;">
    <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); 
                padding: 15px; border-radius: 8px; border-left: 4px solid #2e7d32;">
        <h4 style="color: #2e7d32; margin: 0 0 8px 0; font-size: 13px; font-weight: 700;">
            1. Cambio de Tipología
        </h4>
        <p style="font-size: 11px; color: #1b5e20; margin: 0; line-height: 1.5;">
            La mejor opción para el proyecto es formularlo mediante un <b>proyecto multipropósito</b> cerrando múltiples brechas (educación, cultura, turismo) para aumentar beneficiarios y viabilidad económica. Esto permitirá aprovechar sinergias entre sectores, recoger más población beneficiaria y generar un impacto más integral en el distrito. Es la oportunidad de transformar el proyecto en un verdadero motor de desarrollo local, no solo un espacio cultural aislado.
        </p>
    </div>
    <div style="background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); 
                padding: 15px; border-radius: 8px; border-left: 4px solid #1565c0;">
        <h4 style="color: #1565c0; margin: 0 0 8px 0; font-size: 13px; font-weight: 700;">
            2. Optimización de Aforo
        </h4>
        <p style="font-size: 11px; color: #0d47a1; margin: 0; line-height: 1.5;">
            Sobre el auditorio, la propuesta técnica es un auditorio de entre <b>150-300 butacas</b> con capacidad multifuncional orientado a ser soporte de las actividades colectivas de la poblaicón de Marcon. Migrar a <b>Centro Digital de Inmersión</b> 
        </p>
    </div>
    <div style="background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); 
                padding: 15px; border-radius: 8px; border-left: 4px solid #ef6c00;">
        <h4 style="color: #ef6c00; margin: 0 0 8px 0; font-size: 13px; font-weight: 700;">
            3. Articulación Sectorial
        </h4>
        <p style="font-size: 11px; color: #e65100; margin: 0; line-height: 1.5;">
            Será importante la capacidad de articulación entre sectores: educación (principalmente), cultura, turismo y actividades económicas del distrito. El objetivo es generar sinergias que visivilicen el proyecto como un motor de desarrollo regional y nacional, no solo un espacio cultural aislado. Esto implica diseñar programas y actividades que integren a la comunidad educativa, artistas locales, operadores turísticos y emprendedores para maximizar el impacto social y económico del centro cultural.
        </p>
    </div>
    <div style="background: linear-gradient(135deg, #fce4ec 0%, #f8bbd0 100%); 
                padding: 15px; border-radius: 8px; border-left: 4px solid #c62828;">
        <h4 style="color: #c62828; margin: 0 0 8px 0; font-size: 13px; font-weight: 700;">
            4. Sostenibilidad
        </h4>
        <p style="font-size: 11px; color: #b71c1c; margin: 0; line-height: 1.5;">
            Coordinar grupos sociales y entidades públicas será fundamental, el objetivo será utilizar el Centro Cultural Marcona como un espacio de encuentro comunitario, educativo y turístico que integre a la población local y atraiga visitantes. 
        </p>
    </div>
</div>
""", unsafe_allow_html=True)
# =============================================
# PANEL DE DIMENSIONAMIENTO DEL AUDITORIO
# =============================================
st.markdown('<p class="section-header">🎭 Panel de Dimensionamiento del Auditorio/SUM</p>', unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(135deg, #f5f5f5 0%, #e8eaf6 100%); 
            padding: 15px; border-radius: 8px; margin-bottom: 20px; border-left: 4px solid #3949ab;">
    <p style="font-size: 12px; color: #1a237e; margin: 0; line-height: 1.6;">
        Este modelo de dimensionamiento evalúa el aforo óptimo del auditorio mediante <b>tres enfoques complementarios</b>: 
        <b>educativo</b> (demanda escolar), <b>poblacional</b> (proyección habitantes) y <b>benchmark</b> 
        (comparativo con ciudades similares). Ajusta los parámetros para encontrar el equilibrio entre 
        funcionalidad y sostenibilidad.
    </p>
</div>
""", unsafe_allow_html=True)

# Constantes del padrón educativo (del notebook)
COLEGIO_MAYOR_ALUMNOS = 976
COLEGIO_MAYOR_NOMBRE = "23544 CORONEL FRANCISCO BOLOGNESI"

# Controles en columnas
col_ctrl1, col_ctrl2, col_ctrl3 = st.columns(3, gap="medium")

with col_ctrl1:
    tasa_participacion = st.slider(
        "📚 Participación Escolar (%)",
        min_value=10, max_value=100, value=50, step=5,
        help=f"% de alumnos del colegio mayor ({COLEGIO_MAYOR_ALUMNOS}) que asisten simultáneamente"
    ) / 100
    
    ratio_m2_persona = st.slider(
        "📐 m² por Persona",
        min_value=0.8, max_value=1.5, value=1.0, step=0.1,
        help="Metros cuadrados por butaca (incluye circulación)"
    )

with col_ctrl2:
    horizonte_anos = st.slider(
        "📅 Horizonte de Proyección (años)",
        min_value=5, max_value=20, value=12, step=1,
        help="Años hacia el futuro para calcular población proyectada"
    )
    
    factor_multi = st.slider(
        "🔄 Factor Multifuncionalidad (%)",
        min_value=0, max_value=50, value=15, step=5,
        help="Incremento en demanda por usos múltiples del espacio"
    ) / 100

with col_ctrl3:
    ratio_asistencia = st.slider(
        "👥 Ratio Asistencia Poblacional (%)",
        min_value=0.5, max_value=5.0, value=1.0, step=0.5,
        help="% de la población que asiste a un evento típico"
    ) / 100
    
    aforo_propuesto = st.slider(
        "🎯 Aforo Propuesto (butacas)",
        min_value=100, max_value=800, value=450, step=10,
        help="Propuesta inicial del área usuaria para comparar"
    )

# Calcular dimensionamiento
resultado = calcular_dimensionamiento(
    mayor_alumnos=COLEGIO_MAYOR_ALUMNOS,
    tasa_part=tasa_participacion,
    ratio_m2=ratio_m2_persona,
    horizonte=horizonte_anos,
    factor_multi=factor_multi,
    ratio_asistencia=ratio_asistencia,
    aforo_propuesto=aforo_propuesto
)

# Visualización
col_graf, col_res = st.columns([6, 4], gap="medium")

with col_graf:
    enf = resultado["enfoques"]
    colores_enf = ["#42a5f5", "#66bb6a", "#ffa726"]
    
    fig_dim = go.Figure()
    
    # Barras de los tres enfoques
    for i, e in enumerate(enf):
        fig_dim.add_trace(go.Bar(
            x=[e["enfoque"]],
            y=[e["aforo"]],
            name=e["enfoque"],
            marker_color=colores_enf[i],
            text=[f"{e['aforo']} butacas"],
            textposition="outside",
            hovertext=e["detalle"],
            width=0.35,
        ))
    
    # Punto de equilibrio
    fig_dim.add_trace(go.Bar(
        x=["✦ Recomendación"],
        y=[resultado["punto_equilibrio"]],
        name=f"Equilibrio: {resultado['punto_equilibrio']}",
        marker_color="#ab47bc",
        text=[f"✦ {resultado['punto_equilibrio']} butacas"],
        textposition="outside",
        width=0.35,
    ))
    
    # Propuesta inicial
    fig_dim.add_trace(go.Bar(
        x=["⚠️ Propuesta Inicial"],
        y=[resultado["aforo_propuesto"]],
        name=f"Propuesta: {resultado['aforo_propuesto']}",
        marker_color="#ef5350",
        text=[f"{resultado['aforo_propuesto']} butacas"],
        textposition="outside",
        width=0.35,
    ))
    
    # Rango recomendado
    fig_dim.add_hline(
        y=resultado["rango_min"], line_dash="dot", line_color="green",
        annotation_text=f"Mín: {resultado['rango_min']}",
        annotation_position="top left"
    )
    fig_dim.add_hline(
        y=resultado["rango_max"], line_dash="dot", line_color="orange",
        annotation_text=f"Máx: {resultado['rango_max']}",
        annotation_position="top left"
    )
    fig_dim.add_hrect(
        y0=resultado["rango_min"], y1=resultado["rango_max"],
        fillcolor="green", opacity=0.08, line_width=0
    )
    
    fig_dim.update_layout(
        title=dict(
            text=(f"<b>Dimensionamiento Auditorio/SUM - Marcona</b><br>"
                  f"<sub>Horizonte {resultado['anio_horizonte']} | "
                  f"Pob. Proyectada: {resultado['pob_proyectada']:,.0f} hab.</sub>"),
            font=dict(size=14, family="Inter"),
        ),
        yaxis_title="Aforo (butacas)",
        template="plotly_white",
        height=450,
        showlegend=False,
        yaxis=dict(
            range=[0, max(resultado["aforo_propuesto"], resultado["rango_max"], 
                         resultado["punto_equilibrio"]) * 1.25]
        ),
        margin=dict(t=80, b=40),
        font=dict(family="Inter", size=11),
    )
    st.plotly_chart(fig_dim, key="fig_dimensionamiento")

with col_res:
    st.markdown(f"""
    <div style="background: #f8f9fa; padding: 16px; border-radius: 8px; 
                border-left: 4px solid #1976d2; margin-bottom: 12px;">
        <h4 style="color: #1976d2; margin: 0 0 10px 0; font-size: 13px; font-weight: 700;">
            📊 Parámetros de Entrada
        </h4>
        <table style="font-size: 11px; width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 3px 0;"><b>Año horizonte:</b></td>
                <td style="text-align: right;">{resultado['anio_horizonte']}</td>
            </tr>
            <tr>
                <td style="padding: 3px 0;"><b>Población proyectada:</b></td>
                <td style="text-align: right;">{resultado['pob_proyectada']:,.0f} hab.</td>
            </tr>
            <tr>
                <td style="padding: 3px 0;"><b>Participación escolar:</b></td>
                <td style="text-align: right;">{tasa_participacion:.0%}</td>
            </tr>
            <tr>
                <td style="padding: 3px 0;"><b>Colegio referencia:</b></td>
                <td style="text-align: right;">{COLEGIO_MAYOR_NOMBRE}</td>
            </tr>
            <tr>
                <td style="padding: 3px 0;"><b>Alumnos colegio mayor:</b></td>
                <td style="text-align: right;">{COLEGIO_MAYOR_ALUMNOS}</td>
            </tr>
        </table>
    </div>
    
    <div style="background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); 
                padding: 16px; border-radius: 8px; border-left: 4px solid #2e7d32; margin-bottom: 12px;">
        <h4 style="color: #2e7d32; margin: 0 0 10px 0; font-size: 13px; font-weight: 700;">
            ✅ Resultados por Enfoque
        </h4>
        <table style="font-size: 11px; width: 100%; border-collapse: collapse;">
    """, unsafe_allow_html=True)
    
    for e in enf:
        st.markdown(f"""
            <tr>
                <td style="padding: 4px 0; font-weight: 600;">{e['enfoque']}:</td>
                <td style="text-align: right;">{e['aforo']} butacas ({e['area_m2']:.0f} m²)</td>
            </tr>
            <tr>
                <td colspan="2" style="color: #666; font-size: 10px; padding-bottom: 6px;">
                    {e['detalle']}
                </td>
            </tr>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
        </table>
    </div>
    
    <div style="background: linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%); 
                padding: 16px; border-radius: 8px; border-left: 4px solid #7b1fa2;">
        <h4 style="color: #7b1fa2; margin: 0 0 8px 0; font-size: 13px; font-weight: 700;">
            🎯 Recomendación Final
        </h4>
        <p style="font-size: 12px; margin: 8px 0;">
            <b>Rango recomendado:</b> 
            <span style="color: #2e7d32; font-weight: bold;">
                {resultado['rango_min']} – {resultado['rango_max']} butacas
            </span>
        </p>
        <p style="font-size: 14px; margin: 8px 0;">
            <b>Punto de equilibrio:</b> 
            <span style="color: #7b1fa2; font-weight: bold; font-size: 18px;">
                {resultado['punto_equilibrio']} butacas
            </span>
            <br><span style="font-size: 11px;">→ Área: {resultado['area_equilibrio']:.0f} m²</span>
        </p>
        <p style="font-size: 12px; margin: 8px 0;">
            <b>Propuesta inicial:</b> 
            <span style="color: #c62828; font-weight: bold;">
                {resultado['aforo_propuesto']} butacas
            </span>
        </p>
    """, unsafe_allow_html=True)
    
    if resultado.get("alertas"):
        for alerta in resultado["alertas"]:
            icono = "⚠️" if "ALERTA" in alerta else "ℹ️"
            color = "#ff6f00" if "ALERTA" in alerta else "#1976d2"
            st.markdown(f"""
                <div style="background: #fff3e0; padding: 10px; border-radius: 6px; 
                            border-left: 3px solid {color}; margin-top: 8px;">
                    <p style="font-size: 10px; color: {color}; margin: 0;">
                        {icono} {alerta}
                    </p>
                </div>
            """, unsafe_allow_html=True)
    
    st.markdown("</div>", unsafe_allow_html=True)
# PIE DE PÁGINA
st.markdown("""
<div style="text-align: center; color: #999; font-size: 11px; 
            padding: 20px 0 10px 0; margin-top: 30px; 
            border-top: 1px solid #e0e0e0; font-family: 'Inter', sans-serif;">
    <b>Centro Cultural Marcona</b> | Fuentes: MEF - Invierte.pe, INEI | 
    Análisis comparativo de 43 proyectos de tipología biblioteca | Febrero 2026 | Econ. Amaru Fernandez | https://invierteia.streamlit.app/
</div>
""", unsafe_allow_html=True)
