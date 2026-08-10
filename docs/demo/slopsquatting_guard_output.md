# Demo 预期输出：Slopsquatting / 幻觉包拦截

**场景**：一次 PR 中，AI 生成的代码引入了名为 `lodos` 的 npm 包，这是流行包 `lodash` 的 typosquat，也可能是 LLM 幻觉出的不存在的包名。

**运行命令**：

```bash
uv venv
uv pip install -r requirements.txt
uv pip install -e .
python src/supplyguard/demo/slopsquatting_guard.py
```

---

## 预期终端输出

```
============================================================
SupplyGuard Demo: Slopsquatting / Hallucination Detection
============================================================

Workflow result:
{
  "session_id": "demo-slopsquatting-001",
  "source": "github_pr",
  "repo_url": "https://github.com/acme/demo-app",
  "risk_level": "critical",
  "verdict": "block",
  "strategy": "comment-only",
  "remediation": {
    "verdict": "block",
    "strategy": "comment-only",
    "notes": "Verdict: block. Reasons: Hallucinated or typosquatted package detected.",
    "packages": [
      {
        "name": "hallucination-check",
        "evidence": "{'is_hallucination_risk': True, 'reasoning': \"Package 'lodos' was not found in npm registry. It closely resembles popular package(s): lodash. Possible typosquatting or LLM hallucination.\", 'recommended_alternatives': ['lodash']}"
      }
    ],
    "action_taken": "wrote_blocking_comment",
    "comment_body": "> ⚠️ SupplyGuard blocked this dependency change.\n\nVerdict: block. Reasons: Hallucinated or typosquatted package detected.\n\nEvidence:\n- hallucination-check: {'is_hallucination_risk': True, 'reasoning': \"Package 'lodos' was not found in npm registry. It closely resembles popular package(s): lodash. Possible typosquatting or LLM hallucination.\", 'recommended_alternatives': ['lodash']}"
  },
  "audit_seal": {
    "session_id": "demo-slopsquatting-001",
    "status": "sealed",
    "regression_detected": false,
    "logs_hash": "sha256:demo",
    "sealed_at": "2026-08-10T16:30:57.893726+00:00"
  }
}
```

---

## 流程解读

| 步骤 | Agent | 动作 | 关键证据 |
| --- | --- | --- | --- |
| 1 | Sentinel | 接收 PR webhook，给 `context_text` 打 `UNTRUSTED` 标签 | 原始 diff： `"import { cloneDeep } from 'lodos';"` |
| 2 | Analyst | 调用 `hallucination-check` | npm registry 返回 404；相似度匹配发现 `lodash` |
| 3 | Analyst | 调用 `risk-profile` | 融合为 `critical` + `block` |
| 4 | Auditor | 基于结构化证据裁决 | `verdict: block`，触发生成阻止 comment |
| 5 | Remediator | 生成 comment 内容 | comment body 解释证据与建议 |
| 6 | Auditor | 审计密封 | `status: sealed`，记录证据哈希 |

---

## 网络不可用时的降级行为

如果运行环境无法访问 `https://registry.npmjs.org`，`hallucination-check` 会保守地返回高风险，并附原因：

```json
{
  "is_hallucination_risk": true,
  "reasoning": "Registry unreachable; treating as high-risk per fail-safe policy.",
  "recommended_alternatives": [],
  "evidence": {"registry_error": true}
}
```

这对应设计文档中的**失败处理与降级策略**："registry 不可达 → 高风险 + 人工复核"。
