from __future__ import annotations

from collections import Counter
from pathlib import Path


def write_report(path: Path, screening_rows: list[dict[str, str]], construct_rows: list[dict[str, str]], offline: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    calls = Counter(row.get("priority_call", "") for row in screening_rows)
    passed = [row["gene_symbol"] for row in screening_rows if row.get("priority_call") == "go"]
    conditional = [row["gene_symbol"] for row in screening_rows if row.get("priority_call") == "conditional"]
    failed = [row["gene_symbol"] for row in screening_rows if row.get("priority_call") == "no_go"]
    controls = [row["gene_symbol"] for row in screening_rows if row.get("priority_call") == "control_or_not_applicable"]
    missing = {row["gene_symbol"]: row.get("missing_evidence", "") for row in screening_rows if row.get("missing_evidence")}

    lines = [
        "# 抗原筛选报告",
        "",
        "## 候选输入概况",
        f"- 候选数量：{len(screening_rows)}",
        f"- 本次是否联网：{'否，使用 fixture/local evidence' if offline else '是，包含 live adapter 输出'}",
        "- 判断方式：先 gate，后 tie-break score；score 不覆盖 gate fail。",
        "",
        "## 通过 / 失败 / 不确定靶点",
        f"- Go：{', '.join(passed) if passed else '无'}",
        f"- Conditional：{', '.join(conditional) if conditional else '无'}",
        f"- No-go：{', '.join(failed) if failed else '无'}",
        f"- Control / not applicable：{', '.join(controls) if controls else '无'}",
        "",
        "## Modality-Specific 结论",
        "| Gene | Modality | Modality gate | Fit | Priority |",
        "|---|---|---|---|---|",
    ]
    for row in screening_rows:
        lines.append(
            f"| {row['gene_symbol']} | {row['modality']} | {row['modality_gate']} | {row['modality_fit']} | {row['priority_call']} |"
        )

    lines.extend(["", "## ECD Construct 方案", "| Gene | Recommendation | Stop condition |", "|---|---|---|"])
    for row in construct_rows:
        lines.append(f"| {row['gene_symbol']} | {row['construct_recommendation']} | {row['stop_condition']} |")

    lines.extend(["", "## 风险 Flags"])
    for row in screening_rows:
        lines.append(f"- {row['gene_symbol']}: {row.get('risk_flags') or 'none'}")

    lines.extend(["", "## 缺失证据"])
    if missing:
        for gene, value in missing.items():
            lines.append(f"- {gene}: {value}")
    else:
        lines.append("- 无关键缺失证据。")

    lines.extend(
        [
            "",
            "## 下一步实验建议",
            "1. 对 go/conditional 候选补充 surface protein evidence，如 flow、surface proteomics、IF/IHC 或已知配体/抗体验证。",
            "2. 对构建候选测试表达、还原/非还原胶、SEC 和 binding QC。",
            "3. 对小鼠模型候选补充人鼠 ECD identity 和交叉反应实验；fixture 结果不能替代 live 数据库核验。",
            "",
            "## 计数",
            f"- {dict(calls)}",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
