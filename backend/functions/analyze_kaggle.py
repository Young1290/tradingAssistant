import kagglehub
import pandas as pd
import ta
import matplotlib.pyplot as plt
import seaborn as sns
import google.generativeai as genai
import os
from dotenv import load_dotenv
import warnings
import glob

# 1. 配置环境
load_dotenv()
GENAI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GENAI_API_KEY:
    print("⚠️ 警告: 未找到 GEMINI_API_KEY，AI 分析功能将无法使用")
else:
    genai.configure(api_key=GENAI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

# 忽略 Pandas 的警告
warnings.filterwarnings('ignore')

# 设置绘图风格
sns.set_theme(style="darkgrid")
plt.rcParams['font.sans-serif'] = ['Arial'] 
plt.rcParams['axes.unicode_minus'] = False

def load_and_process_kaggle_data():
    """
    下载并清洗历史数据 (更换为历史数据集)
    """
    print("⬇️ 正在从 Kaggle 下载历史数据集 (sudalairajkumar)...")
    # 更换为一个包含完整历史记录的数据集
    path = kagglehub.dataset_download("sudalairajkumar/cryptocurrencypricehistory")
    print(f"✅ 数据集下载路径: {path}")

    # 寻找比特币的文件 (文件名通常包含 Bitcoin)
    csv_files = glob.glob(f"{path}/*Bitcoin.csv")
    
    if not csv_files:
        # 备用方案：如果没有找到具体名字，尝试找任何csv
        csv_files = glob.glob(f"{path}/*.csv")
    
    if not csv_files:
        print("❌ 未找到 CSV 文件")
        return None

    # 优先读取包含 Bitcoin 的文件
    target_file = csv_files[0]
    print(f"📖 正在读取: {os.path.basename(target_file)}")
    df = pd.read_csv(target_file)
    
    # --- 1. 列名标准化 ---
    df.columns = [c.lower().strip() for c in df.columns]
    
    # --- 2. 时间列处理 ---
    # 这个数据集通常有 'date' 列
    if 'date' in df.columns:
        df.rename(columns={'date': 'time'}, inplace=True)
    elif 'timestamp' in df.columns:
        df.rename(columns={'timestamp': 'time'}, inplace=True)
    
    # 确保时间格式正确
    df['time'] = pd.to_datetime(df['time'], errors='coerce')
    df.dropna(subset=['time'], inplace=True)
    df.set_index('time', inplace=True)
    df.sort_index(inplace=True)

    # --- 3. 确保有 OHLC 数据 ---
    required_cols = ['open', 'high', 'low', 'close', 'volume']
    for col in required_cols:
        if col not in df.columns:
            # 兼容性处理：有些数据集只有 price 没有 close
            if col == 'close' and 'price' in df.columns:
                df['close'] = df['price']
            elif col == 'open':
                df['open'] = df['close'] # 如果没开盘价，暂用收盘价代替
            elif col == 'high':
                df['high'] = df['close']
            elif col == 'low':
                df['low'] = df['close']
    
    # 确保数值类型
    for c in required_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    
    df.dropna(subset=['close'], inplace=True)

    print(f"📊 数据加载完成: {len(df)} 条记录 | 时间范围: {df.index.min().date()} -> {df.index.max().date()}")
    return df

def calculate_v6_indicators(df):
    """
    计算交易策略的核心指标
    """
    # ⚠️ 安全检查：数据量是否足够计算 SMA200
    if len(df) < 200:
        print("❌ 错误: 数据量不足 200 条，无法计算长线指标。")
        return pd.DataFrame()

    print("🧮 正在计算宏观指标...")
    
    # 1. 均线系统
    df['SMA50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
    df['SMA200'] = ta.trend.SMAIndicator(close=df['close'], window=200).sma_indicator()
    
    # 2. 动能
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    # 3. 🔥 核心因子
    # 斜率
    df['SMA200_Slope'] = (df['SMA200'] - df['SMA200'].shift(5)) / df['SMA200'].shift(5) * 100
    # 乖离率
    df['SMA200_Dev'] = (df['close'] - df['SMA200']) / df['SMA200'] * 100
    
    # 4. 牛熊背景判定
    df['Bull_Regime'] = (df['close'] > df['SMA200']) | (df['SMA200_Slope'] > 0)
    
    # 去掉前200个无法计算的空值
    return df.dropna()

def visualize_analysis(df):
    if df.empty: return
    print("🎨 正在生成策略分析图...")
    
    # 只取最近 3 年的数据，看得更清楚
    subset = df.tail(1095)
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # --- 主图 ---
    ax1.plot(subset.index, subset['close'], label='BTC Price', color='#333333', linewidth=1.5)
    ax1.plot(subset.index, subset['SMA50'], label='SMA50', color='#FF9800', linestyle='--')
    ax1.plot(subset.index, subset['SMA200'], label='SMA200', color='#2196F3', linewidth=2)
    
    # 填充背景
    ax1.fill_between(subset.index, subset['close'].min(), subset['close'].max(), 
                     where=subset['Bull_Regime'], color='green', alpha=0.08, label='Bull Regime')
    ax1.fill_between(subset.index, subset['close'].min(), subset['close'].max(), 
                     where=~subset['Bull_Regime'], color='red', alpha=0.08, label='Bear Regime')

    ax1.set_title('BTC Historical Analysis (Strategy Logic)', fontsize=16)
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='upper left')
    ax1.grid(True, alpha=0.3)

    # --- 副图 ---
    ax2.plot(subset.index, subset['SMA200_Dev'], label='Deviation %', color='purple')
    ax2.axhline(0, color='black', linewidth=1)
    ax2.axhline(-20, color='green', linestyle='--', label='Deep Value (-20%)')
    ax2.fill_between(subset.index, 0, 3, color='yellow', alpha=0.3, label='Cliff Zone')
    
    ax2.legend(loc='upper left')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()

def ask_gemini_for_latest(df):
    if df.empty or not GENAI_API_KEY: return

    last_row = df.iloc[-1]
    
    # 准备数据
    price = last_row['close']
    sma200 = last_row['SMA200']
    slope = last_row['SMA200_Slope']
    dev = last_row['SMA200_Dev']
    rsi = last_row['RSI']
    is_bull = last_row['Bull_Regime']
    
    regime_desc = "🐮 牛市/强势背景" if is_bull else "🐻 熊市/弱势背景"
    slope_desc = "向上" if slope > 0 else "向下"
    
    print("\n" + "="*50)
    print(f"🤖 Gemini 历史回测诊断 (数据截止: {last_row.name.date()})")
    print("="*50)
    
    prompt = f"""
    你是一位**宏观趋势交易员**。
    这是历史回测数据的最后一天 ({last_row.name.date()})。
    请基于当前策略逻辑进行复盘。

    【数据快照】
    - 现价: ${price:.2f}
    - 宏观背景: **{regime_desc}**
    - SMA200斜率: {slope:.4f} ({slope_desc})
    - 乖离率: {dev:.2f}%
    - RSI: {rsi:.2f}
    
    【核心逻辑】
    1. 牛市回调: SMA200向上 + 跌破SMA50 + RSI低 = 买入。
    2. 悬崖勒马: 乖离率<3% = 观望。
    3. 熊市中继: SMA200向下 = 观望/卖出。
    4. 极端超跌: 乖离率<-25% = 抄底。

    请给出简短的策略评估：如果身处那一天，该怎么做？
    """
    
    try:
        response = model.generate_content(prompt)
        print(response.text)
    except Exception as e:
        print(f"AI 分析失败: {e}")

# --- 主程序 ---
if __name__ == "__main__":
    df = load_and_process_kaggle_data()
    
    if df is not None:
        df = calculate_v6_indicators(df)
        
        if not df.empty:
            print("\n📋 数据预览 (最新 5 天):")
            print(df[['close', 'SMA200', 'SMA200_Slope', 'SMA200_Dev', 'Bull_Regime']].tail())
            
            ask_gemini_for_latest(df)
            visualize_analysis(df)
        else:
            print("⚠️ 处理后数据为空，无法分析。")