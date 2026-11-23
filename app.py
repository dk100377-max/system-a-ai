import streamlit as st
import requests
import pandas as pd
import numpy as np

st.set_page_config(page_title="系統 A - 頂尖決策中心", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #fafafa; }
    h1, h2, h3, p, div { color: #fafafa !important; }
    .bull-box { background-color: rgba(0, 204, 150, 0.1); border-left: 4px solid #00cc96; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .bear-box { background-color: rgba(255, 75, 75, 0.1); border-left: 4px solid #ff4b4b; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .risk-box { background-color: rgba(56, 123, 255, 0.1); border-left: 4px solid #387bff; padding: 15px; margin: 10px 0; border-radius: 5px; }
    .final-box { background-color: rgba(255, 255, 255, 0.1); border: 2px solid #fafafa; padding: 20px; margin: 20px 0; border-radius: 10px; text-align: center; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 系統 A：多空交易員 vs 風控經理")

# 用最穩定、無依賴的方式抓取幣安 K 線
@st.cache_data(ttl=60)
def fetch_data(symbol, interval, limit):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
        res = requests.get(url, timeout=10)
        data = res.json()
        
        # 處理返回的數據格式
        df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base', 'taker_buy_quote', 'ignore'])
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        # 轉換格式
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df['open'] = df['open'].astype(float)
        df['high'] = df['high'].astype(float)
        df['low'] = df['low'].astype(float)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        return df
    except Exception as e:
        return pd.DataFrame()

# 獲取 4H 和 15m 數據
df_4h = fetch_data("BTCUSDT", "4h", 50)
df_15m = fetch_data("BTCUSDT", "15m", 100)

if not df_4h.empty and not df_15m.empty:
    # 計算指標：4H 的 20 EMA (判斷大趨勢)
    df_4h['EMA_20'] = df_4h['close'].ewm(span=20, adjust=False).mean()
    current_price = df_15m['close'].iloc[-1]
    ema_4h = df_4h['EMA_20'].iloc[-1]
    
    # 簡單波動率計算 (用近 20 根 15m K 線的高低差)
    recent_high = df_15m['high'].rolling(window=20).max().iloc[-1]
    recent_low = df_15m['low'].rolling(window=20).min().iloc[-1]
    volatility = (recent_high - recent_low) / recent_low * 100

    st.markdown(f"### 📊 實時數據 (BTC/USDT) | 現價: `${current_price:.2f}`")

    # 角色 1：多頭頂尖交易員
    st.markdown("<div class='bull-box'><h4>🐂 多頭頂尖交易員：</h4>", unsafe_allow_html=True)
    if current_price > ema_4h:
        bull_opinion = f"4H 價格在 20 EMA 上方 ({ema_4h:.2f})，大趨勢偏多。如果 15m 回踩出現看漲 FVG 或掃蕩前低，我認為是做多良機，目標看向近期高點。"
    else:
        bull_opinion = f"目前價格低於 4H 20 EMA ({ema_4h:.2f})，大趨勢對多頭不利。但我會觀察 15m 是否出現極端洗盤（假跌破），如果跌不下去，我會嘗試搶反彈。"
    st.write(bull_opinion)
    st.markdown("</div>", unsafe_allow_html=True)

    # 角色 2：空頭頂尖交易員
    st.markdown("<div class='bear-box'><h4>🐻 空頭頂尖交易員：</h4>", unsafe_allow_html=True)
    if current_price < ema_4h:
        bear_opinion = f"價格跌破 4H 20 EMA ({ema_4h:.2f})，空頭掌握主導權。反彈無力就是進場機會，我會在 15m 尋找看跌 FVG 或假突破做空。"
    else:
        bear_opinion = f"價格在 4H 20 EMA 上方 ({ema_4h:.2f})，但近期波動極大。若 15m 出現明顯的結構破壞 (CHoCH)，我會嘗試抓頂部做空。"
    st.write(bear_opinion)
    st.markdown("</div>", unsafe_allow_html=True)

    # 角色 3：風控經理 (最高指揮官)
    st.markdown("<div class='risk-box'><h4>🛡️ 風控經理 (最高決策者)：</h4>", unsafe_allow_html=True)
    
    # 風控邏輯：波動率過大或趨勢不明顯時，一票否決
    if volatility > 3.0:
        final_decision = "⚠️ 當前波動率過大 (近期高低差超過 3%)，市場處於極端洗盤狀態，容易多空雙殺。我行使一票否決權：『強制觀望，不准交易』。"
        status_color = "gray"
    elif abs(current_price - ema_4h) / ema_4h < 0.005:
        final_decision = "⚠️ 價格緊貼 4H 20 EMA，市場處於無趨勢震盪狀態。看不出方向，我行使一票否決權：『觀望，等方向明確』。"
        status_color = "gray"
    else:
        if current_price > ema_4h:
            final_decision = "✅ 多頭趨勢明確且波動在可控範圍，批准多頭交易員的計畫。請等待 15m 回踩信號。"
            status_color = "green"
        else:
            final_decision = "✅ 空頭趨勢明確且波動在可控範圍，批准空頭交易員的計畫。請等待 15m 反彈信號。"
            status_color = "red"

    st.write(final_decision)
    st.markdown("</div>", unsafe_allow_html=True)

    # 最終結論
    st.markdown(f"<div class='final-box'><h2 style='color:{status_color} !important;'>最終決策：{'觀望等待' if status_color == 'gray' else ('準備做多' if status_color == 'green' else '準備做空')}</h2></div>", unsafe_allow_html=True)

    # 顯示原始數據
    with st.expander("🔍 查看底層 K 線數據"):
        st.write("**4H K線 (最後 5 根)**")
        st.dataframe(df_4h.tail(5), use_container_width=True)
        st.write("**15m K線 (最後 5 根)**")
        st.dataframe(df_15m.tail(5), use_container_width=True)

else:
    st.error("數據抓取失敗，可能是幣安伺服器在維護，請稍後重新整理網頁。")
