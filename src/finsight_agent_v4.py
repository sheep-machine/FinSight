#!/usr/bin/env python3
"""
FinSight Agent v4 — 面向企业经营与风险研判的金融服务Agent
==========================================================
GOAI 2026 无界应用赛道 · AI+金融方向 参赛作品

核心差异化：模型内生元认知校准层 (Endogenous Metacognitive Calibration)
- 不是外部规则约束，而是模型自己知道什么时候不靠谱
- 基于FinMetaBench实证研究：6模型CFLUE过度自信+11.8~67.5pp，2模型FinBench不自信-7.8~-48.2pp
- Task-type dependent calibration reversal：同一模型在不同任务类型下校准方向相反

v4升级：
1. 专业金融Dashboard（暗色主题）
2. 可视化元认知校准过程（置信度仪表盘+校准前后对比）
3. 多步分析Pipeline可视化（任务理解→知识检索→LLM推理→校准→L2→风险分级）
4. 审计追踪（全链路时间戳记录）
5. 投研报告生成与导出
6. 多公司对比分析
7. 风险分级看板（GREEN/YELLOW/RED）

Usage:
  pip install gradio openai
  export GLM_API_KEY=your_key
  python finsight_agent_v4.py --model glm-4-plus [--share]

  # 有glm-5.2权限：
  python finsight_agent_v4.py --model glm-5.2 --share
"""

import os, json, re, sys, time, argparse, traceback, math
from datetime import datetime
from collections import Counter
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

import gradio as gr

# ============================================================
# 配置
# ============================================================
DEFAULT_MODEL = "glm-4-plus"
API_BASE = "https://open.bigmodel.cn/api/paas/v4/"
API_KEY_ENV = "GLM_API_KEY"

# 元认知校准参数（来自FinMetaBench实验数据）
CALIBRATION_OFFSET = {
    "factual": -12,      # CFLUE过度自信+11.8pp（6模型验证）
    "analytical": +20,   # FinBench-Custom不自信-7.8~-40.8pp（2模型验证）
}
L2_THRESHOLD = 60   # 校准后置信度<60% → 触发L2交叉验证
RISK_GREEN = 75     # ≥75%: GREEN（高置信，可直接采用）
RISK_YELLOW = 50    # 50-74%: YELLOW（需人工复核）
# <50%: RED（高风险，必须人工介入）

# ============================================================
# 知识库 — 11家港股上市公司
# ============================================================
KNOWLEDGE_BASE = [
    {"name":"比亚迪电子","code":"0285.HK","industry":"电子制造",
     "period":"2024年报","revenue":"1773亿","net_profit":"42.7亿","gross_margin":"<7%",
     "key_points":"收入大增但毛利率极低，代工模式利润空间受限。收入增长主要来自大客户订单，但毛利率持续承压。",
     "risk_factors":"客户集中度高|毛利率极低(<7%)|代工模式议价权弱"},
    {"name":"广汽集团","code":"2238.HK","industry":"汽车",
     "period":"2024年报","revenue":"1078亿","net_profit":"8.2亿","gross_margin":"N/A",
     "key_points":"利润暴跌81%，行业承压明显。合资品牌销量下滑，新能源转型需加速。",
     "risk_factors":"利润暴跌81%|合资品牌衰退|新能源转型滞后"},
    {"name":"零跑汽车","code":"9863.HK","industry":"汽车",
     "period":"2024年报","revenue":"321.6亿","net_profit":"-28.2亿（净亏损）","gross_margin":"N/A",
     "key_points":"全年亏损但Q4首次单季盈利，新能源车企成长期特征。毛利率改善趋势明显。",
     "risk_factors":"持续亏损|行业竞争激烈|现金流压力"},
    {"name":"药明康德","code":"2359.HK","industry":"医药CRO",
     "period":"2025H1","revenue":"~208亿","net_profit":"82.9亿","gross_margin":"N/A",
     "key_points":"净利润接近翻倍(+95.5%)，CRO龙头恢复高增长。海外订单回流，产能利用率提升。",
     "risk_factors":"地缘政治风险(中美)|订单波动|汇率敏感性"},
    {"name":"百济神州","code":"6160.HK","industry":"创新药",
     "period":"2024年报","revenue":"US$38.1亿","net_profit":"-US$6.45亿（净亏损）","gross_margin":"N/A",
     "key_points":"核心产品BRUKINSA同比+105%，亏损收窄。全球化布局加速，海外收入占比提升。",
     "risk_factors":"持续亏损|研发投入高|单一产品依赖"},
    {"name":"亚盛医药","code":"6855.HK","industry":"创新药",
     "period":"2024年报","revenue":"9.807亿","net_profit":"-4.057亿（净亏损）","gross_margin":"N/A",
     "key_points":"收入暴增342%，仍处于亏损期。核心产品商业化加速，但研发投入持续高位。",
     "risk_factors":"亏损期|收入基数小|研发投入持续高位"},
    {"name":"康方生物","code":"9926.HK","industry":"创新药",
     "period":"2025H1","revenue":"14.1亿","net_profit":"-5.883亿（净亏损）","gross_margin":"N/A",
     "key_points":"商业销售同比+49.2%，商业化加速。亏损幅度需关注，研发管线推进中。",
     "risk_factors":"亏损扩大|研发管线不确定性|商业化竞争"},
    {"name":"诺诚健华","code":"9969.HK","industry":"创新药",
     "period":"2024年报","revenue":"10.1亿","net_profit":"-4.529亿（净亏损）","gross_margin":"N/A",
     "key_points":"核心产品销售额破10亿门槛，亏损收窄趋势。产品组合丰富，管线深度推进。",
     "risk_factors":"亏损期|单一产品依赖|管线竞争激烈"},
    {"name":"心动公司","code":"02400.HK","industry":"游戏",
     "period":"2025H1","revenue":"30.8亿","net_profit":"7.55亿","gross_margin":"N/A",
     "key_points":"利润暴增268%，游戏业务爆发。新游表现强劲，TapTap平台生态持续完善。",
     "risk_factors":"产品周期性|依赖爆款|版号政策风险"},
    {"name":"易鑫集团","code":"02858.HK","industry":"汽车金融",
     "period":"2025H1","revenue":"54.5亿","net_profit":"5.49亿","gross_margin":"N/A",
     "key_points":"SaaS收入同比+124%，转型成效显著。汽车金融+SaaS双轮驱动模式验证。",
     "risk_factors":"信用风险|汽车周期性|利率敏感性"},
    {"name":"中国飞鹤","code":"06186.HK","industry":"婴幼儿奶粉",
     "period":"2025H1","revenue":"91.5亿","net_profit":"10.3亿","gross_margin":"N/A",
     "key_points":"利润下滑46%，行业竞争加剧。出生率下降叠加竞争加剧，份额保卫战。",
     "risk_factors":"出生率下降|行业竞争加剧|利润下滑46%"},
]

INDUSTRY_MAP = {c["name"]: c["industry"] for c in KNOWLEDGE_BASE}
COMPANY_NAMES = [c["name"] for c in KNOWLEDGE_BASE]

def get_company_data(name):
    for c in KNOWLEDGE_BASE:
        if name in c["name"] or c["name"] in name:
            return c
    return None

def get_peer_data(name):
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
            f"  要点: {c['key_points']}\n"
            f"  风险因素: {c.get('risk_factors','N/A')}")

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
    task_type: str
    raw_confidence: float
    calibrated_confidence: float
    offset: int
    risk_label: str
    l2_triggered: bool
    explanation: str
    evidence: str

class MetacognitiveCalibrator:
    """
    基于FinMetaBench研究发现的任务类型相关校准器
    
    核心发现（已跨模型验证）：
    - factual（选择题）：6模型全部过度自信(+11.8~67.5pp) → calibrate down 12pp
    - analytical（分析题）：2模型全部不自信(-7.8~-48.2pp) → calibrate up 20pp
    - 同一模型在同一领域内，任务类型不同→校准方向反转
    """

    EVIDENCE = {
        "factual": "6模型CFLUE实验：GLM+11.8pp, DS+16.4pp, Qwen+27.8pp, MiMo+17.3pp, Mistral+67.5pp, Step+28.1pp → 全部过度自信",
        "analytical": "FinBench-Custom实验：GLM-7.8~-40.8pp, Kimi-10.6~-48.2pp → 全部不自信",
    }
    
    @staticmethod
    def detect_task_type(query: str) -> str:
        analytical_keywords = [
            "分析", "评估", "预测", "投资", "建议", "风险", "前景",
            "对比", "比较", "趋势", "展望", "判断", "看法", "如何看",
            "值不值得", "能不能投", "健康度", "异常", "投研", "报告",
        ]
        factual_keywords = [
            "多少", "是什么", "哪个", "几亿", "收入", "净利润", "毛利率",
            "同比", "增长率", "选项", "正确答案",
        ]
        
        if re.search(r'[A-D][.、）]\s*\S', query) or "选项" in query:
            return "factual"
        
        analytical_score = sum(1 for k in analytical_keywords if k in query)
        factual_score = sum(1 for k in factual_keywords if k in query)
        
        if analytical_score > factual_score:
            return "analytical"
        if factual_score > 0 and analytical_score == 0:
            return "factual"
        return "analytical"

    @staticmethod
    def calibrate(raw_conf: float, task_type: str) -> CalibrationResult:
        offset = CALIBRATION_OFFSET.get(task_type, 0)
        calibrated = max(0, min(100, raw_conf + offset))
        
        if calibrated >= RISK_GREEN:
            risk = "GREEN"
        elif calibrated >= RISK_YELLOW:
            risk = "YELLOW"
        else:
            risk = "RED"
        
        l2 = calibrated < L2_THRESHOLD
        evidence = MetacognitiveCalibrator.EVIDENCE.get(task_type, "")
        
        if task_type == "factual":
            expl = (f"任务类型: 事实查询（选择题）\n"
                    f"实证发现: 模型系统性过度自信\n"
                    f"校准策略: 置信度下调{abs(offset)}pp\n"
                    f"原始: {raw_conf:.0f}% → 校准后: {calibrated:.0f}%")
        else:
            expl = (f"任务类型: 投研分析（开放式）\n"
                    f"实证发现: 模型系统性不自信\n"
                    f"校准策略: 置信度上调{offset}pp\n"
                    f"原始: {raw_conf:.0f}% → 校准后: {calibrated:.0f}%")
        
        if l2:
            expl += f"\n⚠️ 触发L2交叉验证（校准后置信度<{L2_THRESHOLD}%）"
        
        return CalibrationResult(
            task_type=task_type,
            raw_confidence=raw_conf,
            calibrated_confidence=calibrated,
            offset=offset,
            risk_label=risk,
            l2_triggered=l2,
            explanation=expl,
            evidence=evidence,
        )

# ============================================================
# 审计追踪
# ============================================================
@dataclass
class AuditEntry:
    timestamp: str
    step: str
    detail: str
    status: str  # "done" | "warning" | "error"

class AuditTrail:
    def __init__(self):
        self.entries: List[AuditEntry] = []
    
    def add(self, step: str, detail: str, status: str = "done"):
        self.entries.append(AuditEntry(
            timestamp=datetime.now().strftime("%H:%M:%S.%f")[:-3],
            step=step,
            detail=detail,
            status=status,
        ))
    
    def to_html(self) -> str:
        if not self.entries:
            return '<div style="color:#64748b;text-align:center;padding:20px;">等待分析任务...</div>'
        
        status_colors = {"done": "#22c55e", "warning": "#eab308", "error": "#ef4444"}
        status_icons = {"done": "✓", "warning": "⚠", "error": "✗"}
        
        rows = []
        for e in self.entries:
            color = status_colors.get(e.status, "#64748b")
            icon = status_icons.get(e.status, "•")
            rows.append(f'''
                <div style="display:flex;align-items:flex-start;gap:8px;padding:6px 0;border-bottom:1px solid #1e293b;">
                    <span style="color:{color};font-weight:bold;min-width:16px;">{icon}</span>
                    <div style="flex:1;">
                        <div style="color:#e2e8f0;font-size:13px;font-weight:500;">{e.step}</div>
                        <div style="color:#94a3b8;font-size:11px;margin-top:2px;">{e.detail}</div>
                    </div>
                    <span style="color:#475569;font-size:10px;font-family:monospace;white-space:nowrap;">{e.timestamp}</span>
                </div>
            ''')
        return "".join(rows)

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
    pipeline_steps: List[Dict[str, str]]
    audit: AuditTrail

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
        "风控专员": (
            "你是一名资深风控专员，专注于企业信用风险与市场风险评估。"
            "专业视角：风险因子识别、压力测试、情景分析、风险缓释措施评估。"
            "特别关注：财务杠杆、现金流覆盖、行业风险敞口、尾部风险。"
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
        self.session_results: List[AgentResult] = []
    
    def _call_llm(self, messages, temperature=0.1, max_tokens=2000):
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
        for name in COMPANY_NAMES:
            if name in query:
                return name
        for name in COMPANY_NAMES:
            if len(name) >= 2 and name[:2] in query:
                return name
        return None
    
    def _retrieve_knowledge(self, query, company):
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
        answer, confidence, reasoning = "", 50.0, ""
        if not raw:
            return answer, confidence, reasoning
        
        for pattern in [r'置信度[：:]\s*(\d+)', r'CONFIDENCE[：:]\s*(\d+)', r'confidence[：:]\s*(\d+)']:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                confidence = float(m.group(1))
                break
        
        for pattern in [r'答案[：:]\s*([A-D])', r'ANSWER[：:]\s*([A-D])']:
            m = re.search(pattern, raw, re.IGNORECASE)
            if m:
                answer = m.group(1).upper()
                break
        
        for pattern in [r'理由[：:]\s*(.+)', r'REASON[：:]\s*(.+)', r'分析[：:]\s*(.+)']:
            m = re.search(pattern, raw, re.IGNORECASE | re.DOTALL)
            if m:
                reasoning = m.group(1).strip()[:500]
                break
        
        if not reasoning:
            reasoning = raw[:500]
        return answer, confidence, reasoning
    
    def _initial_answer(self, query, knowledge, task_type):
        if task_type == "factual":
            sys_prompt = (
                "你是一位金融考试专家，精通CPA、CFA、银从等考试。"
                "请回答以下问题，并在末尾给出置信度。\n"
                "输出格式：\n答案：X\n置信度：0-100的整数\n理由：一句话说明"
            )
        else:
            sys_prompt = (
                "你是一位资深金融投研分析师，请基于知识库进行专业分析。\n"
                "要求：\n"
                "1. 结构化输出，使用标题和列表\n"
                "2. 每个关键结论后标注[置信度:高/中/低]\n"
                "3. 末尾给出整体置信度（0-100的整数）\n"
                "4. 低置信度结论需说明不确定的原因\n"
                "输出格式：\n[分析内容]\n\n置信度：0-100的整数\n理由：一句话说明"
            )
        
        user_msg = f"知识库：\n{knowledge}\n\n问题：{query}\n\n请回答。"
        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_msg}]
        raw = self._call_llm(messages)
        answer, conf, reasoning = self._parse_response(raw)
        return answer, conf, reasoning, raw
    
    def _l2_cross_validate(self, query, initial_answer, initial_conf, knowledge, task_type):
        peer_context = ""
        company = self._extract_company(query)
        if company:
            peer_context = get_peer_data(company)
        
        experts_results = []
        for role, prompt in self.EXPERT_PROMPTS.items():
            user_msg = (
                f"请以{role}的专业视角，基于以下数据进行交叉验证分析。\n\n"
                f"问题：{query}\n"
                f"初步结论：{initial_answer[:300] if initial_answer else 'N/A'}\n"
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
            time.sleep(0.3)
        
        avg_conf = sum(r["confidence"] for r in experts_results) / len(experts_results)
        summary = "\n\n".join([
            f"### {r['role']}视角 (置信度:{r['confidence']:.0f}%)\n{r['reasoning']}"
            for r in experts_results
        ])
        return summary, avg_conf
    
    def _generate_report(self, company_name):
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
            f"2. 核心风险因素识别（3-5个，按严重程度排序）\n"
            f"3. 同业对比分析\n"
            f"4. 投资结论与建议\n"
            f"5. 每个结论标注置信度（高/中/低）并说明依据\n\n"
            f"注意：低置信度结论需说明不确定的原因。保持专业客观。"
        )
        
        parts = [f"# FinSight 投研分析报告 — {company_name}({company['code']})\n"]
        parts.append(f"> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}  |  模型: {self.model}\n")
        parts.append("> 本报告由FinSight元认知校准Agent生成，不构成投资建议。\n")
        parts.append(f"> 元认知校准：analytical任务，置信度上调20pp（基于FinBench-Custom实证）\n")
        
        for role, expert_prompt in self.EXPERT_PROMPTS.items():
            messages = [{"role": "system", "content": expert_prompt}, {"role": "user", "content": prompt}]
            raw = self._call_llm(messages, temperature=0.3, max_tokens=3000)
            parts.append(f"\n---\n\n## {role}视角\n")
            parts.append(raw if raw else "[API调用失败]\n")
            time.sleep(0.3)
        
        parts.append("\n---\n\n## 元认知校准说明\n")
        parts.append(
            "| 维度 | 说明 |\n|------|------|\n"
            "| 任务类型 | 投研分析（analytical） |\n"
            "| 校准方向 | 置信度上调 +20pp |\n"
            "| 实证依据 | FinBench-Custom: GLM-7.8~-40.8pp, Kimi-10.6~-48.2pp |\n"
            "| 交叉验证 | 3专家视角（审计师+金融分析师+风控专员） |\n"
            "| 风险提示 | 低置信度结论需进一步人工核查 |\n"
        )
        return "\n".join(parts)
    
    def run(self, query: str) -> AgentResult:
        """完整Agent管线"""
        audit = AuditTrail()
        pipeline_steps = []
        t0 = time.time()
        
        # Step 1: 任务理解
        audit.add("任务理解", f"解析用户查询，检测任务类型...", "done")
        task_type = self.calibrator.detect_task_type(query)
        company = self._extract_company(query)
        audit.add("任务理解", f"任务类型: {task_type} | 目标公司: {company or '未指定'}", "done")
        pipeline_steps.append({"step": "任务理解", "status": "done", "detail": f"类型: {task_type}"})
        
        # Step 2: 知识检索
        audit.add("知识检索", f"从11家公司知识库中检索...", "done")
        knowledge = self._retrieve_knowledge(query, company)
        audit.add("知识检索", f"检索完成: {'命中' + company if company else '全量知识库'}", "done")
        pipeline_steps.append({"step": "知识检索", "status": "done", "detail": f"{'命中: ' + company if company else '全量KB'}"})
        
        # Step 3: LLM推理
        audit.add("LLM推理", f"调用 {self.model} 生成初始分析...", "done")
        answer, raw_conf, reasoning, raw_text = self._initial_answer(query, knowledge, task_type)
        if not answer and task_type == "analytical":
            answer = raw_text[:300] + "..." if len(raw_text) > 300 else raw_text
        audit.add("LLM推理", f"初始置信度: {raw_conf:.0f}%", "done")
        pipeline_steps.append({"step": "LLM推理", "status": "done", "detail": f"原始置信度: {raw_conf:.0f}%"})
        
        # Step 4: 元认知校准
        audit.add("元认知校准", f"应用Task-type dependent calibration...", "done")
        calibration = self.calibrator.calibrate(raw_conf, task_type)
        audit.add("元认知校准", 
                   f"{'下调' if calibration.offset < 0 else '上调'}{abs(calibration.offset)}pp → {calibration.calibrated_confidence:.0f}% [{calibration.risk_label}]",
                   "done" if calibration.risk_label != "RED" else "warning")
        pipeline_steps.append({"step": "元认知校准", "status": "done", "detail": f"{raw_conf:.0f}% → {calibration.calibrated_confidence:.0f}% [{calibration.risk_label}]"})
        
        # Step 5: L2交叉验证
        l2_result = None
        l2_conf = None
        final_answer = answer
        final_conf = calibration.calibrated_confidence
        
        if calibration.l2_triggered:
            audit.add("L2交叉验证", f"校准后置信度<{L2_THRESHOLD}%，启动3专家交叉验证...", "warning")
            pipeline_steps.append({"step": "L2交叉验证", "status": "warning", "detail": "3专家交叉验证中..."})
            l2_result, l2_conf = self._l2_cross_validate(
                query, answer, calibration.calibrated_confidence, knowledge, task_type
            )
            if l2_conf:
                l2_calibrated = self.calibrator.calibrate(l2_conf, task_type)
                final_conf = l2_calibrated.calibrated_confidence
                calibration.risk_label = l2_calibrated.risk_label
                audit.add("L2交叉验证", f"3专家平均置信度: {l2_conf:.0f}% → 校准后: {final_conf:.0f}% [{calibration.risk_label}]", "done")
                pipeline_steps.append({"step": "L2交叉验证", "status": "done", "detail": f"3专家平均: {l2_conf:.0f}% → {final_conf:.0f}%"})
        else:
            pipeline_steps.append({"step": "L2交叉验证", "status": "done", "detail": "未触发（置信度充足）"})
        
        # Step 6: 风险分级
        audit.add("风险分级", f"最终风险等级: {calibration.risk_label} (置信度: {final_conf:.0f}%)", "done")
        pipeline_steps.append({"step": "风险分级", "status": "done", "detail": f"{calibration.risk_label} ({final_conf:.0f}%)"})
        
        elapsed = time.time() - t0
        audit.add("完成", f"全流程耗时: {elapsed:.1f}s", "done")
        
        result = AgentResult(
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
            pipeline_steps=pipeline_steps,
            audit=audit,
        )
        self.session_results.append(result)
        return result

# ============================================================
# 可视化组件 — HTML生成器
# ============================================================

def confidence_gauge_html(raw: float, calibrated: float, task_type: str, offset: int) -> str:
    """置信度仪表盘：原始 vs 校准后"""
    raw_color = "#64748b"
    if calibrated >= RISK_GREEN:
        cal_color = "#22c55e"
    elif calibrated >= RISK_YELLOW:
        cal_color = "#eab308"
    else:
        cal_color = "#ef4444"
    
    arrow = "↓" if offset < 0 else "↑"
    arrow_color = "#3b82f6" if offset < 0 else "#f59e0b"
    
    return f'''
    <div style="background:#111827;border-radius:12px;padding:16px;margin-bottom:12px;border:1px solid #1e293b;">
        <div style="color:#94a3b8;font-size:12px;margin-bottom:12px;letter-spacing:1px;">📊 置信度校准</div>
        
        <!-- 原始置信度 -->
        <div style="margin-bottom:10px;">
            <div style="display:flex;justify-content:space-between;color:#64748b;font-size:11px;margin-bottom:4px;">
                <span>原始置信度</span><span>{raw:.0f}%</span>
            </div>
            <div style="background:#1e293b;border-radius:6px;height:8px;overflow:hidden;">
                <div style="background:{raw_color};height:100%;width:{raw:.0f}%;border-radius:6px;transition:width 0.5s;"></div>
            </div>
        </div>
        
        <!-- 校准箭头 -->
        <div style="text-align:center;color:{arrow_color};font-size:20px;margin:4px 0;">
            {arrow} {abs(offset)}pp <span style="font-size:11px;color:#64748b;">({"过度自信→下调" if offset < 0 else "不自信→上调"})</span>
        </div>
        
        <!-- 校准后置信度 -->
        <div style="margin-bottom:6px;">
            <div style="display:flex;justify-content:space-between;color:#e2e8f0;font-size:12px;margin-bottom:4px;font-weight:600;">
                <span>校准备置信度</span><span>{calibrated:.0f}%</span>
            </div>
            <div style="background:#1e293b;border-radius:6px;height:12px;overflow:hidden;">
                <div style="background:{cal_color};height:100%;width:{calibrated:.0f}%;border-radius:6px;transition:width 0.5s;box-shadow:0 0 8px {cal_color}55;"></div>
            </div>
        </div>
        
        <div style="color:#475569;font-size:10px;margin-top:8px;">
            任务类型: {task_type} | 实证: {"CFLUE 6模型过度自信" if task_type == "factual" else "FinBench 2模型不自信"}
        </div>
    </div>
    '''

def risk_badge_html(risk_label: str, confidence: float) -> str:
    """风险等级徽章"""
    configs = {
        "GREEN": {"color": "#22c55e", "bg": "rgba(34,197,94,0.15)", "icon": "🟢", "label": "GREEN", "desc": "高置信·可直接采用"},
        "YELLOW": {"color": "#eab308", "bg": "rgba(234,179,8,0.15)", "icon": "🟡", "label": "YELLOW", "desc": "中等置信·需人工复核"},
        "RED": {"color": "#ef4444", "bg": "rgba(239,68,68,0.15)", "icon": "🔴", "label": "RED", "desc": "低置信·必须人工介入"},
    }
    c = configs.get(risk_label, configs["YELLOW"])
    return f'''
    <div style="background:{c['bg']};border:2px solid {c['color']};border-radius:12px;padding:14px;text-align:center;margin-bottom:12px;">
        <div style="font-size:28px;margin-bottom:4px;">{c['icon']}</div>
        <div style="color:{c['color']};font-size:18px;font-weight:700;letter-spacing:2px;">{c['label']}</div>
        <div style="color:#94a3b8;font-size:11px;margin-top:4px;">{c['desc']}</div>
        <div style="color:{c['color']};font-size:24px;font-weight:800;margin-top:6px;font-family:monospace;">{confidence:.0f}%</div>
    </div>
    '''

def pipeline_html(steps: List[Dict[str, str]]) -> str:
    """Pipeline步骤可视化"""
    if not steps:
        return '<div style="color:#64748b;text-align:center;padding:20px;">等待分析任务...</div>'
    
    status_colors = {"done": "#22c55e", "warning": "#eab308", "error": "#ef4444", "pending": "#475569"}
    status_icons = {"done": "✓", "warning": "⚠", "error": "✗", "pending": "○"}
    
    items = []
    for i, s in enumerate(steps):
        color = status_colors.get(s["status"], "#475569")
        icon = status_icons.get(s["status"], "○")
        is_last = (i == len(steps) - 1)
        connector = "" if is_last else f'<div style="width:2px;height:16px;background:#1e293b;margin-left:11px;"></div>'
        items.append(f'''
            <div style="display:flex;align-items:center;gap:8px;">
                <div style="width:24px;height:24px;border-radius:50%;background:{color}22;border:2px solid {color};display:flex;align-items:center;justify-content:center;color:{color};font-size:12px;font-weight:bold;flex-shrink:0;">{icon}</div>
                <div>
                    <span style="color:#e2e8f0;font-size:13px;font-weight:500;">{s['step']}</span>
                    <span style="color:#64748b;font-size:11px;margin-left:6px;">{s.get('detail','')}</span>
                </div>
            </div>
            {connector}
        ''')
    
    return f'''
    <div style="background:#111827;border-radius:12px;padding:16px;border:1px solid #1e293b;">
        <div style="color:#94a3b8;font-size:12px;margin-bottom:12px;letter-spacing:1px;">🔄 分析Pipeline</div>
        {''.join(items)}
    </div>
    '''

def calibration_evidence_html(task_type: str) -> str:
    """校准实证数据展示"""
    if task_type == "factual":
        data = [
            ("GLM-5.2", "+11.8pp"),
            ("DeepSeek-V3", "+16.4pp"),
            ("Qwen-Plus", "+27.8pp"),
            ("MiMo-v2.5", "+17.3pp"),
            ("Mistral-7B", "+67.5pp"),
            ("Step-3.5", "+28.1pp"),
        ]
        title = "CFLUE金融选择题 — 6模型全部过度自信"
        avg = "平均+28.2pp"
        color = "#ef4444"
    else:
        data = [
            ("GLM-5.2", "-7.8~-40.8pp"),
            ("Kimi-k2.6", "-10.6~-48.2pp"),
        ]
        title = "FinBench-Custom金融分析 — 模型不自信"
        avg = "平均-20.8pp"
        color = "#3b82f6"
    
    rows = ""
    for model, gap in data:
        rows += f'''
            <div style="display:flex;justify-content:space-between;padding:4px 8px;border-bottom:1px solid #1e293b;">
                <span style="color:#94a3b8;font-size:12px;">{model}</span>
                <span style="color:{color};font-size:12px;font-family:monospace;font-weight:600;">{gap}</span>
            </div>
        '''
    
    return f'''
    <div style="background:#111827;border-radius:12px;padding:14px;border:1px solid #1e293b;margin-bottom:12px;">
        <div style="color:#94a3b8;font-size:12px;margin-bottom:8px;letter-spacing:1px;">🔬 校准实证依据</div>
        <div style="color:#e2e8f0;font-size:13px;font-weight:600;margin-bottom:8px;">{title}</div>
        {rows}
        <div style="text-align:right;color:{color};font-size:12px;margin-top:6px;font-weight:600;">{avg}</div>
    </div>
    '''

def company_card_html(c: dict) -> str:
    """公司卡片HTML"""
    profit_color = "#ef4444" if "亏" in c["net_profit"] else "#22c55e"
    return f'''
    <div style="background:#111827;border-radius:10px;padding:12px;border:1px solid #1e293b;margin-bottom:8px;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
            <span style="color:#e2e8f0;font-size:14px;font-weight:600;">{c['name']}</span>
            <span style="color:#475569;font-size:11px;font-family:monospace;">{c['code']}</span>
        </div>
        <div style="color:#64748b;font-size:11px;margin-bottom:4px;">{c['industry']} | {c['period']}</div>
        <div style="display:flex;gap:12px;font-size:11px;">
            <span style="color:#94a3b8;">收入: <span style="color:#e2e8f0;font-weight:500;">{c['revenue']}</span></span>
            <span style="color:#94a3b8;">净利润: <span style="color:{profit_color};font-weight:500;">{c['net_profit']}</span></span>
        </div>
    </div>
    '''

def session_stats_html(results: List[AgentResult]) -> str:
    """会话统计"""
    if not results:
        return '<div style="color:#64748b;text-align:center;padding:20px;">暂无分析记录</div>'
    
    total = len(results)
    green = sum(1 for r in results if r.risk_label == "GREEN")
    yellow = sum(1 for r in results if r.risk_label == "YELLOW")
    red = sum(1 for r in results if r.risk_label == "RED")
    l2_count = sum(1 for r in results if r.l2_result is not None)
    avg_conf = sum(r.final_confidence for r in results) / total
    
    return f'''
    <div style="background:#111827;border-radius:12px;padding:16px;border:1px solid #1e293b;margin-bottom:12px;">
        <div style="color:#94a3b8;font-size:12px;margin-bottom:12px;letter-spacing:1px;">📈 会话统计</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div style="background:#1e293b;border-radius:8px;padding:10px;text-align:center;">
                <div style="color:#e2e8f0;font-size:24px;font-weight:700;">{total}</div>
                <div style="color:#64748b;font-size:10px;">总分析</div>
            </div>
            <div style="background:#1e293b;border-radius:8px;padding:10px;text-align:center;">
                <div style="color:#3b82f6;font-size:24px;font-weight:700;">{avg_conf:.0f}%</div>
                <div style="color:#64748b;font-size:10px;">平均置信度</div>
            </div>
            <div style="background:#1e293b;border-radius:8px;padding:10px;text-align:center;">
                <div style="color:#22c55e;font-size:20px;font-weight:700;">{green}</div>
                <div style="color:#64748b;font-size:10px;">GREEN</div>
            </div>
            <div style="background:#1e293b;border-radius:8px;padding:10px;text-align:center;">
                <div style="color:#eab308;font-size:20px;font-weight:700;">{yellow}</div>
                <div style="color:#64748b;font-size:10px;">YELLOW</div>
            </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:8px;">
            <div style="background:#1e293b;border-radius:8px;padding:6px 10px;flex:1;text-align:center;">
                <span style="color:#ef4444;font-size:14px;font-weight:600;">{red}</span>
                <span style="color:#64748b;font-size:10px;margin-left:4px;">RED</span>
            </div>
            <div style="background:#1e293b;border-radius:8px;padding:6px 10px;flex:1;text-align:center;">
                <span style="color:#3b82f6;font-size:14px;font-weight:600;">{l2_count}</span>
                <span style="color:#64748b;font-size:10px;margin-left:4px;">L2触发</span>
            </div>
        </div>
    </div>
    '''

# ============================================================
# CSS
# ============================================================
CUSTOM_CSS = """
:root {
    --bg-primary: #0a0e1a;
    --bg-secondary: #111827;
    --bg-tertiary: #1e293b;
    --text-primary: #e2e8f0;
    --text-secondary: #94a3b8;
    --text-muted: #64748b;
    --accent: #3b82f6;
    --success: #22c55e;
    --warning: #eab308;
    --danger: #ef4444;
    --border: #1e293b;
}
.gradio-container {
    max-width: 1400px !important;
    background: var(--bg-primary) !important;
}
.gradio-container > .main {
    background: var(--bg-primary) !important;
}
#header {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 16px;
    border: 1px solid #1e293b;
}
#header h1 {
    color: #e2e8f0;
    font-size: 22px;
    margin: 0;
}
#header .subtitle {
    color: #64748b;
    font-size: 13px;
    margin-top: 4px;
}
.tab-nav {
    background: #111827 !important;
    border-radius: 12px 12px 0 0 !important;
    border: 1px solid #1e293b !important;
    border-bottom: none !important;
}
.tab-nav button {
    color: #64748b !important;
    font-size: 14px !important;
    padding: 12px 20px !important;
}
.tab-nav button.selected {
    color: #3b82f6 !important;
    background: #0a0e1a !important;
    border-bottom: 2px solid #3b82f6 !important;
}
.gr-block {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}
.gr-padded {
    background: var(--bg-secondary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
    padding: 16px !important;
}
.gr-box {
    border-radius: 12px !important;
    background: var(--bg-secondary) !important;
    border-color: var(--border) !important;
}
textarea, input {
    background: #0a0e1a !important;
    color: var(--text-primary) !important;
    border-color: var(--border) !important;
    border-radius: 8px !important;
}
textarea:focus, input:focus {
    border-color: var(--accent) !important;
}
.gr-button {
    border-radius: 8px !important;
    font-weight: 500 !important;
}
.gr-button-primary {
    background: var(--accent) !important;
    border: none !important;
}
.gr-button-primary:hover {
    background: #2563eb !important;
}
.message.user, .message.bot {
    border-radius: 12px !important;
}
footer { display: none !important; }
"""

# ============================================================
# Gradio 界面
# ============================================================

def create_interface(agent: FinSightAgent):
    
    # --- 状态管理 ---
    session_state = {"results": [], "audit": AuditTrail()}
    
    def chat_handler(message, history):
        """处理用户消息"""
        if not message.strip():
            return "", history, "", "", "", "", ""
        
        try:
            result = agent.run(message)
            session_state["results"].append(result)
            
            # 构建回复
            risk_emoji = {"GREEN": "🟢", "YELLOW": "🟡", "RED": "🔴"}
            reply_parts = [
                f"### {risk_emoji.get(result.risk_label, '⚪')} FinSight 分析结果",
                f"**风险等级: {result.risk_label}** | 校准备置信度: **{result.final_confidence:.0f}%**",
                f"",
                f"**任务类型**: {'事实查询（选择题）' if result.task_type == 'factual' else '投研分析（开放式）'}",
                f"**目标公司**: {result.company or '未指定'}",
                f"",
                f"---",
                f"",
            ]
            
            if result.task_type == "factual" and result.initial_answer and len(result.initial_answer) <= 5:
                reply_parts.append(f"**答案**: {result.initial_answer}")
            else:
                reply_parts.append(result.final_answer if result.final_answer else result.initial_answer)
            
            reply_parts.append(f"")
            reply_parts.append(f"---")
            reply_parts.append(f"")
            reply_parts.append(f"**📊 置信度校准**: {result.raw_confidence:.0f}% → {result.final_confidence:.0f}% "
                               f"({'下调' if result.calibration.offset < 0 else '上调'}{abs(result.calibration.offset)}pp)")
            
            if result.l2_result:
                reply_parts.append(f"")
                reply_parts.append(f"<details><summary>🔍 L2交叉验证详情（3专家视角）</summary>")
                reply_parts.append(f"")
                reply_parts.append(result.l2_result)
                reply_parts.append(f"</details>")
            
            reply = "\n".join(reply_parts)
            history.append([message, reply])
            
            # 更新dashboard
            gauge = confidence_gauge_html(
                result.raw_confidence, 
                result.calibration.calibrated_confidence,
                result.task_type,
                result.calibration.offset
            )
            badge = risk_badge_html(result.risk_label, result.final_confidence)
            pipeline = pipeline_html(result.pipeline_steps)
            audit_html = result.audit.to_html()
            evidence = calibration_evidence_html(result.task_type)
            
            return "", history, gauge, badge, pipeline, audit_html, evidence
            
        except Exception as e:
            error_msg = f"❌ 分析失败: {str(e)}"
            history.append([message, error_msg])
            return "", history, "", "", "", "", ""
    
    def report_handler(company_name):
        """生成投研报告"""
        if not company_name:
            return "请选择或输入公司名称", None
        
        report = agent._generate_report(company_name)
        
        # 保存报告到临时文件
        safe_name = re.sub(r'[^\w\u4e00-\u9fff]', '_', company_name)
        filename = f"FinSight_报告_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join("/tmp", filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)
        
        return report, filepath
    
    def compare_handler():
        """多公司对比"""
        lines = ["## 📊 11家港股上市公司对比看板\n"]
        lines.append("| 公司 | 行业 | 收入 | 净利润 | 核心风险 |")
        lines.append("|------|------|------|--------|----------|")
        for c in KNOWLEDGE_BASE:
            risks = c.get("risk_factors", "N/A").split("|")
            top_risk = risks[0] if risks else "N/A"
            lines.append(f"| {c['name']}({c['code']}) | {c['industry']} | {c['revenue']} | {c['net_profit']} | {top_risk} |")
        
        lines.append("\n### 风险因素全景\n")
        all_risks = {}
        for c in KNOWLEDGE_BASE:
            for r in c.get("risk_factors", "").split("|"):
                r = r.strip()
                if r:
                    all_risks.setdefault(r, []).append(c["name"])
        
        for risk, companies in sorted(all_risks.items(), key=lambda x: -len(x[1])):
            lines.append(f"- **{risk}**: {', '.join(companies)}")
        
        return "\n".join(lines)
    
    def kb_handler():
        """知识库浏览"""
        cards = ""
        for c in KNOWLEDGE_BASE:
            cards += company_card_html(c)
        return cards
    
    def stats_handler():
        """会话统计"""
        return session_stats_html(session_state["results"])
    
    # --- 构建界面 ---
    with gr.Blocks(css=CUSTOM_CSS, title="FinSight — 金融投研Agent with 元认知校准", theme=gr.themes.Base()) as app:
        
        # Header
        gr.HTML("""
        <div id="header">
            <h1>🏦 FinSight — 面向企业经营与风险研判的金融服务Agent</h1>
            <div class="subtitle">
                内生元认知校准层 · Endogenous Metacognitive Calibration Layer<br>
                <span style="color:#3b82f6;">模型自己知道什么时候不靠谱</span> · 系统据此路由决策 · GOAI 2026 无界应用·AI+金融
            </div>
        </div>
        """)
        
        with gr.Tabs():
            # ==================== Tab 1: 投研问答 ====================
            with gr.Tab("💬 投研问答"):
                with gr.Row():
                    # 左侧：聊天区
                    with gr.Column(scale=3):
                        chatbot = gr.Chatbot(
                            label="FinSight Agent",
                            height=520,
                            show_label=False,
                            placeholder="输入你的金融问题，例如：\n• 分析比亚迪电子的财务健康状况\n• 广汽集团利润暴跌81%的原因是什么\n• 对比零跑汽车和广汽集团的新能源转型\n• 药明康德2025H1净利润增长95.5%的可持续性如何",
                        )
                        with gr.Row():
                            msg_input = gr.Textbox(
                                placeholder="输入金融问题...",
                                scale=5,
                                show_label=False,
                                lines=2,
                            )
                            send_btn = gr.Button("发送", variant="primary", scale=1)
                        
                        with gr.Row():
                            quick_btns = []
                            for label in ["📊 财务健康度", "⚠️ 风险分析", "🔄 同业对比", "📝 生成报告"]:
                                quick_btns.append(gr.Button(label, size="sm"))
                    
                    # 右侧：Dashboard
                    with gr.Column(scale=2):
                        # 风险等级
                        risk_badge = gr.HTML(
                            value='<div style="background:#111827;border-radius:12px;padding:20px;text-align:center;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">等待分析任务...</div></div>',
                            label="",
                        )
                        # 置信度仪表盘
                        conf_gauge = gr.HTML(
                            value='<div style="background:#111827;border-radius:12px;padding:20px;text-align:center;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">等待分析任务...</div></div>',
                            label="",
                        )
                        # Pipeline
                        pipeline_vis = gr.HTML(
                            value='<div style="background:#111827;border-radius:12px;padding:20px;text-align:center;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">等待分析任务...</div></div>',
                            label="",
                        )
            
            # ==================== Tab 2: 元认知校准监控 ====================
            with gr.Tab("🔬 元认知校准"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML("""
                        <div style="background:#0f172a;border-radius:12px;padding:20px;border:1px solid #1e293b;margin-bottom:12px;">
                            <h2 style="color:#e2e8f0;font-size:18px;margin:0 0 12px 0;">核心研究发现</h2>
                            <div style="color:#94a3b8;font-size:13px;line-height:1.8;">
                                <p><b style="color:#e2e8f0;">贡献1 — M-C解离</b><br>
                                Spontaneous纠错率 1.6-16.7% vs Unconditional 36-45%<br>
                                Oracle 73-96% → 模型能监控但不能控制</p>
                                
                                <p><b style="color:#e2e8f0;">贡献2 — Calibration Reversal</b><br>
                                同一金融领域内，任务类型不同→校准方向反转<br>
                                6模型CFLUE过度自信 / 2模型FinBench不自信</p>
                                
                                <p><b style="color:#e2e8f0;">贡献3 — 校准引导定向纠错</b><br>
                                Multi-sampling: 98.3%系统性错误（死）<br>
                                Graded Feedback: L0=47% → L4=100%（活）<br>
                                校准+阈值选择性触发 → 减少damage</p>
                            </div>
                        </div>
                        """)
                        evidence_panel = gr.HTML(
                            value='<div style="background:#111827;border-radius:12px;padding:20px;text-align:center;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">运行分析任务后显示实证数据</div></div>',
                            label="",
                        )
                    
                    with gr.Column(scale=1):
                        gr.HTML("""
                        <div style="background:#0f172a;border-radius:12px;padding:20px;border:1px solid #1e293b;margin-bottom:12px;">
                            <h2 style="color:#e2e8f0;font-size:18px;margin:0 0 12px 0;">校准参数</h2>
                            <div style="color:#94a3b8;font-size:13px;line-height:2;">
                                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b;">
                                    <span>Factual (选择题)</span><span style="color:#ef4444;font-family:monospace;">-12pp</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b;">
                                    <span>Analytical (分析题)</span><span style="color:#22c55e;font-family:monospace;">+20pp</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b;">
                                    <span>L2触发阈值</span><span style="color:#eab308;font-family:monospace;">< 60%</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b;">
                                    <span>GREEN</span><span style="color:#22c55e;font-family:monospace;">≥ 75%</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #1e293b;">
                                    <span>YELLOW</span><span style="color:#eab308;font-family:monospace;">50-74%</span>
                                </div>
                                <div style="display:flex;justify-content:space-between;padding:4px 0;">
                                    <span>RED</span><span style="color:#ef4444;font-family:monospace;">< 50%</span>
                                </div>
                            </div>
                        </div>
                        """)
                        stats_panel = gr.HTML(
                            value='<div style="background:#111827;border-radius:12px;padding:20px;text-align:center;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">暂无分析记录</div></div>',
                            label="",
                        )
                        refresh_stats_btn = gr.Button("🔄 刷新统计", size="sm")
            
            # ==================== Tab 3: 投研报告 ====================
            with gr.Tab("📄 投研报告"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.HTML('<div style="color:#94a3b8;font-size:14px;margin-bottom:8px;">选择公司生成投研分析报告</div>')
                        company_dropdown = gr.Dropdown(
                            choices=COMPANY_NAMES,
                            label="选择公司",
                            value=COMPANY_NAMES[0],
                        )
                        gen_report_btn = gr.Button("🚀 生成投研报告", variant="primary")
                        report_file = gr.File(label="📥 下载报告")
                    
                    with gr.Column(scale=2):
                        report_output = gr.Markdown(
                            value="点击「生成投研报告」按钮，系统将通过3个专家视角（审计师、金融分析师、风控专员）生成结构化投研分析报告。",
                            label="",
                        )
            
            # ==================== Tab 4: 风险看板 ====================
            with gr.Tab("📊 风险看板"):
                with gr.Row():
                    with gr.Column(scale=2):
                        compare_output = gr.Markdown(value="")
                        gen_compare_btn = gr.Button("🔄 生成对比看板", variant="primary")
                    
                    with gr.Column(scale=1):
                        kb_display = gr.HTML(
                            value='<div style="background:#111827;border-radius:12px;padding:20px;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">点击下方按钮浏览知识库</div></div>',
                            label="",
                        )
                        gen_kb_btn = gr.Button("📋 浏览知识库", size="sm")
            
            # ==================== Tab 5: 审计追踪 ====================
            with gr.Tab("📋 审计追踪"):
                audit_display = gr.HTML(
                    value='<div style="background:#111827;border-radius:12px;padding:20px;text-align:center;border:1px solid #1e293b;"><div style="color:#475569;font-size:14px;">运行分析任务后显示审计追踪</div></div>',
                    label="",
                )
        
        # --- 事件绑定 ---
        send_btn.click(
            chat_handler,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot, conf_gauge, risk_badge, pipeline_vis, audit_display, evidence_panel],
        )
        msg_input.submit(
            chat_handler,
            inputs=[msg_input, chatbot],
            outputs=[msg_input, chatbot, conf_gauge, risk_badge, pipeline_vis, audit_display, evidence_panel],
        )
        
        # 快捷按钮
        quick_actions = [
            "📊 财务健康度",
            "⚠️ 风险分析",
            "🔄 同业对比",
            "📝 生成报告",
        ]
        quick_prompts = [
            "分析比亚迪电子的财务健康度，评估其收入增长与毛利率的矛盾",
            "分析广汽集团的信用风险，利润暴跌81%的原因和影响面",
            "对比零跑汽车和广汽集团的财务状况和新能源转型进展",
            "请为药明康德生成投研分析报告",
        ]
        for btn, prompt in zip(quick_btns, quick_prompts):
            btn.click(lambda p=prompt: p, outputs=msg_input)
        
        # 报告生成
        gen_report_btn.click(
            report_handler,
            inputs=[company_dropdown],
            outputs=[report_output, report_file],
        )
        
        # 对比看板
        gen_compare_btn.click(compare_handler, outputs=compare_output)
        gen_kb_btn.click(kb_handler, outputs=kb_display)
        
        # 统计刷新
        refresh_stats_btn.click(stats_handler, outputs=stats_panel)
        
        # 页面加载时生成对比看板
        app.load(compare_handler, outputs=compare_output)
    
    return app

# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FinSight Agent v4 — 金融投研Agent with 元认知校准")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="LLM模型名称")
    parser.add_argument("--port", type=int, default=7860, help="服务端口")
    parser.add_argument("--share", action="store_true", help="启用公网链接")
    parser.add_argument("--api-key", default=None, help="API Key（默认读环境变量）")
    args = parser.parse_args()
    
    print("=" * 60)
    print("  FinSight Agent v4 — 金融投研Agent with 元认知校准")
    print("  GOAI 2026 无界应用赛道 · AI+金融")
    print("=" * 60)
    print(f"  模型: {args.model}")
    print(f"  端口: {args.port}")
    print(f"  公网链接: {'是' if args.share else '否'}")
    print(f"  知识库: {len(KNOWLEDGE_BASE)}家港股上市公司")
    print(f"  校准参数: factual={CALIBRATION_OFFSET['factual']}pp, analytical={CALIBRATION_OFFSET['analytical']}pp")
    print(f"  L2阈值: {L2_THRESHOLD}% | GREEN≥{RISK_GREEN}% | YELLOW≥{RISK_YELLOW}%")
    print("=" * 60)
    
    agent = FinSightAgent(model=args.model, api_key=args.api_key)
    app = create_interface(agent)
    
    app.launch(
        server_port=args.port,
        share=args.share,
        show_error=True,
        quiet=False,
    )
