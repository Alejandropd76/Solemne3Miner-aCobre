import os
import re
import base64
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

# Rutas relativas de los tres CSV en la carpeta raíz del repositorio
RUTA_COMPANIAS = "Producción de cobre por compañía.xlsx - Sheet0.csv"
RUTA_PRODUCTOS = "produccion-por-producto.csv"
RUTA_PRECIOS = "copper-price.csv"

# Rutas relativas de las imágenes locales en la carpeta raíz
RUTA_FONDO = "fondo_mineria.jpg"
RUTA_BANNER = "banner_cobre.jpg"
RUTA_CATODOS = "catodos_cobre.jpg"

# Factor de conversión oficial: 1 tonelada métrica = 2.204,62262 libras
LIBRAS_POR_TONELADA = 2204.62262

# Paleta de colores temática (Cobre y Minerales de Chile)
COLOR_COBRE = "#B87333"
COLOR_COBRE_CLARO = "#D49A6A"
COLOR_TURQUESA = "#1E7E7A"
COLOR_BRONCE = "#2C1E16"
COLOR_ORO = "#D99B26"

st.set_page_config(
    page_title="CobreChile | Monitor Minero y Cotización BML",
    page_icon="⛏️",
    layout="wide"
)


# ==============================================================================
# 0. ESTILOS VISUALES, FONDO E IDENTIDAD MINERA (CSS + IMÁGENES + SVG)
# ==============================================================================

def obtener_imagen_base64(ruta_imagen: str) -> str:
    """Codifica una imagen local a Base64 para inyectarla en CSS y HTML."""
    if not os.path.exists(ruta_imagen):
        return ""
    with open(ruta_imagen, "rb") as archivo:
        return base64.b64encode(archivo.read()).decode("utf-8")


def aplicar_identidad_minera():
    """Inyecta imagen de fondo, estilos CSS mineros, banner superior y reseña histórica."""
    fondo_b64 = obtener_imagen_base64(RUTA_FONDO)
    banner_b64 = obtener_imagen_base64(RUTA_BANNER)

    if fondo_b64:
        css_fondo = f"""
        [data-testid="stAppViewContainer"] {{
            background-image: linear-gradient(
                rgba(250, 246, 242, 0.58),
                rgba(245, 236, 227, 0.65)
            ), url("data:image/jpeg;base64,{fondo_b64}");
            background-size: cover;
            background-position: center center;
            background-attachment: fixed;
        }}
        [data-testid="stHeader"] {{
            background-color: rgba(250, 246, 242, 0.45);
            backdrop-filter: blur(4px);
        }}
        [data-testid="stSidebar"] {{
            background-color: rgba(240, 229, 218, 0.88);
            backdrop-filter: blur(6px);
            border-right: 1px solid #D49A6A;
        }}
        """
    else:
        css_fondo = ""

    st.markdown(
        f"""
        <style>
        {css_fondo}

        /* Tarjetas de indicadores KPI con borde de cobre metálico */
        div[data-testid="stMetric"] {{
            background-color: rgba(255, 255, 255, 0.94);
            border-left: 6px solid #B87333;
            border-top: 1px solid #E6D5C3;
            border-right: 1px solid #E6D5C3;
            border-bottom: 1px solid #E6D5C3;
            padding: 14px 18px;
            border-radius: 10px;
            box-shadow: 0 3px 10px rgba(44, 30, 22, 0.10);
        }}
        div[data-testid="stMetricLabel"] {{
            color: #6E472B;
            font-weight: 600;
        }}
        div[data-testid="stMetricValue"] {{
            color: #2C1E16;
        }}

        /* Contenedores para pestañas con buena legibilidad sobre el fondo */
        div[data-testid="stTabs"] {{
            background-color: rgba(255, 255, 255, 0.85);
            padding: 16px 20px;
            border-radius: 12px;
            border: 1px solid #E6D5C3;
            box-shadow: 0 2px 10px rgba(44, 30, 22, 0.06);
        }}
        button[data-baseweb="tab"] {{
            font-weight: 600;
            color: #5C3D28;
        }}
        button[data-baseweb="tab"][aria-selected="true"] {{
            color: #B87333;
        }}

        /* Contenedor Banner Principal */
        .banner-cobre {{
            background: linear-gradient(135deg, #241710 0%, #5E3018 52%, #B87333 100%);
            padding: 20px 26px;
            border-radius: 14px;
            color: #FAF6F2;
            margin-bottom: 12px;
            border: 1px solid #D49A6A;
            box-shadow: 0 4px 14px rgba(44, 30, 22, 0.22);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 20px;
        }}
        .banner-cobre h1 {{
            color: #FFFFFF;
            margin: 0 0 6px 0;
            font-size: 1.85rem;
            letter-spacing: -0.3px;
        }}
        .banner-cobre p {{
            color: #F3E5D8;
            margin: 0;
            font-size: 0.95rem;
            line-height: 1.4;
        }}
        .badge-cu {{
            background: rgba(255, 255, 255, 0.12);
            border: 2px solid #F2C185;
            border-radius: 12px;
            padding: 8px 14px;
            text-align: center;
            min-width: 100px;
            backdrop-filter: blur(4px);
        }}
        .badge-cu .num {{
            font-size: 0.82rem;
            color: #F2C185;
            font-weight: 700;
            text-align: left;
        }}
        .badge-cu .sym {{
            font-size: 2.0rem;
            font-weight: 800;
            color: #FFFFFF;
            line-height: 1.05;
        }}
        .badge-cu .name {{
            font-size: 0.72rem;
            color: #F3E5D8;
            letter-spacing: 1px;
            text-transform: uppercase;
        }}

        /* Franja combinada: imagen panorámica compacta + reseña histórica y económica */
        .franja-mina-grid {{
            display: flex;
            flex-wrap: wrap;
            gap: 16px;
            align-items: stretch;
            margin-bottom: 18px;
        }}
        .franja-mina-img {{
            position: relative;
            flex: 0 0 360px;
            max-width: 100%;
            height: 165px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid #B87333;
            box-shadow: 0 3px 10px rgba(44, 30, 22, 0.15);
        }}
        .franja-mina-img img {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            object-position: center 48%;
            display: block;
        }}
        .franja-mina-caption {{
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            background: linear-gradient(transparent, rgba(36, 23, 16, 0.84));
            color: #FAF6F2;
            font-size: 0.76rem;
            padding: 12px 12px 5px 12px;
        }}
        .resena-cobre-box {{
            flex: 1 1 420px;
            min-height: 165px;
            background-color: rgba(255, 255, 255, 0.92);
            border-left: 5px solid #B87333;
            border-top: 1px solid #E6D5C3;
            border-right: 1px solid #E6D5C3;
            border-bottom: 1px solid #E6D5C3;
            border-radius: 12px;
            padding: 14px 20px;
            box-shadow: 0 3px 10px rgba(44, 30, 22, 0.08);
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}
        .resena-cobre-box h3 {{
            margin: 0 0 6px 0;
            color: #2C1E16;
            font-size: 1.08rem;
            font-weight: 700;
        }}
        .resena-cobre-box p {{
            margin: 0 0 8px 0;
            color: #3E2A1D;
            font-size: 0.90rem;
            line-height: 1.48;
        }}
        .resena-cobre-box p:last-child {{
            margin-bottom: 0;
        }}
        </style>

        <div class="banner-cobre">
            <div>
                <h1>Monitor de Producción Minera y Precio del Cobre en Chile</h1>
                <p>
                    Análisis interactivo de la extracción por <strong>compañía y faena (1998–2018)</strong>,
                    desglose metalúrgico por <strong>producto (1998–2017)</strong> y evolución de la
                    <strong>cotización internacional del cobre</strong>.
                </p>
            </div>
            <div style="display:flex; align-items:center; gap:16px;">
                <svg width="105" height="78" viewBox="0 0 120 90" xmlns="http://www.w3.org/2000/svg">
                    <polygon points="5,75 35,25 65,75" fill="#8C5327" opacity="0.7"/>
                    <polygon points="40,75 75,18 112,75" fill="#D49A6A" opacity="0.85"/>
                    <polygon points="75,18 66,33 75,30 84,33" fill="#FAF6F2"/>
                    <path d="M18,75 Q60,55 102,75 Z" fill="#2C1E16"/>
                    <path d="M28,75 Q60,62 92,75" stroke="#F2C185" stroke-width="2" fill="none"/>
                    <path d="M38,75 Q60,68 82,75" stroke="#1E7E7A" stroke-width="2" fill="none"/>
                </svg>
                <div class="badge-cu">
                    <div class="num">29</div>
                    <div class="sym">Cu</div>
                    <div class="name">Cobre • Chile</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Banner compacto acompañado de reseña histórica y económica del cobre en Chile
    if banner_b64:
        st.markdown(
            f"""
            <div class="franja-mina-grid">
                <div class="franja-mina-img">
                    <img src="data:image/jpeg;base64,{banner_b64}" alt="Mina a rajo abierto en Chile">
                    <div class="franja-mina-caption">
                        Gran Minería del Cobre — Norte de Chile
                    </div>
                </div>
                <div class="resena-cobre-box">
                    <h3>Importancia Histórica y Económica del Cobre en Chile</h3>
                    <p>
                        <strong>Legado histórico:</strong> Desde la metalurgia prehispánica y el auge de la gran minería
                        en el siglo XX —culminando en la nacionalización de 1971—, el cobre ha articulado el desarrollo
                        territorial, tecnológico y fiscal del país.
                    </p>
                    <p>
                        <strong>Motor económico:</strong> Como principal productor mundial, Chile depende en gran medida de la
                        dinámica de este metal para sus exportaciones, ingresos fiscales y balanza comercial, haciendo que
                        las variaciones de precio y ley de mineral impacten directamente en la economía nacional.
                    </p>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )


def renderizar_logo_sidebar():
    """Dibuja un emblema vectorial de cátodo de cobre y piquetas en la barra lateral."""
    st.sidebar.markdown(
        """
        <div style="text-align:center; padding: 8px 0 14px 0;">
            <svg width="96" height="96" viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
                <circle cx="50" cy="50" r="46" fill="#2C1E16" stroke="#B87333" stroke-width="4"/>
                <circle cx="50" cy="50" r="39" fill="none" stroke="#1E7E7A" stroke-width="1.5" stroke-dasharray="4 3"/>
                <polygon points="30,66 70,66 63,52 37,52" fill="#B87333" stroke="#F2C185" stroke-width="1.5"/>
                <line x1="32" y1="26" x2="68" y2="48" stroke="#FAF6F2" stroke-width="3" stroke-linecap="round"/>
                <line x1="68" y1="26" x2="32" y2="48" stroke="#FAF6F2" stroke-width="3" stroke-linecap="round"/>
                <path d="M27,31 Q35,21 43,25" stroke="#D49A6A" stroke-width="3" fill="none" stroke-linecap="round"/>
                <path d="M73,31 Q65,21 57,25" stroke="#D49A6A" stroke-width="3" fill="none" stroke-linecap="round"/>
                <text x="50" y="81" font-family="sans-serif" font-size="10" font-weight="bold" fill="#F2C185" text-anchor="middle">
                    MINERÍA CHILE
                </text>
            </svg>
        </div>
        """,
        unsafe_allow_html=True
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

    df = df[~df[col_nombre].astype(str).str.upper().str.startswith("TOTAL")].copy()
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

    df_limpio["produccion_tmf"] = df_limpio["produccion_ktmf"] * 1000.0
    df_limpio = pd.merge(df_limpio, df_precios_anual, on="anio", how="left")

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
    """Filtra el DataFrame de compañías según los parámetros seleccionados."""
    return df[
        (df["compania"].isin(companias)) &
        (df["anio"] >= rango_anios[0]) &
        (df["anio"] <= rango_anios[1])
    ].copy()


# ==============================================================================
# 2. FUNCIONES DE VISUALIZACIÓN (PALETA COBRE Y MINERALES DE CHILE)
# ==============================================================================

def grafico_lineas_evolucion(df: pd.DataFrame, col_val: str, unidad: str, mostrar_precio: bool):
    """Gráfico 1 (Líneas con doble eje): Producción anual (Turquesa) vs. Precio del Cobre (Cobre)."""
    df_anual = df.groupby("anio", as_index=False).agg({
        col_val: "sum",
        "precio_cusd_lb": "mean"
    })

    fig, ax1 = plt.subplots(figsize=(10.5, 4.2))
    fig.patch.set_facecolor("#FFFFFF")
    ax1.set_facecolor("#FCF9F6")

    l1 = ax1.plot(
        df_anual["anio"], df_anual[col_val],
        marker="o", color=COLOR_TURQUESA, linewidth=2.3, label=f"Producción ({unidad})"
    )
    ax1.fill_between(df_anual["anio"], df_anual[col_val], color=COLOR_TURQUESA, alpha=0.10)
    ax1.set_xlabel("Año", fontweight="bold", color=COLOR_BRONCE)
    ax1.set_ylabel(f"Producción Total ({unidad})", color=COLOR_TURQUESA, fontweight="bold")
    ax1.tick_params(axis="y", labelcolor=COLOR_TURQUESA)
    ax1.set_xticks(df_anual["anio"])
    ax1.grid(True, linestyle="--", alpha=0.35, color="#C8B6A6")
    ax1.spines["top"].set_visible(False)

    lineas = l1
    if mostrar_precio:
        ax2 = ax1.twinx()
        l2 = ax2.plot(
            df_anual["anio"], df_anual["precio_cusd_lb"],
            marker="D", linestyle="--", color=COLOR_COBRE, linewidth=2.0,
            label="Precio Cobre (cUS$/lb)"
        )
        ax2.set_ylabel("Precio Promedio (cUS$/lb)", color=COLOR_COBRE, fontweight="bold")
        ax2.tick_params(axis="y", labelcolor=COLOR_COBRE)
        ax2.spines["top"].set_visible(False)
        lineas = l1 + l2

    etiquetas = [l.get_label() for l in lineas]
    ax1.legend(lineas, etiquetas, loc="upper left", frameon=True, facecolor="#FFFFFF")
    plt.title("Evolución Anual de Producción vs. Precio del Cobre", fontweight="bold", color=COLOR_BRONCE)
    fig.tight_layout()
    return fig


def grafico_barras_ranking(df: pd.DataFrame, col_val: str, unidad: str, top_n: int):
    """Gráfico 2 (Barras horizontales): Top N compañías en tonos cobre y bronce."""
    df_top = (
        df.groupby("compania", as_index=False)[col_val]
        .sum()
        .sort_values(by=col_val, ascending=False)
        .head(top_n)
        .sort_values(by=col_val, ascending=True)
    )

    fig, ax = plt.subplots(figsize=(10.5, 4.5))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FCF9F6")

    colores = [COLOR_COBRE if i == len(df_top) - 1 else COLOR_COBRE_CLARO for i in range(len(df_top))]
    barras = ax.barh(df_top["compania"], df_top[col_val], color=colores, edgecolor=COLOR_BRONCE, linewidth=0.5)

    max_val = df_top[col_val].max() if len(df_top) > 0 else 1
    for barra in barras:
        ancho = barra.get_width()
        ax.text(
            ancho + max_val * 0.012,
            barra.get_y() + barra.get_height() / 2,
            f"{ancho:,.0f}",
            va="center", fontsize=8.5, color=COLOR_BRONCE, fontweight="bold"
        )

    ax.set_xlim(0, max_val * 1.14)
    ax.set_title(f"Top {len(df_top)} Compañías por Producción Acumulada", fontweight="bold", color=COLOR_BRONCE)
    ax.set_xlabel(f"Producción Acumulada ({unidad})", fontweight="bold", color=COLOR_BRONCE)
    ax.set_ylabel("Compañía / Faena", fontweight="bold", color=COLOR_BRONCE)
    ax.grid(axis="x", linestyle="--", alpha=0.35, color="#C8B6A6")
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

    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FCF9F6")

    ax.scatter(
        df_anual["precio_cusd_lb"],
        df_anual[col_val],
        color=COLOR_COBRE, edgecolors=COLOR_BRONCE, s=85, alpha=0.9
    )
    for _, fila in df_anual.iterrows():
        ax.annotate(
            str(int(fila["anio"])),
            (fila["precio_cusd_lb"], fila[col_val]),
            fontsize=8, color=COLOR_BRONCE, alpha=0.85, xytext=(4, 3), textcoords="offset points"
        )

    ax.set_title("Correlación: Precio del Cobre vs. Producción Anual", fontweight="bold", color=COLOR_BRONCE)
    ax.set_xlabel("Precio Promedio Anual (cUS$/lb)", fontweight="bold", color=COLOR_BRONCE)
    ax.set_ylabel(f"Producción Total Anual ({unidad})", fontweight="bold", color=COLOR_BRONCE)
    ax.grid(True, linestyle="--", alpha=0.35, color="#C8B6A6")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    fig.tight_layout()
    return fig


def grafico_pastel_refinado(df_prod: pd.DataFrame, col_val: str, rango_anios: tuple):
    """Gráfico 4 (Anillo / Pastel): Participación porcentual de subproductos de cobre refinado."""
    h_min, h_max = rango_anios[0], min(rango_anios[1], 2017)
    df_sub = df_prod[
        (df_prod["categoria"] == "Subproducto Refinado") &
        (df_prod["anio"] >= h_min) &
        (df_prod["anio"] <= h_max)
    ]
    df_pie = df_sub.groupby("producto", as_index=False)[col_val].sum()
    df_pie = df_pie[df_pie[col_val] > 0]

    fig, ax = plt.subplots(figsize=(7.5, 4.4))
    fig.patch.set_facecolor("#FFFFFF")
    colores = [COLOR_COBRE, COLOR_TURQUESA, COLOR_ORO]

    ax.pie(
        df_pie[col_val],
        labels=df_pie["producto"],
        autopct="%1.1f%%",
        startangle=140,
        colors=colores[:len(df_pie)],
        pctdistance=0.78,
        wedgeprops={"edgecolor": "#FFFFFF", "linewidth": 2, "width": 0.45}
    )
    ax.set_title(f"Composición del Cobre Refinado por Subproducto ({h_min}–{h_max})", fontweight="bold", color=COLOR_BRONCE)
    fig.tight_layout()
    return fig


# ==============================================================================
# 3. INTERFAZ PRINCIPAL (MAIN)
# ==============================================================================

def main():
    aplicar_identidad_minera()

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

    todas_companias = sorted(df_comp["compania"].unique().tolist())
    anio_min, anio_max = int(df_comp["anio"].min()), int(df_comp["anio"].max())

    # Inicializar en session_state los controles ubicados debajo de cada gráfico
    if "rango_anios" not in st.session_state:
        st.session_state["rango_anios"] = (anio_min, anio_max)
    if "top_n" not in st.session_state:
        st.session_state["top_n"] = 10

    # --------------------------------------------------------------------------
    # BARRA LATERAL: EMBLEMA Y CONTROLES GENERALES
    # --------------------------------------------------------------------------
    renderizar_logo_sidebar()
    st.sidebar.header("Filtros y Controles")
    st.sidebar.info("Ajusta las compañías y unidades. El rango de años y el Top N se controlan bajo cada gráfico.")

    companias_sel = st.sidebar.multiselect(
        "Compañías / Faenas mineras",
        options=todas_companias,
        default=todas_companias
    )

    unidad_radio = st.sidebar.radio(
        "Unidad de producción",
        options=["Miles de TMF (kTMF)", "Toneladas Métricas de Fino (TMF)"]
    )
    col_val = "produccion_ktmf" if "kTMF" in unidad_radio else "produccion_tmf"
    unidad_txt = "kTMF" if "kTMF" in unidad_radio else "TMF"

    mostrar_precio = st.sidebar.checkbox("Superponer precio del cobre en evolución", value=True)

    rango_actual = st.session_state["rango_anios"]
    top_n_actual = st.session_state["top_n"]

    df_comp_filt = filtrar_companias(df_comp, companias_sel, rango_actual)

    if df_comp_filt.empty:
        st.warning("No hay datos disponibles para la selección actual. Elige al menos una compañía o amplía los años.")
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
        # 1) Gráfico de Evolución Anual + Slider inmediatamente debajo
        st.pyplot(grafico_lineas_evolucion(df_comp_filt, col_val, unidad_txt, mostrar_precio))
        st.slider(
            "Rango de años",
            min_value=anio_min,
            max_value=anio_max,
            key="rango_anios"
        )

        st.divider()

        # 2) Gráfico Top N Compañías debajo del anterior + Control numérico inmediatamente debajo
        st.pyplot(grafico_barras_ranking(df_comp_filt, col_val, unidad_txt, top_n_actual))
        st.number_input(
            "Cantidad de compañías en el ranking (Top N)",
            min_value=3,
            max_value=len(todas_companias),
            step=1,
            key="top_n"
        )

    with tab2:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            st.pyplot(grafico_dispersion_precio_produccion(df_comp_filt, col_val, unidad_txt))
        with col_p2:
            st.caption("Nota: El desglose por subproducto refinado cubre 1998–2017.")
            st.pyplot(grafico_pastel_refinado(df_prod, col_val, rango_actual))

        if os.path.exists(RUTA_CATODOS):
            st.divider()
            col_img, col_txt = st.columns([1.2, 1.8])
            with col_img:
                st.image(
                    RUTA_CATODOS,
                    caption="Cátodos de Cobre Refinado de Alta Pureza (99,99%)",
                    use_container_width=True
                )
            with col_txt:
                st.subheader("Procesamiento Metalúrgico en Chile")
                st.write(
                    "La producción chilena de cobre refinado se divide principalmente en **cátodos electroobtenidos (SX-EW)** "
                    "provenientes de minerales oxidados y **cátodos electrorrefinados (E.R.)** derivados de concentrados sulfurados, "
                    "exportados directamente a mercados industriales globales."
                )

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

    st.caption("Desarrollado para Taller de Programación II • Industria Minera del Cobre en Chile.")


if __name__ == "__main__":
    main()
