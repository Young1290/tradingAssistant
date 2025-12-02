import os
import ccxt
import pandas as pd
import ta
import json
import re
import feedparser
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from pydantic import BaseModel
from dotenv import load_dotenv
import requests

# 加載環境變量 (你可以創建一個 .env 文件放 GEMINI_API_KEY)
load_dotenv()

app = FastAPI()

# 允許跨域請求 (讓前端能連上)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化交易所 (使用幣安公開數據)
exchange = ccxt.binance()

# 初始化 Gemini
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GENAI_API_KEY)

# 列出可用模型（用于调试）
try:
    print("可用的 Gemini 模型：")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"  - {m.name}")
except Exception as e:
    print(f"列出模型时出错: {e}")

# 使用可用的模型（gemini-2.5-flash 是最新且快速的模型）
model = genai.GenerativeModel('gemini-2.5-flash')

class AnalysisRequest(BaseModel):
    symbol: str  # 例如 'BTC/USDT'

# --- 新增功能: 获取恐惧与贪婪指数 ---
def get_fear_and_greed():
    """获取加密货币恐惧与贪婪指数"""
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        response = requests.get(url)
        data = response.json()
        item = data['data'][0]
        return {
            "value": item['value'],
            "value_classification": item['value_classification']
        }
    except Exception:
        # 如果API失败，返回默认值
        return {"value": "50", "value_classification": "Unknown"}

# --- 新增功能: 獲取新聞 ---
def get_crypto_news(symbol_query: str):
    """
    抓取 Google News 的 RSS Feed，返回结构化数据
    """
    # 簡單映射，將 BTC 轉為 Bitcoin 以獲得更準確搜索
    query_map = {'BTC': 'Bitcoin', 'ETH': 'Ethereum', 'SOL': 'Solana'}
    query = query_map.get(symbol_query.split('/')[0], symbol_query)
    
    rss_url = f"https://news.google.com/rss/search?q={query}+crypto&hl=en-US&gl=US&ceid=US:en"
    feed = feedparser.parse(rss_url)
    
    # 取前 5 条最新新闻，返回结构化数据
    news_list = []
    for entry in feed.entries[:5]:
        news_list.append({
            "title": entry.title,
            "published": entry.published,
            "link": entry.link
        })
    
    return news_list

def fetch_data(symbol: str, timeframe='1h', limit=1000):
    """获取 OHLCV 数据并转换为 DataFrame"""
    bars = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    return df

def calculate_indicators(df):
    """计算 RSI, MACD, 布林带, ATR, ADX, EMA50, EMA200"""
    
    # 1. RSI (相对强弱)
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    # 2. MACD (动能)
    macd = ta.trend.MACD(close=df['close'])
    df['MACD_diff'] = macd.macd_diff()
    df['MACD'] = macd.macd()
    df['MACD_signal'] = macd.macd_signal()
    
    # 3. 布林带 (波动通道)
    bollinger = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['BBL_20_2.0'] = bollinger.bollinger_lband()
    df['BBU_20_2.0'] = bollinger.bollinger_hband()
    
    # 4. ATR (波动率 - 用于止损)
    df['ATR'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()
    
    # 5. EMA (核心趋势线 - 重点新增) 
    # EMA 20: 短线保护线
    df['EMA20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    # EMA 50: 中线生命线
    df['EMA50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    # EMA 200: 牛熊分界线 (最重要的优化)
    df['EMA200'] = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator()
    
    # 6. ADX (趋势强度)
    adx_indicator = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14)
    df['ADX'] = adx_indicator.adx()
    
    # 7. 基础支撑阻力 (基于过去20根K线)
    df['Resistance_20'] = df['high'].rolling(window=20).max()
    df['Support_20'] = df['low'].rolling(window=20).min()
    df['Vol_MA20'] = df['volume'].rolling(window=20).mean()
    
# --- 新增：Pivot Points (枢轴点 - 经典算法) ---
    # Pivot Points 通常基于"前一根K线"的 High/Low/Close 计算
    # 这里我们计算每一根K线的 Pivot，AI 会取最后一根作为参考
    
    # 这里的 shift(1) 意思是取"昨天/上一周期"的数据来预测"今天/当前"的阻力
    prev_high = df['high'].shift(1)
    prev_low = df['low'].shift(1)
    prev_close = df['close'].shift(1)
    
    # Pivot Point (中轴)
    df['Pivot'] = (prev_high + prev_low + prev_close) / 3
    
    # Resistance (阻力位)
    df['R1'] = (2 * df['Pivot']) - prev_low
    df['R2'] = df['Pivot'] + (prev_high - prev_low)
    
    # Support (支撑位)
    df['S1'] = (2 * df['Pivot']) - prev_high
    df['S2'] = df['Pivot'] - (prev_high - prev_low)

    return df

def get_trend_status(row):
    """
    基于 EMA, MACD, ADX 判断单周期趋势状态
    返回: 
    - "bullish" (强烈看涨 - 🟢 绿色)
    - "weak_bullish" (弱势看涨 - 🟢 浅绿)
    - "bearish" (强烈看跌 - 🔴 红色)
    - "weak_bearish" (弱势看跌 - 🔴 浅红)
    - "neutral" (震荡/无方向 - ⚪ 灰色)
    """
    
    # 1. 首先看 ADX：如果 ADX < 20，说明市场在横盘，方向不可信
    if row['ADX'] < 20:
        return "neutral"

    # 2. 定义趋势方向 (基于 EMA 系统)
    # 价格在 EMA20 和 EMA50 之上 -> 多头排列
    is_uptrend = row['close'] > row['EMA20'] and row['EMA20'] > row['EMA50']
    # 价格在 EMA20 和 EMA50 之下 -> 空头排列
    is_downtrend = row['close'] < row['EMA20'] and row['EMA20'] < row['EMA50']
    
    # 3. 定义动能 (基于 MACD 柱状图)
    # MACD 柱子 > 0 表示动能向上
    momentum_up = row['MACD_diff'] > 0
    
    # --- 综合判定 ---
    
    if is_uptrend:
        if momentum_up:
            return "bullish"      # 趋势向上 + 动能向上 = 强多
        else:
            return "weak_bullish" # 趋势向上 + 动能减弱 (可能要回调)
            
    elif is_downtrend:
        if not momentum_up:       # 动能向下 (MACD_diff < 0)
            return "bearish"      # 趋势向下 + 动能向下 = 强空
        else:
            return "weak_bearish" # 趋势向下 + 动能反弹 (可能在反抽)
            
    # 如果价格卡在 EMA20 和 50 之间，或者没有明显排列
    else:
        # 看 RSI 辅助判断
        if row['RSI'] > 60: return "weak_bullish"
        if row['RSI'] < 40: return "weak_bearish"
        return "neutral"

@app.get("/")
def read_root():
    return {"message": "Trading Assistant Backend is Running"}

@app.get("/api/market-data/{symbol}")
async def get_market_data(symbol: str):
    try:
        # 格式化交易对，例如将 BTCUSDT 转为 BTC/USDT
        formatted_symbol = symbol.replace('-', '/').upper()
        if '/' not in formatted_symbol: 
             # 简单处理，实际需更严谨
             formatted_symbol = formatted_symbol[:-4] + '/' + formatted_symbol[-4:]
        
        df = fetch_data(formatted_symbol)
        df = calculate_indicators(df)
        
        # 处理 NaN 值以便 JSON 序列化
        df = df.fillna(0)
        
        # 转换为前端图表需要的格式
        chart_data = []
        for index, row in df.iterrows():
            chart_data.append({
                "time": int(row['time'].timestamp()), # Unix timestamp for Lightweight Charts
                "open": row['open'],
                "high": row['high'],
                "low": row['low'],
                "close": row['close'],
                "volume": row['volume'],
                "rsi": row['RSI'],
                "macd": row['MACD'],
                "macd_signal": row['MACD_signal']
            })
            
        return {"symbol": formatted_symbol, "data": chart_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/analyze")
async def analyze_market(request: AnalysisRequest):
    try:
        # 定义需要分析的周期
        timeframes = ['15m', '1h', '4h', '1d']
        
        mtf_data = {}  # 多周期数据
        ui_signals = {}
        current_price = 0
        
        # --- 1. 循环获取多周期数据 ---
        for tf in timeframes:
            df = fetch_data(request.symbol, timeframe=tf, limit=60)
            
            if df.empty:
                continue
                
            df = calculate_indicators(df)
            last_row = df.iloc[-1]
            
            if tf == '15m': 
                current_price = last_row['close']
            
            status = get_trend_status(last_row)
            ui_signals[tf] = status 
            
            adx_str = "趋势强劲" if last_row['ADX'] > 25 else "震荡行情"
            trend_desc = f"状态:{status} | ADX:{last_row['ADX']:.1f}({adx_str}) | RSI:{last_row['RSI']:.1f}"
            mtf_data[tf] = trend_desc

        # --- 2. 获取1小时周期的详细技术指标（用于深度分析）---
        df_1h = fetch_data(request.symbol, timeframe='1h', limit=100)
        df_1h = calculate_indicators(df_1h)
        last_1h = df_1h.iloc[-1]
        
        # 计算额外的技术指标
        price_change_24h = ((last_1h['close'] - df_1h.iloc[-24]['close']) / df_1h.iloc[-24]['close'] * 100) if len(df_1h) >= 24 else 0
        bb_position = (last_1h['close'] - last_1h['BBL_20_2.0']) / (last_1h['BBU_20_2.0'] - last_1h['BBL_20_2.0']) * 100
        vol_status = "放量" if last_1h['volume'] > last_1h['Vol_MA20'] * 1.5 else "缩量"
        macd_status = "金叉" if last_1h['MACD'] > last_1h['MACD_signal'] else "死叉"

        # --- 3. 获取其他数据 ---
        news_list = get_crypto_news(request.symbol)
        news_text = "\n".join([f"- {news['title']}" for news in news_list])
        fng = get_fear_and_greed()
        
        # 获取最新的 EMA 数据
        ema50 = last_row['EMA50']
        # 获取 EMA20 (短期动态压力位)
        ema20 = last_row['EMA20']
        # 获取 EMA200 (长期动态压力位)
        ema200 = last_row['EMA200']
        
        # 判断大趋势 (价格在 EMA200 之上还是之下)
        trend_long_term = "牛市区域 (做多为主)" if last_row['close'] > ema200 else "熊市区域 (做空为主)"
        
        # 计算 ADX 强度
        adx_value = last_row['ADX']
        trend_strength = "极强" if adx_value > 35 else "强" if adx_value > 25 else "弱"
        # 获取最新的 Pivot 数据
        pivot = last_row['Pivot']
        r1 = last_row['R1']
        s1 = last_row['S1']
        
        # --- 4. 构建增强版 Prompt（多周期 + 详细技术分析）---
        prompt = f"""
        你是一位精通**多时间周期共振 (MTF)** 和**量化技术分析**的专业交易员。
        
        
        【资产快照】
        - 标的: {request.symbol}
        - 现价: ${current_price:.2f}
        - 24小时涨跌: {price_change_24h:.2f}%
        
        【多周期趋势雷达 (MTF共振分析)】
        - 1日线 (大势): {mtf_data.get('1d', '数据缺失')}
        - 4小时 (中线): {mtf_data.get('4h', '数据缺失')}
        - 1小时 (波段): {mtf_data.get('1h', '数据缺失')}
        - 15分钟 (入场): {mtf_data.get('15m', '数据缺失')}
        
        【1小时周期详细技术面】
        - RSI (14): {last_1h['RSI']:.2f} {"(超卖<30)" if last_1h['RSI'] < 30 else "(超买>70)" if last_1h['RSI'] > 70 else "(中性)"}
        - MACD: {macd_status}
        - 布林带位置: {bb_position:.1f}% {"(接近下轨-超卖)" if bb_position < 20 else "(接近上轨-超买)" if bb_position > 80 else "(中轨附近)"}
        - 成交量: {vol_status} (当前: {last_1h['volume']:.0f}, 均量: {last_1h['Vol_MA20']:.0f})
        - ATR (波动率): {last_1h['ATR']:.2f}
        - 支撑位: ${last_1h['Support_20']:.2f}
        - 阻力位: ${last_1h['Resistance_20']:.2f}

        ...
        【关键支撑阻力 (Pivot Points)】
        - 阻力位 R1: ${r1:.2f}
        - 中轴 Pivot: ${pivot:.2f}
        - 支撑位 S1: ${s1:.2f}
        (如果做空，请参考 R1 或 Pivot 附近作为入场点；如果做多，参考 S1)
        ...
        
        【核心趋势判定 (必须遵守)】
        - 长期趋势 (EMA200): ${ema200:.2f} -> {trend_long_term}
        - 中期趋势 (EMA50): ${ema50:.2f}
        
        【分析逻辑要求】
        1. **趋势过滤**: 如果价格在 EMA200 之下，严禁建议重仓做多，除非 RSI 极度超卖 (<25)。
        2. **支撑阻力**: EMA50 和 EMA200 通常是极强的动态支撑/阻力位，请重点关注价格是否在此处企稳。
        ...
        
        ...
        【趋势强度分析 (ADX)】
        - ADX值: {adx_value:.1f} ({trend_strength}趋势)
        - 短期均线压力 (EMA20): ${ema20:.2f}
        
        【入场策略调整逻辑 (重要)】
        1. **稳健模式 (ADX < 25)**: 市场震荡，必须等待价格反弹至 Pivot(${pivot:.2f}) 或 R1(${r1:.2f}) 附近才能做空，拒绝现价追单。
        2. **激进模式 (ADX > 30)**: 市场处于极强单边趋势，价格很难反弹到 Pivot。
           - **做空入场点**: 请参考 **EMA20 (${ema20:.2f})** 作为第一入场位。
           - 甚至可以考虑 **Breakout (跌破支撑)** 追空策略。
        ...

        【市场宏观情绪】
        - 恐惧贪婪指数: {fng['value']}/100 ({fng['value_classification']})
        - 解读: {"极度恐慌往往是抄底机会" if int(fng['value']) < 25 else "极度贪婪需警惕回调" if int(fng['value']) > 75 else "情绪中性"}
        
        【消息面 (最新5条)】
        {news_text}
        
        【交易决策框架 (必须遵守)】
        
        **一、多周期共振优先原则**
        1. 如果 [1d] 和 [4h] 都是 bullish/weak_bullish → 主方向做多，在 [15m] 找回调买点
        2. 如果 [1d] 和 [4h] 都是 bearish/weak_bearish → 主方向做空，在 [15m] 找反弹卖点
        3. 如果周期出现分歧 → 优先观望，除非有极端超卖/超买信号
        
        **二、技术面强化信号**
        - 做多加分项: RSI<30 + MACD金叉 + 恐惧指数<30 + 布林带下轨 + 放量上涨
        - 做空加分项: RSI>70 + MACD死叉 + 恐惧指数>70 + 布林带上轨 + 放量下跌
        - 观望条件: ADX<20(震荡市) + 缩量横盘 + 周期严重分歧
        
        **三、风险控制**
        - 止损必须基于 ATR 或关键支撑/阻力位
        - 信心指数 <6 时建议轻仓或观望
        
        请输出纯 JSON (无Markdown):
        {{
            "direction": "做多" | "做空" | "观望",
            "mtf_summary": "一句话概括多周期共振情况",
            "technical_score": "技术面评分1-10 (基于RSI/MACD/布林带/成交量)",
            "sentiment_score": "情绪面评分1-10 (基于恐惧贪婪指数)",
            "news_score": "消息面评分1-10 (基于新闻利好/利空)",
            "entry_price": "入场建议价格",
            "stop_loss": "止损价格 (基于ATR或支撑位)",
            "target_price": "目标价格",
            "position_size": "轻仓/中仓/重仓",
            "confidence": "1-10 (综合信心指数)",
            "reasoning": "详细分析理由，必须包含：1) 量价关系分析 2) 当前价格相对支撑阻力位的位置 3) 多周期共振情况 4) 风险提示。至少150字。"
        }}
        """
        
        # 调用 AI (使用全局定义的模型)
        response = model.generate_content(prompt)
        
        # 尝试解析JSON，如果失败则返回文本格式
        try:
            cleaned_text = re.sub(r'```json\s*', '', response.text)
            cleaned_text = re.sub(r'```', '', cleaned_text).strip()
            analysis_json = json.loads(cleaned_text)
            
            return {
                "ui_signals": ui_signals,
                "analysis": analysis_json,
                "news": news_list,
                "fng": fng
            }
        except json.JSONDecodeError as json_err:
            # JSON解析失败，返回原始文本（保留所有分析内容）
            print(f"JSON解析失败，返回文本格式: {json_err}")
            return {
                "ui_signals": ui_signals,
                "analysis": response.text,  # 返回完整的文本分析
                "news": news_list,
                "fng": fng
            }

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 啟動命令: uvicorn main:app --reload