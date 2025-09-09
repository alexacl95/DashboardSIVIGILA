import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import json

st.set_page_config(
    page_title='Visualización de Datos: SIVIGILA',
    layout='wide',
    page_icon=':ambulance:'
)

# --------- CARGA DE DATOS (cacheada) ----------
@st.cache_data
def load_data():
    df = pd.read_json("Datos_360.json")
    df['FEC_CON'] = pd.to_datetime(df['FEC_CON'], errors="coerce")
    return df

@st.cache_data
def load_geojson():
    with open("Departamentos.geojson", "r", encoding="utf-8") as f:
        return json.load(f)

with st.spinner("Cargando datos..."):
    df = load_data()
    geojson = load_geojson()

# -------- SIDEBAR: FILTROS --------
st.sidebar.title("Filtros")

# Rango de fechas dinámico
fecha_min = df["FEC_CON"].min().date()
fecha_max = df["FEC_CON"].max().date()
rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

# Departamentos
Departamentos = np.sort(df["Departamento_ocurrencia"].dropna().unique())
Departamentos = np.insert(Departamentos, 0, "Todos")
opcionesDepartamento = st.sidebar.multiselect("Departamentos", Departamentos, default=["Todos"])

# Municipios dependientes del departamento
if "Todos" in opcionesDepartamento:
    dfDep = df[["Departamento_ocurrencia", "Municipio_ocurrencia"]]
else:
    dfDep = df[df["Departamento_ocurrencia"].isin(opcionesDepartamento)]

Municipios = np.sort(dfDep["Municipio_ocurrencia"].dropna().unique())
Municipios = np.insert(Municipios, 0, "Todos")
opcionesMunicipios = st.sidebar.multiselect("Municipios", Municipios, default=["Todos"])

# -------- FILTRADO DE DATOS ----------
dfFilter = df[
    (df['FEC_CON'] >= pd.to_datetime(rango[0])) &
    (df['FEC_CON'] <= pd.to_datetime(rango[1]))
]

if "Todos" not in opcionesDepartamento:
    dfFilter = dfFilter[dfFilter["Departamento_ocurrencia"].isin(opcionesDepartamento)]

if "Todos" not in opcionesMunicipios:
    dfFilter = dfFilter[dfFilter["Municipio_ocurrencia"].isin(opcionesMunicipios)]

# -------- VISUALIZACIONES PRINCIPALES --------
st.title("Visualización de Datos: SIVIGILA")
st.markdown("**Fuente de datos:** [SIVIGILA](https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx)  \n"
            "**Contacto:** alexandra.catano@iudigital.edu.co")
# --- Col1: KPIs rápidos
total_casos = len(dfFilter)
st.metric("Total casos", f"{total_casos:,}")

# Layout central (3 columnas principales)
col1, col2, col3 = st.columns([2,3,2])

with col1:
    st.subheader("Top departamentos")
    casos_dep = dfFilter.groupby("Departamento_ocurrencia").size().reset_index(name="conteo")
    casos_dep = casos_dep.sort_values("conteo", ascending=False)
    if not casos_dep.empty:
        fig = px.bar(casos_dep[0:5], x='Departamento_ocurrencia', y='conteo')
        st.plotly_chart(fig, use_container_width=True)

# --- Col2: Mapa coroplético
with col2:
    st.subheader("Mapa de departamento")
    dfAux = (
        dfFilter.groupby("Departamento_ocurrencia")
        .size()
        .reset_index(name="conteo")
        .merge(
            df[["Departamento_ocurrencia", "COD_DPTO_O"]].drop_duplicates(),
            on="Departamento_ocurrencia",
            how="left"
        )
    )

    fig = px.choropleth_mapbox(
        dfAux,
        geojson=geojson,
        locations="COD_DPTO_O",
        featureidkey="properties.ID_ESPACIA",
        color="conteo",
        color_continuous_scale="Reds",
        mapbox_style="carto-positron",
        hover_name="Departamento_ocurrencia",
        zoom=3.8,
        center={"lat": 4.6, "lon": -74.1},
        opacity=0.6
    )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
    st.plotly_chart(fig, use_container_width=True)

# --- Col3: Series de tiempo
with col3:
    st.subheader("Tendencia temporal")
    if not dfFilter.empty:
        dfTime = dfFilter.groupby("INI_SIN").size().reset_index(name="conteo")
        fig = px.area(dfTime, x = "INI_SIN", y = "conteo", title = "",
                      range_x=[pd.to_datetime(rango[0]), pd.to_datetime(rango[1])])
        st.plotly_chart(fig, use_container_width=True)

# -------- SECCIÓN INFERIOR --------
st.subheader("Distribuciones y Tablas")

c1, c2 = st.columns([2,3])

with c1:
    categoria = st.radio("Variable de interés", ["SEXO", "PAC_HOS", "AREA"], horizontal=True)
    dfAux = dfFilter.groupby(categoria).size().reset_index(name="Conteo")
    fig = px.bar(dfAux, x=categoria, y="Conteo", text_auto='.2s', title=f"Distribución por {categoria}")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("### Tabla resumen")
    Cols = ["SEXO", "PAC_HOS", "AREA"]
    Columnas = st.multiselect("Variables de columna", Cols, default=["SEXO"])
    Pivot = pd.pivot_table(
        dfFilter,
        values="index",
        index=["Departamento_ocurrencia"],
        columns=Columnas,
        aggfunc="count"
    ).fillna(0)
    styled_pivot = Pivot.style.background_gradient(cmap="Blues").format(precision=0)
    st.dataframe(styled_pivot, use_container_width=True)
