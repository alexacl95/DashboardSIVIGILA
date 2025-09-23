import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import json

st.set_page_config(
    page_title='Visualización de Datos: SIVIGILA',
    layout='wide',
    page_icon='📊'
)

# --------- CARGA DE DATOS (cacheada) ----------
@st.cache_data
def load_data():
    df = pd.read_json("Datos_360.json")
    df['FEC_NOT'] = pd.to_datetime(df['FEC_NOT'], errors="coerce")
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

# Evento epidemiológico
Evetos = df['Nombre_evento'].sort_values().unique()
EventoElegido = st.sidebar.selectbox("Evento", Evetos)

# filtro por evento
dfEvento = df[df["Nombre_evento"] == EventoElegido]

# Rango de fechas dinámico
fecha_min = dfEvento["FEC_NOT"].min().date()
fecha_max = dfEvento["FEC_NOT"].max().date()

rango = st.sidebar.date_input("Rango de fechas", [fecha_min, fecha_max])

if len(rango) != 2:
    rango = [fecha_min, fecha_max]

# Departamentos
Departamentos = np.sort(dfEvento["Departamento_ocurrencia"].dropna().unique())
Departamentos = np.insert(Departamentos, 0, "Todos")
opcionesDepartamento = st.sidebar.multiselect("Departamentos", Departamentos, default=["Todos"])

# Municipios dependientes del departamento
if "Todos" in opcionesDepartamento:
    dfDep = dfEvento[["Departamento_ocurrencia", "Municipio_ocurrencia"]]
else:
    dfDep = dfEvento[dfEvento["Departamento_ocurrencia"].isin(opcionesDepartamento)]

Municipios = np.sort(dfDep["Municipio_ocurrencia"].dropna().unique())
Municipios = np.insert(Municipios, 0, "Todos")
opcionesMunicipios = st.sidebar.multiselect("Municipios", Municipios, default=["Todos"])

# -------- FILTRADO DE DATOS ----------
dfFilter = dfEvento[
    (dfEvento['FEC_NOT'] >= pd.to_datetime(rango[0])) &
    (dfEvento['FEC_NOT'] <= pd.to_datetime(rango[1]))
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
st.markdown(EventoElegido)
st.metric("Total casos", f"{total_casos:,}")

# Layout central (3 columnas principales)
col1, col2, col3 = st.columns([2,3,2])

with col1:
    st.subheader("Departamentso con más casos")
    casos_dep = dfFilter.groupby("Departamento_ocurrencia").size().reset_index(name="conteo")
    casos_dep = casos_dep.sort_values("conteo", ascending=False)
    if not casos_dep.empty:
        fig = px.bar(casos_dep[0:5], x='Departamento_ocurrencia', y='conteo', text_auto='.2s',
                     labels = {"Departamento_ocurrencia":"Departamento de ocurrencia","conteo":"Cantidad de casos"})
        st.plotly_chart(fig, use_container_width=True)

# --- Col2: Mapa coroplético
with col2:
    st.subheader("Conteo de casos por departamento")
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
    with st.spinner("Cargando mapa..."):
        fig = px.choropleth_map(
            dfAux,
            geojson=geojson,
            locations="COD_DPTO_O",
            featureidkey="properties.ID_ESPACIA",
            color="conteo",
            color_continuous_scale="Reds",
            hover_name="Departamento_ocurrencia",
            zoom=3.8,
            center={"lat": 4.6, "lon": -74.1},
            opacity=0.6,
            labels = {"conteo":"Casos"}
        )
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0}, height=400)
    st.plotly_chart(fig, use_container_width=True)

# --- Col3: Series de tiempo
with col3:
    st.subheader("Tendencia temporal")
    if not dfFilter.empty:
        dfTime = dfFilter.groupby("FEC_NOT").size().reset_index(name="conteo")
        fig = px.area(dfTime, x = "FEC_NOT", y = "conteo", title = "",
                      range_x=[pd.to_datetime(rango[0]), pd.to_datetime(rango[1])],
                      labels = {"FEC_NOT":"Fecha de notificación","conteo":"Cantidad de casos"})
        st.plotly_chart(fig, use_container_width=True)

# -------- SECCIÓN INFERIOR --------
st.subheader("Distribuciones y Tablas")

c1, c2 = st.columns([2,3])
Cols = {"SEXO":"Sexo",
        "PAC_HOS":"Hospitalizado",
        "AREA":"Área de vivienda",
        "PER_ETN":"Pertenencia étnica"}

with c1:
    categoria = st.radio("Variable de interés", list(Cols.values()), 
        index=0, horizontal=True)
    
    opcion_real = [k for k, v in Cols.items() if v == categoria][0]
    dfAux = (
        dfFilter.groupby(opcion_real)
        .size()
        .reset_index(name="Conteo")
        .sort_values("Conteo", ascending=False)  # ordenar por conteo
    )

    fig = px.bar(dfAux, x=opcion_real, y="Conteo", text_auto='.2s', title=f"Distribución por {categoria}",
                 labels = {"SEXO":"Sexo", "PAC_HOS":"Hospitalizado",
                           "AREA": "Área de vivienda","PER_ETN":"Pertenencia étnica",
                           "Conteno": "Cantidad de casos"})
    st.plotly_chart(fig, use_container_width=True)
    dfAux = dfFilter["EDAD"].value_counts().reset_index()
    dfAux.columns = ["EDAD", "Frecuencia"]

    promedio = dfFilter["EDAD"].mean().astype(int)
    st.metric("Edad promedio", f"{promedio:,}")

    fig = px.bar(
        dfAux.sort_values("EDAD"),
        x="EDAD",
        y="Frecuencia",
        title="Frecuencia de edades",
        labels={"Edad": "Edad (años)", "Frecuencia": "Número de casos"},
        color="Frecuencia"
    )
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("### Tabla resumen")
    # multiselect muestra las etiquetas
    Columnas = st.multiselect(
        "Variables de columna",
        list(Cols.values()),
        default=[list(Cols.values())[0]]
    )
    # Mapear de las etiquetas seleccionadas a las claves reales
    opciones_reales = [k for k, v in Cols.items() if v in Columnas]
    
    Pivot = pd.pivot_table(
        dfFilter,
        values="index",
        index=["Departamento_ocurrencia"],
        columns=opciones_reales,
        aggfunc="count"
    ).fillna(0)
    styled_pivot = Pivot.style.background_gradient(cmap="Blues").format(precision=0)
    st.dataframe(styled_pivot, use_container_width=True)
