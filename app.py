import streamlit as st
import requests
import pandas as pd
import numpy as np
import time

st.set_page_config(page_title="系統 A - 多空雙向實戰", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; }
    .stButton>button { width: 100%; background-color: #ff4b4b; color: white; font-weight: bold; font-size: 18px; height: 50px; }
    h1, h2, h3, p { color: #fafafa !important; }
    .stMetric label { color: #aaa !important; }
</style>
""", unsafe_allow_html=True)

st.title("🏛️ 系統 A：多空雙向 FVG 實戰回測")

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

st.info("策略邏輯：大週期 EMA(50) 判斷多空。順勢尋找 15m FVG 缺口，回踩/反抽且出現確認 K 線時進場。嚴格 1:2 盈虧比。")

if st.button("🚀 開始多空雙向回測"):
    df = fetch_historical_data(90)
    
    if df.empty:
        st.error("數據抓取失敗。")
    else:
        st.write(f"✅ 數據抓取成功！共 {len(df)} 根 15m K 線。")
        
        df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
        
        balance = 50.0
        initial_balance = 50.0
        trades = []
        in_position = False
        position_type = None # 'LONG' or 'SHORT'
        entry_price = 0
        sl = 0
        tp = 0
        fee_rate = 0.0005
        
        for i in range(60, len(df)):
            current_open = df['open'].iloc[i]
            current_close = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            ema50 = df['EMA_50'].iloc[i]
            
            if not in_position:
                # 找 FVG
                bull_fvg_found = False
                bear_fvg_found = False
                
                for j in range(i-10, i-1):
                    # 看漲 FVG: K線1的高點 < K線3的低點
                    if df['high'].iloc[j] < df['low'].iloc[j+2]:
                        bull_fvg_low = df['high'].iloc[j]
                        bull_fvg_high = df['low'].iloc[j+2]
                        bull_fvg_found = True
                        break
                
                for j in range(i-10, i-1):
                    # 看跌 FVG: K線1的低點 > K線3的高點
                    if df['low'].iloc[j] > df['high'].iloc[j+2]:
                        bear_fvg_high = df['low'].iloc[j]
                        bear_fvg_low = df['high'].iloc[j+2]
                        bear_fvg_found = True
                        break
                
                # 做多進場邏輯：大趨勢多 + 回踩看漲 FVG + 收陽線
                if current_close > ema50 and bull_fvg_found:
                    if current_low <= bull_fvg_high and current_close > current_open:
                        in_position = True
                        position_type = 'LONG'
                        entry_price = current_close
                        sl = bull_fvg_low * 0.998
                        risk = entry_price - sl
                        
                        if risk / entry_price <= 0.02: # 止損小於 2% 才做
                            tp = entry_price + (risk * 2)
                        else:
                            in_position = False
                
                # 做空進場邏輯：大趨勢空 + 反彈看跌 FVG + 收陰線
                elif current_close < ema50 and bear_fvg_found:
                    if current_high >= bear_fvg_low and current_close < current_open:
                        in_position = True
                        position_type = 'SHORT'
                        entry_price = current_close
                        sl = bear_fvg_high * 1.002
                        risk = sl - entry_price
                        
                        if risk / entry_price <= 0.02:
                            tp = entry_price - (risk * 2)
                        else:
                            in_position = False
            else:
                # 平倉邏輯
                if position_type == 'LONG':
                    if current_low <= sl:
                        loss = - (entry_price - sl) / entry_price - fee_rate * 2
                        balance = balance * (1 + loss)
                        trades.append({'方向': '做多', '結果': '止損', '盈虧': loss, '時間': df['timestamp'].iloc[i], '價格': sl})
                        in_position = False
                    elif current_high >= tp:
                        profit = (tp - entry_price) / entry_price - fee_rate * 2
                        balance = balance * (1 + profit)
                        trades.append({'方向': '做多', '結果': '止盈', '盈虧': profit, '時間': df['timestamp'].iloc[i], '價格': tp})
                        in_position = False
                        
                elif position_type == 'SHORT':
                    if current_high >= sl:
                        loss = - (sl - entry_price) / entry_price - fee_rate * 2
                        balance = balance * (1 + loss)
                        trades.append({'方向': '做空', '結果': '止損', '盈虧': loss, '時間': df['timestamp'].iloc[i], '價格': sl})
                        in_position = False
                    elif current_low <= tp:
                        profit = (entry_price - tp) / entry_price - fee_rate * 2
                        balance = balance * (1 + profit)
                        trades.append({'方向': '做空', '結果': '止盈', '盈虧': profit, '時間': df['timestamp'].iloc[i], '價格': tp})
                        in_position = False
                    
        if len(trades) > 0:
            df_trades = pd.DataFrame(trades)
            total_trades = len(trades)
            wins = len(df_trades[df_trades['結果'] == '止盈'])
            win_rate = (wins / total_trades) * 100
            net_profit = balance - initial_balance
            roi = (net_profit / initial_balance) * 100
            
            long_trades = len(df_trades[df_trades['方向'] == '做多'])
            short_trades = len(df_trades[df_trades['方向'] == '做空'])
            
            st.markdown("### 📊 多空雙向回測數據盤")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("總交易次數", f"{total_trades} 筆 (多:{long_trades} 空:{short_trades})")
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
                st.success(f"🎉 太棒了！這才是真正的「順應市場」。多空雙做讓你在這段時間賺了 {net_profit:.2f} U。")
            else:
                st.error("⚠️ 雖然加入了做空，但這段行情可能過於反覆，導致兩面被止損。我們需要繼續優化。")
        else:
            st.warning("這段時間內沒有觸發交易信號。")
