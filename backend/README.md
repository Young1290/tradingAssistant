# Trading Assistant Backend API

基于 FastAPI 的加密货币交易分析 API，集成实时市场数据、链上数据和 AI 分析。

## 🚀 快速开始

### 方式 1: 本地运行

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
nano .env  # 填入您的 GEMINI_API_KEY

# 3. 启动服务
uvicorn main:app --reload --port 8000
```

访问: http://localhost:8000

### 方式 2: 使用 Docker

```bash
# 1. 配置环境变量
cp .env.example .env
nano .env

# 2. 构建并运行
docker build -t trading-assistant .
docker run -p 8000:8000 --env-file .env trading-assistant
```

### 方式 3: 一键部署脚本

```bash
chmod +x deploy.sh
./deploy.sh
```

## 📡 API 端点

### 1. 市场分析 (V6++ 策略)
```bash
POST /api/analyze
Content-Type: application/json

{
  "symbol": "BTC/USDT"
}
```

**返回**: 双周期技术分析、AI 操作建议、恐慌指数、新闻汇总

### 2. 情景分析 (宏观四大情景)
```bash
POST /api/scenario-analysis
Content-Type: application/json

{
  "symbol": "BTC/USDT"
}
```

**返回**: 
- 宏观数据 (ETF流向、持有者行为、Fed政策等)
- 四大情景概率 (V型反转、高位横盘、缓慢熊市、深度熊市)
- AI 操作建议 (仓位管理、止损止盈)

### 3. 市场数据图表
```bash
GET /api/market-data/{symbol}
```

**返回**: 日线 OHLCV + SMA50/SMA200

## 📊 数据来源

| 数据类型 | 来源 | 备用方案 |
|---------|------|----------|
| **BTC ETF 流向** | Farside Investors (爬虫) | News + AI |
| **持有者行为** | CryptoQuant API | News + AI |
| **市场价格** | Binance API | - |
| **技术指标** | ta-lib (计算) | - |
| **新闻** | Google News RSS | - |
| **恐慌指数** | alternative.me API | - |

## 🔧 环境变量

### 必需
```bash
GEMINI_API_KEY=your_gemini_api_key  # AI 分析
```

### 可选
```bash
CRYPTOQUANT_API_KEY=your_key  # 链上数据 (不设置会自动降级)
```

获取 API Key:
- Gemini: https://aistudio.google.com/apikey
- CryptoQuant: https://cryptoquant.com/docs/api

## 🚀 部署

详细部署指南请查看 [`DEPLOYMENT.md`](./DEPLOYMENT.md)

### 推荐平台

**免费开始**:
- ⭐ Render.com (推荐)
- Railway.app ($5 免费额度)

**企业级**:
- Google Cloud Run
- AWS ECS

### 快速部署到 Render

1. 推送代码到 GitHub
2. 访问 https://render.com
3. 连接仓库并配置环境变量
4. 完成！

## 📖 文档

- **部署指南**: [`DEPLOYMENT.md`](./DEPLOYMENT.md)
- **ETF 数据集成**: [`BTC_ETF_README.md`](./BTC_ETF_README.md)
- **链上数据集成**: [`CRYPTOQUANT_README.md`](./CRYPTOQUANT_README.md)
- **情景规则**: [`ScenarioRules.md`](./ScenarioRules.md)

## 🧪 测试

```bash
# 测试 ETF 数据
python3 btc_etf_flow_helper.py

# 测试 CryptoQuant 集成
python3 test_cryptoquant_integration.py

# 测试情景分析
python3 test_etf_integration.py
```

## 📦 项目结构

```
backend/
├── main.py                         # FastAPI 主程序
├── scenario_scoring.py             # 情景评分系统
├── btc_etf_scraper.py             # ETF 数据爬虫
├── btc_etf_flow_helper.py         # ETF 辅助接口
├── cryptoquant_api.py             # CryptoQuant API
├── holder_behavior_helper.py      # 持有者行为接口
├── requirements.txt               # 依赖列表
├── Dockerfile                     # Docker 配置
├── deploy.sh                      # 部署脚本
└── README.md                      # 本文件
```

## 🔐 安全提示

- ❌ 不要将 `.env` 提交到 Git
- ✅ 使用环境变量管理敏感信息
- ✅ 定期轮换 API Key
- ✅ 在生产环境添加速率限制

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可

MIT License

---

**立即开始使用！** 🚀

```bash
./deploy.sh
```
