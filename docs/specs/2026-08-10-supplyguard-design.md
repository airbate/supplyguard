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

## 4. 待细化清单（下一版补齐）

按重要性排序：

- [ ] **Agent 角色分工**：初拟 4 个 Agent —— Sentinel（触发/协调）、Analyst（分析）、Remediator（修复）、Auditor（审计）。需验证是否与赛题"≥3 个不同职能 Agent"的定义对齐，是否需要合并或拆分
- [ ] **AgentTeams 框架映射**：角色编排、任务拆解、上下文传递、协同执行、状态追踪如何落到 AgentTeams 的具体能力
- [ ] **Skill 清单**：每个 Skill 的名称、用途、输入/输出 Schema、调用条件、依赖工具、失败处理、安全边界、复用价值
- [ ] **MCP 工具集**：GitHub / GitLab / npm registry / OSV / GHSA / SBOM 工具的 MCP 接入契约
- [ ] **RAG / 上下文能力**：需在"记忆存储 / 知识库 RAG / 共享状态 / 轨迹可观测"四项中至少选 2 项
- [ ] **可观测方案**：LoongSuite / AgentScope Studio / AgentLoop 三选一，Trace / Log / Metrics 覆盖策略
- [ ] **数据层**：PolarDB PG 用于 SBOM / 审计日志 / 向量记忆，还是先用 SQLite + pgvector 起步
- [ ] **Demo 场景脚本**：至少准备 2 段——slopsquatting 拦截 + 零日事件响应
- [ ] **初赛提交材料**：500 字作品简介 + PPT

## 5. 关键决策与风险

### 5.1 已做的决策

| 决策 | 结论 | 理由 |
| --- | --- | --- |
| 参赛方向 | Infra 赛道 / 供应链安全与合规 | 作者创业刚需，评审记忆点强 |
| 项目结构 | 双入口一引擎（守门 + 响应融合） | 底层能力复用，叙事完整 |
| 差异化 | 卖点重心从"AI 新攻击面"移到"从告警到闭环修复的最后一公里" | 前者是引流梗、后者是护城河；AI 攻击面（含 slopsquatting）保留为叙事切入点 |
| 安全架构 | 洋葱式 Defense in Depth，7 层 | 抵御 prompt injection / 恶意文件解析；是 Agent 化产品相对存量 SCA 的结构性护城河 |
| 商业化路径 | 优先做完整产品，v1 不做独立开源 SDK | 好的产品能被付费才能持续做下去；先建护城河后再考虑工具化 |

### 5.2 待决策

| 决策 | 备选 | 依据 |
| --- | --- | --- |
| Agent 数量 | 3 vs 4 | 看"职能清晰度"与"协同复杂度"权衡 |
| v1 生态覆盖 | npm 独占 vs npm+PyPI | 6 天到初赛，只做设计不要求代码；但复赛要能跑，建议 v1 只做 npm |
| 是否用 MCP | 用 vs 提供等价契约 | 官方推荐 MCP，加分项 |
| 数据层 | PolarDB PG vs SQLite | 前者推荐加分、后者启动快 |

### 5.3 风险

- **供应链安全域知识深**：需要快速对齐 xz-utils/event-stream/slopsquatting 等参考事件的技术细节，避免方案空对空
- **Demo 戏剧感**：静态扫描类工具本质"无声"，需要精心设计 Demo 剧本
- **AgentTeams 学习成本未评估**：必选框架，需要尽快跑通 hello-world

## 6. 下一步

1. 用户 review 本 v0.1 文档
2. 补齐 v0.2：Agent 分工 + Skill 清单
3. 完成 AgentTeams 框架映射（hello-world 跑通后）
4. 输出初赛 500 字作品简介 + PPT 大纲（8.16 前）
