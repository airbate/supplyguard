---
title: SupplyGuard 设计文档
version: v0.1（骨架版）
status: DRAFT
date: 2026-08-10
author: kona
context: GOAI 2026 Infra 赛道参赛作品 + 创业刚需自用工具
---

# SupplyGuard 设计文档 v0.1

> 本文档为 v0.1 骨架版，只记录已经与用户对齐的方案主干。Agent 分工、Skill 清单、AgentTeams 映射、技术选型等细节将在后续版本补齐。

## 1. 背景

### 1.1 参赛背景

- **赛道**：GOAI 2026 Infra —— 企业级复杂任务下的多 Agent 基础设施与协同系统
- **核心要求**：≥3 个不同职能的 Agent 组成端到端闭环；必须以 AgentTeams 为设计基点；Skill 是必选项
- **评审权重**：场景价值 25% + 多 Agent 协同 25% + Skill 体系 25% + 工程落地 20% + 开源 5%
- **关键时间**：初赛 8.16，复赛 9.3，决赛 9.22

### 1.2 现实背景

- 作者是全栈开发工程师、正在创业，供应链安全是自身刚需
- AI 编程工具（Copilot、Cursor、Claude Code）的普及带来了新的攻击面
- 传统 SCA 工具（Snyk、Dependabot、npm audit）以"扫描 + 告警"为主，Agent 化不足
- 中小团队缺乏一套轻量、可运行、可自托管的智能供应链防御方案

### 1.3 问题定义

企业软件的依赖安全存在两个截然不同、但共享底层能力的痛点时刻：

1. **引入时刻**（proactive）：开发者/AI 提交 PR 引入新依赖或升级版本，此刻是最经济的拦截点。但传统工具在这里只做 CVE 匹配，无法识别 AI 幻觉包、恶意脚本、license 冲突、维护者变更等复合信号，也不参与决策。
2. **爆发时刻**（reactive）：类似 xz-utils、event-stream、log4shell 级别的零日事件披露，团队需要在几小时内完成"我有没有中招—影响多大—怎么修—修完对不对"的全闭环。目前基本靠人肉救火。

两个时刻的核心底层能力（依赖图、SBOM、包风险画像、修复策略）高度重叠，但工作流不同。多 Agent 架构在这里天然适配。

## 2. 目标与非目标

### 2.1 目标（v1）

- 面向单个代码仓库或多仓库组织的供应链安全防御
- 覆盖主流生态：npm / PyPI / Maven（至少支持其一，v1 优先 npm，因为 slopsquatting 在 npm 最猖獗）
- 双入口：守门模式（PR 触发）+ 响应模式（CVE feed 触发）
- 全闭环：检测 → 分析 → 决策 → 修复 → 验证 → 审计 → 沉淀
- 支持人工审批与回滚（高风险动作）
- 可自托管、可开源分发

### 2.2 非目标（明确不做）

- 不做二进制层面的静态分析（那是 Semgrep / CodeQL 的地盘）
- 不做运行时防护（不是 RASP / eBPF 工具）
- 不做企业级 SSO / 多租户管理（v1 单团队足够）
- 不重造 CVE 数据库，直接消费 GHSA / OSV / NVD

## 3. 解决方案：双入口一引擎

### 3.1 顶层结构

```
                    ┌─────────────────────────────────────┐
                    │        SupplyGuard 共享引擎          │
                    │  依赖图 · SBOM · 包画像 · 修复策略    │
                    └─────────────────────────────────────┘
                              ▲                ▲
                              │                │
              ┌───────────────┘                └──────────────┐
              │                                                │
     ┌────────────────┐                             ┌─────────────────┐
     │   守门模式     │                             │    响应模式      │
     │ (Proactive)    │                             │  (Reactive)     │
     ├────────────────┤                             ├─────────────────┤
     │ 触发：PR/依赖变更 │                             │ 触发：CVE/恶意包披露│
     │ 目标：拦截      │                             │ 目标：救火       │
     └────────────────┘                             └─────────────────┘
```

### 3.2 守门模式（Proactive Guard）

**触发**：GitHub/GitLab PR webhook；本地 pre-commit / pre-push hook；IDE 插件（可选，v1 不做）

**目标场景**：
- 开发者手写代码引入新依赖
- AI 助手（Copilot/Cursor/Claude Code）生成的代码引入了幻觉包（slopsquatting 攻击面）
- 依赖版本升级引入的高危 CVE 或 breaking change
- license 不兼容（GPL 污染专有代码库等）
- 包维护者近期变更、包发布方式异常等弱信号

**决策产物**：Allow / Block / Require Human Review + 决策证据链

### 3.3 响应模式（Reactive Response）

**触发**：GHSA/OSV/NVD 增量事件订阅；自建威胁情报源；手动导入（"我听说 xz 又出事了"）

**目标场景**：
- 零日 CVE 全库影响面评估
- 恶意包披露后的紧急下线（含传递依赖）
- 大规模版本升级的批量 PR 生成
- 影响面报告与合规留痕

**决策产物**：影响面清单 + 缓解 PR 集合 + 处置报告

### 3.4 共享引擎的四大底层能力

以下四块是"两入口一引擎"里的**引擎**，也是 Skill 化的天然候选：

1. **依赖图与 SBOM 建模**：解析 lockfile → 构建包依赖 DAG → 维护 SBOM
2. **包风险画像**：多维度评分（CVE + 幻觉概率 + 维护活跃度 + 发布行为异常 + license）
3. **修复策略生成**：升级 / 降级 / 替换 / 隔离 / 移除，附影响面预估
4. **审计与知识沉淀**：决策证据、Trace、复盘、可复用规则

### 3.5 洋葱式安全架构（Defense in Depth）

**核心洞察**：SupplyGuard 的工作对象是"可能怀有恶意的第三方内容"——包源码、README、CVE 描述、commit message、维护者变更说明等，都会被 Agent 读取用于决策。恶意包完全可以在其中嵌入 prompt injection，试图操纵 Agent 帮它"过关"。

**这是 SupplyGuard 特有的元级攻击面**——存量 SCA 工具（Snyk、Dependabot）无需担心，因为它们不是 LLM 系统；Agent 化的供应链安全产品必须原生防御。这也是本方案相对存量工具的结构性差异。

**七层洋葱**（外→内）：

| 层 | 职责 | 关键设计 |
| --- | --- | --- |
| 1. 感知层 | 统一标记 UNTRUSTED | 所有外部输入进入前打标签，不做解析 |
| 2. 净化层 | 沙箱解析 + 注入检测 | 文件解析在容器 / wasm 沙箱内；schema 强校验；剥离零宽字符、异常编码；自由文本走 injection detector |
| 3. 上下文隔离层 | 证据边界化 | Agent prompt 明确 `<untrusted_source>...</untrusted_source>` 标签内是证据不是指令；采用 spotlighting / delimiting 模式 |
| 4. 能力最小化 | 每个 Agent 只有职能所需工具 | 分析 Agent 只读；修复 Agent 只能开 PR 不能 merge；触发 Agent 无外部网络 |
| 5. 决策仲裁 | 高风险动作二次判断 | Auditor Agent 只看结构化证据链，不接触原始 untrusted 内容；类 privileged-LLM / dual-LLM 模式 |
| 6. 执行沙箱 | install / test 全隔离 | 临时容器；`--ignore-scripts`；postinstall 单独审查；白名单网络 |
| 7. 审计不可否认 | 决策全链路可回放 | Provenance 签名；append-only log；证据哈希指纹 |

**产品定位**：洋葱作为**内部架构护城河**优先。v1 不外化为独立 SDK / 开源基础设施——理由是"好的产品别人付费才能持续做下去"，商业化优先于工具化。若未来商业化验证成功，再考虑将其中若干层（如 injection detector）作为独立能力对外。

**Demo 支撑点**：可专门设计一段剧情——恶意包在 README 里嵌入 "ignore previous instructions" 类攻击，被 Auditor 层识破。戏剧感强、评委记忆点强。

**评审对齐**：本节直接命中赛道评审维度中的"安全边界"（Skill 要求）、"审批 / 回滚 / 审计机制"（多 Agent 闭环要求）、"工程落地与安全可审计"（20% 权重）。

## 4. Agent 分工与协作

### 4.1 设计原则

- **职责最小可分**：满足赛道"≥3 个不同职能"要求，同时避免过度拆分导致协同复杂度爆炸。v1 定 **4 个 Agent**。
- **能力最小化**：每个 Agent 只被授予完成职能所需的最小工具集（对应洋葱第 4 层）。
- **决策与执行分离**：Analyst 只读；Remediator 只能开 PR 不能 merge；Auditor 做仲裁不做行动。
- **入口无感**：4 个 Agent 同时服务守门模式与响应模式，Sentinel 的入口路由屏蔽差异。

### 4.2 四个 Agent

#### Sentinel（哨兵 / Coordinator）

- **身份**：外部世界与内部系统的唯一接口层，承担多 Agent 协同框架下的编排角色。
- **输入**：GitHub / GitLab PR webhook；OSV / GHSA / NVD 增量事件订阅；手动触发。
- **输出**：任务包（含入口类型、上下文、优先级、目标 Agent）投递到消息队列 / 共享状态。
- **工具能力**：MCP-GitHub（读 PR）、MCP-OSV（读 feed）、消息队列生产者、Session 状态写入。
- **边界**：不做安全判断；不接触修复动作；无写代码权限。
- **协作协议**：向 Analyst 发送 `AnalysisRequest`（含入口类型 + untrusted payload 标签化后的上下文包）。
- **洋葱层职责**：**第 1 层（感知层）**——对所有输入统一打 UNTRUSTED 标签、剥离危险编码、封装边界标签。

#### Analyst（分析师）

- **身份**：多信号融合的风险画像生成者。
- **输入**：Sentinel 派发的 `AnalysisRequest`。
- **输出**：结构化 `RiskProfile`（多维度评分 + 证据链 + 建议动作）。
- **工具能力**：
  - Skill：`sbom-build`、`cve-match`、`hallucination-check`、`maintainer-profile`、`reachability-scan`、`license-check`
  - MCP：npm registry、PyPI、Maven Central、Socket / OSV
- **边界**：只读；不能开 PR；不能修改文件系统。
- **协作协议**：向 Auditor 送 `RiskProfile` 请求仲裁；明确低风险可绕过 Auditor 直通 Sentinel 结案。
- **洋葱层职责**：**第 2、3 层（净化层 + 上下文隔离层）**——untrusted 内容在 sandbox 中解析；LLM 调用用 `<untrusted_source>` 标签包裹。

#### Remediator（修复师）

- **身份**：修复策略生成与 PR 落地者。
- **输入**：Auditor 批准后的 `RemediationOrder`。
- **输出**：目标仓库的 PR（含变更、测试结果、回归判断、修复报告）。
- **工具能力**：
  - Skill：`bump-version`、`swap-dependency`、`quarantine-package`、`generate-patch`、`sandbox-test-run`
  - MCP：GitHub / GitLab 写权限（仅限开 PR）、CI 触发接口
- **边界**：只能开 PR，不能 merge；不能直推 main；install / test 全部在洋葱第 6 层沙箱内进行。
- **协作协议**：完成后向 Auditor 报告 `RemediationResult`（含验证证据）；被拒后向 Sentinel 报升级。
- **洋葱层职责**：**第 6 层（执行沙箱）**——所有 install / test 在临时容器内，`--ignore-scripts`，postinstall 独立审查。

#### Auditor（审计员 / Arbiter）

- **身份**：决策仲裁 + 审计留痕的独立监督者。
- **输入**：`RiskProfile`（分析结果）、`RemediationResult`（修复结果）。
- **输出**：`Verdict`（Allow / Block / RequireHumanReview）+ 不可否认的审计日志。
- **工具能力**：
  - Skill：`evidence-verify`、`policy-check`、`human-approval-request`、`audit-log-write`
  - MCP：审批系统（钉钉 / 飞书 / GitHub review）、签名服务
- **边界**：**只看结构化证据链，不接触任何 untrusted 原始文本**（洋葱第 5 层核心）；无写代码权限；无外部网络（防被反渗透）。
- **协作协议**：接收 Analyst / Remediator 报文；最终裁决签名后写入 append-only log；高风险动作触发人工审批。
- **洋葱层职责**：**第 5、7 层（决策仲裁 + 审计不可否认）**——privileged-LLM 模式；决策带 provenance 签名。

### 4.3 双入口下的协作流程

**守门模式（PR 触发）**

```
GitHub PR webhook
    → Sentinel（打 UNTRUSTED 标签 + 上下文封装）
    → Analyst（沙箱解析 + 多信号融合 + RiskProfile）
    → Auditor（仲裁：Allow / Block / RequireReview）
    → 若 Block/Review：Remediator（生成建议 PR 或说明性 comment）
    → Auditor（记录审计 + 通知 Sentinel）
    → Sentinel（关闭本轮任务 / 触发人工审批）
```

**响应模式（CVE / 恶意包披露触发）**

```
OSV / GHSA feed
    → Sentinel（识别事件严重度 + 圈定受影响仓库）
    → Analyst（全库扫描 + 影响面评估 + RiskProfile 数组）
    → Auditor（仲裁批量策略 + 分级）
    → Remediator（批量生成 PR + 沙箱验证）
    → Auditor（审计留痕 + 生成合规报告）
    → Sentinel（推送处置报告 + 关闭事件）
```

### 4.4 上下文传递协议（对齐赛题）

赛题要求说明"上下文传递、协同执行与状态追踪"如何映射到 AgentTeams 能力。本方案采用：

- **共享状态**：Session 级共享上下文（当前事件、仓库指纹、依赖图快照），存放在 PolarDB PG / Redis
- **消息报文**：`AnalysisRequest` / `RiskProfile` / `RemediationOrder` / `RemediationResult` / `Verdict`，全部 Schema 化
- **状态机**：任务生命周期 `received → analyzing → arbitrating → remediating → verifying → sealed`
- **可观测轨迹**：每次 Agent 切换记录 span，覆盖 Skill / MCP / LLM 三类调用（对齐 OpenTelemetry GenAI 语义）

### 4.5 Agent Identity 清单速查

| Agent | 职能 | 关键工具 | 边界 | 洋葱层 |
| --- | --- | --- | --- | --- |
| Sentinel | 触发 / 协调 | MCP-Git、MCP-Feed、MQ | 不做安全判断 | L1 |
| Analyst | 分析 / 画像 | 6 类 Skill + 多个 MCP | 只读 | L2、L3 |
| Remediator | 修复 / PR | 5 类 Skill + Git 写 | 不 merge、只沙箱运行 | L6 |
| Auditor | 仲裁 / 审计 | 4 类 Skill + 审批 MCP | 不接触 untrusted 原文 | L5、L7 |

## 5. 待细化清单（下一版补齐）

按重要性排序：

- [ ] **AgentTeams 框架映射**：角色编排、任务拆解、上下文传递、协同执行、状态追踪如何落到 AgentTeams 的具体能力
- [ ] **Skill 清单**：每个 Skill 的名称、用途、输入 / 输出 Schema、调用条件、依赖工具、失败处理、安全边界、复用价值
- [ ] **MCP 工具集**：GitHub / GitLab / npm registry / OSV / GHSA / SBOM 工具的 MCP 接入契约
- [ ] **RAG / 上下文能力**：需在"记忆存储 / 知识库 RAG / 共享状态 / 轨迹可观测"四项中至少选 2 项
- [ ] **可观测方案**：LoongSuite / AgentScope Studio / AgentLoop 三选一，Trace / Log / Metrics 覆盖策略
- [ ] **数据层**：PolarDB PG 用于 SBOM / 审计日志 / 向量记忆，还是先用 SQLite + pgvector 起步
- [ ] **Demo 场景脚本**：至少准备 2 段——slopsquatting 拦截 + 零日事件响应
- [ ] **初赛提交材料**：500 字作品简介 + PPT

## 6. 关键决策与风险

### 6.1 已做的决策

| 决策 | 结论 | 理由 |
| --- | --- | --- |
| 参赛方向 | Infra 赛道 / 供应链安全与合规 | 作者创业刚需，评审记忆点强 |
| 项目结构 | 双入口一引擎（守门 + 响应融合） | 底层能力复用，叙事完整 |
| 差异化 | 卖点重心从"AI 新攻击面"移到"从告警到闭环修复的最后一公里" | 前者是引流梗、后者是护城河；AI 攻击面（含 slopsquatting）保留为叙事切入点 |
| 安全架构 | 洋葱式 Defense in Depth，7 层 | 抵御 prompt injection / 恶意文件解析；是 Agent 化产品相对存量 SCA 的结构性护城河 |
| 商业化路径 | 优先做完整产品，v1 不做独立开源 SDK | 好的产品能被付费才能持续做下去；先建护城河后再考虑工具化 |

### 6.2 待决策

| 决策 | 备选 | 依据 |
| --- | --- | --- |
| v1 生态覆盖 | npm 独占 vs npm+PyPI | 6 天到初赛，只做设计不要求代码；但复赛要能跑，建议 v1 只做 npm |
| 是否用 MCP | 用 vs 提供等价契约 | 官方推荐 MCP，加分项 |
| 数据层 | PolarDB PG vs SQLite | 前者推荐加分、后者启动快 |

### 6.3 风险

- **供应链安全域知识深**：需要快速对齐 xz-utils/event-stream/slopsquatting 等参考事件的技术细节，避免方案空对空
- **Demo 戏剧感**：静态扫描类工具本质"无声"，需要精心设计 Demo 剧本
- **AgentTeams 学习成本未评估**：必选框架，需要尽快跑通 hello-world

## 7. 下一步

1. 跑通 AgentTeams hello-world，评估学习成本，产出框架映射文档
2. 输出 Skill 清单（每个 Skill 的输入 / 输出 Schema、调用条件、失败处理、安全边界）
3. 输出初赛 500 字作品简介 + PPT 大纲（8.16 前）
4. 补 v0.3：Demo 剧本（slopsquatting 拦截 + 零日事件响应）
