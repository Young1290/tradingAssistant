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
import numpy as np

# 加载配置
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GENAI_API_KEY:
    raise ValueError("❌ 错误: 未找到 API Key！请在 .env 文件中配置 GEMINI_API_KEY")

genai.configure(api_key=GENAI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')
exchange = ccxt.binance()

# --- 指标计算函数 (含乖离率更新) ---
def calculate_indicators(df):
    """计算 RSI, MACD, 布林带, ATR, ADX, EMA, Pivot, 乖离率"""
    
    # 1. 基础指标
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['MACD'] = macd.macd()
    
    # 2. 均线系统
    df['EMA20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['EMA50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['EMA200'] = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator()
    
    # 3. 趋势强度
    adx_indicator = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ADX'] = adx_indicator.adx()
    
    # 4. Pivot Points
    prev_high = df['high'].shift(1)
    prev_low = df['low'].shift(1)
    prev_close = df['close'].shift(1)
    df['Pivot'] = (prev_high + prev_low + prev_close) / 3
    df['R1'] = (2 * df['Pivot']) - prev_low
    df['S1'] = (2 * df['Pivot']) - prev_high
    
    # --- 🔥 新增关键指标：乖离率 (Deviation) ---
    # 计算价格偏离 EMA20 的百分比。
    # 作用：防止在暴跌/暴涨后，价格距离均线太远时追单（容易被反抽打脸）。
    df['EMA20_Dev'] = (df['close'] - df['EMA20']) / df['EMA20'] * 100
    
    return df

# --- 获取数据 ---
def fetch_historical_slice(symbol, timeframe, end_time_str, lookback=500):
    try:
        end_dt = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        end_ts = int(end_dt.timestamp() * 1000)
        tf_minutes = 60 if timeframe == '1h' else 1440 # 1d
        start_ts = end_ts - (lookback * tf_minutes * 60 * 1000)
        
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=start_ts, limit=lookback)
        if not bars: return pd.DataFrame()
        
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        print(f"数据获取出错: {e}")
        return pd.DataFrame()

def run_test_case(symbol, test_time, label="测试"):
    print(f"\n--- 🧪 正在测试: {label} ({test_time}) ---")
    
    df_1h = fetch_historical_slice(symbol, '1h', test_time)
    if df_1h.empty:
        print("❌ 数据不足，跳过")
        return

    df_1h = calculate_indicators(df_1h)
    
    # 🛡️ 安全截断
    target_dt = datetime.strptime(test_time, "%Y-%m-%d %H:%M:%S")
    df_truncated = df_1h[df_1h['time'] <= target_dt].copy()
    if df_truncated.empty: return
    last_row = df_truncated.iloc[-1]
    
    # 趋势状态辅助
    trend_dir = "牛市区域" if last_row['close'] > last_row['EMA200'] else "熊市区域"
    
    print(f"价格: ${last_row['close']:.2f} | EMA200: ${last_row['EMA200']:.2f} ({trend_dir})")
    print(f"RSI: {last_row['RSI']:.2f} | ADX: {last_row['ADX']:.2f}")
    print(f"乖离率(EMA20): {last_row['EMA20_Dev']:.2f}%") # 打印乖离率

    # 构建 Prompt (含乖离率过滤)
    prompt = f"""
    假设现在是 {test_time}。你是激进但风控严格的量化交易员。
    
    【资产快照】
    - 现价: ${last_row['close']:.2f}
    - EMA200 (牛熊线): ${last_row['EMA200']:.2f} ({trend_dir})
    - EMA20 (短线均线): ${last_row['EMA20']:.2f}
    
    【关键指标】
    - RSI (14): {last_row['RSI']:.2f}
    - ADX (趋势强度): {last_row['ADX']:.2f}
    - Pivot (中轴): ${last_row['Pivot']:.2f}
    - 乖离率 (EMA20 Deviation): {last_row['EMA20_Dev']:.2f}%
    
    【🔥 核心决策逻辑 (必须遵守) 🔥】
    1. **稳健模式 (ADX < 25)**: 震荡市。依托 Pivot 高抛低吸。RSI>70空，RSI<30多。
    
    2. **激进/突破模式 (ADX > 30 且 价格 > EMA200)**: 
       - 忽略 RSI 超买。只要价格在 EMA20 之上，**顺势做多**。
       - ⚠️ **过滤**: 如果 乖离率 > 3.5% (短线涨幅过大远离均线)，不要现价追多，建议等待回踩 EMA20。
       
    3. **暴跌模式 (ADX > 30 且 价格 < EMA200)**:
       - 忽略 RSI 超卖。建议反弹空。
       - ⚠️ **过滤**: 如果 乖离率 < -3.5% (短线跌幅过大远离均线)，**严禁现价做空**！这往往是反弹前夜。必须建议“观望”或“短多抢反弹”。

    请判断未来 24 小时的走势。
    只输出 JSON: {{ "direction": "做多" | "做空" | "观望", "reason": "简短理由" }}
    """
    
    try:
        response = model.generate_content(prompt)
        cleaned = re.sub(r'```json\s*', '', response.text).replace('```', '').strip()
        res_json = json.loads(cleaned)
        print(f"🤖 AI: {json.dumps(res_json, ensure_ascii=False)}")
        
        # 验证结果
        future_df = fetch_historical_slice(
            symbol, '1h',
            (target_dt + timedelta(hours=24)).strftime("%Y-%m-%d %H:%M:%S"),
            lookback=24
        )
        future_df = future_df[future_df['time'] > target_dt]
        
        if not future_df.empty:
            final_p = future_df['close'].iloc[-1]
            chg = (final_p - last_row['close']) / last_row['close'] * 100
            print(f"📉 24h涨跌: {chg:.2f}%")
            
            # 简单胜率统计
            d = res_json.get("direction")
            if ("多" in d and chg > 0.5) or ("空" in d and chg < -0.5) or ("观" in d and abs(chg) < 2):
                print("✅ 判定成功")
            else:
                print("❌ 判定失败")

    except Exception as e:
        print(f"Error: {e}")

# --- 🔥 新增：自动扫描 2025 年的极端行情 🔥 ---
def scan_and_test_year(symbol, year=2025):
    print(f"\n====== 🔍 正在扫描 {year} 年全年数据寻找极端行情 ======")
    
    # 1. 获取全年的日线数据 (更高效)
    start_of_year = int(datetime(year, 1, 1).timestamp() * 1000)
    # 获取 365 天数据
    bars = exchange.fetch_ohlcv(symbol, '1d', since=start_of_year, limit=365)
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    
    if df.empty:
        print("❌ 无法获取该年份数据 (可能还未发生或API限制)")
        return

    # 2. 计算每日涨跌幅
    df['change_pct'] = (df['close'] - df['open']) / df['open'] * 100
    df['volatility'] = (df['high'] - df['low']) / df['open'] * 100
    
    # 3. 找出 Top 3 暴涨日 (Pump)
    top_pumps = df.nlargest(3, 'change_pct')
    
    # 4. 找出 Top 3 暴跌日 (Dump)
    top_dumps = df.nsmallest(3, 'change_pct')
    
    # 5. 找出 Top 2 死鱼日 (Chop - 波动最小)
    top_chops = df.nsmallest(2, 'volatility')
    
    # --- 自动执行回测 ---
    
    print("\n--- 📈 测试 2025 年度最大暴涨日 ---")
    for _, row in top_pumps.iterrows():
        # 测试暴涨发生时的【中午 12:00】，看 AI 是否敢追
        test_time = row['time'].replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        run_test_case(symbol, test_time, f"暴涨日 (涨幅 {row['change_pct']:.2f}%)")
        
    print("\n--- 📉 测试 2025 年度最大暴跌日 ---")
    for _, row in top_dumps.iterrows():
        # 测试暴跌发生时的【中午 12:00】，看 AI 是否识别暴跌
        test_time = row['time'].replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        run_test_case(symbol, test_time, f"暴跌日 (跌幅 {row['change_pct']:.2f}%)")
        
    print("\n--- 😴 测试 2025 年度最无聊震荡日 ---")
    for _, row in top_chops.iterrows():
        test_time = row['time'].replace(hour=12, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
        run_test_case(symbol, test_time, f"震荡日 (波动 {row['volatility']:.2f}%)")

# --- 执行主程序 ---
if __name__ == "__main__":
    # 1. 先跑一遍经典的历史测试 (用于基准对比)
    run_test_case('BTC/USDT', '2024-11-06 14:00:00', "2024 牛市启动")
    
    # 2. 🔥 自动扫描 2025 年数据 (如果你的时间已经是2025年)
    # 这行代码会自动找出今年发生过的最大行情并测试
    scan_and_test_year('BTC/USDT', 2025)