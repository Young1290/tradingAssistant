#!/usr/bin/env python3
"""
BTC ETF Flow Helper - 为 main.py 提供的简化接口
"""

from btc_etf_scraper import BTCETFScraper


def get_btc_etf_flow_summary():
    """
    获取 BTC ETF 流向汇总信息
    返回: 中文描述字符串，例如 "单日流入 $211.4M; 近5日累计流出 $447.7M"
    """
    try:
        scraper = BTCETFScraper()
        
        # 静默模式：不打印详细信息
        import sys
        from io import StringIO
        old_stdout = sys.stdout
        sys.stdout = StringIO()
        
        # 获取数据
        html_content = scraper.fetch_data()
        raw_df = scraper.parse_html_table(html_content)
        clean_df = scraper.clean_dataframe(raw_df)
        summary = scraper.get_flow_summary(clean_df)
        
        # 恢复输出
        sys.stdout = old_stdout
        
        return summary
    except Exception as e:
        # 如果获取失败，返回默认值
        return f"数据不可用 (错误: {str(e)})"


if __name__ == "__main__":
    # 测试
    result = get_btc_etf_flow_summary()
    print(f"BTC ETF Flow Summary: {result}")
