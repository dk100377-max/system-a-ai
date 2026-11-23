import streamlit as st
import requests

st.set_page_config(page_title="系統 A - AI 交易決策", layout="centered")

# 強制開啟深色模式並自訂 CSS
st.markdown("""
<style>
    /* 強制深色背景 */
    .stApp { background-color: #0e1117; color: #fafafa; }
    .signal-box { text-align: center; padding: 20px; border-radius: 10px; margin: 20px 0; }
    .sell-signal { background-color: rgba(255, 75, 75, 0.1); color: #ff4b4b; border: 1px solid #ff4b4b; }
    .buy-signal { background-color: rgba(0, 204, 150, 0.1); color: #00cc96; border: 1px solid #00cc96; }
    .signal-text { font-size: 40px; font-weight: bold; margin: 0; }
    .price-row { display: flex; justify-content: space-between; text-align: center; margin-top: 20px; }
    .price-col { flex: 1; padding: 10px; border-radius: 5px; margin: 0 5px; }
    .sl-col { background-color: rgba(255, 75, 75, 0.2); border-top: 3px solid #ff4b4b; }
    .tp-col { background-color: rgba(0, 204, 150, 0.2); border-top: 3px solid #00cc96; }
    .entry-col { background-color: rgba(56, 123, 255, 0.2); border-top: 3px solid #387bff; }
    .label { font-size: 14px; color: #aaa; margin-bottom: 5px; }
    .value { font-size: 22px; font-weight: bold; color: #ffffff; }
    /* 強制文字白色 */
    h1, h2, h3, p, div { color: #fafafa !important; }
</style>
""", unsafe_allow_html=True)

# 頂部：時間週期與按鈕
col1, col2 = st.columns([2, 1])
with col1:
    timeframe = st.selectbox("Chart Timeframe", ["1-Min", "15-Min", "1-Hour", "4-Hour"])
with col2:
    st.markdown("<br>", unsafe_allow_html=True)
    analyze_btn = st.button("Analyze Chart", use_container_width=True, type="primary")

st.divider()

# 抓取當前價格 (加入 Headers 防止被幣安阻擋)
@st.cache_data(ttl=60)
def get_price(symbol="BTCUSDT"):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        res = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", headers=headers, timeout=5)
        return float(res.json()["price"])
    except Exception as e:
        return 69000.0 # 如果抓不到，先用預設值防崩潰

current_price = get_price()

# 系統 A 邏輯 (先模擬做空)
is_sell = True 
sl_price = current_price * 1.015 # 止損放上方 1.5%
tp1_price = current_price * 0.985 # TP1 在下方 1.5%
tp2_price = current_price * 0.975 # TP2 在下方 2.5%

st.markdown("### Pattern Analysis")
st.markdown("🟢 **Neutral Market** | 🟡 **1-Min Timeframe**")

# 顯示當前價格與信號
sig_col1, sig_col2 = st.columns(2)
with sig_col1:
    st.markdown("**Current Price**")
    st.markdown(f"<h2 style='margin-top:0;'>{current_price:.2f}</h2>", unsafe_allow_html=True)
with sig_col2:
    if is_sell:
        st.markdown("<div class='signal-box sell-signal'><p class='label'>Sell Signal (Entry)</p><h2 class='signal-text'>SELL</h2><p class='label'>Enter short position at current price</p></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='signal-box buy-signal'><p class='label'>Buy Signal (Entry)</p><h2 class='signal-text'>BUY</h2><p class='label'>Enter long position at current price</p></div>", unsafe_allow_html=True)

# 顯示風控與目標
st.markdown("### Risk Management")
st.markdown("**Scalp Trading: SHORT Position**")

st.markdown(f"""
<div class='price-row'>
    <div class='price-col sl-col'>
        <div class='label'>Stop Loss</div>
        <div class='value'>{sl_price:.2f}</div>
        <div class='label'>1.5%</div>
    </div>
    <div class='price-col entry-col'>
        <div class='label'>Entry</div>
        <div class='value'>{current_price:.2f}</div>
        <div class='label'>Now</div>
    </div>
    <div class='price-col tp-col'>
        <div class='label'>Take Profit 1</div>
        <div class='value'>{tp1_price:.2f}</div>
        <div class='label'>1.5%</div>
    </div>
    <div class='price-col tp-col'>
        <div class='label'>Take Profit 2</div>
        <div class='value'>{tp2_price:.2f}</div>
        <div class='label'>2.5%</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")
st.markdown("💡 **系統 A 交易建議**")
st.markdown("* 等待 15m FVG 回踩並出現確認 K 線")
st.markdown("* 嚴格執行 1:2 與 1:4 盈虧比")
st.markdown("* 本金 50U，單筆風險 1% (0.5U)")
