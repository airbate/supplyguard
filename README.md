# SupplyGuard（暂名）

> 面向 AI 编程时代的多 Agent 供应链安全防御系统。既在 PR 时刻拦下危险依赖（含 AI 幻觉包），也在零日事件披露时刻自动完成全库影响面评估与缓解修复。

## 参赛背景

- **赛事**：GOAI 2026 Infra 赛道 —— 企业级复杂任务下的多 Agent 基础设施与协同系统
- **官网**：<https://www.goaihz.com/tracks?track=infra>
- **关键时间**：
  - 初赛提交截止：2026-08-16
  - 复赛：2026-08-25 ~ 2026-09-03
  - 决赛：2026-09-22
- **必选技术**：AgentTeams（原 Hiclaw）作为多 Agent 协同框架、Skill 抽象层
- **推荐技术**：阿里云 Skills / Nacos / Higress / PolarDB PG / RocketMQ / LoongSuite / MCP

## 项目定位

供应链攻击是当下企业软件最真实、最贵、也最被忽视的风险源。而 AI 编程工具的普及带来了一类全新的攻击面：**LLM 会"幻觉"出并不存在的包名，攻击者会抢注这些名字**（slopsquatting）。传统 SCA/DevSecOps 工具是围绕人写的代码设计的，在 AI 生成代码的时代节奏跟不上、决策不够智能。

SupplyGuard 试图用多 Agent 系统解决这道题：把守门（proactive）与响应（reactive）两个不同触发时刻合并到一套共享引擎里，让 Agent 承担分析、决策、修复与审计的全闭环。

## 双入口一引擎

| 入口 | 触发时刻 | 目标 |
| --- | --- | --- |
| **守门模式** | PR / 依赖变更 | 拦下危险引入、AI 幻觉包、恶意脚本、license 冲突 |
| **响应模式** | 上游 CVE / 恶意包披露 | 全库扫描、影响面评估、生成缓解 PR、自动降级/替换 |

两条链路共享同一套底层能力：依赖图与 SBOM 建模、包风险评估、修复策略生成、审计与知识沉淀。

## 项目状态

**早期设计阶段（v0.1）**。当前已完成：

- [x] 参赛方向确认（Infra 赛道 / 依赖治理与安全修复 / 供应链安全与合规子场景）
- [x] 解决方案骨架（两入口一引擎）
- [ ] 多 Agent 角色分工（≥3 个 Agent 的职能、边界、协作协议）
- [ ] 核心 Skill 清单（输入/输出/失败处理/复用价值）
- [ ] AgentTeams 框架映射
- [ ] MCP / RAG / 可观测选型
- [ ] 初赛提交材料（500 字作品简介 + 方案 PPT）
- [ ] 复赛可运行 Demo

## 目录结构

```
GoAISpace/
├── README.md                              # 本文件
└── docs/
    └── specs/
        └── 2026-08-10-supplyguard-design.md   # 设计文档 v0.1
```

后续会加入：`agents/`（角色定义）、`skills/`（能力清单）、`src/`（工程实现）、`demo/`（Demo 场景）。

## 快速链接

- 设计文档 v0.1：[docs/specs/2026-08-10-supplyguard-design.md](docs/specs/2026-08-10-supplyguard-design.md)
- AgentTeams 官网：<https://hiclaw.io/>

## License

待定。倾向 Apache-2.0（对齐赛道"开放/开源贡献"评分维度）。
