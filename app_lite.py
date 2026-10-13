import streamlit as st
import yfinance as yf
import pandas as pd
import requests

# 1. CONFIGURACIÓN ULTRALIGERA PARA MÓVIL
st.set_page_config(
    page_title="GEM Lite Mobile",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.title("🎯 GEM Scanner Lite")
st.caption("Versión Móvil Ultraligera · Radar Institucional & Auditoría")

# --- LISTA PREDEFINIDA DE LÍDERES SECTORIALES (Descorrelación Dalio) ---
UNIVERSO_SECTORIAL = {
    "Consumo Básico": ["COST", "WMT", "PG"],
    "Industria / Maquinaria": ["CAT", "GE", "URI"],
    "Finanzas / Banca": ["JPM", "V", "MA"],
    "Salud / Farma": ["LLY", "UNH", "ABBV"],
    "Energía / Infraestructura": ["XOM", "BE", "NEE"],
    "Tecnología / Crecimiento": ["QQQ", "AAPL", "GOOGL"]
}

TICKERS_UNIVERSO = [t for grupo in UNIVERSO_SECTORIAL.values() for t in grupo]

# --- SELECTOR INTELIGENTE DE MODELOS RÁPIDOS ---
def obtener_modelos_ordenados(api_key):
    try:
        url_lista = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        lista_req = requests.get(url_lista, timeout=10).json()
        todos = [
            m['name'].replace('models/', '')
            for m in lista_req.get('models', [])
            if 'gemini' in m.get('name', '')
            and 'generateContent' in m.get('supportedGenerationMethods', [])
            and 'vision' not in m.get('name', '')
        ]
        rapidos = [m for m in todos if 'flash' in m and 'thinking' not in m and 'exp' not in m]
        resto = [m for m in todos if m not in rapidos]
        return rapidos + resto
    except Exception:
        return ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]

# --- MOTOR MATEMÁTICO CACHEADO (5 min) ---
@st.cache_data(ttl=300)
def analizar_ticker(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        df = t.history(period="1y")
        if df.empty or len(df) < 50:
            return None

        close = float(df["Close"].iloc[-1])
        ema50 = float(df["Close"].ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = float(df["Close"].ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else ema50

        ventana = df.tail(30)
        high_30 = float(ventana["High"].max())
        low_30 = float(ventana["Low"].min())
        pivot = (high_30 + low_30 + close) / 3.0

        r1 = (2 * pivot) - low_30
        s1 = (2 * pivot) - high_30
        r2 = pivot + (high_30 - low_30)
        s2 = pivot - (high_30 - low_30)

        if close > ema50 and close > ema200:
            score = 85
            estado = "Fuerte 🟢"
        elif close < ema50 and close < ema200:
            score = 25
            estado = "Rota 🔴"
        elif close > ema200:
            score = 60
            estado = "Alerta 🟡"
        else:
            score = 40
            estado = "Débil 🟠"

        dist_s1 = ((close - s1) / close) * 100
        dist_r1 = ((r1 - close) / close) * 100
        stop_loss = round(min(s1, ema200) * 0.98, 2)

        return {
            "Ticker": ticker_symbol.upper(),
            "Precio": round(close, 2),
            "Score": score,
            "Estado": estado,
            "EMA50": round(ema50, 2),
            "EMA200": round(ema200, 2),
            "S1": round(s1, 2),
            "S2": round(s2, 2),
            "R1": round(r1, 2),
            "R2": round(r2, 2),
            "Dist_S1_%": round(dist_s1, 2),
            "Dist_R1_%": round(dist_r1, 2),
            "Stop_Loss": stop_loss
        }
    except Exception:
        return None

# --- COMITÉ GEMINI ---
def consultar_comite_ia(d):
    prompt = f"""
    Actúa como el Comité Financiero GEM (Analista Cuantitativo Institucional).
    Evalúa el siguiente activo usando estrictamente las reglas de Minervini, Tudor Jones y Livermore.

    DATOS DEL ACTIVO:
    Ticker: {d['Ticker']}
    Precio Actual: {d['Precio']:.2f} USD
    EMA 50: {d['EMA50']:.2f} USD
    EMA 200: {d['EMA200']:.2f} USD
    Soportes: S1 {d['S1']:.2f} USD - S2 {d['S2']:.2f} USD
    Resistencias: R1 {d['R1']:.2f} USD - R2 {d['R2']:.2f} USD
    Benchmark (S&P 500): Alcista (sobre EMA 200).

    REGLAS DE EVALUACIÓN:
    - Las resistencias (R1/R2) son SOLO para toma de ganancias. Prohibido comprar cerca de ellas.
    - Los soportes (S1/S2) son zonas de entrada (exige riesgo asimétrico).
    - Si el precio está debajo de EMA 50, la fuerza de corto plazo está rota.
    - Si el precio está debajo de EMA 200, no se recomienda exposición larga.
    - No uses el símbolo de dólar ($) para evitar errores de formato.

    ENTREGA TU RESPUESTA EN 4 PUNTOS BREVES PARA MÓVIL:
    1. VEREDICTO INSTITUCIONAL
    2. DIAGNÓSTICO DE FASES
    3. NIVELES OPERATIVOS
    4. STOP LOSS MATEMÁTICO
    """
    try:
        api_key = st.secrets["GEMINI_API_KEY"].strip()
        headers = {"Content-Type": "application/json"}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}
        modelos = obtener_modelos_ordenados(api_key)
        ultimo_error = "Sin respuesta"

        for modelo in modelos:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent?key={api_key}"
                response = requests.post(url, headers=headers, json=payload, timeout=20)
                if response.status_code == 200:
                    data = response.json()
                    if "candidates" in data and len(data["candidates"]) > 0 and "content" in data["candidates"][0]:
                        texto = data["candidates"][0]["content"]["parts"][0]["text"].replace("$", "USD ")
                        return f"✅ *(Conectado vía {modelo})*\n\n" + texto
                ultimo_error = f"{modelo}: {response.status_code}"
            except Exception as e_inner:
                ultimo_error = str(e_inner)
                continue
        return f"❌ Google no respondió a tiempo. Último estado: {ultimo_error}"
    except Exception as e:
        return f"❌ Error fatal Gemini: {e}"

# 3. INTERFAZ
tab1, tab2 = st.tabs(["🏛️ Radar Francotirador", "📋 Mini-Auditor & Balance"])

with tab1:
    st.subheader("Búsqueda y Detección de Oportunidades")
    
    modo_radar = st.radio("Método de Análisis:", ["Ticker Individual", "Escanear Universo Sectorial (18 Reyes)"], horizontal=True)

    if modo_radar == "Ticker Individual":
        col_t1, col_t2 = st.columns([2, 1])
        with col_t1:
            ticker_input = st.text_input("Ingresa Ticker:", value="COHR").upper().strip()
        with col_t2:
            preset_rapido = st.selectbox("O selecciona líder:", [""] + TICKERS_UNIVERSO)
            if preset_rapido:
                ticker_input = preset_rapido

        if ticker_input:
            with st.spinner(f"Analizando {ticker_input}..."):
                datos = analizar_ticker(ticker_input)

            if datos:
                c1, c2 = st.columns(2)
                c1.metric("Precio Actual", f"${datos['Precio']}")
                c2.metric("Score GEM", f"{datos['Score']} ({datos['Estado']})")

                st.markdown(f"""
                **Niveles Operativos Clave (USD):**
                * 📈 **EMAs:** EMA 50: **{datos['EMA50']}** | EMA 200: **{datos['EMA200']}**
                * 🎯 **Soportes:** S1: **{datos['S1']}** *(a {datos['Dist_S1_%']}%)* | S2: **{datos['S2']}**
                * 🚀 **Resistencias:** R1: **{datos['R1']}** *(a +{datos['Dist_R1_%']}%)* | R2: **{datos['R2']}**
                * 🛡️ **Stop Loss Estructural:** **{datos['Stop_Loss']}**
                """)

                if st.button("🤖 Solicitar Veredicto del Comité GEM", use_container_width=True):
                    with st.spinner("Consultando al Comité..."):
                        st.info(consultar_comite_ia(datos))
            else:
                st.error("No se pudo cargar el ticker. Verifica el símbolo.")

    else:
        st.markdown("**18 Líderes Diversificados (Consumo, Industria, Finanzas, Salud, Energía, Tech):**")
        if st.button("🔍 Escanear Universo Sectorial Ahora", use_container_width=True):
            lista_res = []
            barra = st.progress(0)
            for i, sym in enumerate(TICKERS_UNIVERSO):
                r = analizar_ticker(sym)
                if r:
                    # Identificar sector
                    sector_encontrado = next((sec for sec, ticks in UNIVERSO_SECTORIAL.items() if sym in ticks), "General")
                    r["Sector"] = sector_encontrado
                    lista_res.append(r)
                barra.progress(min((i + 1) / len(TICKERS_UNIVERSO), 1.0))
            barra.empty()

            if lista_res:
                df_univ = pd.DataFrame(lista_res)
                
                # Filtrar solo oportunidades de calidad: Score >= 60
                en_zona = df_univ[(df_univ["Score"] >= 60) & (df_univ["Dist_S1_%"] <= 4.0)]
                fase2 = df_univ[df_univ["Score"] == 85]

                if not en_zona.empty:
                    st.success(f"🎯 **Candidatos en Zona de Recarga (<4% de S1):** {', '.join(en_zona['Ticker'].tolist())}")
                else:
                    st.info("ℹ️ Ningún activo está a menos del 4% de S1 hoy. Paciencia de francotirador.")

                st.markdown("### 📊 Radiografía Completa del Universo")
                st.dataframe(
                    df_univ[["Sector", "Ticker", "Precio", "Score", "Estado", "Dist_S1_%", "EMA50", "EMA200", "S1", "R1"]],
                    use_container_width=True,
                    hide_index=True
                )

with tab2:
    st.subheader("Auditor de Balance y Salud de Cartera")
    preset = st.radio(
        "Elige plantilla rápida:",
        ["Cuenta Schwab ($288)", "Cartera Hijo (Ejemplo)", "Radares del Día"],
        horizontal=True
    )

    if preset == "Cuenta Schwab ($288)":
        df_init = pd.DataFrame([
            {"Ticker": "AMZN", "Valor_USD": 101.98},
            {"Ticker": "BE", "Valor_USD": 43.82},
            {"Ticker": "SNDK", "Valor_USD": 142.63}
        ])
    elif preset == "Cartera Hijo (Ejemplo)":
        df_init = pd.DataFrame([
            {"Ticker": "VOO", "Valor_USD": 150.0},
            {"Ticker": "QQQM", "Valor_USD": 100.0},
            {"Ticker": "AMZN", "Valor_USD": 80.0},
            {"Ticker": "NVDA", "Valor_USD": 70.0}
        ])
    else:
        df_init = pd.DataFrame([
            {"Ticker": "COHR", "Valor_USD": 100.0},
            {"Ticker": "CAT", "Valor_USD": 100.0},
            {"Ticker": "COST", "Valor_USD": 100.0},
            {"Ticker": "QQQ", "Valor_USD": 100.0}
        ])

    df_editado = st.data_editor(df_init, num_rows="dynamic", use_container_width=True, hide_index=True)

    if st.button("⚡ Analizar Balance y Salud Ahora", use_container_width=True):
        filas = df_editado.dropna(subset=["Ticker"])
        total_cartera = float(filas["Valor_USD"].sum()) if not filas.empty else 0.0

        if total_cartera <= 0:
            st.warning("Ingresa al menos un ticker con valor mayor a $0.")
        else:
            resultados = []
            barra = st.progress(0)
            for i, row in filas.iterrows():
                sym = str(row["Ticker"]).strip().upper()
                val = float(row["Valor_USD"])
                if sym:
                    res = analizar_ticker(sym)
                    if res:
                        peso = (val / total_cartera) * 100
                        res["Valor ($)"] = round(val, 2)
                        res["Peso (%)"] = round(peso, 1)
                        resultados.append(res)
                barra.progress(min((i + 1) / len(filas), 1.0))
            barra.empty()

            if resultados:
                df_res = pd.DataFrame(resultados)

                score_pond = sum(r["Score"] * (r["Peso (%)"] / 100) for r in resultados)
                pct_fuerte = sum(r["Peso (%)"] for r in resultados if r["Score"] == 85)

                m1, m2, m3 = st.columns(3)
                m1.metric("Capital Total", f"${total_cartera:,.2f}")
                m2.metric("Score Cartera", f"{score_pond:.0f} / 100")
                m3.metric("En Fase 2 🟢", f"{pct_fuerte:.1f}%")

                st.markdown("### 🧠 Diagnóstico Rápido de Balance")

                concentradas = [f"**{r['Ticker']}** ({r['Peso (%)']}%)" for r in resultados if r["Peso (%)"] > 25]
                if concentradas:
                    st.warning(f"⚠️ **Sobreconcentración (>25%):** {', '.join(concentradas)}.")
                else:
                    st.success("✅ **Pesos Balanceados:** Ninguna posición supera el 25% de la cartera.")

                rotas = [f"**{r['Ticker']}** (Stop: {r['Stop_Loss']} USD)" for r in resultados if r["Score"] == 25]
                alertas = [f"**{r['Ticker']}** (Debajo de EMA50: {r['EMA50']} USD)" for r in resultados if r["Score"] == 60]
                if rotas:
                    st.error(f"🚨 **Tendencia Rota (Score 25 🔴 — Limpiar):** {', '.join(rotas)}.")
                if alertas:
                    st.info(f"🟡 **En Observación (Score 60):** {', '.join(alertas)}.")

                cerca_s1 = [f"**{r['Ticker']}** (S1: {r['S1']} USD)" for r in resultados if r["Dist_S1_%"] <= 3.5 and r["Score"] >= 60]
                cerca_r1 = [f"**{r['Ticker']}** (R1: {r['R1']} USD)" for r in resultados if r["Dist_R1_%"] <= 3.5]
                if cerca_s1:
                    st.success(f"🎯 **En Zona de Compra (<3.5% de S1):** {', '.join(cerca_s1)}.")
                if cerca_r1:
                    st.success(f"💰 **En Zona de Cosecha (<3.5% de R1):** {', '.join(cerca_r1)}.")

                st.markdown("### 📊 Tabla Operativa")
                st.dataframe(
                    df_res[["Ticker", "Peso (%)", "Valor ($)", "Precio", "Score", "Estado", "EMA50", "EMA200", "S1", "R1", "Stop_Loss"]],
                    use_container_width=True,
                    hide_index=True
                )
