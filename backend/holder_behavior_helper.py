#!/usr/bin/env python3
"""
链上数据辅助模块 - 为 main.py 提供的简化接口
"""

from cryptoquant_api import get_holder_behavior_summary as cq_get_summary


def get_holder_behavior_summary():
    """
    获取持有者行为汇总（带备用方案）
    
    Returns:
        str: 中文描述，例如 "30天抛售 45万枚，抛压减缓"
    """
    # 方案 1: 尝试从 CryptoQuant 获取真实链上数据
    try:
        summary = cq_get_summary()
        
        # 如果返回的是错误信息，尝试备用方案
        if "错误" in summary or "不可用" in summary:
            raise Exception("CryptoQuant 数据不可用")
        
        return summary
    except Exception as e:
        # 方案 2: 备用方案 - 使用新闻分析
        print(f"⚠️ CryptoQuant 获取失败，使用备用方案: {e}")
        
        try:
            import feedparser
            import google.generativeai as genai
            import os
            from dotenv import load_dotenv
            
            load_dotenv()
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            rss_url = "https://news.google.com/rss/search?q=Bitcoin+long+term+holders+selling&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(rss_url)
            news_titles = [entry.title for entry in feed.entries[:3]]
            news_text = "\n".join([f"- {title}" for title in news_titles])
            
            prompt = f"""根据以下新闻，判断长期持有者是在抛售还是持有：
{news_text}
请用简短格式回答，例如: "30天抛售 45万枚，抛压减缓" 或 "停止抛售" 或 "大量抛售"
"""
            response = model.generate_content(prompt)
            return response.text.strip()
        except:
            return "数据不可用"


if __name__ == "__main__":
    # 测试
    print("【持有者行为汇总测试】")
    result = get_holder_behavior_summary()
    print(f"结果: {result}")
