#!/usr/bin/env python3
"""
S&P 500 数据获取助手
从 Yahoo Finance 获取真实 S&P500 数据并生成趋势描述
"""

import requests
from datetime import datetime, timedelta


def get_sp500_performance():
    """
    获取 S&P500 最近表现并生成描述
    
    Returns:
        str: S&P500 表现描述，例如 "上涨 2.5%, 创历史新高"
    """
    try:
        # 使用 Yahoo Finance API 获取 S&P500 (^GSPC) 数据
        symbol = "^GSPC"
        
        # 计算时间范围（最近30天）
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        
        # Yahoo Finance API v8 (免费，无需API key)
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "period1": int(start_date.timestamp()),
            "period2": int(end_date.timestamp()),
            "interval": "1d"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            # 提取数据
            result = data['chart']['result'][0]
            meta = result['meta']
            quotes = result['indicators']['quote'][0]
            
            # 获取最新价格和前一天收盘价
            current_price = meta['regularMarketPrice']
            previous_close = meta['chartPreviousClose']
            
            # 获取所有收盘价用于计算趋势
            closes = quotes['close']
            # 过滤 None 值
            valid_closes = [c for c in closes if c is not None]
            
            if len(valid_closes) < 2:
                return "数据不足"
            
            # 计算涨跌幅
            change_pct = ((current_price - previous_close) / previous_close) * 100
            
            # 计算30天涨跌幅
            month_ago_price = valid_closes[0]
            month_change_pct = ((current_price - month_ago_price) / month_ago_price) * 100
            
            # 计算52周高点
            fifty_two_week_high = meta.get('fiftyTwoWeekHigh', current_price)
            distance_from_high = ((current_price - fifty_two_week_high) / fifty_two_week_high) * 100
            
            # 生成描述性文本
            description_parts = []
            
            # 1. 当日表现
            if abs(change_pct) < 0.5:
                description_parts.append("走平震荡")
            elif change_pct >= 2:
                description_parts.append(f"大涨 {change_pct:.1f}%")
            elif change_pct >= 1:
                description_parts.append(f"上涨 {change_pct:.1f}%")
            elif change_pct > 0:
                description_parts.append(f"微涨 {change_pct:.1f}%")
            elif change_pct <= -2:
                description_parts.append(f"大跌 {change_pct:.1f}%")
            elif change_pct <= -1:
                description_parts.append(f"下跌 {change_pct:.1f}%")
            else:
                description_parts.append(f"微跌 {change_pct:.1f}%")
            
            # 2. 月度趋势
            if month_change_pct >= 5:
                description_parts.append(f"近月大涨 {month_change_pct:.1f}%")
            elif month_change_pct >= 2:
                description_parts.append(f"近月上涨 {month_change_pct:.1f}%")
            elif month_change_pct <= -5:
                description_parts.append(f"近月重挫 {month_change_pct:.1f}%")
            elif month_change_pct <= -2:
                description_parts.append(f"近月下滑 {month_change_pct:.1f}%")
            
            # 3. 高点距离
            if distance_from_high >= -1:
                description_parts.append("创历史新高")
            elif distance_from_high >= -5:
                description_parts.append("接近历史高点")
            elif distance_from_high <= -15:
                description_parts.append(f"距高点回撤 {abs(distance_from_high):.1f}%")
            
            # 组合描述
            if description_parts:
                result_text = ", ".join(description_parts)
            else:
                result_text = f"当前 {current_price:.2f} 点"
            
            print(f"✓ S&P500 数据获取成功: {result_text}")
            return result_text
            
        else:
            print(f"⚠️ Yahoo Finance API 响应失败: {response.status_code}")
            return "数据不可用"
            
    except requests.Timeout:
        print("⚠️ S&P500 数据获取超时")
        return "API超时"
    except Exception as e:
        print(f"⚠️ S&P500 数据获取失败: {e}")
        return "数据不可用"


def get_sp500_raw_data():
    """
    获取 S&P500 原始数据（用于更详细的分析）
    
    Returns:
        dict: 包含价格、涨跌幅等详细数据
    """
    try:
        symbol = "^GSPC"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {
            "range": "1mo",
            "interval": "1d"
        }
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            result = data['chart']['result'][0]
            meta = result['meta']
            
            return {
                "current_price": meta['regularMarketPrice'],
                "previous_close": meta['chartPreviousClose'],
                "fifty_two_week_high": meta.get('fiftyTwoWeekHigh'),
                "fifty_two_week_low": meta.get('fiftyTwoWeekLow'),
                "change_percent": ((meta['regularMarketPrice'] - meta['chartPreviousClose']) / meta['chartPreviousClose']) * 100,
                "symbol": "S&P 500",
                "timestamp": datetime.now().isoformat()
            }
        else:
            return None
            
    except Exception as e:
        print(f"⚠️ S&P500 原始数据获取失败: {e}")
        return None


if __name__ == "__main__":
    # 测试
    print("测试 S&P500 数据获取...")
    performance = get_sp500_performance()
    print(f"S&P500 表现: {performance}")
    
    raw_data = get_sp500_raw_data()
    if raw_data:
        print(f"\\n原始数据:")
        print(f"  当前价格: ${raw_data['current_price']:.2f}")
        print(f"  涨跌幅: {raw_data['change_percent']:.2f}%")
        print(f"  52周高点: ${raw_data['fifty_two_week_high']:.2f}")
