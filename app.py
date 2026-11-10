import time
import pandas as pd
import streamlit as st
import yfinance as yf

# Page Configuration
st.set_page_config(
    page_title="Live Trading Assistant", page_icon="📈", layout="wide"
)

st.title("🚀 Advanced Live Trading Monitor, Chart & Signals")
st.markdown(
    "Real-time tracking for Indian Stocks & Nifty with RSI, SMA, MACD, Volume,"
    " Candle Warnings, and Stop-Loss/Target."
)

# Sidebar for settings
st.sidebar.header("Settings")
user_input = st.sidebar.text_input(
    "Enter Stock Name (e.g., Nifty, Bank Nifty, Reliance, TCS)", "Nifty"
)


# Smart Symbol Mapper
def get_yahoo_ticker(query):
  q = query.strip().upper()
  mapping = {
      "NIFTY": "^NSEI",
      "NIFTY50": "^NSEI",
      "BANKNIFTY": "^NSEBANK",
      "BANK NIFTY": "^NSEBANK",
      "SENSEX": "^BSESN",
  }
  if q in mapping:
    return mapping[q]
  if "-" in q or "^" in q or ".NS" in q:
    return q
  return q + ".NS"


ticker_symbol = get_yahoo_ticker(user_input)

timeframe = st.sidebar.selectbox(
    "Select Timeframe", ["1m", "5m", "15m", "1h", "1d"]
)
refresh_rate = st.sidebar.slider(
    "Auto-Refresh Interval (seconds)", min_value=5, max_value=60, value=10
)

# Risk Management Settings in Sidebar
st.sidebar.markdown("---")
st.sidebar.header("🛡️ Risk Management")
risk_percent = (
    st.sidebar.slider(
        "Stop-Loss Risk Percentage (%)", min_value=0.5, max_value=3.0, value=1.0
    )
    / 100
)
reward_ratio = st.sidebar.slider(
    "Risk-to-Reward Ratio", min_value=1.5, max_value=3.0, value=2.0
)


# Function to fetch live data
def get_market_data(symbol, period="1d", interval="1m"):
  try:
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if not df.empty:
      if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
      return df
  except Exception as e:
    st.error(f"Error fetching data: {e}")
  return None


# Helper function to check Hammer / Shooting Star Patterns
def check_candle_patterns(row):
  body = abs(row["Close"] - row["Open"])
  total_range = row["High"] - row["Low"]
  if total_range == 0:
    return "NONE"

  lower_wick = min(row["Close"], row["Open"]) - row["Low"]
  upper_wick = row["High"] - max(row["Close"], row["Open"])

  if (
      lower_wick > (2 * body)
      and upper_wick < (0.5 * body)
      and body < (0.3 * total_range)
  ):
    return "HAMMER"

  if (
      upper_wick > (2 * body)
      and lower_wick < (0.5 * body)
      and body < (0.3 * total_range)
  ):
    return "SHOOTING_STAR"

  return "NONE"


# Main Dashboard Area
placeholder = st.empty()

if st.sidebar.button("Start Live Monitoring"):
  st.session_state["monitoring"] = True

if st.sidebar.button("Stop Monitoring"):
  st.session_state["monitoring"] = False

if "monitoring" not in st.session_state:
  st.session_state["monitoring"] = False

# Display logic
if st.session_state["monitoring"]:
  while st.session_state["monitoring"]:
    with placeholder.container():
      st.subheader(
          f"📊 Live Data for: {user_input.upper()} (Ticker: {ticker_symbol})"
      )
      df = get_market_data(ticker_symbol, period="1d", interval=timeframe)

      if df is not None and len(df) > 26:
        # Technical Indicators Calculation
        df["SMA_9"] = df["Close"].rolling(window=9).mean()
        df["SMA_21"] = df["Close"].rolling(window=21).mean()

        # RSI Calculation
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df["RSI"] = 100 - (100 / (1 + rs))

        # MACD Calculation (NEW!)
        exp1 = df["Close"].ewm(span=12, adjust=False).mean()
        exp2 = df["Close"].ewm(span=26, adjust=False).mean()
        df["MACD"] = exp1 - exp2
        df["Signal_Line"] = df["MACD"].ewm(span=9, adjust=False).mean()

        latest = df.iloc[-1]
        prev = df.iloc[-2]
        pattern = check_candle_patterns(latest)
        current_price = latest["Close"]

        # 1. Metrics Cards (Price, RSI, SMA 9, SMA 21)
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "Current Price",
            f"₹{current_price:,.2f}",
            f"₹{current_price - prev['Close']:,.2f}",
        )
        col2.metric("RSI (14)", f"{latest['RSI']:.2f}")
        col3.metric("SMA 9", f"₹{latest['SMA_9']:,.2f}")
        col4.metric("SMA 21", f"₹{latest['SMA_21']:,.2f}")

        # 💡 Automatically compare SMA 9 and SMA 21
        st.markdown("---")
        if latest["SMA_9"] > latest["SMA_21"]:
          st.success(
              "🟢 **SMA Status:** **SMA 9 ఎక్కువగా ఉంది (బలంగా ఉంది)!** మార్కెట్"
              " పైకి వెళ్లే జోరులో ఉంది."
          )
        else:
          st.error(
              "🔴 **SMA Status:** **SMA 21 కన్నా SMA 9 తక్కువగా ఉంది (బలహీనంగా"
              " ఉంది)!** మార్కెట్ కొద్దిగా డీలా పడింది."
          )

        # 2. Stop-Loss & Target Calculator Section
        st.markdown("### 🛡️ Stop-Loss & Target Calculator (Recommended Levels)")
        buy_stop_loss = current_price * (1 - risk_percent)
        buy_target = current_price + (
            (current_price - buy_stop_loss) * reward_ratio
        )

        sell_stop_loss = current_price * (1 + risk_percent)
        sell_target = current_price - (
            (sell_stop_loss - current_price) * reward_ratio
        )

        calc_col1, calc_col2 = st.columns(2)
        with calc_col1:
          st.info(
              "📈 **Buy (Long) Setup:**\n"
              f"• **Suggested Stop-Loss:** `₹{buy_stop_loss:,.2f}` (-"
              f"{risk_percent*100}%)\n"
              f"• **Suggested Target:** `₹{buy_target:,.2f}`"
          )
        with calc_col2:
          st.warning(
              "📉 **Sell (Short) Setup:**\n"
              f"• **Suggested Stop-Loss:** `₹{sell_stop_loss:,.2f}` (+"
              f"{risk_percent*100}%)\n"
              f"• **Suggested Target:** `₹{sell_target:,.2f}`"
          )

        # 3. Warnings & Buy/Sell Signals Section (Including MACD confirmation)
        st.markdown("### 🔔 Live Trade Signals & Candle Warnings")

        if pattern == "HAMMER":
          st.warning(
              "🔨 **CANDLE WARNING (HAMMER):** Potential bullish reversal"
              " detected! Price might go up."
          )
        elif pattern == "SHOOTING_STAR":
          st.error(
              "⚠️ **DANGEROUS CANDLE WARNING (SHOOTING STAR):** Potential"
              " bearish reversal! High chance price might drop."
          )

        # Enhanced Signal Logic with MACD
        if (
            latest["RSI"] < 30
            and latest["Close"] > latest["SMA_9"]
            and latest["MACD"] > latest["Signal_Line"]
        ):
          st.success(
              "🟢 **STRONG BUY SIGNAL:** Oversold RSI + Bullish SMA/MACD"
              " crossover!"
          )
        elif (
            latest["RSI"] > 70
            and latest["Close"] < latest["SMA_9"]
            and latest["MACD"] < latest["Signal_Line"]
        ):
          st.error(
              "🔴 **STRONG SELL SIGNAL:** Overbought RSI + Bearish SMA/MACD"
              " crossover!"
          )
        else:
            st.info(
                "⚪ **HOLD / NEUTRAL:** Market is consolidating. Wait for clear"
                " breakout."
            )

        # 4. Live Stock Market Chart
        st.markdown("### 📉 Live Price & Moving Average Chart")
        st.line_chart(df[["Close", "SMA_9", "SMA_21"]])

      else:
        st.warning("Fetching data... please check the symbol or market hours.")

      time.sleep(refresh_rate)
      st.rerun()
else:
  st.info(
      "Enter **Nifty** या **Reliance** in the sidebar and click **'Start Live"
      " Monitoring'**."
  )
