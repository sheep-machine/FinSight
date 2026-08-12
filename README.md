# FinSight — 基于元认知监测与知识检索纠错的多Agent金融风控系统

> GOAI 2026 世界人工智能开源大赛 · Agent Infra 赛道参赛项目

FinSight 将原创研究 FinMetaBench 的元认知发现工程化为可复用 Skill，通过 Manager-Worker 多Agent协同实现端到端金融风控闭环。核心差异化在于利用模型内生的监测信号（AUROC 0.83-0.93）触发 L2+ 粒度知识检索式纠错，而非依赖外部规则约束。

## 核心特性

- **5-Agent 协同架构**：1 Manager（投研总监）+ 4 Worker（财报分析师、风控哨兵、交叉校验官、策略规划师）
- **6个可复用 Skill**：`meta-calibrate`、`fin-analysis`、`risk-scan`、`cross-validate`、`strategy-gen`、`kb-query`
- **元认知校准**：基于 FinMetaBench 实证研究（500题×6模型），利用 LLM 已有监测信号触发知识检索式纠错
- **64家上市公司财报知识库**：覆盖银行、保险、互联网、汽车、医药、消费、能源、地产等全行业
- **完整业务闭环**：选标的 → 深度研报 → 校准确认 → 交易决策 → 持仓追踪
- **安全可观测**：Worker 零凭证暴露、Higress 网关凭证隔离、全程 Trace/Log/Metrics 可审计

## 项目结构

```
FinSight/
├── README.md                          # 本文件
├── LICENSE                            # MIT 开源协议
├── .gitignore
├── COMPLIANCE.md                      # 第三方依赖与合规说明
├── demo/
│   └── finsight_trading_terminal.html # 赛博投研交易终端（浏览器直接打开）
├── src/
│   ├── finsight_agent_v3.py           # FinSight Agent v3（Gradio 问答版）
│   └── finsight_agent_v4.py           # FinSight Agent v4（Dashboard + 元认知校准可视化）
├── presentation/
│   └── FinSight_presentation.html     # 15页方案PPT（浏览器打开，F全屏，P导出PDF）
├── docs/
│   ├── GOAI_AgentInfra_提交材料.md     # 完整提交材料（Agent Identity + Skill + 闭环设计）
│   ├── GOAI_最终提交材料_封面.md       # 提交材料索引与核心亮点
│   ├── FinMetaBench_paper_draft_v1.md # 学术论文初稿
│   ├── multi-agent-demo/              # 多Agent策略回测实跑记录
│   └── analysis/                      # FinMetaBench 实验分析
│       ├── FinMetaBench_v5.6_CFLUE_500Q_analysis.md
│       └── FinMetaBench_v5.6_CFLUE_analysis_v3.md
```

## 快速开始

### 方式一：浏览器 Demo（无需安装）

直接用浏览器打开 `demo/finsight_trading_terminal.html`，即可体验赛博投研交易终端：
- 64家上市公司行情看板
- 模拟交易系统（100万虚拟资金）
- 深度研报生成（4-Agent协作可视化）
- 元认知校准风险徽章

### 方式二：本地运行 Agent

```bash
# 安装依赖
pip install gradio openai

# 设置 API Key（支持 GLM 系列）
export GLM_API_KEY=your_key

# 运行 v4（推荐，含 Dashboard）
python src/finsight_agent_v4.py --model glm-4-plus

# 如有 glm-5.2 权限
python src/finsight_agent_v4.py --model glm-5.2 --share
```

### 方式三：查看方案 PPT

浏览器打开 `presentation/FinSight_presentation.html`：
- `←` / `→` 翻页
- `F` 全屏
- `P` 打印/导出PDF

## 技术架构

### Manager-Worker 多Agent协同

```
用户请求 → Manager（投研总监）
               ├─ T1: 财报分析 → Analyst Worker（fin-analysis + kb-query）
               ├─ T2: 风险扫描 → Sentinel Worker（risk-scan + kb-query）
               │   （T1/T2 并行）
               ├─ T3: 交叉校验 → Inspector Worker（cross-validate）
               │   （依赖 T1+T2 完成）
               └─ T4: 策略生成 → Strategist Worker（strategy-gen + meta-calibrate）
                   （依赖 T1+T2+T3 完成）
```

### 核心 Skill：meta-calibrate

基于 FinMetaBench 实证发现：
- **M-C 解离**：LLM 元认知监测质量尚可（AUROC 0.83-0.93），但纠错率仅 38-41%
- **系统性错误**：98.3% 错误为知识性缺口，多采样投票无效
- **L2 相变点**：概念级信息（~80字）才能跨越纠错阈值（47%→73%）
- **REVERSED**：5/6 模型高置信错误反而更易纠正
- **Task-Type Reversal**：选择题过度自信(+11.8~67.5pp)，分析题不自信(-7.8~-48.2pp)

meta-calibrate 不做简单的置信度校准，而是利用已有监测信号触发 L2+ 粒度知识检索式纠错。

## 学术支撑

FinMetaBench 论文初稿已完成，计划投稿 ARR October 2026 → ACL 2027。

三条贡献链：
1. **M-C解离**：元认知监测与控制的系统性分离（6模型验证）
2. **Calibration Reversal**：任务类型决定校准方向（跨6+2模型验证）
3. **校准引导定向纠错**：L2相变点指导知识检索粒度（双模型验证）

## 国家政策对齐

- **央行九部门通知**（2026.07）："打造风控投研模型"、"智能风控"
- **金发〔2026〕8号**（2026.06）："持续监测模型行为"、"知识工程建设"

FinSight 的 meta-calibrate 监测纠错机制是这两项政策要求的技术实现。

## 开源协议

MIT License — 详见 [LICENSE](LICENSE)

## 团队

独立开发者 · GitHub: [@sheep-machine](https://github.com/sheep-machine)

---

*GOAI 2026 世界人工智能开源大赛 · Agent Infra 赛道*
