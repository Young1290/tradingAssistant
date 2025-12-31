#!/usr/bin/env python3
"""
CryptoQuant API 链上数据获取模块
用于获取 Bitcoin 持有者行为、交易所余额等链上指标
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()


class CryptoQuantAPI:
    """CryptoQuant API 封装类"""
    
    def __init__(self, api_key=None):
        """
        初始化 CryptoQuant API
        
        Args:
            api_key: CryptoQuant API key (如果不提供，从环境变量获取)
        """
        self.base_url = "https://api.cryptoquant.com/v1"
        self.api_key = api_key or os.getenv("CRYPTOQUANT_API_KEY")
        
        if not self.api_key:
            print("⚠️ 警告: 未找到 CRYPTOQUANT_API_KEY")
            print("   请在 .env 文件中添加: CRYPTOQUANT_API_KEY=your_key_here")
            print("   或者访问: https://cryptoquant.com/docs/api 获取 API Key")
    
    def _make_request(self, endpoint, params=None):
        """
        发送 API 请求
        
        Args:
            endpoint: API 端点，例如 '/btc/exchange-flows/reserve'
            params: 查询参数
            
        Returns:
            dict: API 响应数据
        """
        if not self.api_key:
            raise ValueError("API Key 未设置，无法进行请求")
        
        headers = {
            'Authorization': f'Bearer {self.api_key}'
        }
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # CryptoQuant 的数据通常在 'result' -> 'data' 里
            if 'result' in data and 'data' in data['result']:
                return data['result']['data']
            else:
                return data
                
        except requests.exceptions.HTTPError as e:
            if response.status_code == 401:
                print("❌ API Key 无效或已过期")
            elif response.status_code == 403:
                print("❌ 权限不足，请检查订阅计划")
            elif response.status_code == 429:
                print("❌ API 请求限制，请稍后再试")
            else:
                print(f"❌ HTTP 错误: {response.status_code}")
            print(f"   详情: {response.text}")
            raise
        except Exception as e:
            print(f"❌ 请求失败: {e}")
            raise
    
    def get_exchange_reserve(self, window='day', limit=30):
        """
        获取交易所 BTC 余额
        余额减少 = 投资者提币到冷钱包 (看涨信号)
        余额增加 = 投资者准备卖出 (看跌信号)
        
        Args:
            window: 时间窗口 ('day', 'week', 'month')
            limit: 返回的数据点数量
            
        Returns:
            pd.DataFrame: 交易所余额数据
        """
        endpoint = "/btc/exchange-flows/reserve"
        params = {
            'window': window,
            'limit': limit
        }
        
        data = self._make_request(endpoint, params)
        df = pd.DataFrame(data)
        
        # 转换时间戳
        if 'datetime' in df.columns:
            df['datetime'] = pd.to_datetime(df['datetime'])
        
        return df
    
    def get_long_term_holder_supply(self, window='day', limit=30):
        """
        获取长期持有者供应量 (持有 155 天以上)
        供应增加 = 长期持有者积累 (看涨)
        供应减少 = 长期持有者抛售 (看跌)
        
        Args:
            window: 时间窗口
            limit: 返回的数据点数量
            
        Returns:
            pd.DataFrame: 长期持有者供应数据
        """
        # 注意：实际的端点可能不同，需要根据 CryptoQuant 文档调整
        endpoint = "/btc/market-indicator/lth-supply"
        params = {
            'window': window,
            'limit': limit
        }
        
        try:
            data = self._make_request(endpoint, params)
            df = pd.DataFrame(data)
            
            if 'datetime' in df.columns:
                df['datetime'] = pd.to_datetime(df['datetime'])
            
            return df
        except Exception as e:
            print(f"⚠️ 无法获取长期持有者数据: {e}")
            return pd.DataFrame()
    
    def get_holder_behavior_summary(self):
        """
        生成持有者行为汇总（中文描述）
        用于集成到 main.py 的情景分析
        
        Returns:
            str: 中文描述，例如 "30天抛售 45万枚，抛压减缓"
        """
        try:
            # 获取最近 30 天的交易所余额变化
            df_reserve = self.get_exchange_reserve(window='day', limit=30)
            
            if df_reserve.empty:
                return "链上数据不可用"
            
            # 假设数据列为 'value' (实际列名可能不同)
            value_col = None
            for col in ['value', 'reserve', 'balance', 'amount']:
                if col in df_reserve.columns:
                    value_col = col
                    break
            
            if value_col is None:
                return "数据格式错误"
            
            # 计算最近 7 天和 30 天的变化
            recent_7_change = df_reserve[value_col].iloc[-1] - df_reserve[value_col].iloc[-7]
            recent_30_change = df_reserve[value_col].iloc[-1] - df_reserve[value_col].iloc[0]
            
            # 生成描述
            if recent_7_change < -50000:  # 交易所余额减少 5万+ BTC
                behavior = "大量提币，积累信号强烈"
            elif recent_7_change < -10000:
                behavior = "持续提币，停止抛售"
            elif recent_7_change > 50000:
                behavior = "大量充值，抛压加剧"
            elif recent_7_change > 10000:
                behavior = "小幅充值，抛售放缓"
            else:
                behavior = "交易所余额稳定"
            
            # 计算 30 天趋势
            if recent_30_change < 0:
                trend = f"30天净流出 {abs(recent_30_change/10000):.1f}万枚"
            else:
                trend = f"30天净流入 {recent_30_change/10000:.1f}万枚"
            
            return f"{trend}；{behavior}"
            
        except Exception as e:
            print(f"⚠️ 生成持有者行为汇总失败: {e}")
            return "链上数据获取失败"


def get_holder_behavior_summary():
    """
    简化接口：获取持有者行为汇总
    供 main.py 调用
    
    Returns:
        str: 中文描述
    """
    try:
        api = CryptoQuantAPI()
        return api.get_holder_behavior_summary()
    except Exception as e:
        return f"数据不可用 (错误: {str(e)})"


# 测试代码
if __name__ == "__main__":
    print("=" * 60)
    print("CryptoQuant API 测试")
    print("=" * 60)
    
    api = CryptoQuantAPI()
    
    if not api.api_key:
        print("\n❌ 请先设置 CRYPTOQUANT_API_KEY")
        print("   在 .env 文件中添加:")
        print("   CRYPTOQUANT_API_KEY=your_key_here")
        print("\n如何获取 API Key:")
        print("   1. 访问 https://cryptoquant.com/")
        print("   2. 注册账号")
        print("   3. 前往 https://cryptoquant.com/docs/api")
        print("   4. 生成 API Key (免费账户有限额)")
    else:
        print(f"\n✓ API Key 已配置: {api.api_key[:10]}...")
        
        try:
            # 测试持有者行为汇总
            print("\n【持有者行为汇总】")
            summary = api.get_holder_behavior_summary()
            print(f"  {summary}")
            
            # 测试交易所余额
            print("\n【交易所余额 (最近 7 天)】")
            df_reserve = api.get_exchange_reserve(limit=7)
            if not df_reserve.empty:
                print(df_reserve.tail())
            
        except Exception as e:
            print(f"\n❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
