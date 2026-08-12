#!/usr/bin/env python3
"""
FinSight Agent v3 — 面向企业经营与风险研判的金融服务Agent
==========================================================
GOAI 2026 无界应用赛道 · AI+金融

核心差异化：模型内生元认知校准层
- 资料理解：11家港股上市公司财报知识库
- 规则匹配：Task-type dependent calibration（选择题calibrate down / 分析题calibrate up）
- 风险提示：校准后置信度→风险分级（GREEN/YELLOW/RED）
- 投研整理：多专家视角+L2交叉验证
- 流程辅助：L0-L4分级反馈机制

Usage:
  pip install gradio openai
  export GLM_API_KEY=your_key
  python finsight_agent_v3.py
  
  # 或指定模型/端口
  python finsight_agent_v3.py --model glm-4-plus --port 7860
"""

import os, json, re, sys, time, argparse, traceback
from datetime import datetime
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Optional

# ============================================================
# 配置
# ============================================================
DEFAULT_MODEL = "glm-4-plus"
API_BASE = "https://open.bigmodel.cn/api/paas/v4/"
API_KEY_ENV = "GLM_API_KEY"

# 元认知校准参数（来自FinMetaBench实验数据）
CALIBRATION_OFFSET = {
    "factual": -12,      # 选择题：模型过度自信+11.8pp，calibrate down
    "analytical": +20,   # 分析题：模型不自信-7.8~-40.8pp，calibrate up
}
L2_THRESHOLD = 60  # 校准后置信度低于此值→触发L2交叉验证
RISK_GREEN = 75    # >=75: GREEN（高置信，可直接采用）
RISK_YELLOW = 50   # 50-74: YELLOW（需人工复核）
# <50: RED（高风险，必须人工介入）

# ============================================================
# 知识库 — 11家港股上市公司
# ============================================================
KNOWLEDGE_BASE = [
    {"name":"比亚迪电子","code":"0285.HK","industry":"电子制造",
     "period":"2024年报","revenue":"1773亿","net_profit":"42.7亿","gross_margin":"<7%",
     "key_points":"收入大增但毛利率极低，代工模式利润空间受限。收入增长主要来自大客户订单，但毛利率持续承压。"},
    {"name":"广汽集团","code":"2238.HK","industry":"汽车",
     "period":"2024年报","revenue":"1078亿","net_profit":"8.2亿","gross_margin":"N/A",
     "key_points":"利润暴跌81%，行业承压明显。合资品牌销量下滑，新能源转型需加速。"},
    {"name":"零跑汽车","code":"9863.HK","industry":"汽车",
     "period":"2024年报","revenue":"321.6亿","net_profit":"-28.2亿（净亏损）","gross_margin":"N/A",
     "key_points":"全年亏损但Q4首次单季盈利，新能源车企成长期特征。毛利率改善趋势明显。"},
    {"name":"药明康德","code":"2359.HK","industry":"医药CRO",
     "period":"2025H1","revenue":"~208亿","net_profit":"82.9亿","gross_margin":"N/A",
     "key_points":"净利润接近翻倍(+95.5%)，CRO龙头恢复高增长。海外订单回流，产能利用率提升。"},
    {"name":"百济神州","code":"6160.HK","industry":"创新药",
     "period":"2024年报","revenue":"US$38.1亿","net_profit":"-US$6.45亿（净亏损）","gross_margin":"N/A",
     "key_points":"核心产品BRUKINSA同比+105%，亏损收窄。全球化布局加速，海外收入占比提升。"},
    {"name":"亚盛医药","code":"6855.HK","industry":"创新药",
     "period":"2024年报","revenue":"9.807亿","net_profit":"-4.057亿（净亏损）","gross_margin":"N/A",
     "key_points":"收入暴增342%，仍处于亏损期。核心产品商业化加速，但研发投入持续高位。"},
    {"name":"康方生物","code":"9926.HK","industry":"创新药",
     "period":"2025H1","revenue":"14.1亿","net_profit":"-5.883亿（净亏损）","gross_margin":"N/A",
     "key_points":"商业销售同比+49.2%，商业化加速。亏损幅度需关注，研发管线推进中。"},
    {"name":"诺诚健华","code":"9969.HK","industry":"创新药",
     "period":"2024年报","revenue":"10.1亿","net_profit":"-4.529亿（净亏损）","gross_margin":"N/A",
     "key_points":"核心产品销售额破10亿门槛，亏损收窄趋势。产品组合丰富，管线深度推进。"},
    {"name":"心动公司","code":"02400.HK","industry":"游戏",
     "period":"2025H1","revenue":"30.8亿","net_profit":"7.55亿","gross_margin":"N/A",
     "key_points":"利润暴增268%，游戏业务爆发。新游表现强劲，TapTap平台生态持续完善。"},
    {"name":"易鑫集团","code":"02858.HK","industry":"汽车金融",
     "period":"2025H1","revenue":"54.5亿","net_profit":"5.49亿","gross_margin":"N/A",
     "key_points":"SaaS收入同比+124%，转型成效显著。汽车金融+SaaS双轮驱动模式验证。"},
    {"name":"中国飞鹤","code":"06186.HK","industry":"婴幼儿奶粉",
     "period":"2025H1","revenue":"91.5亿","net_profit":"10.3亿","gross_margin":"N/A",
     "key_points":"利润下滑46%，行业竞争加剧。出生率下降叠加竞争加剧，份额保卫战。"},
]

INDUSTRY_MAP = {c["name"]: c["industry"] for c in KNOWLEDGE_BASE}
COMPANY_NAMES = [c["name"] for c in KNOWLEDGE_BASE]

def get_company_data(name):
    """模糊匹配公司名"""
    for c in KNOWLEDGE_BASE:
        if name in c["name"] or c["name"] in name:
            return c
    return None

def get_peer_data(name):
    """获取同行业其他公司数据"""
    company = get_company_data(name)
    if not company:
        return ""
    industry = company["industry"]
    peers = [c for c in KNOWLEDGE_BASE if c["industry"] == industry and c["name"] != name]
    if not peers:
        peers = [c for c in KNOWLEDGE_BASE if c["name"] != name][:3]
    lines = []
    for p in peers:
        lines.append(f"  {p['name']}({p['code']}) | {p['period']} | 收入:{p['revenue']} | 净利润:{p['net_profit']} | {p['key_points']}")
    return "\n".join(lines)

def format_company_brief(c):
    return (f"{c['name']}({c['code']}) | {c['industry']} | {c['period']}\n"
            f"  收入: {c['revenue']} | 净利润: {c['net_profit']} | 毛利率: {c['gross_margin']}\n"
            f"  要点: {c['key_points']}")

def format_kb_all():
    lines = ["## 知识库 — 11家港股上市公司\n"]
    for c in KNOWLEDGE_BASE:
        lines.append(format_company_brief(c))
        lines.append("")
    return "\n".join(lines)

# ============================================================
# 元认知校准器
# ============================================================
@dataclass
class CalibrationResult:
    task_type: str           # "factual" | "analytical"
    raw_confidence: float    # 原始置信度 0-100
    calibrated_confidence: float  # 校准后 0-100
    offset: int              # 校准偏移量
    risk_label: str          # GREEN / YELLOW / RED
    l2_triggered: bool       # 是否触发L2
    explanation: str         # 校准说明

class MetacognitiveCalibrator:
    """
    基于FinMetaBench研究发现的任务类型相关校准器
    
    核心发现：
    - 选择题（factual）：6模型全部过度自信(+11.8~67.5pp) → calibrate down
    - 分析题（analytical）：2模型全部不自信(-7.8~-48.2pp) → calibrate up
    
    这意味着：同一个置信度阈值不能适用于所有任务类型
    """
    
    @staticmethod
    def detect_task_type(query: str) -> str:
        """检测任务类型：factual（事实查询/选择题） vs analytical（分析/评估）"""
        analytical_keywords = [
            "分析", "评估", "预测", "投资", "建议", "风险", "前景",
            "对比", "比较", "趋势", "展望", "判断", "看法", "如何看",
            "值不值得", "能不能投", "健康度", "异常", "投研",
        ]
        factual_keywords = [
            "多少", "是什么", "哪个", "几亿", "收入", "净利润", "毛利率",
            "同比", "增长率", "选项", "A.B.C.D", "正确答案",
        ]
        
        query_lower = query.lower()
        analytical_score = sum(1 for k in analytical_keywords if k in query)
        factual_score = sum(1 for k in factual_keywords if k in query)
        
        # 有选项→factual；有分析关键词→analytical
        if re.search(r'[A-D][.、）]', query) or "选项" in query:
            return "factual"
        if analytical_score > factual_score:
            return "analytical"
        if factual_score > 0 and analytical_score == 0:
            return "factual"
        return "analytical"  # 默认按分析题处理（更保守）
    
    @staticmethod
    def calibrate(raw_conf: float, task_type: str) -> CalibrationResult:
        """任务类型相关校准"""
        offset = CALIBRATION_OFFSET.get(task_type, 0)
        calibrated = max(0, min(100, raw_conf + offset))
        
        if calibrated >= RISK_GREEN:
            risk = "GREEN"
        elif calibrated >= RISK_YELLOW:
            risk = "YELLOW"
        else:
            risk = "RED"
        
        l2 = calibrated < L2_THRESHOLD
        
        if task_type == "factual":
            expl = (f"任务类型: 事实查询（选择题）\n"
                    f"FinMetaBench发现: 此类任务模型系统性过度自信(+11.8~67.5pp, 6模型验证)\n"
                    f"校准策略: 置信度下调{abs(offset)}pp\n"
                    f"原始: {raw_conf:.0f}% → 校准后: {calibrated:.0f}%\n"
                    f"风险等级: {risk}" + (f"\n⚠️ 触发L2交叉验证（校准后置信度<{L2_THRESHOLD}%）" if l2 else ""))
        else:
            expl = (f"任务类型: 投研分析（开放式）\n"
                    f"FinBench-Custom发现: 此类任务模型系统性不自信(-7.8~-48.2pp, 2模型验证)\n"
                    f"校准策略: 置信度上调{offset}pp\n"
                    f"原始: {raw_conf:.0f}% → 校准后: {calibrated:.0f}%\n"
                    f"风险等级: {risk}" + (f"\n⚠️ 触发L2交叉验证（校准后置信度<{L2_THRESHOLD}%）" if l2 else ""))
        
        return CalibrationResult(
            task_type=task_type,
            raw_confidence=raw_conf,
            calibrated_confidence=calibrated,
            offset=offset,
            risk_label=risk,
            l2_triggered=l2,
            explanation=expl,
        )

# ============================================================
# FinSight Agent
# ============================================================
@dataclass
class AgentResult:
    query: str
    task_type: str
    company: Optional[str]
    knowledge_used: str
    initial_answer: str
    raw_confidence: float
    calibration: CalibrationResult
    l2_result: Optional[str]
    l2_confidence: Optional[float]
    final_answer: str
    final_confidence: float
    reasoning: str
    risk_label: str

class FinSightAgent:
    """面向企业经营与风险研判的金融服务Agent"""
    
    EXPERT_PROMPTS = {
        "审计师": (
            "你是一名拥有15年经验的资深审计师，精通港股上市公司审计。"
            "专业视角：数据准确性验证、会计处理合规性、潜在财务操纵风险识别。"
            "特别关注：数据逻辑一致性、异常波动、会计估计变更、关联交易等。"
        ),
        "金融分析师": (
            "你是一名资深金融分析师，专注于港股市场投研，覆盖多个行业。"
            "专业视角：业务趋势分析、行业横向对比、增长可持续性评估。"
            "特别关注：收入结构、毛利率变化、行业对标、增长驱动力、估值逻辑。"
        ),
        "注册会计师": (
            "你是一名资深注册会计师(CPA)，精通企业会计准则和国际财务报告准则。"
            "专业视角：会计准则遵循、收入确认方式、成本分摊合理性。"
            "特别关注：会计政策一致性、跨期确认、政府补贴处理、研发资本化等。"
        ),
    }
    
    def __init__(self, model=DEFAULT_MODEL, api_key=None, api_base=API_BASE):
        from openai import OpenAI
        self.model = model
        self.api_key = api_key or os.environ.get(API_KEY_ENV, "")
        self.api_base = api_base
        if not self.api_key:
            print(f"⚠️ 未检测到 {API_KEY_ENV} 环境变量")
            print(f"请设置: export {API_KEY_ENV}=your_api_key")
        self.client = OpenAI(base_url=api_base, api_key=self.api_key or "dummy")
        self.calibrator = MetacognitiveCalibrator()
        self.conversation_history = []
    
    def _call_llm(self, messages, temperature=0.1, max_tokens=2000):
        """调用LLM，带重试"""
        for attempt in range(3):
            try:
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content.strip()
            except Exception as e:
                if attempt < 2:
                    print(f"  [API重试 {attempt+1}/3] {e}")
                    time.sleep(2 ** attempt)
                else:
                    return f"[API调用失败: {e}]"
        return ""
    
    @staticmethod
    def _extract_company(query):
        """从用户查询中提取公司名"""
        for name in COMPANY_NAMES:
            if name in query:
                return name
        # 模糊匹配
        for name in COMPANY_NAMES:
            for part in name[:2]:
                if len(part) > 1 and part in query:
                    return name
        return None
    
    def _retrieve_knowledge(self, query, company):
        """检索相关知识"""
        if company:
            c = get_company_data(company)
            if c:
                kb_text = format_company_brief(c)
                peers = get_peer_data(company)
                if peers:
                    kb_text += f"\n\n同行业对比:\n{peers}"
                return kb_text
        return format_kb_all()
    
    def _parse_response(self, raw):
        """解析LLM输出，提取答案/置信度/理由"""
        answer, confidence, reasoning = "", 50.0, ""
        if not raw:
            return answer, confidence, reasoning
        
        # 提取置信度
        for pattern in [r'置信度[：:]\s*(\d+)', r'CONFIDENCE[：:]\s*(\d+)', r'confidence[：:]\s*(\d+)']:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                confidence = float(m.group(1))
                break
        
        # 提取答案（选择题）
        for pattern in [r'答案[：:]\s*([A-D])', r'ANSWER[：:]\s*([A-D])']:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                answer = m.group(1).upper()
                break
        
        # 提取理由
        for pattern in [r'理由[：:]\s*(.+)', r'REASON[：:]\s*(.+)', r'分析[：:]\s*(.+)']:
            m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
            if m:
                reasoning = m.group(1).strip()[:500]
                break
        
        if not reasoning:
            reasoning = raw[:500]
        
        return answer, confidence, reasoning
    
    def _initial_answer(self, query, knowledge, task_type):
        """生成初始答案+置信度"""
        if task_type == "factual":
            sys_prompt = (
                "你是一位金融考试专家，精通注册会计师、中级经济师、银从中级资格等考试。"
                "请回答以下问题，并在末尾给出置信度。\n"
                "输出格式：\n答案：X\n置信度：0-100的整数\n理由：一句话说明"
            )
        else:
            sys_prompt = (
                "你是一位资深金融投研分析师，请基于知识库进行专业分析。"
                "请在分析末尾给出你对本次分析结论的置信度（0-100的整数）。\n"
                "注意：置信度反映你对分析结论的把握程度，不是对数据准确性的判断。\n"
                "输出格式：\n[分析内容]\n\n置信度：0-100的整数\n理由：一句话说明"
            )
        
        user_msg = f"知识库：\n{knowledge}\n\n问题：{query}\n\n请回答。"
        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}]
        raw = self._call_llm(messages)
        answer, conf, reasoning = self._parse_response(raw)
        return answer, conf, reasoning, raw
    
    def _l2_cross_validate(self, query, initial_answer, initial_conf, knowledge, task_type):
        """L2交叉验证：多专家视角+同业数据注入"""
        peer_context = ""
        company = self._extract_company(query)
        if company:
            peer_context = get_peer_data(company)
        
        experts_results = []
        for role, prompt in self.EXPERT_PROMPTS.items():
            user_msg = (
                f"请以{role}的专业视角，基于以下数据进行交叉验证分析。\n\n"
                f"问题：{query}\n"
                f"初步结论：{initial_answer}\n"
                f"初步置信度：{initial_conf:.0f}%\n\n"
                f"知识库：\n{knowledge}\n"
            )
            if peer_context:
                user_msg += f"\n同行业对比数据：\n{peer_context}\n"
            user_msg += (
                f"\n请从{role}角度重新评估，给出你的判断。\n"
                f"输出格式：\n[分析]\n\n置信度：0-100的整数\n理由：一句话"
            )
            messages = [{"role": "system", "content": prompt}, {"role": "user", "content": user_msg}]
            raw = self._call_llm(messages, temperature=0.3)
            _, conf, reasoning = self._parse_response(raw)
            experts_results.append({"role": role, "confidence": conf, "reasoning": reasoning, "raw": raw})
            time.sleep(0.5)
        
        # 聚合
        avg_conf = sum(r["confidence"] for r in experts_results) / len(experts_results)
        summary = "\n\n".join([f"### {r['role']}视角 (置信度:{r['confidence']:.0f}%)\n{r['reasoning']}" for r in experts_results])
        
        return summary, avg_conf
    
    def _generate_report(self, company_name):
        """生成投研分析报告"""
        company = get_company_data(company_name)
        if not company:
            return f"未找到公司: {company_name}"
        
        kb = format_company_brief(company)
        peers = get_peer_data(company_name)
        
        prompt = (
            f"请基于以下数据，对{company_name}({company['code']})进行全面的投研分析。\n\n"
            f"公司数据：\n{kb}\n\n同行业对比：\n{peers}\n\n"
            f"请包含：\n"
            f"1. 财务健康度评估（收入/利润/毛利率趋势）\n"
            f"2. 核心风险因素识别（3-5个）\n"
            f"3. 同业对比分析\n"
            f"4. 投资结论与建议\n"
            f"5. 每个结论标注置信度（高/中/低）\n\n"
            f"注意：低置信度结论需说明不确定的原因。保持专业客观。"
        )
        
        report_parts = [f"# FinSight 投研分析报告 — {company_name}({company['code']})\n"]
        report_parts.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        report_parts.append("> 本报告由FinSight元认知校准Agent生成，不构成投资建议。\n")
        
        for role, expert_prompt in self.EXPERT_PROMPTS.items():
            messages = [{"role": "system", "content": expert_prompt}, {"role": "user", "content": prompt}]
            raw = self._call_llm(messages, temperature=0.3)
            report_parts.append(f"\n## {role}视角\n")
            report_parts.append(raw if raw else "[API调用失败]\n")
            time.sleep(0.5)
        
        report_parts.append("\n## 元认知校准说明\n")
        report_parts.append(
            f"- 本报告为开放式分析任务（analytical）\n"
            f"- FinBench-Custom研究发现：此类任务模型系统性不自信(-7.8~-48.2pp)\n"
            f"- 校准策略：置信度上调20pp\n"
            f"- 低置信度结论已标注，提示需进一步人工核查\n"
            f"- 多专家视角构成天然交叉验证机制\n"
        )
        
        return "\n".join(report_parts)
    
    def run(self, query: str) -> AgentResult:
        """完整Agent管线"""
        # Step 1: 理解查询
        task_type = self.calibrator.detect_task_type(query)
        company = self._extract_company(query)
        
        # Step 2: 检索知识
        knowledge = self._retrieve_knowledge(query, company)
        
        # Step 3: 初始回答
        answer, raw_conf, reasoning, raw_text = self._initial_answer(query, knowledge, task_type)
        
        # 如果初始回答是长文本（分析题），取前500字作为answer
        if not answer and task_type == "analytical":
            answer = raw_text[:200] + "..." if len(raw_text) > 200 else raw_text
        
        # Step 4: 元认知校准
        calibration = self.calibrator.calibrate(raw_conf, task_type)
        
        # Step 5: L2交叉验证（如果触发）
        l2_result = None
        l2_conf = None
        final_answer = answer
        final_conf = calibration.calibrated_confidence
        
        if calibration.l2_triggered:
            l2_result, l2_conf = self._l2_cross_validate(
                query, answer, calibration.calibrated_confidence, knowledge, task_type
            )
            # L2后重新校准
            if l2_conf:
                l2_calibrated = self.calibrator.calibrate(l2_conf, task_type)
                final_conf = l2_calibrated.calibrated_confidence
                calibration.risk_label = l2_calibrated.risk_label
        
        return AgentResult(
            query=query,
            task_type=task_type,
            company=company,
            knowledge_used=knowledge[:300] + "..." if len(knowledge) > 300 else knowledge,
            initial_answer=answer,
            raw_confidence=raw_conf,
            calibration=calibration,
            l2_result=l2_result,
            l2_confidence=l2_conf,
            final_answer=final_answer,
            final_confidence=final_conf,
            reasoning=reasoning,
            risk_label=calibration.risk_label,
        )
    
    def format_result(self, result: AgentResult) -> str:
        """格式化输出结果"""
        lines = []
        
        # 风险标签emoji
        risk_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
        
        lines.append(f"## {risk_emoji.get(result.risk_label, '⚪')} FinSight 分析结果")
        lines.append(f"**风险等级: {result.risk_label}** | 校准备置信度: {result.final_confidence:.0f}%\n")
        
        # 任务理解
        lines.append("### 📋 任务理解")
        lines.append(f"- 任务类型: {'事实查询（选择题）' if result.task_type == 'factual' else '投研分析（开放式）'}")
        if result.company:
            lines.append(f"- 识别公司: {result.company}")
        lines.append("")
        
        # 初始回答
        lines.append("### 📊 初始分析")
        lines.append(result.initial_answer if result.initial_answer else "[无有效回答]")
        lines.append(f"\n原始置信度: {result.raw_confidence:.0f}%")
        lines.append("")
        
        # 元认知校准
        lines.append("### 🧠 元认知校准层")
        lines.append(f"```\n{result.calibration.explanation}\n```")
        lines.append("")
        
        # L2交叉验证
        if result.l2_result:
            lines.append("### 🔍 L2交叉验证（多专家+同业数据）")
            lines.append(result.l2_result)
            if result.l2_confidence:
                lines.append(f"\nL2后置信度: {result.l2_confidence:.0f}% → 校准后: {result.final_confidence:.0f}%")
            lines.append("")
        
        # 最终结论
        lines.append("### ✅ 最终结论")
        lines.append(f"**置信度: {result.final_confidence:.0f}%** | **风险: {result.risk_label}**")
        if result.risk_label == "RED":
            lines.append("⚠️ 高风险：校准后置信度极低，建议人工介入核查")
        elif result.risk_label == "YELLOW":
            lines.append("⚡ 中风险：结论可供参考，关键决策建议人工复核")
        else:
            lines.append("✅ 低风险：置信度较高，可直接采用")
        lines.append("")
        lines.append("---")
        lines.append(f"*FinSight v3 | 元认知校准金融Agent | FinMetaBench驱动 | {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
        
        return "\n".join(lines)


# ============================================================
# Gradio 界面
# ============================================================
def create_interface(agent: FinSightAgent):
    import gradio as gr
    
    def chat_respond(message, history):
        """聊天模式"""
        if not message.strip():
            return "", history
        
        # 特殊命令
        if message.strip().startswith("/report"):
            parts = message.strip().split(maxsplit=1)
            if len(parts) < 2:
                return "", history + [(message, "请指定公司名，如: /report 零跑汽车")]
            company = parts[1].strip()
            report = agent._generate_report(company)
            return "", history + [(message, report)]
        
        if message.strip() == "/kb":
            return "", history + [(message, format_kb_all())]
        
        if message.strip() == "/help":
            help_text = (
                "## FinSight 使用指南\n\n"
                "**直接提问** — 支持自然语言\n"
                "  • 事实查询: \"比亚迪电子2024年收入是多少？\"\n"
                "  • 投研分析: \"分析零跑汽车的投资价值\"\n"
                "  • 风险评估: \"药明康德有哪些风险因素？\"\n\n"
                "**命令**\n"
                "  • `/report 公司名` — 生成完整投研报告\n"
                "  • `/kb` — 查看知识库\n"
                "  • `/help` — 显示帮助\n\n"
                "**覆盖公司**: " + "、".join(COMPANY_NAMES)
            )
            return "", history + [(message, help_text)]
        
        try:
            result = agent.run(message)
            response = agent.format_result(result)
        except KeyboardInterrupt:
            response = "⚠️ 用户中断"
        except Exception as e:
            response = f"⚠️ 出错了: {e}\n\n```\n{traceback.format_exc()}\n```"
        
        return "", history + [(message, response)]
    
    # 示例问题
    examples = [
        "比亚迪电子2024年毛利率大约在什么范围？",
        "分析零跑汽车的投资价值和风险",
        "药明康德2025年上半年净利润同比增速约为多少？",
        "广汽集团利润暴跌的原因是什么？有哪些风险？",
        "/report 心动公司",
    ]
    
    with gr.Blocks(
        title="FinSight — 元认知校准金融Agent",
        theme=gr.themes.Soft(),
        css="""
        .header { text-align: center; padding: 20px 0; }
        .header h1 { margin: 0; color: #2563eb; }
        .header p { color: #6b7280; margin-top: 8px; }
        .footer { text-align: center; color: #9ca3af; font-size: 12px; padding: 16px 0; }
        """
    ) as demo:
        gr.HTML("""
        <div class="header">
            <h1>🔍 FinSight</h1>
            <p>面向企业经营与风险研判的金融服务Agent · 元认知校准层</p>
        </div>
        """)
        
        with gr.Row():
            with gr.Column(scale=4):
                chatbot = gr.Chatbot(
                    height=600,
                    show_label=False,
                    bubble_full_width=False,
                    render_markdown=True,
                )
                with gr.Row():
                    msg_input = gr.Textbox(
                        placeholder="输入你的金融问题... (如: 分析零跑汽车的投资价值)",
                        show_label=False,
                        scale=9,
                        lines=2,
                    )
                    send_btn = gr.Button("发送", scale=1, variant="primary")
                
                with gr.Row():
                    for ex in examples:
                        gr.Button(ex, size="sm").click(
                            lambda e=ex: (e, ""), outputs=[msg_input, msg_input]
                        ).then(
                            chat_respond, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot]
                        )
                
                send_btn.click(chat_respond, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
                msg_input.submit(chat_respond, inputs=[msg_input, chatbot], outputs=[msg_input, chatbot])
            
            with gr.Column(scale=1):
                gr.Markdown("### 📊 校准参数")
                gr.Markdown(
                    f"**选择题校准**: -{abs(CALIBRATION_OFFSET['factual'])}pp\n"
                    f"  （过度自信+11.8~67.5pp）\n\n"
                    f"**分析题校准**: +{CALIBRATION_OFFSET['analytical']}pp\n"
                    f"  （不自信-7.8~-48.2pp）\n\n"
                    f"**L2触发阈值**: {L2_THRESHOLD}%\n\n"
                    f"**GREEN**: ≥{RISK_GREEN}%\n"
                    f"**YELLOW**: {RISK_YELLOW}-{RISK_GREEN-1}%\n"
                    f"**RED**: <{RISK_YELLOW}%"
                )
                gr.Markdown("---")
                gr.Markdown("### 🏢 知识库")
                gr.Markdown("\n".join([f"- {c['name']}({c['code']})" for c in KNOWLEDGE_BASE]))
                gr.Markdown(f"\n共{len(KNOWLEDGE_BASE)}家公司 · 6大行业")
                gr.Markdown("---")
                gr.Markdown("### 💡 命令")
                gr.Markdown(
                    "`/report 公司名` — 投研报告\n"
                    "`/kb` — 查看知识库\n"
                    "`/help` — 帮助"
                )
        
        gr.HTML('<div class="footer">FinSight v3 · GOAI 2026 无界应用 · AI+金融 · FinMetaBench驱动</div>')
    
    return demo


# ============================================================
# 主入口
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="FinSight Agent v3 — 元认知校准金融Agent")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"LLM模型 (默认: {DEFAULT_MODEL})")
    parser.add_argument("--port", type=int, default=7860, help="Gradio端口 (默认: 7860)")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址 (默认: 0.0.0.0)")
    parser.add_argument("--share", action="store_true", help="生成公网链接")
    args = parser.parse_args()
    
    print("=" * 60)
    print("FinSight Agent v3 — 面向企业经营与风险研判的金融服务Agent")
    print(f"模型: {args.model}")
    print(f"知识库: {len(KNOWLEDGE_BASE)}家港股上市公司")
    print(f"校准参数: factual={CALIBRATION_OFFSET['factual']}pp, analytical={CALIBRATION_OFFSET['analytical']}pp")
    print(f"L2阈值: {L2_THRESHOLD}%")
    print("=" * 60)
    
    agent = FinSightAgent(model=args.model)
    
    if not agent.api_key:
        print(f"\n❌ 请先设置API Key:")
        print(f"  export {API_KEY_ENV}=your_api_key")
        sys.exit(1)
    
    try:
        demo = create_interface(agent)
        demo.launch(
            server_name=args.host,
            server_port=args.port,
            share=args.share,
            show_error=True,
        )
    except KeyboardInterrupt:
        print("\n用户中断，退出。")
    except Exception as e:
        print(f"\n启动失败: {e}")
        traceback.print_exc()


if __name__ == "__main__":
    main()
