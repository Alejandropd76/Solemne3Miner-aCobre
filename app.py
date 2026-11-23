import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Rutas relativas de los tres CSV en la carpeta raíz del repositorio
RUTA_COMPANIAS = "Producción de cobre por compañía.xlsx - Sheet0.csv"
RUTA_PRODUCTOS = "produccion-por-producto.csv"
RUTA_PRECIOS = "copper-price.csv"

# Factor de conversión oficial: 1 tonelada métrica = 2.204,62262 libras
LIBRAS_POR_TONELADA = 2204.62262

st.set_page_config(
    page_title="Dashboard Minería y Precio del Cobre en Chile",
    layout="wide"
)


# ==============================================================================
# 1. FUNCIONES DE CARGA Y PREPARACIÓN DE DATOS
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


def preparar_datos_precios(df_raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """
    Limpia el CSV mensual de precios (US$/TM), convierte unidades a US$/lb y cUS$/lb,
    y agrupa por año calculando el promedio y la volatilidad intra-anual.
    """
    df = df_raw.copy()
    registros_iniciales = len(df)
    df = df.drop_duplicates(subset=["date"])

    df["fecha"] = pd.to_datetime(df["date"], errors="coerce")
    df["precio_usd_ton"] = pd.to_numeric(df["copper_price_usd"], errors="coerce")
    df = df.dropna(subset=["fecha", "precio_usd_ton"]).copy()

    df["anio"] = df["fecha"].dt.year.astype(int)
    df["mes"] = df["fecha"].dt.month.astype(int)
    df["precio_usd_lb"] = df["precio_usd_ton"] / LIBRAS_POR_TONELADA
    df["precio_cusd_lb"] = df["precio_usd_lb"] * 100.0

    # Agrupación anual para cruzar con los registros anuales de producción
    df_anual = df.groupby("anio", as_index=False).agg(
        precio_usd_ton=("precio_usd_ton", "mean"),
        precio_usd_lb=("precio_usd_lb", "mean"),
        precio_cusd_lb=("precio_cusd_lb", "mean"),
        volatilidad_usd_ton=("precio_usd_ton", "std"),
        meses_registrados=("mes", "count")
    )

    resumen = {
        "mensuales_totales": registros_iniciales,
        "nulos": int(df_raw["copper_price_usd"].isna().sum()),
        "duplicados": registros_iniciales - len(df),
        "rango_fechas": f"{df['fecha'].min().strftime('%Y-%m')} a {df['fecha'].max().strftime('%Y-%m')}",
        "anios_cubiertos": len(df_anual)
    }
    return df, df_anual, resumen


def preparar_datos_companias(df_raw: pd.DataFrame, df_precios_anual: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """
    Transforma el CSV de compañías (1998-2018) de formato ancho a largo,
    limpia valores, cruza con precios históricos (pd.merge) y estima la valorización.
    """
    df = df_raw.copy()
    col_nombre = df.columns[0]

    # Excluir fila TOTAL para evitar doble conteo
    df = df[~df[col_nombre].astype(str).str.upper().str.startswith("TOTAL")].copy()

    # Limpiar notas al pie tipo (2), (3), (4), (5)
    df[col_nombre] = df[col_nombre].apply(
        lambda x: re.sub(r"\s*\(\d+\)$", "", str(x).strip())
    )

    df_largo = df.melt(id_vars=[col_nombre], var_name="anio", value_name="produccion_raw")
    df_largo.columns = ["compania", "anio", "produccion_raw"]
    df_largo["anio"] = pd.to_numeric(df_largo["anio"], errors="coerce").astype(int)
    df_largo["produccion_ktmf"] = df_largo["produccion_raw"].apply(limpiar_valor_numerico)

    nulos_guiones = int(df_largo["produccion_ktmf"].isna().sum())

    df_limpio = df_largo.dropna(subset=["produccion_ktmf"]).drop(columns=["produccion_raw"]).copy()
    duplicados = int(df_limpio.duplicated(subset=["compania", "anio"]).sum())
    df_limpio = df_limpio.drop_duplicates(subset=["compania", "anio"])

    # Conversión de unidades y cruce con tabla de precios anuales
    df_limpio["produccion_tmf"] = df_limpio["produccion_ktmf"] * 1000.0
    df_limpio = pd.merge(df_limpio, df_precios_anual, on="anio", how="left")

    # Valorización bruta estimada en millones de USD (TMF * US$/TM / 1.000.000)
    df_limpio["valorizacion_musd"] = (
        df_limpio["produccion_tmf"] * df_limpio["precio_usd_ton"]
    ) / 1_000_000.0

    resumen = {
        "sin_operacion": nulos_guiones,
        "duplicados": duplicados,
        "registros_validos": len(df_limpio),
        "n_companias": df_limpio["compania"].nunique()
    }
    return df_limpio, resumen


def preparar_datos_productos(df_raw: pd.DataFrame, df_precios_anual: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Transforma el CSV de productos (1998-2017) a formato largo y lo cruza con precios."""
    df = df_raw.copy()
    col_prod = df.columns[0]

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
    df_largo = pd.merge(df_largo, df_precios_anual, on="anio", how="left")

    resumen = {
        "registros_validos": len(df_largo),
        "nulos": int(df_largo["produccion_ktmf"].isna().sum()),
        "productos": df_largo["producto"].nunique()
    }
    return df_largo, resumen


def filtrar_companias(df: pd.DataFrame, companias: list, rango_anios: tuple) -> pd.DataFrame:
    """Filtra el DataFrame de compañías según los parámetros de la barra lateral."""
    return df[
        (df["compania"].isin(companias)) &
        (df["anio"] >= rango_anios[0]) &
        (df["anio"] <= rango_anios[1])
    ].copy()


# ==============================================================================
# 2. FUNCIONES DE VISUALIZACIÓN (4 TIPOS DE GRÁFICOS DISTINTOS)
# ==============================================================================

def grafico_lineas_evolucion(df: pd.DataFrame, col_val: str, unidad: str, mostrar_precio: bool):
    """Gráfico 1 (Líneas con doble eje): Producción anual vs. Precio del Cobre (cUS$/lb)."""
    df_anual = df.groupby("anio", as_index=False).agg({
        col_val: "sum",
        "precio_cusd_lb": "mean"
    })

    fig, ax1 = plt.subplots(figsize=(8, 4.3))
    color_prod = "#197A8D"
    l1 = ax1.plot(
        df_anual["anio"], df_anual[col_val],
        marker="o", color=color_prod, linewidth=2, label=f"Producción ({unidad})"
    )
    ax1.set_xlabel("Año")
    ax1.set_ylabel(f"Producción Total ({unidad})", color=color_prod)
    ax1.tick_params(axis="y", labelcolor=color_prod)
    ax1.set_xticks(df_anual["anio"][::2])
    ax1.grid(True, linestyle="--", alpha=0.35)
    ax1.spines["top"].set_visible(False)

    lineas = l1
    if mostrar_precio:
        ax2 = ax1.twinx()
        color_precio = "#D95F02"
        l2 = ax2.plot(
            df_anual["anio"], df_anual["precio_cusd_lb"],
            marker="s", linestyle="--", color=color_precio, linewidth=1.8,
            label="Precio Cobre (cUS$/lb)"
        )
        ax2.set_ylabel("Precio Promedio (cUS$/lb)", color=color_precio)
        ax2.tick_params(axis="y", labelcolor=color_precio)
        ax2.spines["top"].set_visible(False)
        lineas = l1 + l2

    etiquetas = [l.get_label() for l in lineas]
    ax1.legend(lineas, etiquetas, loc="upper left")
    plt.title("Evolución Anual de Producción vs. Precio del Cobre")
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

    fig, ax = plt.subplots(figsize=(8, 4.3))
    ax.barh(df_top["compania"], df_top[col_val], color="#2B8CBE")
    ax.set_title(f"Top {len(df_top)} Compañías por Producción Acumulada")
    ax.set_xlabel(f"Producción Acumulada ({unidad})")
    ax.set_ylabel("Compañía / Faena")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def grafico_dispersion_precio_produccion(df: pd.DataFrame, col_val: str, unidad: str):
    """Gráfico 3 (Dispersión): Relación entre Precio del Cobre (cUS$/lb) y Producción Anual."""
    df_anual = df.groupby("anio", as_index=False).agg({
        col_val: "sum",
        "precio_cusd_lb": "mean"
    })

    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    ax.scatter(
        df_anual["precio_cusd_lb"],
        df_anual[col_val],
        color="#7570B3", edgecolors="black", s=75, alpha=0.85
    )
    for _, fila in df_anual.iterrows():
        ax.annotate(
            str(int(fila["anio"])),
            (fila["precio_cusd_lb"], fila[col_val]),
            fontsize=8, alpha=0.8, xytext=(4, 3), textcoords="offset points"
        )

    ax.set_title("Correlación: Precio del Cobre vs. Producción Anual")
    ax.set_xlabel("Precio Promedio Anual (cUS$/lb)")
    ax.set_ylabel(f"Producción Total Anual ({unidad})")
    ax.grid(True, linestyle="--", alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def grafico_pastel_refinado(df_prod: pd.DataFrame, col_val: str, rango_anios: tuple):
    """Gráfico 4 (Pastel): Participación porcentual de subproductos de cobre refinado."""
    h_min, h_max = rango_anios[0], min(rango_anios[1], 2017)
    df_sub = df_prod[
        (df_prod["categoria"] == "Subproducto Refinado") &
        (df_prod["anio"] >= h_min) &
        (df_prod["anio"] <= h_max)
    ]
    df_pie = df_sub.groupby("producto", as_index=False)[col_val].sum()
    df_pie = df_pie[df_pie[col_val] > 0]

    fig, ax = plt.subplots(figsize=(7.5, 4.3))
    colores = ["#197A8D", "#66C2A5", "#FC8D62"]
    ax.pie(
        df_pie[col_val],
        labels=df_pie["producto"],
        autopct="%1.1f%%",
        startangle=140,
        colors=colores[:len(df_pie)],
        wedgeprops={"edgecolor": "white", "linewidth": 1.5}
    )
    ax.set_title(f"Composición del Cobre Refinado por Subproducto ({h_min}–{h_max})")
    fig.tight_layout()
    return fig


# ==============================================================================
# 3. INTERFAZ PRINCIPAL (MAIN)
# ==============================================================================

def main():
    st.title("Monitor de Producción Minera y Precio del Cobre en Chile")
    st.markdown(
        "Dashboard interactivo para analizar la producción de cobre por **compañía/faena (1998–2018)**, "
        "el desglose por **tipo de producto (1998–2017)** y su relación con la **cotización internacional del cobre**."
    )

    # Carga de los tres archivos CSV desde rutas relativas
    try:
        raw_comp = cargar_csv(RUTA_COMPANIAS)
        raw_prod = cargar_csv(RUTA_PRODUCTOS)
        raw_prec = cargar_csv(RUTA_PRECIOS)
    except FileNotFoundError as err:
        st.error(f"Error al cargar archivos CSV locales: {err}. Verifica que los 3 CSV estén en la carpeta raíz.")
        st.stop()

    df_prec_mensual, df_prec_anual, info_prec = preparar_datos_precios(raw_prec)
    df_comp, info_comp = preparar_datos_companias(raw_comp, df_prec_anual)
    df_prod, info_prod = preparar_datos_productos(raw_prod, df_prec_anual)

    # --------------------------------------------------------------------------
    # BARRA LATERAL: CONTROLES E INTERACTIVIDAD
    # --------------------------------------------------------------------------
    st.sidebar.header("Filtros y Controles")
    st.sidebar.info("Ajusta los filtros para actualizar métricas, gráficos y tablas.")

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
        "Unidad de producción",
        options=["Miles de TMF (kTMF)", "Toneladas Métricas de Fino (TMF)"]
    )
    col_val = "produccion_ktmf" if "kTMF" in unidad_radio else "produccion_tmf"
    unidad_txt = "kTMF" if "kTMF" in unidad_radio else "TMF"

    mostrar_precio = st.sidebar.checkbox("Superponer precio del cobre en gráfico de evolución", value=True)

    df_comp_filt = filtrar_companias(df_comp, companias_sel, rango_anios)

    if df_comp_filt.empty:
        st.warning("No hay datos disponibles para la selección actual. Elige al menos una compañía.")
        st.stop()

    # --------------------------------------------------------------------------
    # INDICADORES CLAVE (KPIs)
    # --------------------------------------------------------------------------
    st.subheader("Indicadores Clave del Período Seleccionado")
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)

    prod_acumulada = df_comp_filt[col_val].sum()
    precio_prom_periodo = df_comp_filt.groupby("anio")["precio_cusd_lb"].mean().mean()
    valorizacion_total = df_comp_filt["valorizacion_musd"].sum()
    lider_fila = df_comp_filt.groupby("compania")[col_val].sum().idxmax()

    kpi1.metric(f"Producción Acumulada ({unidad_txt})", f"{prod_acumulada:,.1f}")
    kpi2.metric("Precio Promedio Cobre", f"{precio_prom_periodo:,.2f} cUS$/lb")
    kpi3.metric("Valorización Bruta Est.", f"US$ {valorizacion_total:,.0f} M")
    kpi4.metric("Compañía Líder", lider_fila)

    st.divider()

    # --------------------------------------------------------------------------
    # PESTAÑAS DE VISUALIZACIÓN Y DATOS
    # --------------------------------------------------------------------------
    tab1, tab2, tab3, tab4 = st.tabs([
        "1. Compañías y Precio del Cobre",
        "2. Correlación y Productos",
        "3. Tabla y Descarga CSV",
        "4. Limpieza y Fuentes"
    ])

    with tab1:
        col_a, col_b = st.columns(2)
        with col_a:
            st.pyplot(grafico_lineas_evolucion(df_comp_filt, col_val, unidad_txt, mostrar_precio))
        with col_b:
            st.pyplot(grafico_barras_ranking(df_comp_filt, col_val, unidad_txt, top_n))

    with tab2:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.pyplot(grafico_dispersion_precio_produccion(df_comp_filt, col_val, unidad_txt))
        with col_p2:
            st.caption("Nota: El desglose por subproducto refinado cubre 1998–2017.")
            st.pyplot(grafico_pastel_refinado(df_prod, col_val, rango_anios))

    with tab3:
        vista_tabla = st.selectbox(
            "Selecciona conjunto de datos a inspeccionar",
            options=[
                "Producción por Compañía + Precio Anual (Filtrada)",
                "Producción por Producto + Precio Anual (1998–2017)",
                "Serie Histórica Mensual Precios Cobre (1992–2026)"
            ]
        )
        if "Compañía" in vista_tabla:
            df_tabla = df_comp_filt
        elif "Producto" in vista_tabla:
            df_tabla = df_prod
        else:
            df_tabla = df_prec_mensual[["date", "anio", "mes", "precio_usd_ton", "precio_usd_lb", "precio_cusd_lb"]]

        st.dataframe(df_tabla, use_container_width=True, hide_index=True)

        csv_descarga = df_tabla.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="Descargar tabla actual en CSV",
            data=csv_descarga,
            file_name="mineria_cobre_con_precios.csv",
            mime="text/csv"
        )

    with tab4:
        st.subheader("Auditoría, Limpieza y Cruce de Datos (Pandas)")
        st.write(
            f"- **Dataset Compañías (`1998–2018`):** {info_comp['registros_validos']} registros válidos "
            f"de {info_comp['n_companias']} faenas ({info_comp['sin_operacion']} celdas `'-'` descartadas por años sin operación; {info_comp['duplicados']} duplicados)."
        )
        st.write(
            f"- **Dataset Productos (`1998–2017`):** {info_prod['registros_validos']} registros válidos en "
            f"{info_prod['productos']} categorías ({info_prod['nulos']} valores nulos)."
        )
        st.write(
            f"- **Dataset Precios (`copper-price.csv`):** {info_prec['mensuales_totales']} registros mensuales "
            f"({info_prec['rango_fechas']}, {info_prec['nulos']} nulos, {info_prec['duplicados']} duplicados) "
            f"agrupados en {info_prec['anios_cubiertos']} promedios anuales y convertidos de US$/TM a cUS$/lb "
            f"(1 TM = 2.204,62 lb) para cruzar mediante `pd.merge()`."
        )
        st.warning(
            "Notas sobre calidad de datos: En 'Producción de cobre por compañía', la columna 2018 utiliza punto de miles "
            "y coma decimal ('1.242,70'), estandarizado mediante limpieza de strings. En 'produccion-por-producto.csv', "
            "el bloque 2008–2017 replica las cifras de 1998–2007 en la fuente original."
        )

        st.subheader("Fuentes Oficiales de los Datos")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown("**1. Producción Minera por Compañía y Producto**")
            st.write("Comisión Chilena del Cobre (COCHILCO) — Estadísticas de Producción Minera.")
            st.link_button("Visitar Portal Oficial COCHILCO", "https://www.cochilco.cl")
        with col_f2:
            st.markdown("**2. Serie Histórica del Precio del Cobre (US$/TM)**")
            st.write("Eco3Min — Copper Price History Dataset (cotización mensual 1992–2026).")
            st.link_button("Visitar Fuente Eco3Min", "https://eco3min.fr/en/copper-price-history-dataset/")


if __name__ == "__main__":
    main()
