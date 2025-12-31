import ccxt
import pandas as pd
import ta
import time
from datetime import datetime, timedelta
import google.generativeai as genai
import os
from dotenv import load_dotenv
import re
import json
import random

# 加载配置
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GENAI_API_KEY:
    raise ValueError("❌ 错误: 未找到 API Key！")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
exchange = ccxt.binance()

# --- 1. 指标计算 ---
def calculate_long_term_indicators(df):
    df['SMA50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
    df['SMA200'] = ta.trend.SMAIndicator(close=df['close'], window=200).sma_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    # 核心因子
    df['SMA200_Dev'] = (df['close'] - df['SMA200']) / df['SMA200'] * 100
    df['SMA200_Slope'] = (df['SMA200'] - df['SMA200'].shift(5)) / df['SMA200'].shift(5) * 100
    
    return df

# --- 2. 获取数据 ---
def fetch_daily_data(symbol, end_time_str, lookback_days=400):
    try:
        end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        end_ts = int(end_dt.timestamp() * 1000)
        start_ts = end_ts - (lookback_days * 24 * 60 * 60 * 1000)
        
        bars = exchange.fetch_ohlcv(symbol, '1d', since=start_ts, limit=lookback_days)
        if not bars: return pd.DataFrame()
        
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        print(f"数据获取出错: {e}")
        return pd.DataFrame()

# --- 3. 执行测试 ---
def run_swing_test(symbol, test_time, label="测试"):
    print(f"\n====== 📅 波段测试 (14-30天): {label} ({test_time}) ======")
    
    for _ in range(3):
        df = fetch_daily_data(symbol, test_time)
        if not df.empty: break
        time.sleep(1)
    
    if df.empty: return

    df = calculate_long_term_indicators(df)
    
    target_dt = datetime.strptime(test_time, "%Y-%m-%d %H:%M:%S")
    df_truncated = df[df['time'] <= target_dt].copy()
    if df_truncated.empty: return
    last_row = df_truncated.iloc[-1]
    
    # 提取数据
    price = last_row['close']
    sma200 = last_row['SMA200']
    sma50 = last_row['SMA50']
    slope = last_row['SMA200_Slope']
    dev = last_row['SMA200_Dev']
    rsi = last_row['RSI']
    
    # 判定市场背景 (Regime Definition)
    # 只要价格在 SMA200 之上，或者 SMA200 斜率向上，都算广义牛市
    is_bull_regime = (price > sma200) or (slope > 0)
    regime_desc = "🐮 牛市/强势背景" if is_bull_regime else "🐻 熊市/弱势背景"
    
    macd_status = "✅ 金叉" if last_row['MACD'] > last_row['MACD_Signal'] else "⚠️ 死叉"

    print(f"现价: ${price:.0f} | SMA200: ${sma200:.0f} | 乖离率: {dev:.2f}%")
    print(f"背景: {regime_desc} (斜率:{slope:.4f}) | SMA50: ${sma50:.0f}")

    # --- 🔥 v6.0 牛熊分层 Prompt 🔥 ---
    prompt = f"""
    假设现在是 {test_time}。你是一位**趋势跟踪型**长线交易员。
    
    【市场背景判定】
    - 当前环境: **{regime_desc}**
    - 现价 vs SMA200: {"价格在长期均线上方" if price > sma200 else "价格在长期均线下方"}
    - 现价 vs SMA50: {"价格在生命线上方" if price > sma50 else "价格在生命线下方"}
    - RSI: {rsi:.1f} | MACD: {macd_status}
    
    【🔥 核心决策逻辑 (分场景执行) 🔥】
    
    **场景 A: 牛市/强势背景 (Bull Regime)**
    *逻辑: 顺势而为，回调即买入。*
    1. **牛市回调 (Buy Dip)**: 
       - 如果 **价格 < SMA50** (跌破生命线) 但 **RSI < 50** (指标冷却)。
       - 此时不要恐慌卖出！这是黄金坑。
       - 决策: **买入/持有**。
       - *目标: 修复 2024-05-01 / 2025-04-10 卖飞地板的问题。*
       
    2. **趋势延续 (Trend Hold)**:
       - 如果 **价格 > SMA50**。即使 RSI > 70 也不要轻易卖出，那是主升浪。
       - 决策: **持有/买入**。
       - *目标: 修复 2024-02-15 卖飞主升浪的问题。*
       
    3. **趋势反转启动 (Reversal Start)**:
       - 如果之前是熊市，现在 **价格强力突破 SMA200** (乖离率变正)。
       - 忽略斜率滞后。
       - 决策: **买入/持有**。
       - *目标: 修复 2023-10-20 踏空的问题。*

    **场景 B: 熊市/弱势背景 (Bear Regime)**
    *逻辑: 现金为王，反弹即逃命。*
    1. **熊市中继 (Bear Continuation)**:
       - 如果 **价格 < SMA200** 且 **价格 < SMA50**。
       - 无论 RSI 是多少，这都是阴跌。
       - 决策: **卖出/观望**。
       - *目标: 修复 519 亏损。*
       
    2. **熊市诱多 (Bear Trap)**:
       - 如果 **价格反弹至 SMA50 附近** 但 **无法有效站稳 (MACD死叉)**。
       - 决策: **卖出/观望**。
       - *目标: 修复 FTX 前夕乱买的问题。*
       
    3. **极端超跌 (Only Deep Value)**:
       - 只有在 **乖离率 < -25%** (极度恐慌) 时才考虑左侧抄底。
       - 普通跌幅 (-10%左右) 不要接飞刀。

    请根据当前 {regime_desc}，判断未来 14-30 天策略。
    只输出 JSON: {{ "direction": "买入/持有" | "卖出/观望", "reason": "基于市场背景的逻辑分析" }}
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned = re.sub(r'```json\s*', '', response.text).replace('```', '').strip()
        res_json = json.loads(cleaned)
        print(f"🤖 AI: {json.dumps(res_json, ensure_ascii=False)}")
        
        # 验证未来 14 天
        days_forward = 14
        future_df = fetch_daily_data(
            symbol, 
            (target_dt + timedelta(days=days_forward + 10)).strftime("%Y-%m-%d %H:%M:%S"), 
            lookback_days=30
        )
        future_df = future_df[(future_df['time'] > target_dt) & (future_df['time'] <= target_dt + timedelta(days=days_forward))]
        
        if not future_df.empty:
            exit_price = future_df['close'].iloc[-1]
            min_price = future_df['low'].min()
            pnl = (exit_price - price) / price * 100
            max_dd = (min_price - price) / price * 100
            
            print(f"📉 {days_forward}天后盈亏: {pnl:.2f}% | 期间最大回撤: {max_dd:.2f}%")
            
            d = res_json.get("direction")
            is_success = False
            
            # 宽松判定
            if "买入" in d or "持有" in d:
                if pnl > -3.0 and max_dd > -12.0: is_success = True
            elif "卖出" in d or "观望" in d:
                if pnl < 3.0: is_success = True
            
            if is_success: print("✅ 判定成功")
            else: print("❌ 判定失败")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # --- 1. 之前失败的牛市回调 (现在应该买) ---
    run_swing_test('BTC/USDT', '2023-10-20 00:00:00', "牛市启动 (2023)") # 之前踏空
    run_swing_test('BTC/USDT', '2024-05-01 00:00:00', "牛市回调 (2024)") # 之前卖飞
    run_swing_test('BTC/USDT', '2025-04-10 00:00:00', "牛市黄金坑 (2025)") # 之前卖飞
    
    # --- 2. 之前失败的熊市 (现在应该卖) ---
    run_swing_test('BTC/USDT', '2022-06-10 00:00:00', "Luna 崩盘") # 之前乱买
    run_swing_test('BTC/USDT', '2022-11-08 00:00:00', "FTX 崩盘") # 之前乱买
    
    # --- 3. 之前失败的疯牛 (现在应该拿) ---
    run_swing_test('BTC/USDT', '2024-02-15 00:00:00', "疯牛主升浪") # 之前卖飞
    run_swing_test('BTC/USDT', '2025-12-01 00:00:00', "疯牛主升浪") # 之前卖飞
    run_swing_test('BTC/USDT', '2025-11-01 00:00:00', "疯牛主升浪") # 之前卖飞
    run_swing_test('BTC/USDT', '2025-09-01 00:00:00', "疯牛主升浪") # 之前卖飞