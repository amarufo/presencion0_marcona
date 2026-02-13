"""
Presentacion -- Carrusel de Filigramas
=======================================
Pagina de presentacion con 15 filigramas navegables
mediante botones de avance y retroceso.
"""

import streamlit as st
from pathlib import Path

st.set_page_config(
    page_title="Presentacion -- Centro Cultural Marcona",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).parent.parent
IMG_PATH = BASE_DIR / "assets" / "ejemplo.png"

TOTAL_SLIDES = 15

# Titulos descriptivos para cada filigrama
TITULOS = [
    "1. Contexto General del Distrito de Marcona",
    "2. Diagnostico de Infraestructura Cultural Actual",
    "3. Analisis Demografico y Proyeccion Poblacional",
    "4. Brechas Identificadas en Servicios Culturales",
    "5. Justificacion del Proyecto de Misional Institucional",
    "6. Eje Educativo: Formal y No Formal",
    "7. Eje Turismo: Reservas Naturales y Potencial",
    "8. Eje Cultural: Patrimonio Historico de Ica",
    "9. Eje Investigacion: Vinculacion con Sectores Productivos",
    "10. Propuesta de Distribucion de Espacios",
    "11. Dimensionamiento del Auditorio / SUM",
    "12. Analisis de Costo-Beneficio Comparativo",
    "13. Estrategia de Sostenibilidad",
    "14. Alianzas Estrategicas y Gobernanza",
    "15. Hoja de Ruta y Proximos Pasos",
]

# -- Estado de sesion --
if "slide_idx" not in st.session_state:
    st.session_state.slide_idx = 0


def ir_anterior():
    if st.session_state.slide_idx > 0:
        st.session_state.slide_idx -= 1


def ir_siguiente():
    if st.session_state.slide_idx < TOTAL_SLIDES - 1:
        st.session_state.slide_idx += 1


def ir_a(idx):
    st.session_state.slide_idx = idx


# =============================================
# LAYOUT
# =============================================

# -- Header --
st.markdown(
    """
    <div style="background: linear-gradient(135deg, #1565c0 0%, #0d47a1 100%);
                padding: 16px 30px; border-radius: 10px; margin-bottom: 16px;">
        <h2 style="color: white; margin: 0;">
            Presentacion -- Centro Cultural Marcona
        </h2>
        <p style="color: #bbdefb; margin: 4px 0 0 0; font-size: 13px;">
            Filigramas del proyecto | Navegacion mediante botones
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# -- Barra de navegacion --
nav_top = st.columns([1, 1, 6, 1, 1])

with nav_top[0]:
    st.button("Anterior", on_click=ir_anterior, use_container_width=True,
              disabled=(st.session_state.slide_idx == 0))

with nav_top[1]:
    st.button("Inicio", on_click=lambda: ir_a(0), use_container_width=True)

with nav_top[2]:
    st.markdown(
        f"<h3 style='text-align:center; color:#1565c0; margin:0;'>"
        f"{TITULOS[st.session_state.slide_idx]}"
        f"</h3>",
        unsafe_allow_html=True,
    )

with nav_top[3]:
    st.button("Final", on_click=lambda: ir_a(TOTAL_SLIDES - 1), use_container_width=True)

with nav_top[4]:
    st.button("Siguiente", on_click=ir_siguiente, use_container_width=True,
              disabled=(st.session_state.slide_idx == TOTAL_SLIDES - 1))

# -- Barra de progreso --
progress = (st.session_state.slide_idx + 1) / TOTAL_SLIDES
st.progress(progress)
st.caption(f"Filigrama {st.session_state.slide_idx + 1} de {TOTAL_SLIDES}")

# -- Contenido del slide --
st.divider()

col_margin_l, col_slide, col_margin_r = st.columns([0.5, 9, 0.5])

with col_slide:
    st.image(
        str(IMG_PATH),
        caption=TITULOS[st.session_state.slide_idx],
        use_container_width=True,
    )

st.divider()

# -- Selector rapido (thumbnails) --
st.markdown("**Selector rapido de filigramas:**")

# Mostrar en filas de 5
for fila_start in range(0, TOTAL_SLIDES, 5):
    cols = st.columns(5)
    for j, col in enumerate(cols):
        idx = fila_start + j
        if idx < TOTAL_SLIDES:
            with col:
                is_current = idx == st.session_state.slide_idx
                border = "3px solid #1565c0" if is_current else "1px solid #ddd"
                st.markdown(
                    f"<div style='border:{border}; border-radius:6px; padding:4px; "
                    f"text-align:center; cursor:pointer;'>"
                    f"<span style='font-size:11px; color:{'#1565c0' if is_current else '#666'};'>"
                    f"{idx + 1}. {TITULOS[idx].split('. ', 1)[1][:25]}...</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.button(
                    f"Ir a {idx + 1}",
                    key=f"btn_slide_{idx}",
                    on_click=ir_a,
                    args=(idx,),
                    use_container_width=True,
                )

# -- Pie de pagina --
st.divider()
st.markdown(
    """
    <div style="text-align:center; color:#999; font-size:12px;">
        Centro Cultural Marcona -- Presentacion de Filigramas | Febrero 2026
    </div>
    """,
    unsafe_allow_html=True,
)
