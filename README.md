# SupplyGuard

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

**v0.3：能力补齐阶段**（在 v0.2 骨架基础上落地）。

- [x] 参赛方向与场景确认
- [x] 解决方案架构（双入口一引擎 + 洋葱式安全防御）
- [x] 多 Agent 角色分工（Sentinel / Analyst / Remediator / Auditor）
- [x] 核心 Skill 清单（13 个 Skill，含输入输出与失败降级）
- [x] 可运行骨架代码（Python 3.10+）
- [x] 已实现 Skill：`hallucination-check`、`cve-match`（OSV 实时 + 离线降级）、`risk-profile`、`sbom-build`、`license-check`
- [x] 审计日志 append-only + HMAC 签名哈希链（替换占位 `sha256:demo`）
- [x] 可观测：结构化 JSON 日志 + span trace（标准库，无重依赖）
- [x] 洋葱 L2/L3：prompt-injection 检测 + 零宽字符剥离
- [x] HiClaw adapter 骨架（Manager=Sentinel，Workers=Analyst/Remediator/Auditor）
- [ ] AgentTeams/HiClaw 真实框架接入（待 hello-world 验证）
- [ ] 初赛提交材料（500 字作品简介 + 方案 PPT）
- [ ] 复赛完整 Demo（第二段：零日 CVE 响应）

> 依赖已收敛：移除未使用的 `sqlalchemy` / `pgvector`（v1 用内存审计日志 + 结构化日志；RAG / 共享状态为复赛 TODO）。

## 目录结构

```
GoAISpace/
├── README.md                              # 本文件
├── pyproject.toml                         # Python 项目配置
├── requirements.txt                       # 依赖
├── docs/
│   └── specs/
│       └── 2026-08-10-supplyguard-design.md   # 设计文档 v0.2
├── agents/                                # Agent Identity 与 K8s pod 模板
│   ├── sentinel/
│   ├── analyst/
│   ├── remediator/
│   └── auditor/
├── src/supplyguard/                       # 核心实现
│   ├── agents/                            # 4 个 Agent
│   ├── skills/                            # Skill 实现
│   ├── mcp/                               # MCP 等效工具层 + 工具契约
│   ├── models/                            # 消息与状态 Schema
│   ├── runtime/                           # 本地编排器 + HiClaw adapter 骨架
│   ├── audit/                             # append-only 签名审计日志
│   ├── security/                          # 洋葱 L2/L3（injection detector）
│   ├── observability.py                   # 结构化日志 + span trace
│   └── demo/                              # Demo 场景
└── tests/                                 # 单元测试（43 例）
```

## 本地运行

### 环境要求

- Python 3.10+
- （可选）npm registry 网络访问；Demo 在离线时会回退到本地相似度匹配

### 安装

```bash
uv venv
uv pip install -r requirements.txt
uv pip install -e .
```

### 运行 Demo：Slopsquatting / 幻觉包拦截

```bash
python src/supplyguard/demo/slopsquatting_guard.py
```

或直接使用 uv run：

```bash
uv run python src/supplyguard/demo/slopsquatting_guard.py
```

该 Demo 模拟一次 PR 事件：AI 生成的代码引入了名为 `lodos` 的包（`lodash` 的 typosquat / 幻觉）。
SupplyGuard 会按以下链路执行：

1. **Sentinel** 接收 PR 事件，给外部内容打 `UNTRUSTED` 标签
2. **Analyst** 调用 `hallucination-check` Skill 查询 npm registry 并做相似度匹配
3. **Analyst** 调用 `risk-profile` Skill 融合信号
4. **Auditor** 根据 RiskProfile 裁决 `block`
5. **Remediator** 生成阻止性 comment
6. **Auditor** 写入审计摘要

预期输出见 [docs/demo/slopsquatting_guard_output.md](docs/demo/slopsquatting_guard_output.md)。

### 运行测试

```bash
uv run pytest tests/
```

## 架构要点

### 洋葱式安全架构

SupplyGuard 的工作对象本身可能是恶意的。Agent 读取包 README、CVE 描述、commit message 来做决策，恶意包可以嵌入 prompt injection 操纵 Agent。我们设计 7 层防御：

1. 感知层：统一标记 UNTRUSTED
2. 净化层：沙箱解析 + 注入检测
3. 上下文隔离层：`\<untrusted_source\>` 边界
4. 能力最小化：每个 Agent 只有最小工具集
5. 决策仲裁：Auditor 只看结构化证据
6. 执行沙箱：`--ignore-scripts`、临时容器
7. 审计不可否认：append-only log + 签名

这是 Agent 化供应链安全产品相对传统 SCA 工具的结构性差异。

### 与 AgentTeams / HiClaw 的关系

- 业务层（Agent 逻辑、Skill、MCP 适配）与编排层解耦
- 当前使用 `LocalOrchestrator` 在进程内模拟多 Agent 编排
- 验证 HiClaw hello-world 后，通过 adapter 替换为真实 AgentTeams runtime
- Agent Identity 文件已按 HiClaw 的 `identity.yaml + pod-template.yaml` 形式准备

## 快速链接

- 设计文档：[docs/specs/2026-08-10-supplyguard-design.md](docs/specs/2026-08-10-supplyguard-design.md)
- Demo 预期输出：[docs/demo/slopsquatting_guard_output.md](docs/demo/slopsquatting_guard_output.md)
- AgentTeams 官网：<https://hiclaw.io/>

## License

待定。倾向 Apache-2.0（对齐赛道"开放/开源贡献"评分维度）。
