// 情景分析组件
export default function ScenarioAnalysis({ data, loading }) {
    if (loading) {
        return (
            <div className="w-full max-w-6xl">
                <div className="bg-white p-8 rounded-xl shadow-lg text-center">
                    <div className="animate-spin inline-block w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full mb-4"></div>
                    <p className="text-gray-600">正在获取宏观数据并进行情景分析...</p>
                    <p className="text-sm text-gray-400 mt-2">这可能需要30-60秒</p>
                </div>
            </div>
        );
    }

    if (!data) {
        return (
            <div className="w-full max-w-6xl">
                <div className="bg-white p-8 rounded-xl shadow-lg text-center">
                    <p className="text-gray-500">点击"获取情景分析"按钮开始分析</p>
                </div>
            </div>
        );
    }

    if (data.error) {
        return (
            <div className="w-full max-w-6xl">
                <div className="bg-red-50 border-2 border-red-300 p-6 rounded-xl">
                    <p className="text-red-700">❌ {data.error}</p>
                </div>
            </div>
        );
    }

    const scenarios = data.scenario_probabilities || {};
    const mostLikely = data.most_likely_scenario || {};
    const macroData = data.macro_data || {};
    const aiAnalysis = data.ai_analysis || {};

    // 情景颜色映射
    const scenarioColors = {
        "情景 1: V型反转": { bg: "#dcfce7", border: "#22c55e", text: "#166534" },
        "情景 2: 高位横盘": { bg: "#dbeafe", border: "#3b82f6", text: "#1e40af" },
        "情景 3: 缓慢熊市": { bg: "#fef3c7", border: "#f59e0b", text: "#92400e" },
        "情景 4: 深度熊市": { bg: "#fee2e2", border: "#ef4444", text: "#991b1b" }
    };

    return (
        <div className="w-full max-w-6xl space-y-6">
            {/* 宏观数据总览 */}
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 p-6 rounded-xl shadow-2xl border border-slate-700">
                <h3 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                    <span className="text-2xl">📊</span>
                    当前宏观数据
                </h3>
                <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                    {Object.entries(macroData).map(([key, value]) => (
                        <div key={key} className="bg-slate-700/50 p-3 rounded-lg">
                            <div className="text-xs text-gray-400 mb-1">{key}</div>
                            <div className="text-sm text-white font-medium">{value}</div>
                        </div>
                    ))}
                </div>
            </div>

            {/* 最可能情景高亮 */}
            <div className="bg-gradient-to-r from-blue-500 to-purple-600 p-6 rounded-xl shadow-2xl text-white">
                <h3 className="text-2xl font-bold mb-2 flex items-center gap-2">
                    <span>🎯</span>
                    最可能情景
                </h3>
                <div className="text-4xl font-bold mb-2">{mostLikely.name}</div>
                <div className="text-2xl font-semibold">概率: {mostLikely.probability}</div>
            </div>

            {/* 四大情景概率分析 */}
            <div className="bg-white p-6 rounded-xl shadow-lg">
                <h3 className="text-xl font-bold text-gray-800 mb-6 flex items-center gap-2">
                    <span className="text-2xl">📈</span>
                    四大情景概率分布
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
                    {Object.entries(scenarios).map(([scenarioName, info]) => {
                        const colors = scenarioColors[scenarioName] || { bg: "#f3f4f6", border: "#9ca3af", text: "#374151" };
                        const probability = parseFloat(info.probability.replace('%', ''));

                        return (
                            <div
                                key={scenarioName}
                                className="border-2 rounded-lg p-4"
                                style={{
                                    borderColor: colors.border,
                                    backgroundColor: colors.bg
                                }}
                            >
                                <div className="flex justify-between items-center mb-2">
                                    <h4 className="font-bold text-lg" style={{ color: colors.text }}>
                                        {scenarioName}
                                    </h4>
                                    <span className="text-2xl font-bold" style={{ color: colors.text }}>
                                        {info.probability}
                                    </span>
                                </div>

                                {/* 概率进度条 */}
                                <div className="w-full bg-gray-200 rounded-full h-4 mb-3">
                                    <div
                                        className="h-4 rounded-full transition-all duration-500"
                                        style={{
                                            width: `${probability}%`,
                                            backgroundColor: colors.border
                                        }}
                                    ></div>
                                </div>

                                <div className="text-xs mb-2" style={{ color: colors.text }}>
                                    原始分数: {info.raw_score}
                                </div>

                                {/* 匹配因素 */}
                                {info.matched_factors && info.matched_factors.length > 0 && (
                                    <div className="mt-3">
                                        <div className="text-xs font-semibold mb-1" style={{ color: colors.text }}>
                                            ✅ 匹配因素:
                                        </div>
                                        <ul className="text-xs space-y-1">
                                            {info.matched_factors.slice(0, 3).map((factor, idx) => (
                                                <li key={idx} className="text-gray-700">• {factor}</li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        );
                    })}
                </div>

                {/* 概率分布饼图（简化版 - 使用CSS） */}
                <div className="mt-6 p-4 bg-gray-50 rounded-lg">
                    <h4 className="font-semibold text-gray-800 mb-3 text-center">概率可视化</h4>
                    <div className="flex items-center justify-center gap-2 flex-wrap">
                        {Object.entries(scenarios).map(([scenarioName, info]) => {
                            const colors = scenarioColors[scenarioName];
                            const probability = parseFloat(info.probability.replace('%', ''));

                            return (
                                <div key={scenarioName} className="flex items-center gap-2">
                                    <div
                                        className="w-4 h-4 rounded-full"
                                        style={{ backgroundColor: colors.border }}
                                    ></div>
                                    <span className="text-sm text-gray-700">
                                        {scenarioName.split(':')[1]}: {probability}%
                                    </span>
                                </div>
                            );
                        })}
                    </div>
                </div>
            </div>

            {/* AI 详细分析 */}
            <div className="bg-white p-6 rounded-xl shadow-lg border-l-4 border-purple-500">
                <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                    <span className="text-2xl">🤖</span>
                    AI 综合分析与操作建议
                </h3>

                {/* 价格目标 */}
                <div className="mb-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                    <div className="text-sm text-blue-700 mb-1 font-semibold">价格目标预期</div>
                    <div className="text-2xl font-bold text-blue-900">{aiAnalysis.价格目标预期}</div>
                </div>

                {/* 操作建议 */}
                <div className="mb-4 p-4 bg-green-50 rounded-lg border border-green-200">
                    <div className="text-sm text-green-700 mb-2 font-semibold">💼 操作建议</div>
                    <div className="space-y-2 text-gray-700">
                        <div>
                            <span className="font-semibold">仓位管理:</span> {aiAnalysis.操作建议?.仓位管理}
                        </div>
                        <div className="grid grid-cols-2 gap-4 mt-2">
                            <div className="p-2 bg-white rounded border border-green-300">
                                <div className="text-xs text-gray-500">止损位</div>
                                <div className="font-bold text-red-600">{aiAnalysis.操作建议?.止损位}</div>
                            </div>
                            <div className="p-2 bg-white rounded border border-green-300">
                                <div className="text-xs text-gray-500">止盈位</div>
                                <div className="font-bold text-green-600">{aiAnalysis.操作建议?.止盈位}</div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* 综合分析 */}
                <div className="mb-4 p-4 bg-purple-50 rounded-lg border border-purple-200">
                    <div className="text-sm text-purple-700 mb-2 font-semibold">💡 综合分析</div>
                    <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-line">
                        {aiAnalysis.综合分析}
                    </div>
                </div>

                {/* 风险提示 */}
                <div className="p-4 bg-red-50 rounded-lg border border-red-200">
                    <div className="text-sm text-red-700 mb-2 font-semibold">⚠️ 风险提示</div>
                    <div className="text- text-gray-700 leading-relaxed">
                        {aiAnalysis.风险提示}
                    </div>
                </div>
            </div>

            {/* 计算方法说明 */}
            <div className="bg-gray-100 p-4 rounded-lg text-xs text-gray-600">
                <div className="font-semibold mb-1">📚 计算方法</div>
                <div>使用透明的规则评分系统计算概率（Fed政策、持有者行为、ETF流动、逻辑支撑、技术位、美股关联），结合AI生成详细分析</div>
                <div className="mt-1">数据来源：Google News RSS + AI实时分析</div>
            </div>
        </div>
    );
}
