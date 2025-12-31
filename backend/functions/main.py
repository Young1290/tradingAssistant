import os
import ccxt
import pandas as pd
import ta
import json
import re
import feedparser
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv
from datetime import datetime

# 1. 加载环境变量
load_dotenv()

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Trading Assistant API - See /docs for endpoints"}

# 2. 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 3. 初始化
exchange = ccxt.binance()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GENAI_API_KEY:
    print("⚠️ 警告: 未找到 GEMINI_API_KEY，请检查 .env 文件")
else:
    genai.configure(api_key=GENAI_API_KEY)

model = genai.GenerativeModel('gemini-2.5-flash')

class AnalysisRequest(BaseModel):
    symbol: str 

# --- 辅助功能 ---
def get_fear_and_greed():
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        r = requests.get(url, timeout=5)
        return {"value": r.json()['data'][0]['value'], "value_classification": r.json()['data'][0]['value_classification']}
    except:
        return {"value": "50", "value_classification": "Neutral"}

def get_crypto_news(symbol_query: str):
    """获取 Google News (包含发布时间)"""
    try:
        # 简单映射
        query_map = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'SOL': 'Solana'}
        query = query_map.get(symbol_query.split('/')[0], symbol_query)
        
        # RSS URL
        rss_url = f"https://news.google.com/rss/search?q={query}+crypto&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(rss_url)
        
        news_items = []
        for entry in feed.entries[:5]:
            # 获取发布时间，如果没有则显示 '未知'
            pub_date = entry.get('published', 'N/A')
            
            # 尝试简单格式化日期 (去掉时区等冗余信息，让前端显示更短)
            # Google 格式通常是: "Fri, 05 Dec 2025 03:00:00 GMT"
            try:
                # 截取前16个字符 -> "Fri, 05 Dec 2025" 
                # 或者保留原样让前端处理
                pass 
            except:
                pass

            news_items.append({
                "title": entry.title,
                "link": entry.link,
                "published": pub_date  # <--- 新增这行
            })
            
        return news_items
    except Exception as e:
        print(f"获取新闻出错: {e}")
        return []

def fetch_data(symbol: str, timeframe='1h', limit=500):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        return df
    except Exception as e:
        print(f"Error fetching {timeframe}: {e}")
        return pd.DataFrame()

# --- 🔥 核心指标计算 ---

def calculate_indicators(df):
    """微观指标 (1H/15m): RSI, MACD, EMA, ADX"""
    if df.empty: return df
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    df['MACD_diff'] = macd.macd_diff() # 柱状图
    
    df['EMA20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['EMA50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['EMA200'] = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator()
    
    df['BBL_20_2.0'] = ta.volatility.BollingerBands(close=df['close']).bollinger_lband()
    df['BBU_20_2.0'] = ta.volatility.BollingerBands(close=df['close']).bollinger_hband()
    df['ATR'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()
    df['ADX'] = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close']).adx()
    
    # Pivot Points
    prev_high = df['high'].shift(1)
    prev_low = df['low'].shift(1)
    prev_close = df['close'].shift(1)
    df['Pivot'] = (prev_high + prev_low + prev_close) / 3
    df['R1'] = (2 * df['Pivot']) - prev_low
    df['S1'] = (2 * df['Pivot']) - prev_high
    df['Vol_MA20'] = df['volume'].rolling(window=20).mean()
    return df.fillna(0)

def calculate_daily_indicators(df):
    """宏观指标 (1D): SMA200, 斜率, 乖离率"""
    if df.empty: return df
    df['SMA50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
    df['SMA200'] = ta.trend.SMAIndicator(close=df['close'], window=200).sma_indicator()
    
    df['SMA200_Slope'] = (df['SMA200'] - df['SMA200'].shift(5)) / df['SMA200'].shift(5) * 100
    df['SMA200_Dev'] = (df['close'] - df['SMA200']) / df['SMA200'] * 100
    return df.fillna(0)

# --- 🔥 这里就是你缺少的 Function 🔥 ---
def get_trend_status(row, is_macro=False, macro_bullish=False):
    """
    前端红绿灯状态判断
    - is_macro: 是否是宏观周期 (日线)
    - macro_bullish: 如果是宏观，是牛还是熊
    """
    # --- 1. 如果是日线 (Macro)，直接根据双周期共振逻辑定色 ---
    if is_macro:
        return "bullish" if macro_bullish else "bearish"

    # --- 2. 如果是短线 (Micro)，看 ADX 和 EMA20 ---
    # 如果 ADX 低，说明没趋势，灰色 (震荡)
    if row['ADX'] < 20:
        return "neutral"

    # 基于 EMA 排列判断
    is_uptrend = row['close'] > row['EMA20']
    is_downtrend = row['close'] < row['EMA20']
    
    # 基于 MACD 动能判断
    momentum_up = row['MACD_diff'] > 0
    
    # 强趋势
    if is_uptrend and momentum_up:
        return "bullish"
    elif is_downtrend and not momentum_up:
        return "bearish"
    
    # 弱趋势 (给前端浅色)
    if row['RSI'] > 55: return "weak_bullish"
    if row['RSI'] < 45: return "weak_bearish"
    
    return "neutral"

# --- API ---

@app.get("/api/market-data/{symbol}")
async def get_market_data(symbol: str):
    """图表数据"""
    try:
        formatted_symbol = symbol.replace('-', '/').upper()
        if '/' not in formatted_symbol: formatted_symbol = formatted_symbol[:-4] + '/' + formatted_symbol[-4:]
        
        # 返回日线数据画长线图
        df = fetch_data(formatted_symbol, timeframe='1d', limit=365)
        df = calculate_daily_indicators(df)
        
        chart_data = []
        for index, row in df.iterrows():
            chart_data.append({
                "time": int(row['time'].timestamp()),
                "open": row['open'], "high": row['high'], "low": row['low'], "close": row['close'],
                "volume": row['volume'],
                "sma50": row['SMA50'], "sma200": row['SMA200']
            })
        return {"symbol": formatted_symbol, "data": chart_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_market(request: AnalysisRequest):
    try:
        # 1. 双脑数据获取
        df_daily = fetch_data(request.symbol, '1d', limit=500)
        df_hourly = fetch_data(request.symbol, '1h', limit=100)
        
        if df_daily.empty: df_daily = df_hourly # 兜底
        if df_hourly.empty: raise HTTPException(status_code=500, detail="数据获取失败")

        # 2. 计算指标
        df_daily = calculate_daily_indicators(df_daily)
        df_hourly = calculate_indicators(df_hourly)
        
        last_daily = df_daily.iloc[-1]
        last_hourly = df_hourly.iloc[-1]
        
        # 3. 宏观背景判定 (🔥 严格风控核心逻辑)
        slope = last_daily['SMA200_Slope']
        dev = last_daily['SMA200_Dev']
        price = last_daily['close']
        sma200 = last_daily['SMA200']
        
        # ❌ 旧逻辑: is_bull_regime = (price > sma200) or (slope > 0)
        # ✅ 当前逻辑: 只有价格站在 SMA200 之上才算牛市，跌破即熊市
        is_bull_regime = price > sma200
        
        regime_desc = "🐮 牛市/强势背景" if is_bull_regime else "🐻 熊市/弱势背景"

        # 4. 生成雷达图信号
        ui_signals = {}
        mtf_desc = {}
        target_timeframes = ['1w', '1d', '4h', '1h'] 

        for tf in target_timeframes:
            if tf == '1d':
                # 日线强制跟随严格风控判定
                status = "bullish" if is_bull_regime else "bearish"
                ui_signals[tf] = status
                mtf_desc[tf] = f"趋势:{'牛市' if is_bull_regime else '熊市'} (SMA200:{sma200:.0f})"
            elif tf == '1w':
                df_w = fetch_data(request.symbol, '1w', limit=52)
                if not df_w.empty:
                    df_w = calculate_indicators(df_w)
                    ui_signals[tf] = get_trend_status(df_w.iloc[-1])
                    mtf_desc[tf] = f"RSI:{df_w.iloc[-1]['RSI']:.1f}"
                else: ui_signals[tf] = "neutral"
            elif tf == '1h':
                 ui_signals[tf] = get_trend_status(last_hourly)
                 mtf_desc[tf] = f"RSI:{last_hourly['RSI']:.1f}"
            else:
                df_tf = fetch_data(request.symbol, tf, limit=100)
                if not df_tf.empty:
                    df_tf = calculate_indicators(df_tf)
                    ui_signals[tf] = get_trend_status(df_tf.iloc[-1])
                    mtf_desc[tf] = f"RSI:{df_tf.iloc[-1]['RSI']:.1f}"
                else: ui_signals[tf] = "neutral"

        # 5. 微观数据
        momentum_4h = 0.0
        if len(df_hourly) >= 4:
            momentum_4h = (last_hourly['close'] - df_hourly.iloc[-4]['close']) / df_hourly.iloc[-4]['close'] * 100
            
        macd_status = "✅ 金叉" if last_hourly['MACD'] > last_hourly['MACD_signal'] else "⚠️ 死叉"
        
        # 6. Prompt (🔥 严格风控版)
        news_list = get_crypto_news(request.symbol)
        news_text = "\n".join([f"- {n['title']}" for n in news_list])
        fng = get_fear_and_greed()

        prompt = f"""
        你是一位**严格风控**的趋势交易员。
        
        【宏观背景 (日线)】
        - 环境: **{regime_desc}**
        - SMA200: ${sma200:.2f}
        - 乖离率: {dev:.2f}% (价格距离SMA200的距离)
        - 斜率: {slope:.4f}
        - 恐慌指数: {fng['value']}
        
        【微观参考 (1小时)】
        - 现价: ${last_hourly['close']:.2f}
        - Pivot: ${last_hourly['Pivot']:.2f}
        - MACD: {macd_status}
        
        【🔥 核心决策逻辑 (严格执行) 🔥】
        
        **场景 A: 牛市背景 (价格 > SMA200)**
        *逻辑: 持有为主，回调买入，但在悬崖边要小心。*
        1. **悬崖勒马**: 虽然价格 > SMA200，但如果 **乖离率 < 3%** 且 **斜率 < 0** (均线开始拐头)，说明趋势可能终结 -> **减仓/观望**。
        2. **牛市回调 (黄金坑)**: 价格 > SMA200 且 RSI < 50 -> **买入/加仓**。
        3. **趋势跟随**: 只要价格稳在 SMA200 之上 -> **持有**。

        **场景 B: 熊市背景 (价格 < SMA200)**
        *逻辑: 只要在水下，默认空仓/做空。不要轻易抄底。*
        1. **止损/空仓 (Bear Defense)**: 只要 价格 < SMA200 -> **卖出/观望**。
           - *理由: 宁可错过反弹，也不要接飞刀。2022年的教训。*
        2. **熊市诱多**: 价格反弹测试 SMA200 但未站稳 -> **做空**。
        3. **极端超跌 (唯一买点)**: 只有 **乖离率 < -30%** (极度恐慌) 时，才可轻仓博反弹。

        【任务】
        请给出未来 **14-30天** 的操作建议。
        
        请输出纯 JSON:
        {{
            "direction": "买入" | "持有" | "卖出" | "观望",
            "entry_price": "建议挂单价 (参考日线SMA50 或 小时线S1)",
            "stop_loss": "建议止损价 (参考 SMA200)",
            "target_price": "建议止盈价",
            "reasoning": "详细理由 (必须基于严格风控逻辑，特别是SMA200的位置)",
            "confidence": "1-10",
            "risk_warning": "风险提示"
        }}
        """
        
        response = model.generate_content(prompt)
        
        try:
            cleaned_text = re.sub(r'```json\s*', '', response.text).replace('```', '').strip()
            analysis_json = json.loads(cleaned_text)
            
            return {
                "ui_signals": ui_signals,
                "analysis": analysis_json,
                "news": news_list,
                "fng": fng
            }
        except json.JSONDecodeError:
            return {
                "ui_signals": ui_signals,
                "analysis": {"direction": "解析错误", "reasoning": response.text, "confidence": 0},
                "news": news_list,
                "fng": fng
            }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 🔥 Firebase Cloud Functions 适配器 (加在文件最末尾)
# ==========================================
from firebase_functions import https_fn
from firebase_admin import initialize_app

# 初始化 Firebase
initialize_app()

@https_fn.on_request(region="us-central1", memory=512, timeout_sec=60)
def api(req: https_fn.Request) -> https_fn.Response:
    """
    这是一个适配器，把 Firebase 的 HTTP 请求转发给 FastAPI 处理。
    注意：这是简化的同步转发，生产环境通常建议用 Google Cloud Run，
    但在 Firebase Functions 里这样写能跑通基本的 API。
    """
    with app.request_context(req.environ):
        return app.full_dispatch_request()