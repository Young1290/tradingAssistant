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
        
        # 3. 宏观背景判定 (🔥 V6++策略核心逻辑)
        slope = last_daily['SMA200_Slope']
        dev = last_daily['SMA200_Dev']
        price = last_daily['close']
        sma200 = last_daily['SMA200']
        
        # 🔥 V6++逻辑: 宽松牛市判定 (价格>SMA200 OR 斜率>0)
        # 优势: 减少误判，避免震荡市频繁止损，5年回测+514% vs V7的-18%
        is_bull_regime = (price > sma200) or (slope > 0)
        
        # 做空条件判定 (V6++新增)
        can_short = (not is_bull_regime) and (dev < -10) and (slope < -0.5)
        
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
        
        # 6. Prompt (🔥 V6++策略版 - 历史回测+514%收益)
        news_list = get_crypto_news(request.symbol)
        news_text = "\n".join([f"- {n['title']}" for n in news_list])
        fng = get_fear_and_greed()
        
        # 预计算做空状态（避免f-string嵌套）
        short_status = "✅可做空" if can_short else "❌不可做空"

        prompt = f"""
        你是一位采用**V6++策略**的趋势交易员。
        
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
        
        
        【🔥 V6++核心决策逻辑 (历史回测+514%收益) 🔥】
        
        **V6++牛市判定**: 价格>SMA200 OR 斜率>0 (宽松判定，避免误判)
        
        **场景 A: 牛市背景**
        *逻辑: 持有为主，回调买入，盈利100%获利了结。*
        1. **🎯 100%获利了结**: 如果持仓盈利 >= 100% -> **立即卖出锁定利润** (避免顶点回撤)。
        2. **悬崖勒马**: 乖离率 < 3% 且 斜率 < 0 (均线拐头) -> **减仓/观望**。
        3. **牛市回调**: 价格 > SMA200 且 RSI < 50 -> **买入/加仓**。
        4. **趋势跟随**: 价格稳在 SMA200 之上或斜率向上 -> **持有**。

        **场景 B: 熊市背景 (价格<SMA200 且 斜率<0)**
        *逻辑: 可做空赚钱，不要轻易抄底。*
        1. **止损/空仓**: 价格 < SMA200 -> **卖出/观望**。
        2. **📉 做空机会 (当前{short_status})**: 
           - 条件: 乖离率 < -10% 且 斜率 < -0.5% -> **可考虑做空**
           - 平空: 盈利100% 或 乖离率>-5% 或 转牛
        3. **极端超跌**: 乖离率 < -30% -> 可轻仓博反弹。

        【任务】
        请给出未来 **14-30天** 的操作建议。
        
        请输出纯 JSON:
        {{
            "direction": "买入" | "持有" | "卖出" | "观望" | "做空",
            "entry_price": "建议挂单价",
            "stop_loss": "建议止损价 (参考 SMA200)",
            "target_price": "建议止盈价 (多头考虑100%获利)",
            "reasoning": "详细理由 (必须基于V6++逻辑)",
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
                "fng": fng,
                "v6pp_info": {
                    "is_bull_v6": bool(is_bull_regime),
                    "can_short": bool(can_short),
                    "strategy_version": "V6++",
                    "backtest_performance": "+514% (2021-2025)"
                }
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

# --- 🔥 情景分析 API (新增) ---

from scenario_scoring import ScenarioScorer

@app.post("/api/scenario-analysis")
async def scenario_analysis(request: AnalysisRequest):
    """
    宏观情景分析 - 自动获取数据并计算四大情景概率
    """
    try:
        # 1. 自动获取宏观数据
        print(f"📊 开始获取 {request.symbol} 的宏观数据...")
        
        # 1.1 美元指数（简化 - 使用固定值或外部API）
        dxy_value = "98.5 (估算)"
        dxy_trend = "走弱"
        
        # 1.2 Fed 利率政策（通过AI分析新闻）
        try:
            rss_url = "https://news.google.com/rss/search?q=Federal+Reserve+interest+rate&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            news_titles = [entry.title for entry in feed.entries[:5]]
            news_text = "\n".join([f"- {title}" for title in news_titles])
            
            prompt = f"""根据以下最新新闻，用一句话总结当前 Fed 利率政策状态：
{news_text}
请用简短格式回答，例如: "降息 25bp" 或 "维持利率不变" 或 "加息 50bp"
"""
            response = model.generate_content(prompt)
            fed_policy = response.text.strip()
        except:
            fed_policy = "维持现状"
        
        # 1.3 BTC ETF 净流入 (来自 Farside Investors 真实数据)
        try:
            from btc_etf_flow_helper import get_btc_etf_flow_summary
            etf_flow = get_btc_etf_flow_summary()
            print(f"✓ 获取到 BTC ETF 真实数据: {etf_flow}")
        except Exception as e:
            print(f"⚠️ BTC ETF 数据获取失败，使用备用方案: {e}")
            # 备用方案：使用AI分析新闻
            try:
                rss_url = "https://news.google.com/rss/search?q=Bitcoin+ETF+flow&hl=en-US&gl=US&ceid=US:en"
                feed = feedparser.parse(rss_url)
                news_titles = [entry.title for entry in feed.entries[:5]]
                news_text = "\n".join([f"- {title}" for title in news_titles])
                
                prompt = f"""根据以下新闻，总结最近的 BTC ETF 资金流动情况：
{news_text}
请用简短格式回答，例如: "单周流入 $1.2B" 或 "单月流出 $3B" 或 "每日小幅波动"
"""
                response = model.generate_content(prompt)
                etf_flow = response.text.strip()
            except:
                etf_flow = "数据不明确"
        
        # 1.4 长期持有者行为 (来自 CryptoQuant 链上真实数据)
        try:
            from holder_behavior_helper import get_holder_behavior_summary as get_holder_summary
            holder_behavior = get_holder_summary()
            print(f"✓ 获取到持有者行为链上数据: {holder_behavior}")
        except Exception as e:
            print(f"⚠️ 持有者行为数据获取失败，使用备用方案: {e}")
            # 备用方案已在 holder_behavior_helper.py 中实现
            holder_behavior = "数据不可用"
        
        # 1.5 挖矿成本 (来自 Bitdeer 矿机关机价数据)
        try:
            from mining_shutdown_price import get_mining_cost_summary
            mining_cost = get_mining_cost_summary()
            print(f"✓ 获取到矿机关机价数据: {mining_cost}")
        except Exception as e:
            print(f"⚠️ 矿机成本数据获取失败，使用备用值: {e}")
            mining_cost = "约$75,000 (参考值)"
        
        # 1.6 美股 S&P500 表现 (从 Yahoo Finance 获取真实数据)
        try:
            from sp500_helper import get_sp500_performance
            sp500_performance = get_sp500_performance()
            print(f"✓ 获取到 S&P500 真实数据: {sp500_performance}")
        except Exception as e:
            print(f"⚠️ S&P500 数据获取失败: {e}")
            sp500_performance = "数据不可用"
        
        # 1.7 风险事件
        try:
            rss_url = "https://news.google.com/rss/search?q=cryptocurrency+crisis+OR+exchange+collapse+OR+regulation&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            news_titles = [entry.title for entry in feed.entries[:5]]
            news_text = "\n".join([f"- {title}" for title in news_titles])
            
            prompt = f"""根据以下新闻，判断是否存在重大风险事件或黑天鹅：
{news_text}
请用简短格式回答，例如: "无明显风险" 或 "某交易所爆雷" 或 "监管收紧"
"""
            response = model.generate_content(prompt)
            risk_events = response.text.strip()
        except:
            risk_events = "未检测到"
        
        # 2. 汇总宏观数据
        macro_data = {
            "美元指数 (DXY)": f"{dxy_value}, {dxy_trend}",
            "Fed 利率政策": fed_policy,
            "BTC ETF 净流入": etf_flow,
            "长期持有者行为": holder_behavior,
            "挖矿生产成本": mining_cost,
            "美股表现 (S&P500)": sp500_performance,
            "风险事件": risk_events
        }
        
        # 3. 使用规则评分系统计算概率
        scorer = ScenarioScorer()
        probabilities = scorer.calculate_scenario_scores(macro_data)
        most_likely = scorer.get_most_likely_scenario(probabilities)
        
        # 4. 用 AI 生成详细分析和操作建议
        scenario_names = {
            "scenario_1": "情景 1: V型反转",
            "scenario_2": "情景 2: 高位横盘",
            "scenario_3": "情景 3: 缓慢熊市",
            "scenario_4": "情景 4: 深度熊市"
        }
        
        # 构建概率摘要
        prob_summary = "\n".join([
            f"- {scenario_names[k]}: {v['probability']}%"
            for k, v in probabilities.items()
        ])
        
        analysis_prompt = f"""
你是一位专业的加密货币宏观分析师。

【当前宏观数据】
{json.dumps(macro_data, ensure_ascii=False, indent=2)}

【规则评分系统计算的概率】
{prob_summary}

【最可能情景】
{most_likely['name']} ({most_likely['probability']}%)

请基于以上数据和概率分析，生成详细的操作建议。

请以 JSON 格式输出：
{{
  "价格目标预期": "$XX,XXX - $XX,XXX",
  "操作建议": {{
    "仓位管理": "具体建议（考虑最可能情景）",
    "止损位": "$XX,XXX",
    "止盈位": "$XX,XXX 或 分批止盈策略"
  }},
  "综合分析": "详细说明当前市场状态，为什么各情景有相应概率，重点分析最可能的情景",
  "风险提示": "针对当前情景的风险警告"
}}
"""
        
        try:
            ai_response = model.generate_content(analysis_prompt)
            cleaned_text = re.sub(r'```json\s*', '', ai_response.text).replace('```', '').strip()
            ai_analysis = json.loads(cleaned_text)
        except:
            ai_analysis = {
                "价格目标预期": "数据不足",
                "操作建议": {
                    "仓位管理": "建议观望",
                    "止损位": "待定",
                    "止盈位": "待定"
                },
                "综合分析": "AI分析生成失败，请参考概率数据",
                "风险提示": "数据不完整，谨慎操作"
            }
        
        # 5. 组装返回结果
        return {
            "macro_data": macro_data,
            "scenario_probabilities": {
                scenario_names[k]: {
                    "probability": f"{v['probability']}%",
                    "raw_score": f"{v['raw_score']}/100",
                    "matched_factors": v['details']['matched'],
                    "unmatched_factors": v['details']['unmatched']
                }
                for k, v in probabilities.items()
            },
            "most_likely_scenario": {
                "name": most_likely['name'],
                "probability": f"{most_likely['probability']}%"
            },
            "ai_analysis": ai_analysis,
            "calculation_method": "rule_based_scoring_plus_ai"
        }
        
    except Exception as e:
        print(f"Scenario Analysis Error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))