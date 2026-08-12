# GOAI 2026 世界人工智能开源大赛 — Agent Infra 赛道提交材料

## 赛道：Agent Infra（新智基座）
## 方向：金融风控与理赔自动化
## 项目名称：FinSight — 基于元认知监测与知识检索纠错的多Agent金融风控系统

---

## 一、作品简介（500字）

FinSight 是基于 AgentTeams 框架的多 Agent 金融风控协同系统，将原创研究 FinMetaBench 的发现工程化为可复用 Skill。

系统采用 Manager-Worker 架构：投研总监（Manager）接收企业分析请求，拆解任务并协调4个 Worker（财报分析师、风控哨兵、交叉校验官、策略规划师）完成端到端闭环——财报提取、风险扫描、交叉校验到策略生成，全程 Matrix 房间留痕，支持人工审批回滚。

核心 Skill `meta-calibrate` 基于以下实证发现：在 FinMetaBench（500题×6模型）上，LLM 的元认知监测与控制能力存在系统性解离——监测质量尚可（AUROC 0.83-0.93），但纠错率聚类于38-41%（4个中文模型），自发纠错率仅8.9-16.7%。根因不是监测失灵，而是知识生成瓶颈：98.3%的错误为系统性错误（5次采样仍全错），分级反馈实验显示概念级信息（L2）才能跨越纠错阈值（47%→73%），完整答案（L4）达100%。此外发现 REVERSED 现象：5/6模型中高置信错误反而更易纠正，说明置信度信号未能有效引导纠错。

基于此，meta-calibrate 不做简单的置信度校准，而是利用已有的监测信号触发 L2+ 粒度的知识检索式纠错。补充发现 Task-Type Dependent Calibration Reversal（CFLUE选择题6模型过度自信+11.8~67.5pp，FinBench-Custom分析题2模型不自信-7.8~-48.2pp）为不同金融任务的触发策略提供了依据。

系统将6个能力封装为可复用 Skill，知识库覆盖64家上市公司财报，支持 RAG 检索。Agent 通信走 Matrix 协议，凭证由 Higress 网关托管，Worker 零凭证暴露。

FinSight 的技术路线与国家政策方向高度契合：央行等九部门《关于加强科技金融领域数据开发利用的通知》（2026.07）明确引导金融机构"打造特色的科技型企业风控投研模型"，聚焦"智能风控"环节；金融监管总局金发〔2026〕8号（2026.06）要求"持续监测模型行为"、"推进知识工程建设"，防范Agent"工具滥用、运行失控"。FinSight 的 meta-calibrate 监测纠错机制正是这两项政策要求的技术实现。

---

## 二、Agent Identity 清单

### Agent 1: 投研总监（Manager）

| 属性 | 值 |
|------|-----|
| Agent ID | finsight-manager |
| 角色 | Manager |
| 运行时 | OpenClaw |
| 职责 | 接收用户分析请求→任务拆解→派发Worker→收集结果→生成综合报告→触发校准 |
| 能力边界 | 不直接执行财报分析，仅做编排和汇总 |
| 协同关系 | 向4个Worker派发任务，接收Worker输出，汇总后交策略规划师 |
| 安全边界 | 可读写MinIO共享文件，不直接调用LLM API（通过网关） |
| 校准偏移 | factual=-5, analytical=+10（Manager偏保守汇总） |
| SOUL.md摘要 | "你是FinSight投研总监。你的职责是将复杂金融分析任务拆解为可执行的子任务，协调专业分析师团队完成端到端分析。你不直接做分析，而是确保每个环节的质量和一致性。" |

### Agent 2: 财报分析师（Worker）

| 属性 | 值 |
|------|-----|
| Agent ID | finsight-analyst |
| 角色 | Worker |
| 运行时 | OpenClaw |
| 职责 | 财务健康度分析：营收趋势、利润质量、毛利率变化、现金流状况 |
| 能力边界 | 仅分析财务数据，不做投资建议 |
| 协同关系 | 接收Manager派发的公司分析任务→输出财务分析报告→风控哨兵和交叉校验官可读取 |
| 安全边界 | 只读知识库数据，不修改；通过Higress网关调用LLM |
| 依赖Skill | fin-analysis, kb-query |
| 校准偏移 | factual=-15, analytical=+15（分析师倾向保守判断事实、乐观分析趋势） |
| SOUL.md摘要 | "你是FinSight财报分析师。你擅长从财报数据中提取关键指标，识别财务健康度信号。你坚持数据驱动，不做没有数据支撑的判断。" |

### Agent 3: 风控哨兵（Worker）

| 属性 | 值 |
|------|-----|
| Agent ID | finsight-sentinel |
| 角色 | Worker |
| 运行时 | OpenClaw |
| 职责 | 风险因子扫描：识别财报中的风险信号（利润暴跌、毛利率异常、债务风险等） |
| 能力边界 | 只识别风险，不评估投资价值 |
| 协同关系 | 读取财报分析师输出→扫描风险因子→输出风险报告→策略规划师参考 |
| 安全边界 | 只读，不修改任何数据 |
| 依赖Skill | risk-scan, kb-query |
| 校准偏移 | factual=-10, analytical=+25（风控偏保守，放大风险感知） |
| SOUL.md摘要 | "你是FinSight风控哨兵。你的使命是发现风险，宁可误报不可漏报。你对财务异常高度敏感，擅长识别利润操纵、债务隐患和经营风险。" |

### Agent 4: 交叉校验官（Worker）

| 属性 | 值 |
|------|-----|
| Agent ID | finsight-inspector |
| 角色 | Worker |
| 运行时 | OpenClaw |
| 职责 | 多源数据交叉校验：验证前序Agent输出的一致性，标记冲突和矛盾 |
| 能力边界 | 只做验证和标记，不生成新分析 |
| 协同关系 | 读取分析师+风控哨兵输出→交叉验证→输出一致性报告→策略规划师参考 |
| 安全边界 | 只读，不修改原始数据 |
| 依赖Skill | cross-validate |
| 校准偏移 | factual=-12, analytical=+18（校验官偏严格，倾向质疑） |
| SOUL.md摘要 | "你是FinSight交叉校验官。你不信任任何单一来源的结论，你的职责是发现矛盾、验证一致性。你像审计师一样严谨，每个结论都需要交叉验证。" |

### Agent 5: 策略规划师（Worker）

| 属性 | 值 |
|------|-----|
| Agent ID | finsight-strategist |
| 角色 | Worker |
| 运行时 | OpenClaw |
| 职责 | 综合投资策略：整合前序Agent输出+校准数据→生成BUY/HOLD/AVOID建议 |
| 能力边界 | 只在收到完整前序数据后生成策略，高风险建议需人工确认 |
| 协同关系 | 读取全部前序Agent输出+校准结果→生成策略→交Manager汇总 |
| 安全边界 | BUY/AVOID建议需人工在Matrix房间确认；HOLD可自动输出 |
| 依赖Skill | strategy-gen, meta-calibrate |
| 校准偏移 | factual=-8, analytical=+22（策略师偏保守决策） |
| SOUL.md摘要 | "你是FinSight策略规划师。你综合所有分析师和风控的结论，做出最终投资建议。你知道自己的判断可能有偏差，所以你依赖校准数据来约束自己的自信度。" |

---

## 三、Skill 清单（必选，6个核心Skill）

### Skill 1: fin-analysis（财报分析）

| 字段 | 内容 |
|------|------|
| 名称 | fin-analysis |
| 用途 | 从知识库提取公司财报数据，计算关键财务指标，生成财务健康度分析 |
| 输入 | `{company_code: string, period: string, metrics: string[]}` |
| 输出 | `{indicators: {revenue, net_profit, gross_margin, ...}, analysis_text: string, health_score: number}` |
| 调用条件 | Manager派发财报分析任务时由Analyst Worker调用 |
| 依赖工具 | kb-query Skill（数据源）、Higress网关（LLM调用） |
| 失败处理 | 知识库无数据→返回空+告警；LLM超时→降级返回原始指标计算结果 |
| 安全边界 | 只读知识库，不修改数据；不直接调用外部API |
| 复用价值 | 任何需要财报分析的金融场景（信贷评估、投研、审计、尽调） |
| 与协同流程关系 | Analyst Worker核心能力，输出供Sentinel和Inspector读取 |

### Skill 2: risk-scan（风险扫描）

| 字段 | 内容 |
|------|------|
| 名称 | risk-scan |
| 用途 | 识别财报中的风险因子，按严重程度分级，生成风险评估报告 |
| 输入 | `{financial_data: object, company_context: object}` |
| 输出 | `{risk_level: "HIGH"|"MEDIUM"|"LOW", risk_factors: [{type, severity, description}], risk_score: number}` |
| 调用条件 | Manager派发风控任务时由Sentinel Worker调用 |
| 依赖工具 | kb-query Skill（同业对比数据）、Higress网关（LLM调用） |
| 失败处理 | 数据不足→标记为"无法评估"+告警；LLM超时→降级返回规则引擎结果 |
| 安全边界 | 只读，不修改数据；风险评分不直接触发交易动作 |
| 复用价值 | 信贷风控、投研风控、审计风险识别、合规检查 |
| 与协同流程关系 | Sentinel Worker核心能力，输出供Inspector校验和Strategist参考 |

### Skill 3: cross-validate（交叉校验）

| 字段 | 内容 |
|------|------|
| 名称 | cross-validate |
| 用途 | 对多个Agent的输出进行一致性校验，标记矛盾点，生成验证报告 |
| 输入 | `{agent_outputs: {analyst: object, sentinel: object}, company_data: object}` |
| 输出 | `{consistency_score: number, conflicts: [{source1, source2, description}], verified_claims: string[]}` |
| 调用条件 | Analyst和Sentinel均完成后，由Inspector Worker调用 |
| 依赖工具 | Higress网关（LLM调用） |
| 失败处理 | 输入不完整→标记缺失项+降级为单源验证；LLM超时→返回规则化一致性检查 |
| 安全边界 | 只读不修改原始输出；冲突标记不自动修正，仅提示 |
| 复用价值 | 任何多Agent协同场景的结果验证、多源数据校验、事实核查 |
| 与协同流程关系 | Inspector Worker核心能力，闭环"结果验证"环节 |

### Skill 4: strategy-gen（策略生成）

| 字段 | 内容 |
|------|------|
| 名称 | strategy-gen |
| 用途 | 综合前序Agent输出和校准数据，生成投资策略建议 |
| 输入 | `{analysis: object, risk: object, validation: object, calibration: object}` |
| 输出 | `{recommendation: "BUY"|"HOLD"|"AVOID", confidence: number, rationale: string, key_risks: string[]}` |
| 调用条件 | 前序3个Agent全部完成后，由Strategist Worker调用 |
| 依赖工具 | meta-calibrate Skill（校准置信度）、Higress网关（LLM调用） |
| 失败处理 | 前序数据缺失→降级为HOLD+告警；校准失败→使用原始置信度+标记"未校准" |
| 安全边界 | BUY/AVOID需人工在Matrix房间确认；HOLD可自动输出；不直接触发交易 |
| 复用价值 | 投研决策、信贷审批、风险管理、投资组合管理 |
| 与协同流程关系 | Strategist Worker核心能力，闭环"经验沉淀"环节（校准反馈） |

### Skill 5: meta-calibrate（元认知监测与纠错触发）

| 字段 | 内容 |
|------|------|
| 名称 | meta-calibrate |
| 用途 | 利用LLM已有的监测信号（AUROC 0.83-0.93）评估输出可靠性，对低置信输出触发L2+粒度知识检索式纠错，生成风险徽章 |
| 输入 | `{raw_confidence: number, task_type: "factual"|"analytical", model_id: string, response: string, knowledge_base: object}` |
| 输出 | `{risk_badge: "GREEN"|"YELLOW"|"RED", correction_triggered: boolean, retrieved_knowledge: string, l2_level: number}` |
| 调用条件 | 每个Worker的LLM调用返回后自动执行；strategy-gen生成建议前必须执行 |
| 依赖工具 | kb-query Skill（L2+知识检索）、Higress网关（LLM重检调用） |
| 失败处理 | 监测信号缺失→标记"未评估"+默认YELLOW；知识检索失败→降级为L0提示重答；不阻塞主流程 |
| 安全边界 | 不修改LLM原始输出内容；纠错由原Worker执行，meta-calibrate只提供检索到的知识片段 |
| 复用价值 | 任何使用LLM的Agent系统——模型无关的监测-纠错触发层 |
| 与协同流程关系 | 贯穿全流程，每个Worker调用LLM后执行监测；低置信触发kb-query检索L2+知识→Worker基于检索结果重检 |
| 学术支撑 | FinMetaBench：M-C解离（监测AUROC 0.83-0.93 vs 纠错率38-41%）、98.3%系统性错误、L2阈值（47%→73%）、REVERSED（5/6模型高置信错误更易纠正） |

### Skill 6: kb-query（知识库RAG检索）

| 字段 | 内容 |
|------|------|
| 名称 | kb-query |
| 用途 | 从知识库检索公司财报数据、行业对比数据、历史分析记录 |
| 输入 | `{query: string, company_code: string, top_k: number}` |
| 输出 | `{results: [{content, source, score}], context: string}` |
| 调用条件 | fin-analysis和risk-scan需要数据时调用 |
| 依赖工具 | PolarDB for PostgreSQL（向量存储）、MinIO（原始财报文件） |
| 失败处理 | 检索无结果→返回空+日志；数据库超时→降级返回缓存数据 |
| 安全边界 | 只读，不修改知识库；检索结果带来源标注 |
| 复用价值 | 任何需要金融数据检索的场景；可作为RAG模板用于其他领域 |
| 与协同流程关系 | 为Analyst和Sentinel提供数据基础，闭环"上下文增强"环节 |

---

## 四、多Agent闭环设计（8环节映射）

```
用户在 Element Web 选择目标公司
         │
         ▼
┌─ ① 任务输入 ──────────────────────────────────┐
│  用户 → Manager Matrix房间："分析比亚迪电子0285.HK" │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ② 任务拆解 ──────────────────────────────────┐
│  Manager 拆为4个子任务：                          │
│  T1: 财报分析 → Analyst                          │
│  T2: 风险扫描 → Sentinel                         │
│  T3: 交叉校验 → Inspector（依赖T1+T2完成）         │
│  T4: 策略生成 → Strategist（依赖T1+T2+T3完成）     │
│  T1/T2并行，T3串行等待，T4串行等待                  │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ③ 上下文传递 ─────────────────────────────────┐
│  T1完成 → Analyst在Matrix房间发布分析报告           │
│  T2完成 → Sentinel在Matrix房间发布风险报告          │
│  T3启动 → Inspector读取T1+T2报告，执行校验          │
│  T4启动 → Strategist读取T1+T2+T3全部报告           │
│  文件类产出存入MinIO，Matrix房间仅传递摘要+链接       │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ④ 工具调用 ──────────────────────────────────┐
│  Analyst调用: kb-query → fin-analysis → meta-calibrate │
│  Sentinel调用: kb-query → risk-scan → meta-calibrate   │
│  Inspector调用: cross-validate → meta-calibrate         │
│  Strategist调用: meta-calibrate → strategy-gen          │
│  所有LLM调用通过Higress网关，Worker不持有API Key        │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ⑤ 结果验证 ──────────────────────────────────┐
│  Inspector Worker 执行 cross-validate Skill：       │
│  - 检查Analyst和Sentinel结论是否一致                │
│  - 标记矛盾点（如Analyst说健康，Sentinel说高风险）    │
│  - 验证关键财务指标的计算正确性                      │
│  - 输出一致性评分 + 冲突列表                         │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ⑥ 执行证据沉淀 ───────────────────────────────┐
│  Matrix房间：全部对话、工具调用、中间结论留痕         │
│  MinIO存储：完整分析报告、风险报告、校准日志          │
│  Manager汇总：生成结构化执行证据包（JSON+Markdown）   │
│  可追溯：每个结论可追溯到源数据和Agent推理链           │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ⑦ 审批与回滚 ────────────────────────────────┐
│  Strategist输出BUY/AVOID → Matrix房间@用户确认      │
│  用户可：✅确认 / ❌否决 / 🔄要求重做               │
│  确认 → Manager生成最终报告                         │
│  否决 → Manager记录否决原因，触发重新分析             │
│  重做 → 回到②，Manager调整拆解策略                  │
│  HOLD建议可自动输出，无需人工确认                     │
└───────────────────────────┬───────────────────┘
                            ▼
┌─ ⑧ 经验沉淀 ──────────────────────────────────┐
│  校准结果反馈：每次meta-calibrate的offset写入知识库   │
│  案例归档：完整分析流程存入MinIO，可复用于相似公司     │
│  参数更新：Manager定期汇总校准偏差，调整Worker的       │
│  calOffset参数（如某Worker持续过度自信→增大负偏移）   │
│  知识库扩展：新分析的公司财报数据自动入库              │
└────────────────────────────────────────────────┘
```

---

## 五、AgentTeams 架构映射

### 5.1 框架能力映射

| AgentTeams能力 | FinSight映射 |
|---------------|-------------|
| 角色编排 | Manager=投研总监, Workers=分析师/哨兵/校验官/策略师 |
| 任务拆解 | Manager将"分析公司X"拆为4个子任务，T1/T2并行，T3/T4串行 |
| 上下文传递 | Matrix房间共享对话+MinIO共享文件，Worker间通过@mension传递 |
| 协同执行 | T1/T2并行执行→T3等待T1+T2完成→T4等待T3完成 |
| 状态追踪 | Manager监听各Worker完成状态，Matrix消息即状态变更事件 |

### 5.2 声明式资源定义（YAML示例）

```yaml
# Team 定义
apiVersion: agentteams.io/v1
kind: Team
metadata:
  name: finsight-team
spec:
  manager:
    runtime: openclaw
    soul: |
      你是FinSight投研总监。你的职责是将复杂金融分析任务拆解为
      可执行的子任务，协调专业分析师团队完成端到端分析。
  workers:
    - name: analyst
      runtime: openclaw
      skills: [fin-analysis, kb-query, meta-calibrate]
      soul: |
        你是FinSight财报分析师。你擅长从财报数据中提取关键指标。
    - name: sentinel
      runtime: openclaw
      skills: [risk-scan, kb-query, meta-calibrate]
      soul: |
        你是FinSight风控哨兵。你的使命是发现风险，宁可误报不可漏报。
    - name: inspector
      runtime: openclaw
      skills: [cross-validate, meta-calibrate]
      soul: |
        你是FinSight交叉校验官。你不信任任何单一来源的结论。
    - name: strategist
      runtime: openclaw
      skills: [strategy-gen, meta-calibrate]
      soul: |
        你是FinSight策略规划师。你依赖校准数据来约束自己的自信度。
  humans:
    - name: analyst-user
      role: approver
      rooms: [finsight-main]
```

### 5.3 安全模型

```
用户（Element Web）
    │ Matrix协议（端到端加密）
    ▼
Manager Agent ──── Higress AI Gateway ──── LLM API (GLM-5.2/DeepSeek/Qwen)
    │                    │                    MCP Servers
    │ Matrix协议         │ 凭证托管            Skills Registry
    ▼                    │
Worker Agents ──────────┘ (consumer token only, 无真实API Key)
    │
    ▼
MinIO（共享文件） + PolarDB（知识库RAG）
```

- Worker 永不持有真实 API Key，仅持 consumer token
- 所有 LLM/MCP 调用经 Higress 网关代理
- Matrix 全对话加密留痕
- MinIO 文件访问受网关权限控制

---

## 六、RAG 与上下文增强

满足4项中3项（要求至少2项）：

| 能力 | 实现 |
|------|------|
| ✅ 知识库RAG | 64家上市公司财报存入PolarDB for PostgreSQL（pgvector），kb-query Skill执行语义检索 |
| ✅ Agent记忆存储 | 每个Worker的SOUL.md定义人格+校准参数；校准历史写入MinIO |
| ✅ 共享状态管理 | Matrix房间传递对话上下文，MinIO传递文件，Manager维护全局状态 |
| ✅ 轨迹可观测 | Matrix全对话留痕（Trace），Manager心跳（Metrics），Skill调用日志（Log） |

### 知识库RAG架构

```
原始财报数据（64家公司）
    │ 向量化
    ▼
PolarDB for PostgreSQL (pgvector)
    │ 语义检索
    ▼
kb-query Skill
    │ 返回top-k相关片段
    ▼
Analyst/Sentinel Worker
    │ 注入LLM context
    ▼
分析结果 + 来源标注
```

---

## 七、可观测设计

| 数据类型 | 采集方式 | 应用场景 |
|---------|---------|---------|
| Trace | Matrix消息序列（每条消息含Agent ID+时间戳+Skill调用链） | 追溯分析推理链，定位错误环节 |
| Log | Skill调用日志（输入/输出/耗时/状态） | Skill质量评估，失败排查 |
| Metrics | Manager心跳（Worker状态/任务进度/校准偏差统计） | 实时监控，告警，参数调优 |

建议遵循 OpenTelemetry GenAI 语义规范，为后续接入 AgentLoop/LoongSuite 铺路。

---

## 八、核心差异化——meta-calibrate Skill 的学术基础

### 8.1 核心发现：M-C解离（论文 Section 4.1）

FinMetaBench 在500题×6模型上发现，LLM的元认知可分解为监测（M）和控制（C）两个功能独立的组件，二者系统性解离：

| 维度 | 指标 | 数据 | 说明 |
|------|------|------|------|
| 监测（M） | AUROC | 0.83-0.93（Step/Mistral除外） | 模型区分对错的能力其实不差 |
| 控制（C） | 无条件纠错率 | 38-41%（4个中文模型聚类） | 被告知"错了"后的纠错率 |
| 控制（C） | 自发纠错率 | 8.9-16.7%（GLM） | 不告知对错，模型自己判断要不要改 |
| 理论上限 | Oracle（L4） | 96.4-100% | 给完整答案后的识别率 |

关键洞察：**监测能力够用，bottleneck在知识生成**。模型能识别对错（AUROC 0.83+），但无法自行生成正确答案。

### 8.2 系统性错误与多采样失效（论文 Section 4.4）

GLM-5.2 的121个错误题，5次采样（temp=0.7）：
- 98.3%的错误：5次采样全错——系统性知识缺口
- 仅1.7%：采样中出现过正确答案
- 0%的错误：5次给出相同错误答案（错误有变化但仍是错的）

结论：多采样投票对金融推理错误无效，因为错误是知识性的而非随机性的。

### 8.3 L2阈值：知识粒度的相变点（论文 Section 4.5）

分级反馈实验，逐步增加反馈信息量：

| 级别 | 给模型什么 | GLM纠错率 | Qwen纠错率 | 跨越 |
|------|-----------|----------|-----------|------|
| L0 | "你答错了" + 反思 | 47% | 32.1% | 基线 |
| L1 | + 主题提示（30字） | 52% | 45.7% | +5pp / +13.6pp |
| L2 | + 关键概念（80字） | 73% | 60.7% | **+21pp / +15pp 相变** |
| L3 | + 详细解释（200字） | 87% | 79.3% | +14pp / +18.6pp |
| L4 | + 完整正确答案 | 100% | 96.4% | +13pp / +17.1pp |

关键发现：L1→L2 是相变点。主题级提示不够，必须到概念级信息（~80字）才能跨越纠错阈值。meta-calibrate 据此设计：低置信输出触发 kb-query 检索 L2+ 粒度知识，而非简单要求模型重答。

### 8.4 REVERSED：置信度与可纠错性的反常关系（论文 Section 4.6）

| 模型 | 低置信纠错率(<0.7) | 高置信纠错率(≥0.7) | 模式 |
|------|-------------------|-------------------|------|
| GLM-5.2 | 20.0% | 42.3% | REVERSED |
| DeepSeek-V3 | 36.4% | 38.5% | REVERSED (mild) |
| Qwen-Plus | 28.6% | 39.5% | REVERSED |
| MiMo-v2.5 | 16.7% | 39.0% | REVERSED |
| Step-3.5-Flash | 30.6% | 17.9% | Normal |
| Mistral-7B | 1.9% | 1.2% | No signal |

5/6模型出现REVERSED：高置信错误反而更易纠正。原因：91.7%的错误携带高置信度（≥0.7），少量低置信错误接近随机猜测，几乎不可纠正。这说明置信度信号未能有效引导纠错——模型"自信地错"比"犹豫地错"更容易被纠正。

### 8.5 Task-Type Dependent Calibration Reversal（FinBench-Custom扩展实验）

在 FinBench-Custom（自建金融分析评测集）上扩展验证：

| 任务类型 | 模型 | 校准方向 | Gap |
|---------|------|---------|-----|
| CFLUE选择题 | GLM-5.2 | 过度自信 | +11.8pp |
| CFLUE选择题 | DeepSeek-V3 | 过度自信 | +16.4pp |
| CFLUE选择题 | Qwen-Plus | 过度自信 | +27.8pp |
| CFLUE选择题 | Mistral-7B | 过度自信 | +67.5pp |
| FinBench分析题 | GLM-5.2 | 不自信 | -7.8~-40.8pp |
| FinBench分析题 | Kimi-k2.6 | 不自信 | -10.6~-48.2pp |

同一金融领域内，任务类型不同→校准方向反转。这一发现指导 meta-calibrate 的 Task-Type 策略：事实性任务（选择题/指标计算）calibrate down + 触发检索纠错；分析性任务（趋势分析/策略建议）calibrate up + 不触发纠错。

### 8.6 meta-calibrate 工作流程（基于论文发现设计）

```
LLM输出 (raw_confidence, task_type, response)
    │
    ▼
监测评估
    │ AUROC 0.83-0.93 → 监测信号可信
    │ 阈值判断：
    │   GREEN ≥ 0.75 → 通过
    │   YELLOW ≥ 0.50 → 标记预警
    │   RED < 0.50 → 触发纠错
    ▼
触发L2+知识检索（非简单重答）
    │ kb-query 检索 ~80字+ 相关概念
    │ 注入Worker context → Worker基于知识重检
    ▼
输出: {badge, correction_triggered, retrieved_knowledge, l2_level}
```

设计依据：
- 不用多采样投票（98.3%系统性错误，投票无效）
- 不用结构化自审（论文证明改善监测但降低纠错率，C: 40.5%→35.2%）
- 用L2+知识检索（L2相变点47%→73%，L4上限96.4-100%）

---

## 九、国家政策对齐分析

FinSight 的技术路线与2026年两项核心金融AI政策高度契合，以下为逐条映射：

### 9.1 央行等九部门《关于加强科技金融领域数据开发利用的通知》（2026.07.29）

**发文单位**：中国人民银行、国家发展改革委、科技部、工业和信息化部、海关总署、市场监管总局、金融监管总局、国家知识产权局、国家数据局

**发布《全国科技金融领域数据开发利用目录1.0》**：8大类、26个数据指标

| 政策要求 | FinSight 对应实现 |
|---------|------------------|
| "引导金融机构依托科技金融领域数据库，构建科技型企业数字信用画像，**打造特色的科技型企业风控投研模型**" | FinSight 多Agent风控投研系统：5个Agent协同完成财报分析→风险扫描→交叉校验→策略生成，覆盖64家上市公司 |
| "聚焦融资对接、**智能风控**、产品创新等环节" | risk-scan Skill 实现智能风控：风险因子自动扫描、分级评估、交叉校验 |
| "加强科技金融领域数据**开放共享和融合运用**" | kb-query Skill + RAG：64家公司财报向量化存储于PolarDB，支持语义检索与多源融合 |
| "开展科技金融**可信数据空间**创新发展试点" | Matrix协议加密通信 + Higress网关凭证隔离 + MinIO共享存储 = 可信数据空间架构 |
| "加强**全过程安全管理**，切实防范各种数据风险" | Worker零凭证暴露 + 全程Trace/Log/Metrics可审计 + 人工审批回滚 |
| "推广**信息查询、联合建模**等模式" | 多Agent协同分析 = 联合建模；kb-query = 信息查询；meta-calibrate = 模型质量监测 |

### 9.2 金融监管总局 金发〔2026〕8号《银行业保险业人工智能安全开发应用指导意见》（2026.06.18）

**发文单位**：国家金融监督管理总局

| 政策要求 | FinSight 对应实现 |
|---------|------------------|
| "**持续监测模型行为**"（第二十条） | meta-calibrate Skill 核心功能：每个Worker的LLM调用后自动执行监测信号评估（AUROC 0.83-0.93） |
| "推进**知识工程**建设"（第十一条） | kb-query Skill + L2知识检索：构建企业级知识库，支持知识萃取、整合、共享 |
| "建立从知识创建、审核、发布、更新到归档的**全流程管理规范**" | 8环节闭环：任务输入→拆解→传递→调用→验证→证据沉淀→审批回滚→经验沉淀 |
| "加强**对抗攻击测试和输出验证**" | cross-validate Skill：多Agent输出交叉校验，标记矛盾点，验证一致性 |
| "防范数据泄露、记忆污染、身份越权、**工具滥用、运行失控**等安全风险" | Higress网关凭证隔离 + Worker零凭证 + BUY/AVOID人工确认 + Matrix全对话留痕 |
| "为高风险场景应用制定**透明度和可解释性**标准" | meta-calibrate输出风险徽章（GREEN/YELLOW/RED）+ 置信度标注 + 纠错触发记录 |
| "建立对监管政策和监管效果的**年度评估机制**" | 经验沉淀环节：校准参数自动更新 + 案例归档 + Manager定期汇总校准偏差 |
| "鼓励利用人工智能技术提升**知识萃取、表示、融合和对齐能力**" | L2+知识检索纠错：从知识库检索概念级信息（~80字），注入Worker context实现知识对齐 |

### 9.3 政策叙事价值

FinSight 的参赛叙事因此获得三重支撑：

1. **战略正当性**：不是"我们觉得重要"，而是"国家政策明确要求"——央行九部门通知直接点名"风控投研模型"和"智能风控"
2. **监管合规性**：金发〔2026〕8号对金融AI提出的安全要求，FinSight通过架构设计逐条响应
3. **技术前瞻性**：政策要求"持续监测模型行为"和"知识工程建设"，而FinSight的meta-calibrate正是基于FinMetaBench研究的"监测信号+知识检索纠错"机制——政策方向与学术发现 convergence

---

## 十、方案PPT框架（15页）

### P1. 封面
- FinSight: 基于元认知校准的多Agent金融风控协同系统
- GOAI 2026 Agent Infra 赛道 · 金融风控与理赔自动化
- 基于 AgentTeams 框架 + FinMetaBench 研究

### P2. 场景与问题
- 金融风控的痛点：AI"自信地给出错误答案"
- WAIC 2026调研：8家厂商均依赖外部规则约束，无内生元认知能力
- 现有多Agent系统缺乏"自我认知"层——Agent不知道自己不知道
- **国家政策方向**：央行九部门通知（2026.07）要求"打造风控投研模型"；金发〔2026〕8号（2026.06）要求"持续监测模型行为"、"知识工程建设"

### P3. 解决方案概述
- FinSight = AgentTeams多Agent协同 + 元认知校准Skill
- 5个Agent（1 Manager + 4 Worker）端到端金融风控闭环
- 6个可复用Skill，核心差异化在meta-calibrate
- 全程Matrix透明可审计，人工可干预

### P4. AgentTeams架构设计
- Manager-Worker架构图
- 5个Agent角色编排与职责
- Matrix协议通信 + Higress网关 + MinIO共享存储
- 声明式YAML资源定义

### P5. 多Agent闭环流程
- 8环节闭环图（任务输入→拆解→上下文传递→工具调用→结果验证→证据沉淀→审批回滚→经验沉淀）
- T1/T2并行 → T3串行等待 → T4串行等待
- 关键设计：Inspector做结果验证，Strategist需人工确认BUY/AVOID

### P6. Skill工程体系（1）— 6个核心Skill
- fin-analysis / risk-scan / cross-validate / strategy-gen / meta-calibrate / kb-query
- 每个Skill的输入输出、调用条件、失败处理、复用价值
- Skill作为任务能力抽象层，不是一次性Agent行为

### P7. Skill工程体系（2）— meta-calibrate 监测与纠错触发
- 学术基础：M-C解离（监测AUROC 0.83-0.93 vs 纠错率38-41%）
- 为什么不用多采样投票：98.3%系统性错误
- 为什么不用结构化自审：改善监测但降低纠错（C: 40.5%→35.2%）
- 工作流程：监测信号评估→低置信触发L2+知识检索→Worker基于知识重检
- L2相变点：L0=47%→L2=73%→L4=100%（跨GLM+Qwen双模型验证）
- REVERSED发现：5/6模型高置信错误更易纠正

### P8. 安全与凭证隔离
- Worker零凭证暴露（consumer token only）
- Higress网关统一托管API Key
- Matrix全对话加密留痕
- BUY/AVOID需人工Matrix房间确认
- 审批/回滚/审计机制

### P9. RAG与上下文增强
- 知识库RAG：64家公司财报 → PolarDB pgvector → kb-query Skill
- Agent记忆：SOUL.md + 校准参数历史
- 共享状态：Matrix + MinIO
- 轨迹可观测：Trace/Log/Metrics

### P10. 核心实验数据（1）— M-C解离与系统性错误
- 监测（M）vs 控制（C）解离：AUROC 0.83-0.93 vs 纠错率38-41%
- 4个中文模型纠错率聚类于38-41%（GLM 40.5%/DS 38.8%/Qwen 39.5%/MiMo 38.5%）
- 自发纠错率仅8.9-16.7%（GLM），告知"错了"后升至38-41%
- 多采样失效：98.3%错误为系统性知识缺口（5次采样全错）
- REVERSED：5/6模型高置信错误反而更易纠正（91.7%错误携带高置信度）
- 结构化自审反而降低纠错：C 40.5%→35.2%（监测改善但控制恶化）

### P11. 核心实验数据（2）— L2阈值与Task-Type策略
- 分级反馈L0-L4：L0=47%→L1=52%→L2=73%→L3=87%→L4=100%（GLM）
- 跨模型复制：Qwen L0=32.1%→L2=60.7%→L4=96.4%
- L1→L2相变：概念级信息（~80字）是跨越纠错阈值的关键粒度
- Task-Type Dependent Calibration Reversal：
  - CFLUE选择题：6模型全部过度自信（+11.8~67.5pp）
  - FinBench分析题：2模型全部不自信（-7.8~-48.2pp）
- 设计含义：事实性任务calibrate down+触发检索，分析性任务calibrate up+不触发

### P12. 可观测与经验沉淀
- Trace：Matrix消息序列追溯推理链
- Log：Skill调用日志
- Metrics：Manager心跳 + 校准偏差统计
- 经验沉淀：校准参数自动更新 + 案例归档复用

### P13. 差异化与行业可复制性
- 对比WAIC 8家厂商：均依赖外部规则约束，无一利用模型内生监测信号
- FinSight：利用已有监测信号（AUROC 0.83+）触发L2+知识检索纠错，不依赖外部规则
- meta-calibrate可插入任意LLM Agent系统，模型无关
- **政策对齐**：央行九部门通知明确要求"风控投研模型"和"智能风控"；金发〔2026〕8号要求"持续监测模型行为"——FinSight逐条响应
- 场景迁移：信贷风控→保险理赔→审计→合规
- 开源计划：FinMetaBench评测框架 + 6个Skill + AgentTeams配置

### P14. 工程落地与路线图
- 已完成：6模型验证 + 64家公司知识库 + 4套评测任务 + 交易终端Demo
- 复赛计划：AgentTeams部署 + Skill实现 + 可运行Demo
- 决赛目标：完整闭环演示 + 代码仓库 + 开源发布
- 长期：FinMetaBench论文投稿ARR October → ACL 2027

### P15. 团队与开源贡献
- 基于FinMetaBench开源研究框架
- 计划开源：6个Skill + AgentTeams配置 + 评测数据集
- 数据来源：CFLUE金融职业资格考试 + 港交所公开财报
- 学术支撑：ICLR 2027投稿中，三大贡献点

---

## 十一、提交清单

### 初赛提交材料（截止 2026-08-16）

| 序号 | 材料 | 状态 | 文件 |
|------|------|------|------|
| 1 | 作品简介（500字） | ✅ 定稿 | 本文档 第一部分 |
| 2 | 方案PPT（15页） | ✅ 定稿 | FinSight_presentation.html |
| 3 | Agent Identity清单（5个Agent） | ✅ 定稿 | 本文档 第二部分 |
| 4 | Skill清单（6个核心Skill） | ✅ 定稿 | 本文档 第三部分 |
| 5 | 多Agent闭环设计（8环节） | ✅ 定稿 | 本文档 第四部分 |
| 6 | AgentTeams架构映射 | ✅ 定稿 | 本文档 第五部分 |

### 复赛阶段补充材料（8.25-9.3）

| 序号 | 材料 | 状态 | 说明 |
|------|------|------|------|
| 7 | AgentTeams代码包 | 待提交 | 复赛需可运行Demo |
| 8 | 可运行Demo部署 | 待提交 | Docker环境部署HiClaw |

## 十二、关键数据索引

| 数据 | 来源 |
|------|------|
| 6模型CFLUE精确数据 | FinMetaBench论文初稿表1 |
| Temperature Scaling校准结果 | 论文初稿表2 |
| 阈值触发结果 | 论文初稿表3 |
| FinBench-Custom双模型结果 | 论文初稿表4 |
| Graded Feedback L0-L4 | 论文初稿表5 |
| Multi-sampling结果 | 论文初稿表6 |
| WAIC 2026调研报告 | waic2026_fintech_ai_report.md |
