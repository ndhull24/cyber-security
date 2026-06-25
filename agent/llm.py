"""
LLM layer.
Calls the Anthropic API to generate the executive narrative section of the report.
Gracefully degrades to a template-based fallback if the API key is missing.
"""

from __future__ import annotations
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent.scoring import StackAnalysis

SYSTEM_PROMPT = """You are a senior cybersecurity analyst at Shieldient, an AI-first managed security \
services provider (MSSP) headquartered in Dallas, Texas.

Your job is to write a concise executive narrative for a vendor stack rationalization report. \
The audience is a CISO or IT Director — not a technical engineer. \
They care about business risk, regulatory exposure, and dollar impact.

Rules:
- 180–220 words maximum
- Plain prose, no bullet points, no markdown, no headers
- Quantify everything you can (dollars, percentages, risk levels)
- Name specific tools only when it strengthens the point
- Close with a single clear recommendation — either consolidate-first or gap-fill-first
- Final sentence must reference how an MSSP engagement reduces implementation burden
- Never use the word "leverage" or "synergies"
- Tone: direct, analytical, confident — not sales-y"""


def _build_user_prompt(analysis: "StackAnalysis") -> str:
    overlap_summary = ""
    if analysis.overlap_pairs:
        pairs = "; ".join(
            f"{op.tool_a.name} + {op.tool_b.name} (shared: {', '.join(op.shared_domains[:2])})"
            for op in analysis.overlap_pairs
        )
        overlap_summary = f"Overlap pairs detected: {pairs}."
    else:
        overlap_summary = "No functional overlaps detected."

    gap_summary = ""
    if analysis.coverage_gaps:
        top_gaps = ", ".join(
            g.domain.replace("_", " ") for g in analysis.coverage_gaps[:4]
        )
        gap_summary = f"Coverage gaps: {top_gaps}."
    else:
        gap_summary = "No coverage gaps detected."

    return f"""Write an executive narrative for the following stack rationalization analysis.

Company profile:
- Industry: {analysis.industry}
- Size: {analysis.size}
- Compliance framework: {analysis.compliance}
- Annual security budget: ${analysis.budget_k}K
- Tools deployed: {len(analysis.selected_tools)} ({', '.join(t.name for t in analysis.selected_tools)})
- Total estimated spend: ${analysis.total_spend_k}K/yr

Findings:
- Overall stack score: {analysis.overall_score}/100
- Efficiency score: {analysis.efficiency_score}/100
- Coverage score: {analysis.coverage_score}/100
- Compliance alignment: {analysis.compliance_score}/100
- {overlap_summary}
- Estimated redundant spend: ${analysis.wasted_spend_k}K/yr (${analysis.recoverable_spend_k}K conservatively recoverable)
- {gap_summary}
- Budget utilization: {analysis.budget_utilization_pct}%

Write the narrative now. No preamble."""


def generate_narrative(analysis: "StackAnalysis") -> str:
    """
    Generate an executive narrative using the Anthropic API.
    Falls back to a template string if ANTHROPIC_API_KEY is not set.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")

    if not api_key:
        return _template_fallback(analysis)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(analysis)}],
        )
        return message.content[0].text.strip()

    except Exception as exc:
        return f"[LLM narrative unavailable: {exc}]\n\n" + _template_fallback(analysis)


def _template_fallback(analysis: "StackAnalysis") -> str:
    """Rule-based narrative when the API is unavailable."""
    overlap_line = (
        f"The stack carries {len(analysis.overlap_pairs)} functional overlap(s) "
        f"accounting for approximately ${analysis.wasted_spend_k}K in redundant annual spend, "
        f"of which ${analysis.recoverable_spend_k}K is conservatively recoverable through consolidation."
        if analysis.overlap_pairs
        else "No functional overlaps were detected; current tool selection is non-redundant."
    )

    gap_line = (
        f"{len(analysis.coverage_gaps)} control domain(s) remain uncovered, "
        f"including {', '.join(g.domain.replace('_', ' ') for g in analysis.coverage_gaps[:2])}, "
        f"which represent direct exposure under {analysis.compliance} requirements."
        if analysis.coverage_gaps
        else "Coverage across all assessed domains is complete."
    )

    recommendation = (
        "Priority action is overlap consolidation to recover budget before addressing gaps."
        if analysis.overlap_pairs
        else "Priority action is filling coverage gaps — spend efficiency is not the constraint."
    )

    return (
        f"This {analysis.industry} organization is running {len(analysis.selected_tools)} security tools "
        f"at an estimated ${analysis.total_spend_k}K annually against a ${analysis.budget_k}K budget "
        f"({analysis.budget_utilization_pct}% utilization). "
        f"The overall stack score of {analysis.overall_score}/100 reflects the findings below. "
        f"{overlap_line} "
        f"{gap_line} "
        f"{recommendation} "
        f"An MSSP engagement can absorb residual coverage gaps without additional tool licenses, "
        f"converting capital expenditure into a predictable managed service retainer."
    )
