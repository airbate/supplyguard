# SupplyGuard 初赛 PPT 大纲

## 建议总页数：12 页

---

## 第 1 页：封面

- **标题**：SupplyGuard：AI 编程时代的多 Agent 供应链安全守门员
- **副标题**：从 PR 拦截到零日响应，让依赖安全从"告警"走向"闭环"
- **参赛赛道**：GOAI 2026 Infra 赛道
- **团队 / 作者**：kona

---

## 第 2 页：一句话定位

- AI 写代码引入了不存在的包（slopsquatting），传统 SCA 工具拦不住
- SupplyGuard 是多 Agent 系统，在 PR 时刻拦截、在 CVE 爆发后自动修复
- 卖点：不是又一个扫描器，而是会分析、会决策、会修复、会审计的"供应链安全 Agent 团队"

---

## 第 3 页：痛点（Why Now）

- AI 编程工具普及 → LLM 幻觉包名 → 攻击者抢注
- 传统 SCA 终点是"告警"，修复靠人肉
- 零日事件（xz-utils、event-stream）响应慢、成本高
- 中小团队缺一套轻量、自托管、可闭环的方案

---

## 第 4 页：解决方案总览（双入口一引擎）

- 图：守门模式 + 响应模式 + 共享引擎
- 守门模式触发：PR / 依赖变更
- 响应模式触发：CVE / 恶意包披露
- 共享引擎：依赖图 / SBOM、包风险画像、修复策略、审计沉淀

---

## 第 5 页：多 Agent 架构

- 4 个 Agent：Sentinel（协调）、Analyst（分析）、Remediator（修复）、Auditor（审计）
- 职责边界、能力最小化、决策与执行分离
- 上下文传递协议：AnalysisRequest → RiskProfile → RemediationOrder → Verdict
- 状态机：received → analyzing → arbitrating → remediating → verifying → sealed

---

## 第 6 页：洋葱式安全架构（核心差异化）

- 元级风险：恶意包内容里可能嵌入 prompt injection，操纵 Agent 帮它过关
- 7 层防御：感知 → 净化 → 上下文隔离 → 能力最小化 → 决策仲裁 → 执行沙箱 → 审计不可否认
- 这是 Agent 化供应链安全产品相对 Snyk/Dependabot 的结构性差异

---

## 第 7 页：Skill 工程体系

- 13 个 Skill 分层：数据层、信号层、融合层、修复层、验证层、治理层
- 每个 Skill：输入输出 Schema、调用条件、失败处理、安全边界、复用价值
- 重点展示：hallucination-check、risk-profile、reachability-scan、sandbox-test-run
- Skill 与 Agent 关系矩阵

---

## 第 8 页：AgentTeams / HiClaw 框架映射

- Sentinel = Manager Agent；Analyst / Remediator / Auditor = Worker Agents
- Matrix room 作为编排与审计舞台
- Agent Identity：system prompt + MCP binding + RBAC + pod template
- Human-in-the-loop：高风险动作人工审批

---

## 第 9 页：技术栈

- 必选：AgentTeams（HiClaw）
- 推荐：阿里云 Skills、Nacos、Higress、PolarDB PG、RocketMQ、LoongSuite/AgentLoop
- MCP 工具：GitHub、npm registry、OSV、CI、Approval Gateway
- v1：SQLite + pgvector；复赛：PolarDB PG
- 可观测：OpenTelemetry GenAI Trace + Log

---

## 第 10 页：Demo 展示

- 场景：AI 生成代码 `import { cloneDeep } from 'lodos'`
- 流程图：Sentinel → Analyst → Auditor → Remediator → Auditor
- 结果：RiskLevel = critical，Verdict = block，自动生成阻止 comment
- 放实际终端输出截图或录屏二维码

---

## 第 11 页：开放价值与商业化

- Skill 层可复用、可开源
- v1 优先做完整产品，验证付费后再考虑独立 SDK
- 目标客户：中小团队、AI 原生创业公司、对供应链安全有强需求的企业
- 未来：Rust 重写核心安全组件（沙箱、SBOM、injection detector）

---

## 第 12 页： roadmap 与当前进展

- 初赛（8.16）：方案设计 + 可运行 Demo
- 复赛（9.3）：AgentTeams 真实接入 + PolarDB + 可观测 + CVE 响应 Demo
- 决赛（9.22）：现场路演 + 完整端到端演示
- 当前：Demo 已跑通，AgentTeams hello-world 验证中

---

## 附录页（可选）：评审维度对齐

- 场景价值 25%：真实痛点、AI 新攻击面、创业刚需
- 多 Agent 协同 25%：4 Agent 闭环、上下文传递、状态追踪
- Skill 体系 25%：13 Skill、可复用、失败降级
- 工程落地 20%：Demo 可运行、洋葱安全、审计留痕
- 开源贡献 5%：Skill 设计、Agent Identity、开源计划
