import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="系統 A - 頂尖決策中心", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    h1, h2, h3, p, span { color: #fafafa !important; }
    .bull-box { background-color: rgba(0, 204, 150, 0.1); border-left: 4px solid #00cc96; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .bear-box { background-color: rgba(255, 75, 75, 0.1); border-left: 4px solid #ff4b4b; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .risk-box { background-color: rgba(56, 123, 255, 0.1); border-left: 4px solid #387bff; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .final-box { background-color: rgba(255, 255, 255, 0.1); border: 2px solid #fafafa; padding: 20px; margin: 20px 0; border-radius: 10px; text-align: center; }
    .price-row { display: flex; justify-content: space-between; text-align: center; margin-top: 20px; }
    .price-col { flex: 1; padding: 10px; border-radius: 5px; margin: 0 5px; }
    .sl-col { background-color: rgba(255, 75, 75, 0.2); border-top: 3px solid #ff4b4b; }
    .tp-col { background-color: rgba(0, 204, 150, 0.2); border-top: 3px solid #00cc96; }
    .entry-col { background-color: rgba(56, 123, 255, 0.2); border-top: 3px solid #387bff; }
    .label { font-size: 14px; color: #aaa; margin-bottom: 5px; }
    .value { font-size: 22px; font-weight: bold; color: #ffffff; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 系統 A：多空交易員 vs 風控經理")

@st.cache_data(ttl=60)
def fetch_data_okx(symbol, bar, limit):
    try:
        url = f"https://www.okx.com/api/v5/market/candles?instId={symbol}&bar={bar}&limit={limit}"
        res = requests.get(url, timeout=10)
        data = res.json()
        if data['code'] != '0' or not data['data']: return pd.DataFrame()
        df = pd.DataFrame(data['data'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
        df = df.iloc[::-1].reset_index(drop=True)
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        return df
    except:
        return pd.DataFrame()

df_4h = fetch_data_okx("BTC-USDT", "4H", 50)
df_15m = fetch_data_okx("BTC-USDT", "15m", 100)

if not df_4h.empty and not df_15m.empty:
    # 計算指標
    df_4h['EMA_20'] = df_4h['close'].ewm(span=20, adjust=False).mean()
    current_price = df_15m['close'].iloc[-1]
    ema_4h = df_4h['EMA_20'].iloc[-1]
    
    recent_high = df_15m['high'].rolling(window=20).max().iloc[-1]
    recent_low = df_15m['low'].rolling(window=20).min().iloc[-1]
    volatility = (recent_high - recent_low) / recent_low * 100

    # 尋找最近的 FVG (掃描最後 30 根 15m K 線)
    def find_fvg(df, is_bullish=True):
        if is_bullish:
            for i in range(len(df)-3, 0, -1):
                if df['high'].iloc[i-2] < df['low'].iloc[i]:
                    if df['low'].iloc[i-1:].min() > df['high'].iloc[i-2]:
                        return df['high'].iloc[i-2], df['low'].iloc[i]
        else:
            for i in range(len(df)-3, 0, -1):
                if df['low'].iloc[i-2] > df['high'].iloc[i]:
                    if df['high'].iloc[i-1:].max() < df['low'].iloc[i-2]:
                        return df['high'].iloc[i], df['low'].iloc[i-2]
        return None, None

    bull_fvg_low, bull_fvg_high = find_fvg(df_15m, True)
    bear_fvg_high, bear_fvg_low = find_fvg(df_15m, False)

    st.markdown(f"### 📊 實時數據 (BTC/USDT) | 現價: `${current_price:.2f}`")

    # 多頭對話
    st.markdown("<div class='bull-box'><h4>🐂 多頭頂尖交易員：</h4>", unsafe_allow_html=True)
    if current_price > ema_4h:
        if bull_fvg_low:
            st.write(f"4H 趨勢偏多。我發現下方有一個看漲 FVG ({bull_fvg_low:.2f} - {bull_fvg_high:.2f})，如果回踩到這裡，絕對是做多良機。")
        else:
            st.write("4H 趨勢偏多，但目前沒有找到未回補的看漲 FVG，我會繼續等待。")
    else:
        st.write("大趨勢偏空。我暫時不進場，除非 15m 跌破前低又迅速收回，我才會考慮搶反彈。")
    st.markdown("</div>", unsafe_allow_html=True)

    # 空頭對話
    st.markdown("<div class='bear-box'><h4>🐻 空頭頂尖交易員：</h4>", unsafe_allow_html=True)
    if current_price < ema_4h:
        if bear_fvg_low:
            st.write(f"價格在 4H EMA 下方，空頭主導。上方有一個看跌 FVG ({bear_fvg_low:.2f} - {bear_fvg_high:.2f})，反彈到這裡我就空。")
        else:
            st.write("價格在 4H EMA 下方，但上方沒有發現有效的看跌 FVG 缺口，目前不適合追空。")
    else:
        st.write("價格還在均線上方，我暫時觀望。如果 15m 出現明顯的假突破，我會嘗試抓頂部。")
    st.markdown("</div>", unsafe_allow_html=True)

    # 風控經理
    st.markdown("<div class='risk-box'><h4>🛡️ 風控經理 (最高決策者)：</h4>", unsafe_allow_html=True)
    
    decision = "觀望等待"
    status_color = "gray"
    trade_setup = None

    if volatility > 3.0:
        st.write("⚠️ 當前波動率過大，市場處於極端洗盤狀態。強制觀望！")
    elif abs(current_price - ema_4h) / ema_4h < 0.005:
        st.write("⚠️ 價格緊貼 4H 20 EMA，看不出方向。觀望，等方向明確！")
    else:
        if current_price > ema_4h and bull_fvg_low:
            st.write("✅ 批准多頭計畫。請等待回踩 FVG 區間。")
            decision = "準備做多"
            status_color = "green"
            trade_setup = "bull"
        elif current_price < ema_4h and bear_fvg_low:
            st.write("✅ 批准空頭計畫。請等待反彈 FVG 區間。")
            decision = "準備做空"
            status_color = "red"
            trade_setup = "bear"
        else:
            st.write("⚠️ 當前趨勢明確，但沒有找到有效的 FVG 進場點。強制觀望，絕不追高殺低。")
    
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='final-box'><h2 style='color:{status_color} !important;'>最終決策：{decision}</h2></div>", unsafe_allow_html=True)

    # 如果風控批准，顯示精準點位
    if trade_setup:
        st.markdown("### 🎯 交易員狙擊計畫")
        if trade_setup == "bull":
            entry_price = (bull_fvg_low + bull_fvg_high) / 2
            sl_price = bull_fvg_low * 0.995
            risk = entry_price - sl_price
            tp1 = entry_price + risk * 2
            tp2 = entry_price + risk * 4
            
            st.markdown(f"""
            <div class='price-row'>
                <div class='price-col sl-col'><div class='label'>Stop Loss</div><div class='value'>{sl_price:.2f}</div></div>
                <div class='price-col entry-col'><div class='label'>Entry (FVG 50%)</div><div class='value'>{entry_price:.2f}</div></div>
                <div class='price-col tp-col'><div class='label'>Take Profit 1</div><div class='value'>{tp1:.2f}</div></div>
                <div class='price-col tp-col'><div class='label'>Take Profit 2</div><div class='value'>{tp2:.2f}</div></div>
            </div>
            """, unsafe_allow_html=True)

        elif trade_setup == "bear":
            entry_price = (bear_fvg_low + bear_fvg_high) / 2
            sl_price = bear_fvg_high * 1.005
            risk = sl_price - entry_price
            tp1 = entry_price - risk * 2
            tp2 = entry_price - risk * 4
            
            st.markdown(f"""
            <div class='price-row'>
                <div class='price-col sl-col'><div class='label'>Stop Loss</div><div class='value'>{sl_price:.2f}</div></div>
                <div class='price-col entry-col'><div class='label'>Entry (FVG 50%)</div><div class='value'>{entry_price:.2f}</div></div>
                <div class='price-col tp-col'><div class='label'>Take Profit 1</div><div class='value'>{tp1:.2f}</div></div>
                <div class='price-col tp-col'><div class='label'>Take Profit 2</div><div class='value'>{tp2:.2f}</div></div>
            </div>
            """, unsafe_allow_html=True)

    with st.expander("🔍 查看底層 K 線數據"):
        st.dataframe(df_15m.tail(10), use_container_width=True)
