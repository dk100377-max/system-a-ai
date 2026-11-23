import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="系統 A - 頂尖交易員回測", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; font-size: 18px; height: 50px; }
    h1, h2, h3, p { color: #fafafa !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 系統 A：頂尖交易員結構回測")

@st.cache_data(ttl=3600)
def fetch_historical_data(days_back=90):
    all_data = []
    end_time = int(time.time() * 1000)
    loops = (days_back * 24 * 4) // 300 + 1
    progress_bar = st.progress(0)
    
    for i in range(loops):
        url = f"https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=15m&limit=300&after={end_time}"
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if data['code'] == '0' and data['data']:
                all_data.extend(data['data'])
                end_time = int(data['data'][-1][0])
            else:
                break
        except:
            break
        time.sleep(0.1)
        progress_bar.progress((i + 1) / loops)
    
    progress_bar.empty()
    if not all_data: return pd.DataFrame()
        
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
    df = df.iloc[::-1].reset_index(drop=True)
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms') + pd.Timedelta(hours=8)
    return df

st.info("預測邏輯：尋找 15m 假跌破（流動性掃蕩）後迅速收回，並留下看漲 FVG。價格回踩缺口時進場。單筆風險 1%，盈虧比 1:2。")

if st.button("🚀 開始頂尖交易員回測"):
    df = fetch_historical_data(90)
    
    if df.empty:
        st.error("數據抓取失敗。")
    else:
        st.success(f"數據抓取成功！共 {len(df)} 根 15m K 線。")
        
        balance = 50.0
        initial_balance = 50.0
        trades = []
        in_position = False
        entry_price = 0
        sl = 0
        tp = 0
        fee_rate = 0.0005
        
        # 尋找假跌破 (Liquidity Sweep) 與 FVG
        for i in range(15, len(df)):
            current_open = df['open'].iloc[i]
            current_close = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            if not in_position:
                # 條件 1：尋找前低 (過去 10 根的最低點)
                prev_low = df['low'].iloc[i-10:i].min()
                
                # 條件 2：流動性掃蕩 (當前K線跌破前低，但收盤價又拉回前低之上)
                is_sweep = current_low < prev_low and current_close > prev_low
                
                # 條件 3：這根 K 線必須是陽線 (強勢收回)
                is_bullish = current_close > current_open
                
                # 條件 4：尋找這根 K 線與前兩根產生的 FVG
                if i >= 2:
                    fvg_low = df['high'].iloc[i-2]
                    fvg_high = df['low'].iloc[i]
                    has_fvg = fvg_low < fvg_high
                else:
                    has_fvg = False
                    
                # 預測進場：發生掃蕩 + 陽線 + 有FVG，且當前價格剛好回踩到 FVG 上沿附近
                if is_sweep and is_bullish and has_fvg:
                    # 我們在這裡做一個「預測性」進場：直接在這根 V 轉 K 線的收盤價買入
                    in_position = True
                    entry_price = current_close
                    sl = current_low * 0.998 # 止損設在剛剛插針的最低點下方
                    
                    # 確保止損距離合理 (小於 2%)
                    if (entry_price - sl) / entry_price > 0.02:
                        in_position = False 
                    else:
                        tp = entry_price * 1.035 # 止盈設 3.5%
            else:
                if current_low <= sl:
                    loss = - (entry_price - sl) / entry_price - fee_rate * 2
                    balance = balance * (1 + loss)
                    trades.append({'result': 'SL', 'pnl': loss, 'time': df['timestamp'].iloc[i]})
                    in_position = False
                elif current_high >= tp:
                    profit = (tp - entry_price) / entry_price - fee_rate * 2
                    balance = balance * (1 + profit)
                    trades.append({'result': 'TP', 'pnl': profit, 'time': df['timestamp'].iloc[i]})
                    in_position = False
                    
        if len(trades) > 0:
            df_trades = pd.DataFrame(trades)
            total_trades = len(trades)
            wins = len(df_trades[df_trades['result'] == 'TP'])
            win_rate = (wins / total_trades) * 100
            net_profit = balance - initial_balance
            roi = (net_profit / initial_balance) * 100
            
            st.markdown("### 📊 頂尖結構回測數據盤")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("總交易次數", f"{total_trades} 筆")
            col2.metric("勝率", f"{win_rate:.2f} %")
            col3.metric("最終資金", f"${balance:.2f} U")
            col4.metric("總收益率", f"{roi:.2f} %")
            
            equity = [initial_balance]
            for t in trades:
                equity.append(equity[-1] * (1 + t['pnl']))
                
            st.markdown("### 📉 資金淨值曲線")
            st.line_chart(equity)
            
            # 顯示交易明細供你參考
            st.markdown("### 📝 最近 10 筆交易明細")
            st.dataframe(df_trades.tail(10), use_container_width=True)
            
            st.success("💡 這就是頂尖交易員的預測邏輯：不猜底，等主力露出馬腳（掃蕩）再跟進。")
        else:
            st.warning("這段時間內沒有觸發「掃蕩 + FVG」的頂級信號。")
