"""Evaluation report formatting — JSON + markdown table output."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .runner import EvalReport


def to_dict(report: EvalReport) -> dict:
    """Convert report to JSON-serializable dict."""
    data = asdict(report)
    data["generated_at"] = datetime.now(timezone.utc).isoformat()
    return data


def to_markdown(report: EvalReport) -> str:
    """Render a markdown table summary of evaluation results."""
    lines = [
        "# RiskScout Evaluation Report",
        "",
        f"**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Summary",
        "",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Total Documents | {report.total} |",
        f"| Correct Decisions | {report.correct} |",
        f"| Accuracy | {report.accuracy:.1%} |",
        f"| Avg Latency | {report.avg_latency_ms:.0f} ms |",
        f"| Total Input Tokens | {report.total_input_tokens:,} |",
        f"| Total Output Tokens | {report.total_output_tokens:,} |",
        f"| Estimated Cost | ${report.estimated_cost_usd:.4f} |",
        f"| False Positive (Approve→Reject) | {report.false_positive_approve} |",
        f"| False Negative (Reject→Approve) | {report.false_negative_approve} |",
        "",
        "## Per-Document Results",
        "",
        "| Doc ID | Expected | Actual | Score | Correct | Latency (ms) | Error |",
        "|--------|----------|--------|-------|---------|--------------|-------|",
    ]

    for r in sorted(report.results, key=lambda x: x.doc_id):
        correct_str = "YES" if r.correct else "NO"
        score_str = str(r.actual_score) if r.actual_score is not None else "-"
        error_str = r.error[:40] + "..." if r.error and len(r.error) > 40 else (r.error or "")
        lines.append(
            f"| {r.doc_id} | {r.expected_decision} | {r.actual_decision or '-'} "
            f"| {score_str} | {correct_str} | {r.latency_ms:.0f} | {error_str} |"
        )

    lines += [
        "",
        "## Decision Distribution",
        "",
    ]

    decisions = [r.actual_decision for r in report.results if r.actual_decision]
    for label in ["approve", "review", "reject"]:
        count = decisions.count(label)
        pct = count / len(decisions) * 100 if decisions else 0
        lines.append(f"- **{label.title()}**: {count} ({pct:.0f}%)")

    return "\n".join(lines)


def print_report(report: EvalReport) -> None:
    print(to_markdown(report))


def save_report(report: EvalReport, output_dir: str = "eval/results") -> None:
    """Save report as both JSON and Markdown."""
    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    json_path = path / f"report_{ts}.json"
    json_path.write_text(json.dumps(to_dict(report), indent=2))
    print(f"JSON report saved: {json_path}")

    md_path = path / f"report_{ts}.md"
    md_path.write_text(to_markdown(report))
    print(f"Markdown report saved: {md_path}")
