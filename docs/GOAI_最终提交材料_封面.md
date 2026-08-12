# GOAI 2026 世界人工智能开源大赛
## 初赛提交材料 — 最终版

---

| 项目 | 内容 |
|------|------|
| **赛道** | Agent Infra（新智基座） |
| **方向** | 金融风控与理赔自动化 |
| **项目名称** | FinSight — 基于元认知监测与知识检索纠错的多Agent金融风控系统 |
| **技术框架** | AgentTeams（HiClaw） |
| **提交日期** | 2026-07-28 |
| **初赛截止** | 2026-08-16 |

---

## 一句话概述

FinSight 将原创研究 FinMetaBench 的元认知发现工程化为可复用 Skill，通过 Manager-Worker 多Agent协同实现端到端金融风控闭环——核心差异化在于利用模型内生的监测信号（AUROC 0.83-0.93）触发 L2+ 粒度知识检索式纠错，而非依赖外部规则约束。

---

## 提交材料清单

| 序号 | 材料 | 文件名 | 说明 |
|------|------|--------|------|
| 1 | **项目简介（500字）** | GOAI_AgentInfra_提交材料.md → 第一部分 | 涵盖系统架构、核心发现、差异化定位 |
| 2 | **方案PPT（15页）** | FinSight_presentation.html | 纯HTML/CSS演示文稿，浏览器打开即可演示 |
| 3 | **Agent Identity清单** | GOAI_AgentInfra_提交材料.md → 第二部分 | 5个Agent（1 Manager + 4 Worker），含SOUL.md |
| 4 | **Skill清单** | GOAI_AgentInfra_提交材料.md → 第三部分 | 6个核心Skill，含meta-calibrate差异化Skill |
| 5 | **多Agent闭环设计** | GOAI_AgentInfra_提交材料.md → 第四部分 | 8环节闭环流程图 |
| 6 | **AgentTeams架构映射** | GOAI_AgentInfra_提交材料.md → 第五部分 | YAML配置 + 安全模型 + RAG设计 |

> 所有材料均收录在 `GOAI_AgentInfra_提交材料.md` 中，PPT为独立HTML文件。

---

## 方案PPT使用说明

**文件**：`FinSight_presentation.html`

**打开方式**：浏览器直接打开（推荐 Chrome/Edge），支持全屏演示。

**键盘快捷键**：
| 按键 | 功能 |
|------|------|
| ← / → | 翻页 |
| Space / PageDown | 下一页 |
| PageUp | 上一页 |
| Home / End | 首页 / 末页 |
| F | 全屏切换 |
| P | 打印 / 导出PDF |

**设计系统**：
- 配色：深藏青(#0F1B2D) + 古铜金(#BFA46F) + 暖象牙白(#FAFAF5)
- 字体：Cormorant Garamond（衬线标题）+ Inter（无衬线正文）+ JetBrains Mono（等宽数据）
- 尺寸：1280×720px（16:9）

**15页内容索引**：
| 页码 | 标题 | 核心内容 |
|------|------|----------|
| P1 | 封面 | 项目名 + 赛道 + 框架 |
| P2 | 场景与问题 | 金融风控痛点 + WAIC调研 |
| P3 | 解决方案概述 | FinSight = AgentTeams + meta-calibrate |
| P4 | 架构设计 | Manager-Worker + Matrix + Higress |
| P5 | 八环节闭环 | 任务输入→拆解→传递→调用→验证→沉淀→审批→经验 |
| P6 | 六个Skill | fin-analysis/risk-scan/cross-validate/strategy-gen/meta-calibrate/kb-query |
| P7 | meta-calibrate | M-C解离 + L2阈值 + REVERSED + 工作流程 |
| P8 | 安全模型 | Worker零凭证 + Higress网关 + 人工审批 |
| P9 | RAG设计 | 64家公司 + PolarDB + 4项RAG能力 |
| P10 | 数据：M-C解离 | AUROC 0.83-0.93 vs 纠错率38-41% + 98.3%系统性错误 |
| P11 | 数据：L2阈值 | L0=47%→L2=73%→L4=100% + Task-Type Reversal |
| P12 | 可观测 | Trace/Log/Metrics + 经验沉淀 |
| P13 | 差异化 | vs WAIC 8家厂商 + 可复制性 |
| P14 | 路线图 | 已完成→复赛→决赛→开源 |
| P15 | 团队与开源 | 开源计划 + 学术支撑 |

---

## 核心技术亮点

### 1. 原创研究支撑（FinMetaBench）
- **M-C解离**：LLM元认知监测（AUROC 0.83-0.93）与控制（纠错率38-41%）系统性解离
- **系统性错误**：98.3%错误为知识性缺口，多采样投票无效
- **L2相变点**：概念级信息（~80字）才能跨越纠错阈值（47%→73%）
- **REVERSED**：5/6模型高置信错误反而更易纠正
- **Task-Type Reversal**：同一金融领域内，选择题过度自信(+11.8~67.5pp)，分析题不自信(-7.8~-48.2pp)

### 2. AgentTeams多Agent协同
- 5个Agent（1 Manager + 4 Worker），Manager-Worker架构
- 8环节闭环：任务输入→拆解→上下文传递→工具调用→结果验证→证据沉淀→审批回滚→经验沉淀
- Matrix协议通信 + Higress网关凭证隔离 + MinIO共享存储

### 3. 6个可复用Skill
- `meta-calibrate`：核心差异化Skill，基于监测信号触发L2+知识检索纠错
- `fin-analysis` / `risk-scan` / `cross-validate` / `strategy-gen` / `kb-query`
- Skill作为任务能力抽象层，模型无关，可插入任意LLM Agent系统

### 4. 安全与可观测
- Worker零凭证暴露，所有API调用经Higress网关
- BUY/AVOID建议需人工Matrix房间确认
- 全程Trace/Log/Metrics可审计

---

## 与行业方案的差异化

基于 WAIC 2026 调研8家金融AI厂商（蚂蚁、恒生、腾讯、百度、商汤、第四范式、京东科技、润和软件），所有方案均依赖外部规则约束实现风控合规，无一利用模型内生元认知能力。

FinSight 的差异化：
- 不依赖外部规则，利用模型已有的监测信号（AUROC 0.83+）
- 不做简单的置信度校准，而是触发L2+知识检索式纠错
- meta-calibrate作为通用Skill可插入任意Agent系统

---

## 国家政策背书

FinSight 的技术路线与2026年两项核心金融AI政策高度契合：

### 政策一：央行等九部门《关于加强科技金融领域数据开发利用的通知》（2026.07.29）

发文单位：央行、发改委、科技部、工信部、海关总署、市监总局、金融监管总局、知识产权局、国家数据局

| 政策原文 | FinSight对应 |
|---------|-------------|
| "打造特色的科技型企业**风控投研模型**" | 多Agent风控投研系统（5 Agent + 6 Skill） |
| "聚焦**智能风控**环节" | risk-scan Skill 自动风险因子扫描与分级 |
| "加强数据**开放共享和融合运用**" | kb-query + RAG，64家公司财报语义检索 |
| "开展**可信数据空间**试点" | Matrix加密 + Higress网关 + MinIO共享 |
| "加强**全过程安全管理**" | Worker零凭证 + Trace/Log/Metrics + 人工审批 |

### 政策二：金融监管总局 金发〔2026〕8号《银行业保险业人工智能安全开发应用指导意见》（2026.06.18）

| 政策原文 | FinSight对应 |
|---------|-------------|
| "**持续监测模型行为**" | meta-calibrate 监测信号评估（AUROC 0.83-0.93） |
| "推进**知识工程**建设" | kb-query + L2知识检索纠错 |
| "加强**输出验证**" | cross-validate 多Agent交叉校验 |
| "防范**工具滥用、运行失控**" | Higress凭证隔离 + BUY/AVOID人工确认 |
| "制定**透明度和可解释性**标准" | 风险徽章（GREEN/YELLOW/RED）+ 置信度标注 |

**叙事价值**：FinSight不是"我们觉得重要"，而是"国家政策明确要求"——政策方向与学术发现 convergence。

---

## 学术支撑

FinMetaBench 论文初稿已完成，计划投稿 ARR October 2026 → ACL 2027。

三条贡献链：
1. **M-C解离**：元认知监测与控制的系统性分离（6模型验证）
2. **Calibration Reversal**：任务类型决定校准方向（跨6+2模型验证）
3. **校准引导定向纠错**：L2相变点指导知识检索粒度（双模型验证）

---

*本材料为 GOAI 2026 世界人工智能开源大赛 Agent Infra 赛道初赛提交最终版。*
