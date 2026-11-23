import streamlit as st
import requests
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="系統 A - 千筆大回測", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; font-size: 18px; height: 50px; }
    h1, h2, h3, p { color: #fafafa !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 系統 A：千筆交易大回測")

@st.cache_data(ttl=3600) # 快取一小時，避免重複拉取
def fetch_historical_data(days_back=90):
    # 抓取 15m 數據，一次 300 根，往前推
    all_data = []
    end_time = int(time.time() * 1000)
    
    # 計算需要拉取多少次 (90天 * 24小時 * 4根/小時 = 8640根，大約 29 次)
    loops = (days_back * 24 * 4) // 300 + 1
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(loops):
        status_text.text(f"正在抓取歷史數據... 第 {i+1}/{loops} 批次")
        url = f"https://www.okx.com/api/v5/market/history-candles?instId=BTC-USDT&bar=15m&limit=300&after={end_time}"
        try:
            res = requests.get(url, timeout=10)
            data = res.json()
            if data['code'] == '0' and data['data']:
                all_data.extend(data['data'])
                end_time = int(data['data'][-1][0]) # 更新時間戳，往前推
            else:
                break
        except:
            break
        time.sleep(0.1) # 防止被 API 封鎖
        progress_bar.progress((i + 1) / loops)
    
    status_text.text("數據抓取完成，準備運算...")
    progress_bar.empty()
    
    if not all_data:
        return pd.DataFrame()
        
    df = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'volCcy', 'volCcyQuote', 'confirm'])
    df = df.iloc[::-1].reset_index(drop=True) # 按時間從舊到新排序
    
    for col in ['open', 'high', 'low', 'close']:
        df[col] = df[col].astype(float)
    df['timestamp'] = pd.to_datetime(df['timestamp'].astype(float), unit='ms') + pd.Timedelta(hours=8)
    return df

st.info("回測邏輯：採用 EMA(9) 與 EMA(21) 交叉策略。死叉做空，金叉做多。本金 50U，單筆風險 1%，盈虧比 1:2，包含手續費磨損。")
st.write("這將模擬過去 **90 天** 的數據，預計產生 **數百至上千筆** 交易，徹底檢驗策略真實期望值。")

if st.button("🚀 開始千筆大回測 (需時約 10-20 秒)"):
    df = fetch_historical_data(90)
    
    if df.empty:
        st.error("數據抓取失敗，請稍後重試。")
    else:
        st.success(f"成功抓取 {len(df)} 根 15m K 線！時間跨度：{df['timestamp'].iloc[0]} 到 {df['timestamp'].iloc[-1]}")
        
        # 計算指標
        df['EMA_9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['close'].ewm(span=21, adjust=False).mean()
        
        # 模擬交易
        balance = 50.0
        initial_balance = 50.0
        trades = []
        in_position = False
        position_type = None
        entry_price = 0
        sl = 0
        tp = 0
        fee_rate = 0.0005 # 假設單邊手續費 0.05%
        
        for i in range(1, len(df)):
            current_close = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            ema9_prev = df['EMA_9'].iloc[i-1]
            ema21_prev = df['EMA_21'].iloc[i-1]
            ema9_curr = df['EMA_9'].iloc[i]
            ema21_curr = df['EMA_21'].iloc[i]
            
            if not in_position:
                # 金叉做多 (9 穿 21 向上)
                if ema9_prev <= ema21_prev and ema9_curr > ema21_curr:
                    in_position = True
                    position_type = 'LONG'
                    entry_price = current_close
                    sl = entry_price * 0.99  # 1% 止損
                    tp = entry_price * 1.02  # 2% 止盈 (1:2)
                    
                # 死叉做空 (9 穿 21 向下)
                elif ema9_prev >= ema21_prev and ema9_curr < ema21_curr:
                    in_position = True
                    position_type = 'SHORT'
                    entry_price = current_close
                    sl = entry_price * 1.01  # 1% 止損
                    tp = entry_price * 0.98  # 2% 止盈
                    
            else:
                # 處理平倉邏輯 (簡化為只看當前K線的高低點是否觸及)
                if position_type == 'LONG':
                    if current_low <= sl:
                        loss = -0.01 - fee_rate * 2 # 虧損 1% + 手續費
                        balance = balance * (1 + loss)
                        trades.append({'result': 'SL', 'pnl': loss, 'time': df['timestamp'].iloc[i]})
                        in_position = False
                    elif current_high >= tp:
                        profit = 0.02 - fee_rate * 2 # 盈利 2% - 手續費
                        balance = balance * (1 + profit)
                        trades.append({'result': 'TP', 'pnl': profit, 'time': df['timestamp'].iloc[i]})
                        in_position = False
                        
                elif position_type == 'SHORT':
                    if current_high >= sl:
                        loss = -0.01 - fee_rate * 2
                        balance = balance * (1 + loss)
                        trades.append({'result': 'SL', 'pnl': loss, 'time': df['timestamp'].iloc[i]})
                        in_position = False
                    elif current_low <= tp:
                        profit = 0.02 - fee_rate * 2
                        balance = balance * (1 + profit)
                        trades.append({'result': 'TP', 'pnl': profit, 'time': df['timestamp'].iloc[i]})
                        in_position = False

        # 輸出結果
        if len(trades) > 0:
            df_trades = pd.DataFrame(trades)
            total_trades = len(trades)
            wins = len(df_trades[df_trades['result'] == 'TP'])
            win_rate = (wins / total_trades) * 100
            net_profit = balance - initial_balance
            roi = (net_profit / initial_balance) * 100
            
            st.markdown("### 📊 千筆回測真實數據盤")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("總交易次數", f"{total_trades} 筆")
            col2.metric("勝率", f"{win_rate:.2f} %")
            col3.metric("最終資金", f"${balance:.2f} U")
            col4.metric("總收益率", f"{roi:.2f} %")
            
            # 畫資金曲線
            equity = [initial_balance]
            for t in trades:
                equity.append(equity[-1] * (1 + t['pnl']))
                
            st.markdown("### 📉 資金淨值曲線")
            st.line_chart(equity)
            
            # 顯示最近 10 筆交易明細
            st.markdown("### 📝 最近 10 筆交易明細")
            st.dataframe(df_trades.tail(10), use_container_width=True)
            
            st.warning("⚠️ 注意：回測結果不代表未來收益。這就是為什麼我們需要嚴格的風控。")
        else:
            st.warning("在過去 90 天內，沒有觸發任何交易信號。")
