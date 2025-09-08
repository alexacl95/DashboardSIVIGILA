import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

st.set_page_config(
    page_title='Visualización de Datos: SIVIGILA',
    layout='wide',
    page_icon=':ambulance:'
)

st.title("Visualización de Datos: SIVIGILA")
st.markdown(" **Datos tomados y procesados de:** https://portalsivigila.ins.gov.co/Paginas/Buscador.aspx")
st.markdown("**email:** alexandra.catano@iudigital.edu.co")

# Cachear la carga de datos: solo se hace una vez por sesión
@st.cache_data
def load_data():
    df = pd.read_json("Datos_360.json")
    df['FEC_CON'] = pd.to_datetime(df['FEC_CON'], errors="coerce")
    return df

with st.spinner("Cargando datos..."):
    df = load_data()


# -------- FILTROS ----------
t1, t2, t3 = st.columns(3)

# Rango de fechas dinámico
fecha_min = df["FEC_CON"].min().date()
fecha_max = df["FEC_CON"].max().date()
rango = t1.date_input("Selecciona un rango de fechas", [fecha_min, fecha_max])

# Departamentos
Departamentos = np.sort(df["Departamento_ocurrencia"].dropna().unique())
Departamentos = np.insert(Departamentos, 0, "Todos")
opcionesDepartamento = t2.multiselect("Selecciona al menos un departamento", Departamentos, default=["Todos"])

# Municipios dependientes del departamento
if "Todos" in opcionesDepartamento:
    dfDep = df[["Departamento_ocurrencia", "Municipio_ocurrencia"]]
else:
    dfDep = df[df["Departamento_ocurrencia"].isin(opcionesDepartamento)]

Municipios = np.sort(dfDep["Municipio_ocurrencia"].dropna().unique())
Municipios = np.insert(Municipios, 0, "Todos")
opcionesMunicipios = t3.multiselect("Selecciona al menos un municipio", Municipios, default=["Todos"])

# ---------- FILTRADO DE DATOS ----------
dfFilter = df[
    (df['FEC_CON'] >= pd.to_datetime(rango[0])) &
    (df['FEC_CON'] <= pd.to_datetime(rango[1]))
]

if "Todos" not in opcionesDepartamento:
    dfFilter = dfFilter[dfFilter["Departamento_ocurrencia"].isin(opcionesDepartamento)]

if "Todos" not in opcionesMunicipios:
    dfFilter = dfFilter[dfFilter["Municipio_ocurrencia"].isin(opcionesMunicipios)]

# ---------- VISUALIZACIÓN ----------

col1, col2 = st.columns(2)

# Cantidad por departamento
with col1:
    dfAux = dfFilter[["index", "Departamento_ocurrencia"]].groupby(["Departamento_ocurrencia"]).count().sort_values("index")
    fig = px.bar(dfAux, text_auto='.2s', title="Casos por departamento")
    st.plotly_chart(fig, use_container_width=True)

# Series de tiempo
with col2:
    Variable = "INI_SIN"
    dfAux = dfFilter[["index", Variable]].groupby([Variable]).count()
    fig = px.area(dfAux,
                  range_x=[pd.to_datetime(rango[0]), pd.to_datetime(rango[1])],
                  title="Series de tiempo")
    fig.update_xaxes(
        ticks="outside",
        ticklabelmode="period",
        tickcolor="black",
        ticklen=10,
        minor=dict(
            ticklen=4,
            tick0="2006-01-01",
            griddash='dot',
            gridcolor='white'
        )
    )
    st.plotly_chart(fig, use_container_width=True)

# Selección de variable
st.markdown("### Seleccione una variable de interés")
Variable = ["SEXO", "PAC_HOS", "AREA"]
categoria = st.radio("Variable", Variable, horizontal=True)

dfAux = dfFilter.groupby(categoria).size().reset_index(name="Conteo")
fig = px.bar(dfAux, x=categoria, y="Conteo", text_auto='.2s', title=f"Distribución por {categoria}")
st.plotly_chart(fig, use_container_width=True)

col1, col2 = st.columns(2)
# Tabla pivote
with col1:
    st.markdown("### Tabla resumen")
    Variable = ["Departamento_ocurrencia"]
    Cols = ["SEXO", "PAC_HOS", "AREA"]
    Columnas = st.multiselect("Variables", Cols, default = 'SEXO')
Pivot = pd.pivot_table(
    dfFilter,
    values="index",
    index=Variable,
    columns=Columnas,
    aggfunc="count"
).fillna(0)

# Mejorar visualización con estilos
styled_pivot = Pivot.style.background_gradient(cmap="Blues").format(precision=0)
st.dataframe(styled_pivot, use_container_width=True)
