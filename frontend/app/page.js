'use client';
import { useState, useEffect } from 'react';
import { Chart } from '../components/Chart';
import ScenarioAnalysis from '../components/ScenarioAnalysis';

export default function Home() {
  const [symbol, setSymbol] = useState('BTC/USDT');
  const [marketData, setMarketData] = useState([]);
  const [aiAnalysis, setAiAnalysis] = useState(null);
  const [loading, setLoading] = useState(false);
  const [news, setNews] = useState([]);
  const [fng, setFng] = useState(null);
  const [uiSignals, setUiSignals] = useState(null);

  // Tab 切换和情景分析
  const [activeTab, setActiveTab] = useState('ai-analysis'); // 'ai-analysis' | 'scenario-analysis'
  const [scenarioData, setScenarioData] = useState(null);
  const [scenarioLoading, setScenarioLoading] = useState(false);

  // 1. 颜色映射
  const getColor = (status) => {
    if (!status) return '#9ca3af'; // 默认灰色
    if (status === 'bullish') return '#22c55e'; // 鲜绿
    if (status === 'weak_bullish') return '#86efac'; // 浅绿
    if (status === 'bearish') return '#ef4444'; // 鲜红
    if (status === 'weak_bearish') return '#fca5a5'; // 浅红
    return '#9ca3af'; // neutral 灰色
  };

  // 2. 文字映射
  const getStatusText = (status) => {
    if (!status) return '加载中';
    if (status === 'bullish') return '强势看涨';
    if (status === 'weak_bullish') return '弱势看涨';
    if (status === 'bearish') return '趋势看空'; // 对于日线，这代表熊市
    if (status === 'weak_bearish') return '弱势回调';
    return '震荡整理';
  };

  // 1. 獲取市場數據
  const fetchMarketData = async () => {
    try {
      const safeSymbol = symbol.replace('/', '-'); // 簡單處理 URL
      const res = await fetch(`http://127.0.0.1:8000/api/market-data/${safeSymbol}`);
      const json = await res.json();
      setMarketData(json.data);
    } catch (error) {
      console.error("Failed to fetch data", error);
    }
  };

  // 2. 獲取 AI 分析
  const askAI = async () => {
    setLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol })
      });
      const json = await res.json();
      setAiAnalysis(json.analysis);
      setNews(json.news || []);
      setFng(json.fng);
      setUiSignals(json.ui_signals || null);
    } catch (error) {
      setAiAnalysis("分析失败，请检查后端连接。");
    }
    setLoading(false);
  };

  // 3. 获取情景分析
  const fetchScenarioAnalysis = async () => {
    setScenarioLoading(true);
    try {
      const res = await fetch('http://127.0.0.1:8000/api/scenario-analysis', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: symbol })
      });
      const json = await res.json();
      setScenarioData(json);
    } catch (error) {
      console.error("情景分析失败", error);
      setScenarioData({ error: "分析失败，请检查后端连接。" });
    }
    setScenarioLoading(false);
  };

  useEffect(() => {
    fetchMarketData();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center p-8 bg-gray-100">
      <h1 className="text-4xl font-bold mb-8 text-blue-800">加密货币 AI 交易助手</h1>

      {/* 控制区 */}
      <div className="w-full max-w-6xl mb-8">
        <div className="flex gap-4 mb-4">
          <select
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            className="p-2 border rounded text-black"
          >
            <option value="BTC/USDT">比特币 (BTC/USDT)</option>
            <option value="ETH/USDT">以太坊 (ETH/USDT)</option>
            <option value="SOL/USDT">Solana (SOL/USDT)</option>
          </select>

          <button
            onClick={fetchMarketData}
            className="bg-blue-500 text-white px-4 py-2 rounded hover:bg-blue-600"
          >
            刷新图表
          </button>

          <button
            onClick={askAI}
            className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
            disabled={loading}
          >
            {loading ? '🤖 思考中...' : '询问 🤖 AI'}
          </button>

          <button
            onClick={fetchScenarioAnalysis}
            className="bg-gradient-to-r from-orange-500 to-red-600 text-white px-4 py-2 rounded hover:from-orange-600 hover:to-red-700 font-semibold"
            disabled={scenarioLoading}
          >
            {scenarioLoading ? '📊 分析中...' : '获取情景分析'}
          </button>
        </div>

        {/* Tab 导航 */}
        <div className="flex gap-2 border-b border-gray-300">
          <button
            onClick={() => setActiveTab('ai-analysis')}
            className={`px-6 py-3 font-semibold transition-all ${activeTab === 'ai-analysis'
              ? 'border-b-2 border-purple-600 text-purple-600 bg-purple-50'
              : 'text-gray-600 hover:text-purple-600 hover:bg-gray-50'
              }`}
          >
            🤖 AI 分析
          </button>
          <button
            onClick={() => setActiveTab('scenario-analysis')}
            className={`px-6 py-3 font-semibold transition-all ${activeTab === 'scenario-analysis'
              ? 'border-b-2 border-orange-600 text-orange-600 bg-orange-50'
              : 'text-gray-600 hover:text-orange-600 hover:bg-gray-50'
              }`}
          >
            📊 情景分析
          </button>
        </div>
      </div>

      {/* Tab 内容区 */}
      {activeTab === 'ai-analysis' && (
        <>
          {/* 图表区 */}
          <div className="w-full max-w-4xl bg-white p-4 rounded-xl shadow-lg mb-6">
            {marketData.length > 0 ? (
              <Chart data={marketData} />
            ) : (
              <p className="text-center p-10 text-gray-500">加载数据中...</p>
            )}
          </div>

          {/* 多周期共振雷达 - 双脑模式优化版 */}
          {uiSignals && (
            <div className="w-full max-w-4xl mb-6 bg-gradient-to-br from-slate-900 to-slate-800 p-6 rounded-xl shadow-2xl border border-slate-700">
              <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <span className="text-2xl">📡</span>
                多周期趋势雷达
              </h3>

              <div className="grid grid-cols-4 gap-4">
                {[
                  // 1. 周线 (新增)
                  { key: '1w', label: '周线 (历史)', desc: '长期大周期' },
                  // 2. 日线 (核心)
                  { key: '1d', label: '日线 (大势)', desc: 'SMA200 牛熊判定' },
                  // 3. 4小时
                  { key: '4h', label: '4小时 (中线)', desc: '波段方向' },
                  // 4. 1小时 (最小关注)
                  { key: '1h', label: '1小时 (入场)', desc: '执行周期' }
                ].map(({ key, label, desc }) => {
                  // 获取状态颜色
                  const status = uiSignals[key];
                  const color = getColor(status);

                  // 特殊处理：如果是日线，加粗边框以示重要
                  const isMacro = key === '1d';

                  return (
                    <div
                      key={key}
                      className={`
                    relative rounded-lg p-3 border-2 transition-all hover:scale-105
                    ${isMacro ? 'bg-slate-800 border-yellow-500/30' : 'bg-slate-800/50'}
                  `}
                      style={{
                        borderColor: isMacro ? undefined : color, // 日线用金色微光，其他用信号色
                        boxShadow: isMacro ? '0 0 15px rgba(234, 179, 8, 0.1)' : 'none'
                      }}
                    >
                      {/* 顶部标签 */}
                      <div className={`text-xs mb-2 font-bold ${isMacro ? 'text-yellow-400' : 'text-gray-400'}`}>
                        {label}
                      </div>

                      {/* 信号灯图标 */}
                      <div
                        className="w-10 h-10 rounded-full mx-auto mb-2 flex items-center justify-center text-xl shadow-lg transition-colors duration-300"
                        style={{
                          backgroundColor: `${color}20`, // 20% 透明度背景
                          border: `2px solid ${color}`,
                          boxShadow: `0 0 10px ${color}60`
                        }}
                      >
                        {/* 根据状态显示不同图标 */}
                        {status.includes('bullish') ? '🟢' :
                          status.includes('bearish') ? '🔴' : '⚪'}
                      </div>

                      {/* 状态文字 */}
                      <div className="text-white text-xs text-center font-bold mb-1">
                        {getStatusText(status)}
                      </div>

                      {/* 底部辅助说明 (新增) */}
                      <div className="text-[10px] text-gray-500 text-center leading-tight transform scale-90">
                        {desc}
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="mt-4 flex justify-between items-center text-xs text-gray-400 px-2">
                <span>💡 策略逻辑: 大周期定方向(日线)，小周期找共振(1H)</span>
                <div className="flex gap-3">
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-green-500"></span>看涨</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500"></span>看跌</span>
                  <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-gray-400"></span>震荡</span>
                </div>
              </div>
            </div>
          )}

          {/* 恐惧贪婪指数 */}
          {fng && (
            <div className="w-full max-w-4xl mb-6 flex items-center p-4 bg-slate-800 rounded-lg border border-slate-700">
              <div className="mr-4">
                <span className="text-gray-400 text-sm">市场情绪指数</span>
                <div className={`text-3xl font-bold ${parseInt(fng.value) > 75 ? 'text-green-500' :
                  parseInt(fng.value) < 25 ? 'text-red-500' : 'text-yellow-500'
                  }`}>
                  {fng.value}
                </div>
              </div>
              <div className="flex-1">
                {/* 进度条背景 */}
                <div className="h-4 w-full bg-gray-700 rounded-full overflow-hidden">
                  {/* 动态进度条 */}
                  <div
                    className={`h-full ${parseInt(fng.value) > 50 ? 'bg-gradient-to-r from-yellow-500 to-green-500' : 'bg-gradient-to-r from-red-500 to-yellow-500'
                      }`}
                    style={{ width: `${fng.value}%`, transition: 'width 1s ease-in-out' }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>0 (恐慌)</span>
                  <span className="text-white font-bold">{fng.value_classification}</span>
                  <span>100 (贪婪)</span>
                </div>
              </div>
            </div>
          )}

          {/* AI 分析结果区 (JSON格式) */}
          {aiAnalysis && typeof aiAnalysis === 'object' && (
            <div className="w-full max-w-4xl bg-white p-6 rounded-xl shadow-lg border-l-4 border-purple-500">
              <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center gap-2">
                <span className="text-2xl">🤖</span>
                AI 交易建议
              </h2>

              {/* 操作方向 */}
              <div className="mb-6 p-4 rounded-lg" style={{
                backgroundColor: aiAnalysis.direction === '做多' ? '#dcfce7' :
                  aiAnalysis.direction === '做空' ? '#fee2e2' : '#f3f4f6'
              }}>
                <div className="text-sm text-gray-600 mb-1">操作方向</div>
                <div className="text-3xl font-bold" style={{
                  color: aiAnalysis.direction === '做多' ? '#16a34a' :
                    aiAnalysis.direction === '做空' ? '#dc2626' : '#6b7280'
                }}>
                  {aiAnalysis.direction}
                </div>
              </div>

              {/* 共振分析 */}
              <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-sm font-semibold text-blue-900 mb-2">📊 多周期共振分析</div>
                <div className="text-gray-700">{aiAnalysis.mtf_summary}</div>
              </div>

              {/* 三维评分系统 */}
              {(aiAnalysis.technical_score || aiAnalysis.sentiment_score || aiAnalysis.news_score) && (
                <div className="mb-4 grid grid-cols-3 gap-3">
                  <div className="p-3 bg-gradient-to-br from-blue-50 to-blue-100 rounded-lg border border-blue-200">
                    <div className="text-xs text-blue-700 mb-1">技术面</div>
                    <div className="text-2xl font-bold text-blue-900">{aiAnalysis.technical_score}/10</div>
                  </div>
                  <div className="p-3 bg-gradient-to-br from-purple-50 to-purple-100 rounded-lg border border-purple-200">
                    <div className="text-xs text-purple-700 mb-1">情绪面</div>
                    <div className="text-2xl font-bold text-purple-900">{aiAnalysis.sentiment_score}/10</div>
                  </div>
                  <div className="p-3 bg-gradient-to-br from-green-50 to-green-100 rounded-lg border border-green-200">
                    <div className="text-xs text-green-700 mb-1">消息面</div>
                    <div className="text-2xl font-bold text-green-900">{aiAnalysis.news_score}/10</div>
                  </div>
                </div>
              )}

              {/* 交易参数 */}
              <div className="grid grid-cols-3 gap-4 mb-4">
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-xs text-gray-500 mb-1">入场点位</div>
                  <div className="text-lg font-bold text-green-600">{aiAnalysis.entry_price}</div>
                </div>
                <div className="p-3 bg-gray-50 rounded-lg">
                  <div className="text-xs text-gray-500 mb-1">止损点位</div>
                  <div className="text-lg font-bold text-red-600">{aiAnalysis.stop_loss}</div>
                </div>
                {aiAnalysis.target_price && (
                  <div className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500 mb-1">目标点位</div>
                    <div className="text-lg font-bold text-blue-600">{aiAnalysis.target_price}</div>
                  </div>
                )}
              </div>

              {/* 持仓建议 */}
              {aiAnalysis.position_size && (
                <div className="mb-4 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div className="text-xs text-yellow-700 mb-1">持仓建议</div>
                  <div className="text-lg font-bold text-yellow-900">{aiAnalysis.position_size}</div>
                </div>
              )}

              {/* 信心指数 */}
              <div className="mb-4">
                <div className="text-sm text-gray-600 mb-2 flex justify-between">
                  <span>综合信心指数</span>
                  <span className="font-bold">{aiAnalysis.confidence}/10</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div
                    className="h-3 rounded-full transition-all"
                    style={{
                      width: `${aiAnalysis.confidence * 10}%`,
                      background: aiAnalysis.confidence >= 7 ? 'linear-gradient(to right, #22c55e, #16a34a)' :
                        aiAnalysis.confidence >= 5 ? 'linear-gradient(to right, #eab308, #ca8a04)' :
                          'linear-gradient(to right, #ef4444, #dc2626)'
                    }}
                  ></div>
                </div>
              </div>

              {/* 详细分析理由 */}
              <div className="p-5 bg-gradient-to-br from-purple-50 to-indigo-50 rounded-lg border border-purple-200">
                <div className="text-base font-bold text-purple-900 mb-3 flex items-center gap-2">
                  <span>💡</span>
                  <span>详细分析理由</span>
                </div>
                <div className="text-gray-800 text-sm leading-relaxed whitespace-pre-wrap" style={{
                  lineHeight: '1.8'
                }}>
                  {aiAnalysis.reasoning}
                </div>
              </div>
            </div>
          )}

          {/* 文本格式分析（完整显示所有内容）*/}
          {aiAnalysis && typeof aiAnalysis === 'string' && (
            <div className="w-full max-w-4xl bg-white p-6 rounded-xl shadow-lg border-l-4 border-purple-500">
              <h2 className="text-xl font-bold mb-4 text-gray-800 flex items-center gap-2">
                <span className="text-2xl">🤖</span>
                AI 完整分析报告
              </h2>
              <div className="prose prose-sm max-w-none text-gray-700">
                <div className="whitespace-pre-wrap leading-relaxed" style={{
                  fontSize: '0.95rem',
                  lineHeight: '1.8'
                }}>
                  {aiAnalysis}
                </div>
              </div>
              <div className="mt-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
                <div className="text-xs text-blue-700">
                  💡 提示: AI返回了详细的文本分析，包含综合评分、量价分析、支撑阻力位等完整信息
                </div>
              </div>
            </div>
          )}
          {news.length > 0 && (
            <div className="w-full max-w-4xl mt-6 bg-white p-6 rounded-xl shadow-lg">
              <h3 className="font-bold text-gray-800 mb-4 text-lg">📢 相关市场新闻 (AI 已读取)</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full border-collapse">
                  <thead>
                    <tr className="bg-slate-100">
                      <th className="border border-slate-300 px-4 py-2 text-left text-sm font-semibold text-gray-700">新闻标题</th>
                      <th className="border border-slate-300 px-4 py-2 text-left text-sm font-semibold text-gray-700">发布时间</th>
                      <th className="border border-slate-300 px-4 py-2 text-center text-sm font-semibold text-gray-700">链接</th>
                    </tr>
                  </thead>
                  <tbody>
                    {news.map((item, index) => (
                      <tr key={index} className="hover:bg-slate-50">
                        <td className="border border-slate-300 px-4 py-2 text-sm text-gray-700">{item.title}</td>
                        <td className="border border-slate-300 px-4 py-2 text-sm text-gray-600 whitespace-nowrap">{item.published}</td>
                        <td className="border border-slate-300 px-4 py-2 text-center">
                          <a
                            href={item.link}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800 underline text-sm"
                          >
                            查看
                          </a>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      {/* 情景分析 Tab 内容 */}
      {activeTab === 'scenario-analysis' && (
        <ScenarioAnalysis data={scenarioData} loading={scenarioLoading} />
      )}
    </main>
  );
}