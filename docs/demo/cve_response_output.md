# Demo 预期输出：零日 CVE 响应

**场景**：OSV feed 披露 `lodash@4.17.4` 存在严重漏洞（`CVE-2019-10744`、`CVE-2020-8203`）。SupplyGuard 自动扫描仓库影响面，生成升级 PR，并进入人工审批流程。

**运行命令**：

```bash
uv run python src/supplyguard/demo/cve_response.py
```

---

## 预期终端输出

```
============================================================
SupplyGuard Demo: Zero-day CVE Response
============================================================

Workflow result:
{
  "session_id": "demo-cve-response-001",
  "source": "osv_feed",
  "repo_url": "https://github.com/acme/demo-app",
  "risk_level": "critical",
  "verdict": "require_human_review",
  "strategy": "bump-version",
  "remediation": {
    "verdict": "require_human_review",
    "strategy": "bump-version",
    "notes": "Verdict: require_human_review. Reasons: Critical CVE detected.",
    "packages": [
      {
        "name": "hallucination-check",
        "evidence": "{'is_hallucination_risk': False, 'reasoning': \"Package 'lodash' exists in npm registry.\", 'recommended_alternatives': [], 'evidence': {'registry_exists': True, ...}"
      },
      {
        "name": "cve-match",
        "evidence": "{'vulnerable': True, 'max_severity': 'critical', 'cves': ['CVE-2019-10744', 'CVE-2020-8203'], 'fixed_versions': ['4.17.21'], 'reasoning': 'lodash@4.17.4 matches CVE-2019-10744, CVE-2020-8203. Fixed in 4.17.21.'}"
      }
    ],
    "action_taken": "created_upgrade_pr",
    "pr_branch": "supplyguard/remediate-demo-cve"
  },
  "audit_seal": {
    "session_id": "demo-cve-response-001",
    "status": "sealed",
    "regression_detected": false,
    "logs_hash": "sha256:demo",
    "sealed_at": "2026-08-10T16:51:48.091598+00:00"
  }
}
```

---

## 流程解读

| 步骤 | Agent | 动作 | 关键证据 |
| --- | --- | --- | --- |
| 1 | Sentinel | 接收 OSV feed，识别为响应模式 | `source: osv_feed` |
| 2 | Analyst | 调用 `hallucination-check` | `lodash` 真实存在，非幻觉 |
| 3 | Analyst | 调用 `cve-match`（v1 stub） | `CVE-2019-10744`、`CVE-2020-8203`，fixed in `4.17.21` |
| 4 | Analyst | 调用 `risk-profile` | 融合为 `critical` + `remediate` |
| 5 | Auditor | 基于策略裁决 | `require_human_review`（自动 PR 属高风险动作） |
| 6 | Remediator | 生成升级 PR | branch: `supplyguard/remediate-demo-cve` |
| 7 | Auditor | 审计密封 | `status: sealed`，记录证据哈希 |

---

## 设计说明

- **为什么不是直接 merge？** 高风险修复动作必须人工审批，符合赛道"审批 / 回滚 / 审计机制"要求。
- **为什么同时调用 hallucination-check？** 在真实世界中，CVE 描述文本本身也可能包含 prompt injection；多信号交叉验证是洋葱架构的一部分。
- **v1 stub 与生产区别**：当前 `cve-match` 使用本地硬编码漏洞数据库；生产会通过 MCP 调用 OSV / GHSA / NVD 实时数据。
