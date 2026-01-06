"""
使用 CoinGecko API 获取 Bitcoin 市场数据
完全免费，每分钟 10-50 次请求，无需 API Key
"""

import requests
import json
import pandas as pd
from datetime import datetime

print("=" * 70)
print("Bitcoin Market Data - CoinGecko API")
print("=" * 70)

# ============================================
# 1. Bitcoin 详细市场数据
# ============================================
print("\n【Bitcoin 市场数据】")
print("-" * 70)

try:
    url = "https://api.coingecko.com/api/v3/coins/bitcoin"
    params = {
        "localization": "false",
        "tickers": "false",
        "community_data": "false",
        "developer_data": "false"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        market = data.get('market_data', {})
        
        # 当前价格
        current_price = market.get('current_price', {}).get('usd', 0)
        print(f"\n💰 当前价格: ${current_price:,.2f}")
        
        # 24小时变化
        change_24h = market.get('price_change_percentage_24h', 0)
        emoji = "📈" if change_24h > 0 else "📉"
        print(f"{emoji} 24h 变化: {change_24h:+.2f}%")
        
        # 市场数据
        print(f"\n📊 市场数据:")
        print(f"  市值: ${market.get('market_cap', {}).get('usd', 0):,.0f}")
        print(f"  24h 交易量: ${market.get('total_volume', {}).get('usd', 0):,.0f}")
        print(f"  流通量: {market.get('circulating_supply', 0):,.0f} BTC")
        print(f"  总量: {market.get('total_supply', 0):,.0f} BTC")
        
        # 价格变化趋势
        print(f"\n📈 价格变化:")
        changes = {
            "1小时": market.get('price_change_percentage_1h_in_currency', {}).get('usd', 0),
            "24小时": market.get('price_change_percentage_24h', 0),
            "7天": market.get('price_change_percentage_7d', 0),
            "30天": market.get('price_change_percentage_30d', 0),
            "1年": market.get('price_change_percentage_1y', 0)
        }
        
        for period, change in changes.items():
            emoji = "🟢" if change > 0 else "🔴"
            print(f"  {emoji} {period:6s}: {change:+7.2f}%")
        
        # ATH/ATL 数据
        print(f"\n📊 历史记录:")
        ath = market.get('ath', {}).get('usd', 0)
        ath_change = market.get('ath_change_percentage', {}).get('usd', 0)
        print(f"  历史最高 (ATH): ${ath:,.2f} (距离: {ath_change:.2f}%)")
        
        atl = market.get('atl', {}).get('usd', 0)
        atl_change = market.get('atl_change_percentage', {}).get('usd', 0)
        print(f"  历史最低 (ATL): ${atl:,.2f} (增长: {atl_change:+.0f}%)")
        
    else:
        print(f"❌ 请求失败: {response.status_code}")
        if response.status_code == 429:
            print("  提示: 速率限制，请等待1分钟后重试")
        
except Exception as e:
    print(f"❌ 错误: {e}")

# ============================================
# 2. Top 交易所 BTC 交易量
# ============================================
print("\n【Top 10 交易所 BTC 交易量】")
print("-" * 70)

try:
    url = "https://api.coingecko.com/api/v3/coins/bitcoin/tickers"
    params = {
        "order": "volume_desc",
        "depth": "true"
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        data = response.json()
        tickers = data.get('tickers', [])[:10]
        
        print(f"\n{'排名':<4} {'交易所':<20} {'交易对':<15} {'价格 (USD)':<15} {'24h交易量 (BTC)'}")
        print("-" * 70)
        
        for i, ticker in enumerate(tickers, 1):
            exchange = ticker.get('market', {}).get('name', 'Unknown')
            pair = f"{ticker.get('base', '')}/{ticker.get('target', '')}"
            volume = ticker.get('volume', 0)
            price = ticker.get('last', 0)
            
            print(f"{i:<4} {exchange:<20} {pair:<15} ${price:<14,.2f} {volume:>16,.2f}")
        
        # 总交易量
        total_volume = sum(t.get('volume', 0) for t in tickers)
        print("-" * 70)
        print(f"{'Top 10 总交易量':<54} {total_volume:>16,.2f} BTC")
        
    else:
        print(f"❌ 请求失败: {response.status_code}")
        
except Exception as e:
    print(f"❌ 错误: {e}")

# ============================================
# 3. 保存数据到 CSV
# ============================================
print("\n【保存数据】")
print("-" * 70)

try:
    # 保存市场数据
    market_data = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'price': current_price,
        'change_24h': change_24h,
        'market_cap': market.get('market_cap', {}).get('usd', 0),
        'volume_24h': market.get('total_volume', {}).get('usd', 0),
        'circulating_supply': market.get('circulating_supply', 0)
    }
    
    df = pd.DataFrame([market_data])
    filename = "btc_market_data.csv"
    
    # 追加模式保存（如果文件存在）
    import os
    if os.path.exists(filename):
        df.to_csv(filename, mode='a', header=False, index=False)
        print(f"✅ 数据已追加到: {filename}")
    else:
        df.to_csv(filename, index=False)
        print(f"✅ 数据已保存到: {filename}")
    
    print(f"   最新记录: {len(df)} 条")
    
except Exception as e:
    print(f"⚠️ 保存数据时出错: {e}")

print("\n" + "=" * 70)
print("✅ CoinGecko 数据获取完成！")
print("=" * 70)

# API 使用提示
print("\n💡 CoinGecko API 使用提示:")
print("  - 免费额度: 10-50 次/分钟")
print("  - 无需 API Key")
print("  - 数据更新频率: 实时")
print("  - 文档: https://www.coingecko.com/en/api/documentation")