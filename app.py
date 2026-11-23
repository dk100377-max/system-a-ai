import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="系統 A - 實戰交易回測", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; font-size: 18px; height: 50px; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 系統 A：高頻實戰交易回測")

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

st.info("實戰邏輯：當 RSI(14) 跌破 30 且在 EMA(100) 之上時做多。止損 1.5%，止盈 3%。這能保證在三個月內產生大量交易。")

if st.button("🚀 開始實戰回測"):
    df = fetch_historical_data(90)
    
    if df.empty:
        st.error("數據抓取失敗。")
    else:
        st.write(f"✅ 數據抓取成功！共 {len(df)} 根 15m K 線。")
        
        # 計算指標
        df['EMA_100'] = df['close'].ewm(span=100, adjust=False).mean()
        
        # 計算 RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        balance = 50.0
        initial_balance = 50.0
        trades = []
        in_position = False
        entry_price = 0
        sl = 0
        tp = 0
        fee_rate = 0.0005
        
        for i in range(100, len(df)):
            current_close = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            rsi = df['RSI'].iloc[i]
            ema100 = df['EMA_100'].iloc[i]
            
            if not in_position:
                # 進場條件：RSI 超賣跌破30，且大趨勢向上
                if rsi < 30 and current_close > ema100:
                    in_position = True
                    entry_price = current_close
                    sl = entry_price * 0.985  # 1.5% 止損
                    tp = entry_price * 1.03   # 3% 止盈
            else:
                if current_low <= sl:
                    loss = -0.015 - fee_rate * 2
                    balance = balance * (1 + loss)
                    trades.append({'結果': '止損', '盈虧': loss, '時間': df['timestamp'].iloc[i], '價格': sl})
                    in_position = False
                elif current_high >= tp:
                    profit = 0.03 - fee_rate * 2
                    balance = balance * (1 + profit)
                    trades.append({'結果': '止盈', '盈虧': profit, '時間': df['timestamp'].iloc[i], '價格': tp})
                    in_position = False
                    
        if len(trades) > 0:
            df_trades = pd.DataFrame(trades)
            total_trades = len(trades)
            wins = len(df_trades[df_trades['結果'] == '止盈'])
            win_rate = (wins / total_trades) * 100
            net_profit = balance - initial_balance
            roi = (net_profit / initial_balance) * 100
            
            st.markdown("### 📊 實戰回測數據盤")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("總交易次數", f"{total_trades} 筆")
            col2.metric("勝率", f"{win_rate:.2f} %")
            col3.metric("最終資金", f"${balance:.2f} U")
            col4.metric("總收益率", f"{roi:.2f} %")
            
            equity = [initial_balance]
            for t in trades:
                equity.append(equity[-1] * (1 + t['盈虧']))
                
            st.markdown("### 📉 資金淨值曲線")
            st.line_chart(equity)
            
            st.markdown("### 📝 交易明細 (最近 10 筆)")
            st.dataframe(df_trades.tail(10), use_container_width=True)
            
            if roi > 0:
                st.success(f"🎉 恭喜！這套策略在過去三個月為你的 50U 賺了 {net_profit:.2f} U！")
            else:
                st.error("⚠️ 這套策略在過去三個月依然虧損，這說明我們需要更好的過濾條件。")
        else:
            st.warning("這段時間內沒有觸發交易信號。")
