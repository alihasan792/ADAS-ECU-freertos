"""
Standalone HTML Report Generator for ADAS ECU Automated Test Harness.
Generates an interactive, beautiful, zero-external-dependency HTML dashboard.
"""

from pathlib import Path
from typing import Optional
import html
import json

from harness.models import RunSummary, TestStatus


class HTMLReporter:
    """Renders a standalone visual HTML report."""

    @staticmethod
    def generate_report(summary: RunSummary, output_dir: str = "reports") -> str:
        run_dir = Path(output_dir) / "runs" / summary.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        html_path = run_dir / "report.html"

        pass_color = "#10b981"
        fail_color = "#ef4444"
        skip_color = "#f59e0b"
        card_bg = "#ffffff"

        rows_html = []
        for suite_name, suite_res in summary.suites.items():
            for r in suite_res.test_results:
                badge_color = pass_color if r.status == TestStatus.PASSED else (fail_color if r.status == TestStatus.FAILED else skip_color)
                failure_detail = f"<div class='failure-box'>{html.escape(r.failure_reason or '')}</div>" if r.failure_reason else ""
                logs_detail = f"<details><summary>View Logs ({len(r.logs)})</summary><pre>{html.escape(chr(10).join(r.logs))}</pre></details>" if r.logs else ""
                evidence_link = f"<div class='evidence-tag'>Evidence: {html.escape(r.evidence_dir)}</div>" if r.evidence_dir else ""

                row = f"""
                <tr class="test-row {r.status.value.lower()}">
                    <td><span class="test-id">{html.escape(r.test_id)}</span></td>
                    <td><strong>{html.escape(r.name)}</strong></td>
                    <td><span class="badge-suite">{html.escape(r.suite)}</span></td>
                    <td><span class="badge-status" style="background-color: {badge_color};">{r.status.value}</span></td>
                    <td>{r.duration_ms:.1f} ms</td>
                    <td>
                        {failure_detail}
                        {evidence_link}
                        {logs_detail}
                    </td>
                </tr>
                """
                rows_html.append(row)

        content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ADAS ECU Test Report - {summary.run_id}</title>
    <style>
        :root {{
            --primary: #2563eb;
            --bg: #f8fafc;
            --text: #1e293b;
            --border: #e2e8f0;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg);
            color: var(--text);
            margin: 0;
            padding: 24px;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
            color: white;
            padding: 32px;
            border-radius: 12px;
            margin-bottom: 24px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        }}
        .header h1 {{ margin: 0 0 8px 0; font-size: 28px; }}
        .header p {{ margin: 0; opacity: 0.9; }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            border: 1px solid var(--border);
            text-align: center;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .stat-num {{ font-size: 32px; font-weight: bold; margin-bottom: 4px; }}
        .stat-label {{ color: #64748b; font-size: 13px; text-transform: uppercase; font-weight: 600; }}
        .table-card {{
            background: white;
            border-radius: 10px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ background: #f1f5f9; padding: 14px 18px; font-weight: 600; color: #475569; font-size: 13px; }}
        td {{ padding: 14px 18px; border-bottom: 1px solid var(--border); font-size: 14px; vertical-align: top; }}
        tr:hover {{ background-color: #f8fafc; }}
        .test-id {{ font-family: monospace; font-weight: 700; color: #0284c7; }}
        .badge-status {{ color: white; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; display: inline-block; }}
        .badge-suite {{ background: #e0e7ff; color: #3730a3; padding: 3px 8px; border-radius: 6px; font-size: 12px; font-weight: 500; text-transform: uppercase; }}
        .failure-box {{ background: #fef2f2; color: #991b1b; border-left: 3px solid #ef4444; padding: 8px 12px; margin-bottom: 6px; border-radius: 4px; font-size: 12px; }}
        .evidence-tag {{ font-family: monospace; font-size: 11px; color: #6b7280; margin-bottom: 6px; }}
        details {{ margin-top: 6px; font-size: 12px; }}
        pre {{ background: #0f172a; color: #e2e8f0; padding: 12px; border-radius: 6px; overflow-x: auto; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>ADAS ECU Automated Validation Report</h1>
        <p>Run ID: <strong>{summary.run_id}</strong> &nbsp;|&nbsp; Timestamp: {summary.timestamp} &nbsp;|&nbsp; Framework: CLI-First Test Harness v1.0.0</p>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-num" style="color: #2563eb;">{summary.total_tests}</div>
            <div class="stat-label">Total Tests</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: {pass_color};">{summary.passed_tests}</div>
            <div class="stat-label">Passed</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: {fail_color};">{summary.failed_tests}</div>
            <div class="stat-label">Failed</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: {pass_color if summary.pass_rate >= 80 else fail_color};">{summary.pass_rate:.1f}%</div>
            <div class="stat-label">Pass Rate</div>
        </div>
        <div class="stat-card">
            <div class="stat-num" style="color: #64748b;">{summary.duration_ms:.0f} ms</div>
            <div class="stat-label">Duration</div>
        </div>
    </div>

    <div class="table-card">
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Test Case Name</th>
                    <th>Suite</th>
                    <th>Status</th>
                    <th>Duration</th>
                    <th>Details & Evidence</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(content)

        # Also write reports/latest_report.html
        latest_html = Path(output_dir) / "latest_report.html"
        with open(latest_html, "w", encoding="utf-8") as f:
            f.write(content)

        return str(html_path)
