import yfinance as yf
import pandas as pd
import ta
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

# 忽略警告
warnings.filterwarnings('ignore')
sns.set_theme(style="darkgrid")
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['axes.unicode_minus'] = False

# --- 1. 数据加载 (修改为 2020-01-01 开始) ---
def load_data():
    print("⬇️ 正在从 Yahoo Finance 下载 BTC 数据 (2020 - 2025)...")
    
    # 🔥 修改点：指定 start="2020-01-01"
    df = yf.download("BTC-USD", start="2020-01-01", interval="1d", progress=False)
    
    if df.empty:
        print("❌ 数据下载失败")
        return None
        
    # --- 数据清洗 ---
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    
    df.columns = [c.lower() for c in df.columns]
    
    if 'date' in df.columns:
        df['time'] = pd.to_datetime(df['date'])
        df.set_index('time', inplace=True)
    elif isinstance(df.index, pd.DatetimeIndex):
        df.index.name = 'time'
    
    cols = ['open', 'high', 'low', 'close', 'volume']
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors='coerce')
            
    print(f"✅ 数据加载完成: {len(df)} 条 | 时间: {df.index.min().date()} -> {df.index.max().date()}")
    return df

# --- 2. 计算指标 ---
def prepare_indicators(df):
    df['SMA50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
    df['SMA200'] = ta.trend.SMAIndicator(close=df['close'], window=200).sma_indicator()
    df['RSI'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    
    df['SMA200_Slope'] = (df['SMA200'] - df['SMA200'].shift(5)) / df['SMA200'].shift(5) * 100
    df['SMA200_Dev'] = (df['close'] - df['SMA200']) / df['SMA200'] * 100
    
    # 🔥 关键修改：只有价格在 SMA200 之上，才配叫牛市！
    # 去掉了 "OR Slope > 0"。斜率再好，跌破了线就是熊。
    df['Is_Bull'] = df['close'] > df['SMA200']
    
    return df.dropna()

# --- 3. 回测引擎 (保持 V6 逻辑不变) ---
def run_backtest(df, initial_capital=10000, fee_rate=0.001):
    print("🚀 开始回测 (严格风控版)...")
    
    balance = initial_capital
    btc_held = 0
    equity_curve = []
    trades = []
    in_position = False
    
    for i in range(len(df)):
        row = df.iloc[i]
        price = row['close']
        date = df.index[i]
        
        # 因子
        is_bull = row['Is_Bull'] # 现在只代表 Price > SMA200
        slope = row['SMA200_Slope']
        dev = row['SMA200_Dev']
        rsi = row['RSI']
        sma50 = row['SMA50']
        
        signal = "HOLD"
        
        # --- 🧠 决策逻辑 ---
        
        if is_bull: # 价格 > SMA200 (真牛市)
            # 1. 悬崖勒马: 离悬崖太近，且斜率已经不对劲了 -> 减仓/观望
            if dev < 3 and slope < 0:
                signal = "SELL"
            
            # 2. 正常持有/回调买入
            elif price < sma50 and rsi < 50:
                signal = "BUY"
            else:
                signal = "HOLD" # 只要在SMA200之上，就拿住
                
            # 建仓逻辑: 只要在牛市区且空仓，就买
            if not in_position and signal != "SELL":
                signal = "BUY"

        else: # 价格 < SMA200 (熊市/破位)
            # 🔥 铁律：跌破 SMA200 无脑止损，除非极端超跌
            
            # 1. 极端超跌 (抢反弹)
            if dev < -30: # 要求更严，跌30%才抢
                signal = "BUY"
            
            # 2. 止损/空仓 (核心改动)
            else:
                signal = "SELL"

        # --- 执行交易 ---
        if signal == "BUY" and not in_position:
            btc_held = (balance * (1 - fee_rate)) / price
            balance = 0
            in_position = True
            trades.append({'date': date, 'type': 'BUY', 'price': price})
        
        elif signal == "SELL" and in_position:
            balance = btc_held * price * (1 - fee_rate)
            btc_held = 0
            in_position = False
            trades.append({'date': date, 'type': 'SELL', 'price': price})
            
        current_equity = balance + (btc_held * price)
        equity_curve.append(current_equity)

    df['Equity'] = equity_curve
    return df, trades

# --- 4. 结果可视化 ---
def analyze_results(df, trades, initial_capital=10000):
    final_equity = df['Equity'].iloc[-1]
    total_return = (final_equity - initial_capital) / initial_capital * 100
    
    # 计算最大回撤
    df['Peak'] = df['Equity'].cummax()
    df['Drawdown'] = (df['Equity'] - df['Peak']) / df['Peak'] * 100
    max_drawdown = df['Drawdown'].min()
    
    print("\n" + "="*30)
    print("📊 策略回测报告 (2020-2025)")
    print("="*30)
    print(f"数据范围: {df.index.min().date()} 到 {df.index.max().date()}")
    print(f"初始资金: ${initial_capital:,.2f}")
    print(f"最终资金: ${final_equity:,.2f}")
    print(f"总收益率: {total_return:.2f}%")
    print(f"最大回撤: {max_drawdown:.2f}%")
    print(f"交易次数: {len(trades)}")
    
    first_price = df['close'].iloc[0]
    last_price = df['close'].iloc[-1]
    hodl_return = (last_price - first_price) / first_price * 100
    print(f"囤币不动 (HODL) 收益: {hodl_return:.2f}%")
    
    # 绘图
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]}, sharex=True)
    
    # 资金曲线
    ax1.plot(df.index, df['Equity'], label='Strategy', color='green', linewidth=2)
    ax1.plot(df.index, df['close'] / df['close'].iloc[0] * initial_capital, label='Buy & Hold (Benchmark)', color='gray', linestyle='--', alpha=0.5)
    
    ax1.set_title('Strategy vs HODL (2020-2025)', fontsize=14)
    ax1.set_ylabel('Capital ($)')
    ax1.legend()
    ax1.grid(True)
    
    # 信号点
    buy_dates = [t['date'] for t in trades if t['type'] == 'BUY']
    buy_prices = [df.loc[t['date']]['close'] for t in trades if t['type'] == 'BUY']
    sell_dates = [t['date'] for t in trades if t['type'] == 'SELL']
    sell_prices = [df.loc[t['date']]['close'] for t in trades if t['type'] == 'SELL']
    
    ax2.plot(df.index, df['close'], label='BTC Price', color='black', alpha=0.3)
    ax2.scatter(buy_dates, buy_prices, marker='^', color='green', s=80, label='Buy', zorder=5)
    ax2.scatter(sell_dates, sell_prices, marker='v', color='red', s=80, label='Sell', zorder=5)
    
    ax2.set_title('Trading Signals', fontsize=12)
    ax2.legend()
    ax2.grid(True)
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    df = load_data()
    if df is not None:
        df = prepare_indicators(df)
        df_result, trades = run_backtest(df)
        analyze_results(df_result, trades)