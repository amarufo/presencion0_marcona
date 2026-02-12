# Centro Cultural Marcona -- Dashboard de Analisis

Dashboard interactivo desarrollado en Streamlit para la justificacion tecnica del proyecto Centro Cultural Marcona.

## Estructura

```
dashboard_ccm/
├── app.py                       # Pagina principal del dashboard
├── pages/
│   └── 02_Presentacion.py       # Carrusel de filigramas
├── data/
│   ├── inversiones_mapav2.csv   # Datos de inversiones con coordenadas
│   └── resultado_motor.json     # Proyecciones poblacionales
├── assets/
│   ├── ejemplo.png              # Imagen placeholder para filigramas
│   └── tactical.jpg             # Icono de la aplicacion
├── .streamlit/
│   └── config.toml              # Configuracion de tema y servidor
├── .gitignore
├── requirements.txt             # Dependencias
└── README.md
```

## Ejecucion local

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Despliegue en Streamlit Cloud

1. Subir esta carpeta a un repositorio de GitHub.
2. En [share.streamlit.io](https://share.streamlit.io), conectar el repositorio.
3. Configurar el archivo principal como `app.py`.

## Contenido del Dashboard

### Pagina Principal
- **Mapa interactivo** con ubicacion de proyectos de bibliotecas en Peru y el proyecto de Marcona.
- **Panel de detalle** del proyecto seleccionado en el mapa.
- **Panel de control** con sliders para dimensionamiento del auditorio.
- **Analisis de contraste** con graficos de cajas, dispersion, ranking y proyeccion poblacional.
- **Paneles de recomendaciones** con conclusiones del analisis.

### Presentacion
- Carrusel de 15 filigramas con navegacion por botones.
- Selector rapido de filigramas mediante thumbnails.

## Fuentes de datos

- MEF - Invierte.pe (inversiones en bibliotecas publicas)
- INEI (proyecciones poblacionales)
- Motor de Proyeccion Poblacional
