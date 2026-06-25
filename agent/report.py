"""
PDF report generator.
Produces a professional rationalization report using fpdf2.
"""

from __future__ import annotations
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.scoring import StackAnalysis, RoadmapStep

try:
    from fpdf import FPDF, XPos, YPos
    FPDF_AVAILABLE = True
except ImportError:
    FPDF_AVAILABLE = False


# ── Colour palette (matches Shieldient dark/professional aesthetic) ────────────
C_DARK   = (15,  23,  42)    # near-black headings
C_ACCENT = (29, 158, 117)    # teal — Shieldient / Securonix green
C_WARN   = (186, 117,  23)   # amber
C_DANGER = (163,  45,  45)   # red
C_MUTED  = (100, 110, 120)   # grey body text
C_LINE   = (220, 225, 230)   # border/divider


class ReportPDF(FPDF):
    def __init__(self, company_name: str = "Client Organization"):
        super().__init__()
        self.company_name = company_name
        self.set_margins(18, 18, 18)
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_fill_color(*C_DARK)
        self.rect(0, 0, 210, 14, "F")
        self.set_xy(18, 3)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 8, "SHIELDIENT  |  Vendor Stack Rationalization Report", align="L")
        self.set_text_color(*C_DARK)
        self.ln(10)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*C_MUTED)
        self.cell(0, 6, f"Confidential  ·  Generated {datetime.now().strftime('%B %d, %Y')}  ·  Page {self.page_no()}", align="C")

    def section_title(self, text: str):
        self.ln(4)
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*C_DARK)
        self.cell(0, 8, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*C_ACCENT)
        self.set_line_width(0.5)
        self.line(self.get_x(), self.get_y(), self.get_x() + 174, self.get_y())
        self.ln(3)

    def metric_box(self, label: str, value: str, color: tuple):
        x, y = self.get_x(), self.get_y()
        self.set_fill_color(245, 248, 252)
        self.rect(x, y, 40, 18, "F")
        self.set_xy(x + 2, y + 2)
        self.set_font("Helvetica", "", 7)
        self.set_text_color(*C_MUTED)
        self.cell(36, 4, label.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_xy(x + 2, y + 7)
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(*color)
        self.cell(36, 8, value)
        self.set_xy(x + 42, y)

    def score_bar(self, label: str, score: int, color: tuple):
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*C_DARK)
        self.cell(70, 6, label)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*color)
        self.cell(20, 6, f"{score}/100")
        # bar background
        bx = self.get_x() + 4
        by = self.get_y() + 1
        self.set_fill_color(220, 225, 230)
        self.rect(bx, by, 60, 4, "F")
        self.set_fill_color(*color)
        self.rect(bx, by, max(1, score * 0.6), 4, "F")
        self.ln(8)
        self.set_text_color(*C_DARK)

    def finding_block(self, badge: str, badge_color: tuple, title: str, body: str):
        self.set_fill_color(*badge_color)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 7)
        self.cell(18, 5, f" {badge} ", fill=True)
        self.set_text_color(*C_DARK)
        self.set_font("Helvetica", "B", 9)
        self.cell(0, 5, f"  {title}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*C_MUTED)
        self.set_x(self.l_margin + 4)
        self.multi_cell(166, 5, body)
        self.ln(2)
        self.set_text_color(*C_DARK)


def score_color(score: int) -> tuple:
    if score >= 75:
        return C_ACCENT
    elif score >= 50:
        return C_WARN
    else:
        return C_DANGER


def generate_pdf(
    analysis: "StackAnalysis",
    roadmap: "list[RoadmapStep]",
    output_path: str = "reports/stack_report.pdf",
) -> str:
    """Generate and save the PDF report. Returns the output path."""
    if not FPDF_AVAILABLE:
        raise ImportError("fpdf2 is required for PDF generation. Run: pip install fpdf2")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    pdf = ReportPDF()
    pdf.add_page()

    # ── Cover block ───────────────────────────────────────────────────────
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*C_DARK)
    pdf.ln(2)
    pdf.cell(0, 10, "Cybersecurity Stack", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.cell(0, 10, "Rationalization Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_MUTED)
    pdf.cell(0, 6, f"{analysis.industry}  ·  {analysis.size}  ·  {analysis.compliance}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.ln(6)

    # ── Metric row ────────────────────────────────────────────────────────
    pdf.metric_box("Overall Score",   f"{analysis.overall_score}/100",    score_color(analysis.overall_score))
    pdf.metric_box("Tools Deployed",  str(len(analysis.selected_tools)),  C_DARK)
    pdf.metric_box("Annual Spend",    f"${analysis.total_spend_k}K",      C_DARK)
    pdf.metric_box("Wasted Spend",    f"${analysis.wasted_spend_k}K",     C_DANGER if analysis.wasted_spend_k else C_ACCENT)
    pdf.ln(22)

    # ── Score bars ────────────────────────────────────────────────────────
    pdf.section_title("Score Breakdown")
    pdf.score_bar("Stack Efficiency",       analysis.efficiency_score,  score_color(analysis.efficiency_score))
    pdf.score_bar("Coverage Completeness",  analysis.coverage_score,    score_color(analysis.coverage_score))
    pdf.score_bar("Compliance Alignment",   analysis.compliance_score,  score_color(analysis.compliance_score))

    # ── Narrative ─────────────────────────────────────────────────────────
    if analysis.narrative:
        pdf.section_title("Executive Summary")
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(*C_DARK)
        pdf.multi_cell(0, 6, analysis.narrative)

    # ── Findings ─────────────────────────────────────────────────────────
    pdf.section_title("Key Findings")

    for pair in analysis.overlap_pairs:
        shared = ", ".join(pair.shared_domains[:2])
        pdf.finding_block(
            "OVERLAP", C_WARN,
            f"{pair.tool_a.name}  ×  {pair.tool_b.name}",
            f"Shared coverage: {shared}. Estimated redundant spend: ~${pair.estimated_wasted_cost_k}K/yr.",
        )

    for gap in analysis.coverage_gaps[:6]:
        from data.tool_catalog import DOMAIN_DISPLAY
        risk = "HIGH" if gap.compliance_weight >= 2 else ("MEDIUM" if gap.compliance_weight == 1 else "LOW")
        recs = ", ".join(gap.recommended_tools[:2]) if gap.recommended_tools else "Evaluate vendors"
        pdf.finding_block(
            f"GAP · {risk}", C_DANGER,
            DOMAIN_DISPLAY[gap.domain],
            f"Not covered by current stack. Recommended: {recs}.",
        )

    if not analysis.overlap_pairs and not analysis.coverage_gaps:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*C_ACCENT)
        pdf.cell(0, 6, "No overlaps or gaps detected. Stack is well-optimised.", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_text_color(*C_DARK)

    # ── Tool inventory ────────────────────────────────────────────────────
    pdf.section_title("Tool Inventory")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_fill_color(230, 235, 240)
    pdf.set_text_color(*C_DARK)
    col_w = [60, 35, 25, 54]
    headers = ["Tool", "Category", "Cost/yr", "Coverage Domains"]
    for h, w in zip(headers, col_w):
        pdf.cell(w, 6, h, border="B", fill=True)
    pdf.ln()

    pdf.set_font("Helvetica", "", 8)
    for tool in analysis.selected_tools:
        domains_short = ", ".join(d.replace("_", " ") for d in tool.coverage[:2])
        if len(tool.coverage) > 2:
            domains_short += f" +{len(tool.coverage)-2}"
        pdf.cell(col_w[0], 5, tool.name[:34])
        pdf.cell(col_w[1], 5, tool.category)
        pdf.cell(col_w[2], 5, f"${tool.annual_cost_k}K")
        pdf.cell(col_w[3], 5, domains_short, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ── Roadmap ───────────────────────────────────────────────────────────
    if roadmap:
        pdf.add_page()
        pdf.section_title("Consolidation Roadmap")
        for step in roadmap:
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(*C_DARK)
            effort_color = {"Low": C_ACCENT, "Medium": C_WARN, "High": C_DANGER}.get(step.effort, C_MUTED)
            pdf.cell(10, 6, f"{step.priority}.")
            pdf.cell(0, 6, step.action, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.set_font("Helvetica", "", 8.5)
            pdf.set_text_color(*C_MUTED)
            pdf.set_x(pdf.l_margin + 10)
            pdf.multi_cell(0, 5, step.rationale)
            pdf.set_x(pdf.l_margin + 10)
            pdf.set_font("Helvetica", "B", 8)
            pdf.set_text_color(*effort_color)
            savings = f"  ·  Saves ${step.estimated_savings_k}K/yr" if step.estimated_savings_k else ""
            pdf.cell(0, 5, f"Effort: {step.effort}{savings}", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            pdf.ln(3)

    pdf.output(output_path)
    return output_path
