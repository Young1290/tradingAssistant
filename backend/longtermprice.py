import requests
import pandas as pd
import json

# 1. 目标 URL
# 注意：这个 URL 结尾必须是 /_dash-update-component
# 如果报错 404，请回到 Network 标签，点击 headers，复制 Request URL 的完整路径
url = "https://www.bitcoinmagazinepro.com/django_plotly_dash/app/realized_price_lth/_dash-update-component"

# 2. 请求头 (必须伪装)
headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Content-Type": "application/json",
    # Origin 和 Referer 有时候是防盗链的关键
    "Origin": "https://www.bitcoinmagazinepro.com",
    "Referer": "https://www.bitcoinmagazinepro.com/charts/long-term-holder-realized-price/"
}

# 3. 请求体 (Payload) - 你的截图同款
# 这里完全使用了你截图中 "Request Payload" 的内容
payload = {
    "output": "chart.figure",
    "outputs": {"id": "chart", "property": "figure"},
    "changedPropIds": ["url.pathname", "display.children"],
    "inputs": [
        {"id": "url", "property": "pathname", "value": "/charts/long-term-holder-realized-price/"},
        # 这里的 sm 670px 是你浏览器当前的宽度参数，服务器可能会根据这个调整图表大小
        {"id": "display", "property": "children", "value": "sm 670px"}
    ]
}

print("正在发送请求...")

try:
    response = requests.post(url, headers=headers, json=payload)
    
    if response.status_code == 200:
        json_data = response.json()
        
        # 4. 数据解析 (基于 Screenshot 4.14.45 PM 的 Preview 结构)
        # 结构路径：response -> chart -> figure -> data -> [数组]
        # 数组[0] 是 BTC Price (黑色线)
        # 数组[1] 通常是 Long Term Holder Price (橙色线)
        
        # 为了稳健，我们直接定位到 'data' 列表
        try:
            series_list = json_data['response']['chart']['figure']['data']
        except KeyError:
            # 备用路径 (有时候结构会少一层)
            series_list = json_data.get('figure', {}).get('data', [])

        print(f"找到 {len(series_list)} 条数据线")

        # 遍历找到我们想要的那条线
        for item in series_list:
            name = item.get('name', 'Unknown')
            print(f"正在处理: {name}")
            
            # 通常我们要保存 'BTC Price' 和指标线
            # 这里演示保存第一条线 (通常是 BTC Price)
            if 'x' in item and 'y' in item:
                x_data = item['x']
                y_data = item['y']
                
                # 检查数组长度
                print(f"  数据点数: x={len(x_data)}, y={len(y_data)}")
                
                # 确保长度一致
                min_len = min(len(x_data), len(y_data))
                if len(x_data) != len(y_data):
                    print(f"  ⚠️ 警告: x和y长度不同，截取到 {min_len} 条")
                    x_data = x_data[:min_len]
                    y_data = y_data[:min_len]
                
                df = pd.DataFrame({
                    'date': x_data,
                    'value': y_data,
                    'type': name
                })
                
                # 保存文件
                filename = f"btc_{name.replace(' ', '_')}.csv"
                df.to_csv(filename, index=False)
                print(f"✅ 已保存: {filename} (最后5行如下)")
                print(df.tail())
                print("-" * 30)

    else:
        print(f"❌ 请求失败: {response.status_code}")
        print(response.text[:200])

except Exception as e:
    print(f"❌ 发生错误: {e}")