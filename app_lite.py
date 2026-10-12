import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai

# 1. CONFIGURACIÓN ULTRALIGERA PARA MÓVIL
st.set_page_config(
    page_title="GEM Lite Mobile",
    page_icon="🎯",
    layout="centered",
    initial_sidebar_state="collapsed"
)

API_KEY = (
    st.secrets.get("GEMINI_API_KEY")
    or st.secrets.get("GOOGLE_API_KEY")
    or st.secrets.get("API_KEY")
    or ""
).strip()

if API_KEY:
    genai.configure(api_key=API_KEY)

st.title("🎯 GEM Scanner Lite")
st.caption("Versión Móvil Ultraligera · Radar & Balance de Cartera")

# 2. MOTOR MATEMÁTICO CACHEADO (5 min)
@st.cache_data(ttl=300)
def analizar_ticker(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        df = t.history(period="1y")
        if df.empty or len(df) < 50:
            return None

        close = df["Close"]
        precio = float(close.iloc[-1])
        ema50 = float(close.ewm(span=50, adjust=False).mean().iloc[-1])
        ema200 = float(close.ewm(span=200, adjust=False).mean().iloc[-1]) if len(df) >= 200 else ema50

        ventana = df.tail(20)
        high_20 = float(ventana["High"].max())
        low_20 = float(ventana["Low"].min())
        pivot = (high_20 + low_20 + precio) / 3.0

        r1 = (2 * pivot) - low_20
        s1 = (2 * pivot) - high_20
        r2 = pivot + (high_20 - low_20)
        s2 = pivot - (high_20 - low_20)

        if precio > ema50 and precio > ema200:
            score = 85
            estado = "Fuerte 🟢"
        elif precio > ema200 and precio <= ema50:
            score = 60
            estado = "Alerta 🟡"
        elif precio <= ema200 and precio > ema50:
            score = 40
            estado = "Recuperando 🟠"
        else:
            score = 25
            estado = "Rota 🔴"

        dist_s1 = ((precio - s1) / precio) * 100
        dist_r1 = ((r1 - precio) / precio) * 100
        stop_loss = round(min(s1, ema200) * 0.98, 2)

        return {
            "Ticker": ticker_symbol.upper(),
            "Precio": round(precio, 2),
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

def consultar_comite_ia(d):
    if not API_KEY:
        return "⚠️ No se detectó GEMINI_API_KEY en los Secrets de Streamlit."
    prompt = f"""
    Actúa como el Comité Financiero GEM (Minervini, Tudor Jones, Livermore).
    Evalúa {d['Ticker']} en formato corto para celular (máximo 4 puntos breves, usa USD en vez del signo de dólar para evitar formato LaTeX):
    - Precio Actual: {d['Precio']} USD | Score GEM: {d['Score']} ({d['Estado']})
    - EMA 50: {d['EMA50']} USD | EMA 200: {d['EMA200']} USD
    - Soportes: S1 {d['S1']} USD / S2 {d['S2']} USD | Resistencias: R1 {d['R1']} USD / R2 {d['R2']} USD
    Indica: 1) Veredicto directo (Comprar, Esperar o Vender), 2) Fase técnica, 3) Nivel exacto de entrada o cosecha, 4) Stop Loss matemático ({d['Stop_Loss']} USD).
    """
    # Priorizamos gemini-3.8-flash y dejamos respaldo dinámico
    modelos = ["gemini-3.8-flash", "gemini-3.0-flash", "gemini-2.5-pro", "gemini-pro"]
    ultimo_error = ""
    for nombre_modelo in modelos:
        try:
            model = genai.GenerativeModel(nombre_modelo)
            resp = model.generate_content(prompt)
            return resp.text.replace("$", "USD ")
        except Exception as e:
            ultimo_error = str(e)
            continue

    # Si ninguno de la lista fija coincide, busca automáticamente el primer modelo flash disponible en tu cuenta
    try:
        for m in genai.list_models():
            if "generateContent" in m.supported_generation_methods and "flash" in m.name:
                model = genai.GenerativeModel(m.name)
                resp = model.generate_content(prompt)
                return resp.text.replace("$", "USD ")
    except Exception:
        pass

    return f"Error al conectar con IA: {ultimo_error}"

# 3. INTERFAZ DE DOS PESTAÑAS LIGERAS
tab1, tab2 = st.tabs(["🏛️ Radar Francotirador", "📋 Mini-Auditor & Balance"])

with tab1:
    st.subheader("Escáner Individual Instantáneo")
    ticker_input = st.text_input("Ticker a evaluar:", value="COHR").upper().strip()

    if ticker_input:
        with st.spinner(f"Escaneando {ticker_input}..."):
            datos = analizar_ticker(ticker_input)

        if datos:
            c1, c2 = st.columns(2)
            c1.metric("Precio Actual", f"${datos['Precio']}")
            c2.metric("Score GEM", f"{datos['Score']} ({datos['Estado']})")

            # Formato limpio con USD para evitar que Streamlit active LaTeX y ponga asteriscos
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

with tab2:
    st.subheader("Auditor de Balance y Salud de Cartera")
    preset = st.radio(
        "Elige plantilla rápida (puedes editar montos y agregar filas abajo):",
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
                    st.warning(f"⚠️ **Sobreconcentración (>25%):** {', '.join(concentradas)}. Reduce tamaño en rebotes para no depender de una sola acción.")
                else:
                    st.success("✅ **Pesos Balanceados:** Ninguna posición supera el 25% de la cartera.")

                rotas = [f"**{r['Ticker']}** (Stop: {r['Stop_Loss']} USD)" for r in resultados if r["Score"] == 25]
                alertas = [f"**{r['Ticker']}** (Debajo de EMA50: {r['EMA50']} USD)" for r in resultados if r["Score"] == 60]
                if rotas:
                    st.error(f"🚨 **Tendencia Rota (Score 25 🔴 — Limpiar):** {', '.join(rotas)}.")
                if alertas:
                    st.info(f"🟡 **En Observación (Score 60 — Esperar rebote a EMA50 o vigilar S1):** {', '.join(alertas)}.")

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
