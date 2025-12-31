#!/usr/bin/env python3
"""
BTC 情景评分系统 - 透明的规则评分机制
基于 ScenarioRules.md 中的情景触发条件
"""

class ScenarioScorer:
    """
    情景评分器 - 根据宏观数据计算每个情景的匹配分数
    """
    
    def __init__(self):
        # 定义各维度的权重（总和 = 100）
        self.weights = {
            "fed_policy": 20,      # Fed 政策
            "holder_behavior": 25, # 持有者行为
            "etf_flow": 15,        # ETF 资金流
            "logic_support": 10,   # 逻辑支撑
            "tech_level": 15,      # 关键技术位
            "stock_correlation": 15 # 美股关联
        }
    
    def calculate_scenario_scores(self, macro_data):
        """
        计算所有情景的分数
        
        Args:
            macro_data: dict, 包含所有宏观数据
            
        Returns:
            dict: 每个情景的分数和详细分析
        """
        # 提取数据（转小写便于匹配）
        fed_policy = macro_data.get("Fed 利率政策", "").lower()
        holder_behavior = macro_data.get("长期持有者行为", "").lower()
        etf_flow = macro_data.get("BTC ETF 净流入", "").lower()
        mining_cost = macro_data.get("挖矿生产成本", "")
        sp500 = macro_data.get("美股表现 (S&P500)", "").lower()
        risk_events = macro_data.get("风险事件", "").lower()
        
        # 计算每个情景的分数
        scores = {
            "scenario_1": self._score_scenario_1(fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events),
            "scenario_2": self._score_scenario_2(fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events),
            "scenario_3": self._score_scenario_3(fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events),
            "scenario_4": self._score_scenario_4(fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events)
        }
        
        # 归一化为概率
        probabilities = self._normalize_to_probabilities(scores)
        
        return probabilities
    
    def _score_scenario_1(self, fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events):
        """
        情景 1: V型反转
        触发条件：QE + 停止抛售 + 流入>$1B + 信用对冲 + $100K守住 + 美股爆涨
        """
        score = 0
        details = {"matched": [], "unmatched": []}
        
        # 1. Fed 政策 (权重 20)
        if "qe" in fed_policy or "量化宽松" in fed_policy:
            score += 20
            details["matched"].append("Fed开启QE")
        elif "降息" in fed_policy:
            score += 8  # 部分符合
            details["matched"].append("Fed降息（部分符合）")
        else:
            details["unmatched"].append("Fed未开启QE")
        
        # 2. 持有者行为 (权重 25)
        if "停止抛售" in holder_behavior or "积累" in holder_behavior:
            score += 25
            details["matched"].append("长期持有者停止抛售")
        elif "减缓" in holder_behavior:
            score += 15
            details["matched"].append("抛售减缓（部分符合）")
        else:
            details["unmatched"].append("长期持有者未停止抛售")
        
        # 3. ETF 资金流 (权重 15)
        if "流入" in etf_flow and ("1b" in etf_flow or "10亿" in etf_flow):
            score += 15
            details["matched"].append("ETF单周流入>$1B")
        elif "流入" in etf_flow:
            score += 10
            details["matched"].append("ETF有流入（部分符合）")
        else:
            details["unmatched"].append("ETF未见大额流入")
        
        # 4. 逻辑支撑 - 信用对冲 + 机构抢筹 (权重 10)
        # 通过持有者行为和ETF流入推断
        if ("积累" in holder_behavior or "抢筹" in holder_behavior) and "流入" in etf_flow:
            score += 10
            details["matched"].append("机构抢筹迹象")
        else:
            details["unmatched"].append("未见机构大规模抢筹")
        
        # 5. 关键技术位 - $100K 守住并 V 反 (权重 15)
        # 需要实际价格数据，这里简化判断
        # 如果没有明确跌破信号，给予部分分数
        score += 5  # 默认给部分分
        details["unmatched"].append("$100K守住需实际价格确认")
        
        # 6. 美股关联 (权重 15)
        if "爆涨" in sp500 or "新高" in sp500 or "大涨" in sp500:
            score += 15
            details["matched"].append("美股爆涨")
        elif "上涨" in sp500 or "微涨" in sp500:
            score += 8
            details["matched"].append("美股上涨（部分符合）")
        else:
            details["unmatched"].append("美股未爆涨")
        
        return {"score": score, "details": details}
    
    def _score_scenario_2(self, fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events):
        """
        情景 2: 高位横盘
        触发条件：仅降息不QE + 抛售放缓 + 小幅波动 + 矿工挺价 + $94K守住 + 美股走平
        """
        score = 0
        details = {"matched": [], "unmatched": []}
        
        # 1. Fed 政策 (权重 20)
        if "降息" in fed_policy and "qe" not in fed_policy and "量化宽松" not in fed_policy:
            score += 20
            details["matched"].append("Fed仅降息，不QE")
        elif "降息" in fed_policy:
            score += 15
            details["matched"].append("Fed降息（部分符合）")
        elif "维持" in fed_policy or "不变" in fed_policy:
            score += 10
            details["matched"].append("利率维持（部分符合）")
        else:
            details["unmatched"].append("Fed政策不符合")
        
        # 2. 持有者行为 (权重 25)
        if "放缓" in holder_behavior:
            score += 25
            details["matched"].append("抛售放缓")
        elif "停止" in holder_behavior or "积累" in holder_behavior:
            score += 20  # 更积极，也算部分符合
            details["matched"].append("停止抛售/积累（更积极）")
        elif "减缓" in holder_behavior:
            score += 15
            details["matched"].append("抛压减缓（部分符合）")
        else:
            details["unmatched"].append("持有者行为不符合")
        
        # 3. ETF 资金流 (权重 15)
        if "小幅" in etf_flow or "波动" in etf_flow or "不明确" in etf_flow:
            score += 15
            details["matched"].append("ETF小幅波动或数据不明确")
        elif "流出" not in etf_flow and "流入" not in etf_flow:
            score += 10
            details["matched"].append("无明显单边流动（部分符合）")
        else:
            details["unmatched"].append("ETF出现单边大量流动")
        
        # 4. 逻辑支撑 - 矿工挺价 (权重 10)
        if "$94" in mining_cost or "94000" in mining_cost:
            score += 10
            details["matched"].append("挖矿成本$94K支撑")
        else:
            score += 5
            details["matched"].append("有挖矿成本支撑（部分）")
        
        # 5. 关键技术位 - $94K 守住 (权重 15)
        # 基于挖矿成本和持有者行为推断
        if "$94" in mining_cost and ("停止" in holder_behavior or "积累" in holder_behavior):
            score += 15
            details["matched"].append("$94K关键支撑守住")
        else:
            score += 8
            details["matched"].append("技术位支撑存在（部分）")
        
        # 6. 美股关联 (权重 15)
        if "走平" in sp500 or "震荡" in sp500 or "微涨" in sp500:
            score += 15
            details["matched"].append("美股走平或微涨")
        elif "下跌" in sp500 or "下滑" in sp500:
            score += 8  # 下跌也可能导致横盘
            details["matched"].append("美股下跌（可能增加波动）")
        else:
            details["unmatched"].append("美股表现不符合")
        
        return {"score": score, "details": details}
    
    def _score_scenario_3(self, fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events):
        """
        情景 3: 缓慢熊市
        触发条件：利率不变 + 抛售加速 + 流出>$2B + 预期透支 + 跌破$94K/$90K + 美股下跌
        """
        score = 0
        details = {"matched": [], "unmatched": []}
        
        # 1. Fed 政策 (权重 20)
        if "维持" in fed_policy or "不变" in fed_policy:
            score += 20
            details["matched"].append("Fed维持利率不变")
        elif "降息" not in fed_policy and "加息" not in fed_policy:
            score += 10
            details["matched"].append("Fed无明显宽松（部分符合）")
        else:
            details["unmatched"].append("Fed政策不符合")
        
        # 2. 持有者行为 (权重 25)
        if "加速" in holder_behavior and "抛售" in holder_behavior:
            score += 25
            details["matched"].append("抛售加速")
        elif "抛售" in holder_behavior:
            score += 15
            details["matched"].append("有抛售行为（部分符合）")
        else:
            details["unmatched"].append("未见抛售加速")
        
        # 3. ETF 资金流 (权重 15)
        if "流出" in etf_flow and ("2b" in etf_flow or "20亿" in etf_flow or "3b" in etf_flow):
            score += 15
            details["matched"].append("ETF单月流出>$2B")
        elif "流出" in etf_flow:
            score += 10
            details["matched"].append("ETF有流出（部分符合）")
        else:
            details["unmatched"].append("ETF未见大额流出")
        
        # 4. 逻辑支撑 - 预期透支 + 老玩家离场 (权重 10)
        if "离场" in holder_behavior or "抛售" in holder_behavior:
            score += 10
            details["matched"].append("老玩家离场迹象")
        else:
            details["unmatched"].append("未见老玩家离场")
        
        # 5. 关键技术位 - 跌破 $94K/$90K (权重 15)
        # 需要实际价格数据，这里基于其他信号推断
        if "流出" in etf_flow and "抛售" in holder_behavior:
            score += 10  # 有压力但不确定
            details["matched"].append("技术位面临压力（推断）")
        else:
            details["unmatched"].append("技术位跌破需价格确认")
        
        # 6. 美股关联 (权重 15)
        if "下跌" in sp500 or "下滑" in sp500 or "回撤" in sp500:
            score += 15
            details["matched"].append("美股下跌")
        elif "震荡" in sp500:
            score += 8
            details["matched"].append("美股震荡（部分符合）")
        else:
            details["unmatched"].append("美股未下跌")
        
        return {"score": score, "details": details}
    
    def _score_scenario_4(self, fed_policy, holder_behavior, etf_flow, mining_cost, sp500, risk_events):
        """
        情景 4: 深度熊市
        触发条件：衰退+政策失败 + 恐慌抛售 + 流出>$5B + 系统性风险 + 跌破$85K + 美股泡沫破灭
        """
        score = 0
        details = {"matched": [], "unmatched": []}
        
        # 1. Fed 政策 (权重 20)
        if "衰退" in fed_policy or "失败" in fed_policy or "紧急" in fed_policy:
            score += 20
            details["matched"].append("经济衰退+政策失败")
        elif "加息" in fed_policy:
            score += 10
            details["matched"].append("Fed加息（部分符合）")
        else:
            details["unmatched"].append("未见衰退或政策失败")
        
        # 2. 持有者行为 (权重 25)
        if "恐慌" in holder_behavior or ("大量" in holder_behavior and "抛售" in holder_behavior):
            score += 25
            details["matched"].append("恐慌性抛售")
        elif "抛售" in holder_behavior and "加速" in holder_behavior:
            score += 15
            details["matched"].append("抛售加速（部分符合）")
        else:
            details["unmatched"].append("未见恐慌抛售")
        
        # 3. ETF 资金流 (权重 15)
        if "流出" in etf_flow and ("5b" in etf_flow or "50亿" in etf_flow or "10b" in etf_flow):
            score += 15
            details["matched"].append("ETF单月流出>$5B")
        elif "流出" in etf_flow and ("大量" in etf_flow or "巨额" in etf_flow):
            score += 10
            details["matched"].append("ETF大量流出（部分符合）")
        else:
            details["unmatched"].append("ETF未见巨额流出")
        
        # 4. 逻辑支撑 - 系统性风险 + 泡沫破灭 (权重 10)
        if "系统" in risk_events or "危机" in risk_events or "爆雷" in risk_events or "崩盘" in risk_events:
            score += 10
            details["matched"].append("系统性风险")
        else:
            details["unmatched"].append("未见系统性风险")
        
        # 5. 关键技术位 - 跌破 $85K (权重 15)
        # 极端情况才会发生
        if "崩盘" in holder_behavior or "恐慌" in etf_flow:
            score += 8
            details["matched"].append("技术位面临极端压力（推断）")
        else:
            details["unmatched"].append("$85K跌破需极端情况")
        
        # 6. 美股关联 (权重 15)
        if "泡沫" in sp500 or "崩盘" in sp500 or "暴跌" in sp500:
            score += 15
            details["matched"].append("美股泡沫破灭")
        elif "大跌" in sp500 or "重挫" in sp500:
            score += 10
            details["matched"].append("美股大跌（部分符合）")
        else:
            details["unmatched"].append("美股未崩盘")
        
        return {"score": score, "details": details}
    
    def _normalize_to_probabilities(self, scores):
        """
        将分数归一化为概率（总和100%）
        """
        # 提取分数
        total_score = sum(s["score"] for s in scores.values())
        
        if total_score == 0:
            # 如果所有分数都是0，平均分配
            probabilities = {k: {"probability": 25, "score": v["score"], "details": v["details"]} 
                           for k, v in scores.items()}
        else:
            # 归一化
            probabilities = {
                k: {
                    "probability": round((v["score"] / total_score) * 100, 1),
                    "raw_score": v["score"],
                    "details": v["details"]
                }
                for k, v in scores.items()
            }
        
        return probabilities
    
    def get_most_likely_scenario(self, probabilities):
        """
        获取最可能的情景
        """
        max_prob = max(probabilities.values(), key=lambda x: x["probability"])
        scenario_name = [k for k, v in probabilities.items() if v["probability"] == max_prob["probability"]][0]
        
        scenario_names = {
            "scenario_1": "情景 1: V型反转",
            "scenario_2": "情景 2: 高位横盘",
            "scenario_3": "情景 3: 缓慢熊市",
            "scenario_4": "情景 4: 深度熊市"
        }
        
        return {
            "name": scenario_names[scenario_name],
            "probability": max_prob["probability"],
            "raw_score": max_prob["raw_score"]
        }
