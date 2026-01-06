"""
长期持有者行为数据获取 - 整合多数据源
优先级: Bitcoin Magazine Pro (长期持有者实现价格) > CoinGecko (市场数据) > News AI 分析
"""

import requests
import pandas as pd

def get_lth_realized_price():
    """
    获取长期持有者实现价格 (Long-Term Holder Realized Price)
    数据源: Bitcoin Magazine Pro
    """
    try:
        url = "https://www.bitcoinmagazinepro.com/django_plotly_dash/app/realized_price_lth/_dash-update-component"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Content-Type": "application/json",
            "Origin": "https://www.bitcoinmagazinepro.com",
            "Referer": "https://www.bitcoinmagazinepro.com/charts/long-term-holder-realized-price/"
        }
        
        payload = {
            "output": "chart.figure",
            "outputs": {"id": "chart", "property": "figure"},
            "changedPropIds": ["url.pathname", "display.children"],
            "inputs": [
                {"id": "url", "property": "pathname", "value": "/charts/long-term-holder-realized-price/"},
                {"id": "display", "property": "children", "value": "sm 670px"}
            ]
        }
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        
        if response.status_code == 200:
            json_data = response.json()
            
            # 提取数据
            try:
                series_list = json_data['response']['chart']['figure']['data']
            except KeyError:
                series_list = json_data.get('figure', {}).get('data', [])
            
            # 查找 LTH Realized Price 数据
            for item in series_list:
                name = item.get('name', '')
                if 'Long-Term Holder' in name and 'x' in item and 'y' in item:
                    x_data = item['x']
                    y_data = item['y']
                    
                    # 确保长度一致
                    min_len = min(len(x_data), len(y_data))
                    if len(x_data) != len(y_data):
                        x_data = x_data[:min_len]
                        y_data = y_data[:min_len]
                    
                    # 获取最新数据
                    if min_len > 0:
                        latest_price = y_data[-1]
                        latest_date = x_data[-1]
                        
                        # 计算30天变化
                        if min_len >= 30:
                            price_30d_ago = y_data[-30]
                            change_30d = ((latest_price / price_30d_ago) - 1) * 100
                        else:
                            change_30d = 0
                        
                        return {
                            'success': True,
                            'source': 'Bitcoin Magazine Pro',
                            'lth_price': latest_price,
                            'date': latest_date,
                            'change_30d': change_30d,
                            'data_points': min_len
                        }
            
            return {'success': False, 'error': 'No LTH data found'}
            
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_coingecko_market_data():
    """
    获取 CoinGecko 市场数据作为辅助分析
    """
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin"
        params = {
            "localization": "false",
            "tickers": "false",
            "community_data": "false",
            "developer_data": "false"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            market = data.get('market_data', {})
            
            return {
                'success': True,
                'source': 'CoinGecko',
                'current_price': market.get('current_price', {}).get('usd', 0),
                'change_24h': market.get('price_change_percentage_24h', 0),
                'change_7d': market.get('price_change_percentage_7d', 0),
                'change_30d': market.get('price_change_percentage_30d', 0),
                'market_cap': market.get('market_cap', {}).get('usd', 0),
                'volume_24h': market.get('total_volume', {}).get('usd', 0)
            }
        else:
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except Exception as e:
        return {'success': False, 'error': str(e)}


def get_holder_behavior_summary():
    """
    生成长期持有者行为摘要
    整合多个数据源，优先使用链上数据
    """
    
    # 1. 尝试获取长期持有者实现价格
    lth_data = get_lth_realized_price()
    
    # 2. 获取市场数据
    market_data = get_coingecko_market_data()
    
    # 3. 生成摘要
    if lth_data.get('success') and market_data.get('success'):
        # 两个数据源都成功
        lth_price = lth_data['lth_price']
        current_price = market_data['current_price']
        change_30d = lth_data['change_30d']
        
        # 计算 MVRV ratio (市场价格 / 实现价格)
        mvrv_ratio = current_price / lth_price if lth_price > 0 else 0
        
        # 判断持有者行为
        if mvrv_ratio > 3.0:
            behavior = "大量获利抛售"
        elif mvrv_ratio > 2.0:
            behavior = "部分获利了结"
        elif mvrv_ratio > 1.5:
            behavior = "温和抛售压力"
        elif mvrv_ratio > 1.0:
            behavior = "持续持有，小幅抛售"
        else:
            behavior = "停止抛售，强力支撑"
        
        # 生成中文摘要
        summary = f"LTH实现价格${lth_price:,.0f}，MVRV {mvrv_ratio:.2f}倍；{behavior}"
        
        print(f"✓ 获取到长期持有者数据: {summary}")
        return summary
        
    elif market_data.get('success'):
        # 只有市场数据成功
        change_30d = market_data['change_30d']
        
        if change_30d > 10:
            behavior = "价格大涨，可能触发抛售"
        elif change_30d > 5:
            behavior = "价格上涨，持有为主"
        elif change_30d > 0:
            behavior = "稳定持有"
        elif change_30d > -10:
            behavior = "价格回调，坚定持有"
        else:
            behavior = "深度调整，加仓信号"
        
        summary = f"30天{change_30d:+.1f}%；{behavior}"
        
        print(f"✓ 获取到市场数据: {summary}")
        return summary
        
    else:
        # 所有数据源失败，使用新闻降级
        try:
            import feedparser
            import google.generativeai as genai
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            
            rss_url = "https://news.google.com/rss/search?q=Bitcoin+long+term+holders+selling&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            news_titles = [entry.title for entry in feed.entries[:3]]
            news_text = "\n".join([f"- {title}" for title in news_titles])
            
            prompt = f"""根据以下新闻，判断长期持有者是在抛售还是持有：
{news_text}
请用简短格式回答，例如: "30天抛售 45万枚，抛压减缓" 或 "停止抛售" 或 "大量抛售"
"""
            response = model.generate_content(prompt)
            summary = response.text.strip()
            
            print(f"⚠️ 使用新闻分析: {summary}")
            return summary
            
        except Exception as e:
            print(f"❌ 所有数据源失败: {e}")
            return "数据暂时不可用"


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("长期持有者行为数据测试")
    print("=" * 60)
    
    summary = get_holder_behavior_summary()
    print(f"\n最终摘要: {summary}")
