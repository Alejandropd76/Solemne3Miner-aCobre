import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Rutas relativas con los nombres originales exactos de los CSV
RUTA_COMPANIAS = "Producción de cobre por compañía.xlsx - Sheet0.csv"
RUTA_PRODUCTOS = "produccion-por-producto.csv"

# Configuración general de la página
st.set_page_config(
    page_title="Dashboard Minería del Cobre en Chile",
    layout="wide"
)


# ==============================================================================
# 1. FUNCIONES DE CARGA Y LIMPIEZA DE DATOS
# ==============================================================================

@st.cache_data
def cargar_csv(ruta_relativa: str) -> pd.DataFrame:
    """Lee un archivo CSV local desde una ruta relativa con codificación UTF-8."""
    return pd.read_csv(ruta_relativa, sep=",", encoding="utf-8-sig")


def limpiar_valor_numerico(valor) -> float:
    """
    Convierte strings numéricos con formatos mixtos a float.
    Maneja guiones ('-'), puntos de miles y comas decimales (ej. '1.242,70' -> 1242.7).
    """
    if pd.isna(valor):
        return np.nan
    texto = str(valor).strip()
    if texto in ["-", "", "nan", "NaN", "None"]:
        return np.nan
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except ValueError:
        return np.nan


def preparar_datos_companias(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Transforma el CSV de compañías de formato ancho (1998-2018) a formato largo,
    excluye la fila TOTAL, limpia notas al pie y convierte tipos numéricos.
    """
    df = df_raw.copy()
    col_nombre = df.columns[0]

    # Eliminar fila de totales para evitar doble conteo
    df = df[~df[col_nombre].astype(str).str.upper().str.startswith("TOTAL")].copy()

    # Limpiar notas al pie tipo (2), (3), (4), (5) al final del nombre
    df[col_nombre] = df[col_nombre].apply(
        lambda x: re.sub(r"\s*\(\d+\)$", "", str(x).strip())
    )

    # Pasar de formato ancho (columnas por año) a formato largo (tidy data)
    df_largo = df.melt(id_vars=[col_nombre], var_name="anio", value_name="produccion_raw")
    df_largo.columns = ["compania", "anio", "produccion_raw"]
    df_largo["anio"] = pd.to_numeric(df_largo["anio"], errors="coerce").astype(int)
    df_largo["produccion_ktmf"] = df_largo["produccion_raw"].apply(limpiar_valor_numerico)

    total_celdas = len(df_largo)
    nulos_guiones = int(df_largo["produccion_ktmf"].isna().sum())

    # Descartar años previos al inicio de operación de cada faena
    df_limpio = df_largo.dropna(subset=["produccion_ktmf"]).drop(columns=["produccion_raw"]).copy()
    duplicados = int(df_limpio.duplicated(subset=["compania", "anio"]).sum())
    df_limpio = df_limpio.drop_duplicates(subset=["compania", "anio"])

    # Columna derivada en Toneladas Métricas de Fino (TMF)
    df_limpio["produccion_tmf"] = df_limpio["produccion_ktmf"] * 1000.0

    resumen = {
        "celdas_totales": total_celdas,
        "sin_operacion": nulos_guiones,
        "duplicados": duplicados,
        "registros_validos": len(df_limpio),
        "n_companias": df_limpio["compania"].nunique()
    }
    return df_limpio, resumen


def preparar_datos_productos(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Transforma el CSV de productos (1998-2017) a formato largo y clasifica
    etapas principales vs. subproductos de cobre refinado.
    """
    df = df_raw.copy()
    col_prod = df.columns[0]

    # Simplificar nombres bilingües dejando la etiqueta en español
    df[col_prod] = df[col_prod].apply(lambda x: str(x).split(" - ")[0].strip())

    df_largo = df.melt(id_vars=[col_prod], var_name="anio", value_name="produccion_ktmf")
    df_largo.columns = ["producto", "anio", "produccion_ktmf"]
    df_largo["anio"] = df_largo["anio"].astype(int)
    df_largo["produccion_ktmf"] = pd.to_numeric(df_largo["produccion_ktmf"], errors="coerce")
    df_largo = df_largo.dropna(subset=["produccion_ktmf"]).copy()
    df_largo["produccion_tmf"] = df_largo["produccion_ktmf"] * 1000.0

    subproductos_refinado = ["Cátodos SX-EW", "Cátodos E.R.", "Refinado a fuego"]
    df_largo["categoria"] = df_largo["producto"].apply(
        lambda p: "Subproducto Refinado" if p in subproductos_refinado else "Etapa Principal"
    )

    resumen = {
        "registros_validos": len(df_largo),
        "nulos": int(df_largo["produccion_ktmf"].isna().sum()),
        "productos": df_largo["producto"].nunique()
    }
    return df_largo, resumen


def filtrar_companias(df: pd.DataFrame, companias: list, rango_anios: tuple) -> pd.DataFrame:
    """Filtra el DataFrame de compañías según selección del usuario."""
    return df[
        (df["compania"].isin(companias)) &
        (df["anio"] >= rango_anios[0]) &
        (df["anio"] <= rango_anios[1])
    ].copy()


# ==============================================================================
# 2. FUNCIONES DE VISUALIZACIÓN (4 TIPOS DE GRÁFICOS DISTINTOS)
# ==============================================================================

def grafico_lineas_evolucion(df: pd.DataFrame, col_val: str, unidad: str, mostrar_prom: bool):
    """Gráfico 1 (Líneas): Evolución anual de la producción total filtrada."""
    df_anual = df.groupby("anio", as_index=False)[col_val].sum()

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.plot(
        df_anual["anio"], df_anual[col_val],
        marker="o", color="#197A8D", linewidth=2, label=f"Producción anual ({unidad})"
    )

    if mostrar_prom and len(df_anual) > 0:
        promedio = df_anual[col_val].mean()
        ax.axhline(
            promedio, color="#D95F02", linestyle="--", linewidth=1.5,
            label=f"Promedio período ({promedio:,.1f} {unidad})"
        )

    ax.set_title("Evolución Anual de Producción de Cobre (Compañías Seleccionadas)")
    ax.set_xlabel("Año")
    ax.set_ylabel(f"Producción ({unidad})")
    ax.set_xticks(df_anual["anio"][::2])
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend()
    fig.tight_layout()
    return fig


def grafico_barras_ranking(df: pd.DataFrame, col_val: str, unidad: str, top_n: int):
    """Gráfico 2 (Barras horizontales): Top N compañías por producción acumulada."""
    df_top = (
        df.groupby("compania", as_index=False)[col_val]
        .sum()
        .sort_values(by=col_val, ascending=False)
        .head(top_n)
        .sort_values(by=col_val, ascending=True)
    )

    fig, ax = plt.subplots(figsize=(8, 4.2))
    ax.barh(df_top["compania"], df_top[col_val], color="#2B8CBE")
    ax.set_title(f"Top {len(df_top)} Compañías por Producción Acumulada")
    ax.set_xlabel(f"Producción Acumulada ({unidad})")
    ax.set_ylabel("Compañía / Faena")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def grafico_pastel_refinado(df_prod: pd.DataFrame, col_val: str, rango_anios: tuple):
    """Gráfico 3 (Pastel): Participación porcentual de subproductos de cobre refinado."""
    h_min, h_max = rango_anios[0], min(rango_anios[1], 2017)
    df_sub = df_prod[
        (df_prod["categoria"] == "Subproducto Refinado") &
        (df_prod["anio"] >= h_min) &
        (df_prod["anio"] <= h_max)
    ]
    df_pie = df_sub.groupby("producto", as_index=False)[col_val].sum()
    df_pie = df_pie[df_pie[col_val] > 0]

    fig, ax = plt.subplots(figsize=(7, 4.2))
    colores = ["#197A8D", "#66C2A5", "#FC8D62"]
    ax.pie(
        df_pie[col_val],
        labels=df_pie["producto"],
        autopct="%1.1f%%",
        startangle=140,
        colors=colores[:len(df_pie)],
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    ax.set_title(f"Distribución de Cobre Refinado por Subproducto ({h_min}–{h_max})")
    fig.tight_layout()
    return fig


def grafico_dispersion_etapas(df_prod: pd.DataFrame, col_val: str, unidad: str, rango_anios: tuple):
    """Gráfico 4 (Dispersión): Relación entre Producción de Mina y Producción de Refinado."""
    h_min, h_max = rango_anios[0], min(rango_anios[1], 2017)
    df_etapas = df_prod[
        (df_prod["producto"].isin(["PRODUCCIÓN DE MINA", "PRODUCCIÓN DE REFINADO"])) &
        (df_prod["anio"] >= h_min) &
        (df_prod["anio"] <= h_max)
    ]
    df_piv = df_etapas.pivot(index="anio", columns="producto", values=col_val).dropna()

    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.scatter(
        df_piv["PRODUCCIÓN DE MINA"],
        df_piv["PRODUCCIÓN DE REFINADO"],
        color="#7570B3", edgecolors="black", s=75, alpha=0.85
    )
    for anio, fila in df_piv.iterrows():
        ax.annotate(str(anio), (fila["PRODUCCIÓN DE MINA"], fila["PRODUCCIÓN DE REFINADO"]), fontsize=8, alpha=0.75)

    ax.set_title(f"Relación Producción de Mina vs. Refinado ({h_min}–{h_max})")
    ax.set_xlabel(f"Producción de Mina ({unidad})")
    ax.set_ylabel(f"Producción de Refinado ({unidad})")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


# ==============================================================================
# 3. INTERFAZ PRINCIPAL (MAIN)
# ==============================================================================

def main():
    st.title("Monitor de Producción de Cobre en Chile: Compañías y Productos")
    st.markdown(
        "Dashboard interactivo para explorar la producción minera chilena por **compañía/faena (1998–2018)** "
        "y por **etapa o tipo de producto (1998–2017)** a partir de estadísticas oficiales de COCHILCO."
    )

    # Carga de ambos CSV locales desde rutas relativas
    try:
        raw_comp = cargar_csv(RUTA_COMPANIAS)
        raw_prod = cargar_csv(RUTA_PRODUCTOS)
    except FileNotFoundError as err:
        st.error(f"Error al cargar archivos CSV locales: {err}. Verifica que ambos estén en la carpeta raíz.")
        st.stop()

    df_comp, info_comp = preparar_datos_companias(raw_comp)
    df_prod, info_prod = preparar_datos_productos(raw_prod)

    # --------------------------------------------------------------------------
    # BARRA LATERAL: CONTROLES E INTERACTIVIDAD
    # --------------------------------------------------------------------------
    st.sidebar.header("Filtros y Controles")
    st.sidebar.info("Usa estos controles para filtrar las compañías, el rango de años y las unidades.")

    todas_companias = sorted(df_comp["compania"].unique().tolist())
    companias_sel = st.sidebar.multiselect(
        "Compañías / Faenas mineras",
        options=todas_companias,
        default=todas_companias
    )

    anio_min, anio_max = int(df_comp["anio"].min()), int(df_comp["anio"].max())
    rango_anios = st.sidebar.slider(
        "Rango de años",
        min_value=anio_min,
        max_value=anio_max,
        value=(anio_min, anio_max)
    )

    top_n = st.sidebar.number_input(
        "Cantidad de compañías en el ranking (Top N)",
        min_value=3,
        max_value=len(todas_companias),
        value=10,
        step=1
    )

    unidad_radio = st.sidebar.radio(
        "Unidad de medida",
        options=["Miles de TMF (kTMF)", "Toneladas Métricas de Fino (TMF)"]
    )
    col_val = "produccion_ktmf" if "kTMF" in unidad_radio else "produccion_tmf"
    unidad_txt = "kTMF" if "kTMF" in unidad_radio else "TMF"

    mostrar_promedio = st.sidebar.checkbox("Mostrar línea de promedio anual", value=True)

    # Filtrado efectivo
    df_comp_filt = filtrar_companias(df_comp, companias_sel, rango_anios)

    if df_comp_filt.empty:
        st.warning("No hay datos disponibles para la selección actual. Elige al menos una compañía.")
        st.stop()

    # --------------------------------------------------------------------------
    # INDICADORES CALCULADOS (KPIs)
    # --------------------------------------------------------------------------
    st.subheader("Indicadores Clave del Período Seleccionado")
    kpi1, kpi2, kpi3 = st.columns(3)

    prod_acumulada = df_comp_filt[col_val].sum()
    prod_anual_media = df_comp_filt.groupby("anio")[col_val].sum().mean()
    lider_fila = df_comp_filt.groupby("compania")[col_val].sum().idxmax()

    kpi1.metric(f"Producción Acumulada ({unidad_txt})", f"{prod_acumulada:,.1f}")
    kpi2.metric(f"Promedio Anual Selección ({unidad_txt})", f"{prod_anual_media:,.1f}")
    kpi3.metric("Compañía Líder del Período", lider_fila)

    st.divider()

    # --------------------------------------------------------------------------
    # PESTAÑAS DE VISUALIZACIÓN Y DATOS
    # --------------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Evolución y Ranking por Compañía",
        "2. Análisis por Tipo de Producto",
        "3. Tabla y Descarga CSV",
        "4. Limpieza y Fuentes"
    ])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.pyplot(grafico_lineas_evolucion(df_comp_filt, col_val, unidad_txt, mostrar_promedio))
        with col_b:
            st.pyplot(grafico_barras_ranking(df_comp_filt, col_val, unidad_txt, top_n))

    with tab2:
        st.caption("Nota: El desglose por producto cubre el período 1998–2017 según disponibilidad de la serie.")
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.pyplot(grafico_pastel_refinado(df_prod, col_val, rango_anios))
        with col_p2:
            st.pyplot(grafico_dispersion_etapas(df_prod, col_val, unidad_txt, rango_anios))

    with tab3:
        vista_tabla = st.selectbox(
            "Selecciona conjunto de datos a inspeccionar",
            options=["Producción por Compañía (Filtrada)", "Producción por Producto (1998–2017)"]
        )
        df_tabla = df_comp_filt if "Compañía" in vista_tabla else df_prod
        st.dataframe(df_tabla, use_container_width=True, hide_index=True)

        csv_descarga = df_tabla.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="Descargar tabla actual en CSV",
            data=csv_descarga,
            file_name="mineria_cobre_filtrado.csv",
            mime="text/csv"
        )

    with tab4:
        st.subheader("Auditoría y Preparación de Datos (Pandas)")
        st.write(
            f"- **Dataset Compañías (`1998–2018`):** {info_comp['registros_validos']} registros operativos válidos "
            f"de {info_comp['n_companias']} compañías/faenas ({info_comp['sin_operacion']} celdas `'-'` descartadas por corresponder a años previos al inicio de operación; {info_comp['duplicados']} duplicados)."
        )
        st.write(
            f"- **Dataset Productos (`1998–2017`):** {info_prod['registros_validos']} registros válidos en "
            f"{info_prod['productos']} categorías ({info_prod['nulos']} valores nulos)."
        )
        st.warning(
            "Nota metodológica sobre calidad de datos: En 'Producción de cobre por compañía', la columna 2018 "
            "utiliza separador decimal con coma y punto de miles ('1.242,70'), estandarizado mediante limpieza de cadenas. "
            "En 'produccion-por-producto.csv', los valores del bloque 2008–2017 replican exactamente el bloque 1998–2007 en la fuente original."
        )

        st.subheader("Fuente Oficial")
        st.write("Comisión Chilena del Cobre (COCHILCO) - Estadísticas de Producción Minera.")
        st.link_button("Visitar Portal Oficial de Estadísticas COCHILCO", "https://www.cochilco.cl")


if __name__ == "__main__":
    main()
