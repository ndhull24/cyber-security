"""
Scoring engine.
Pure functions — no I/O, no external calls.
Takes a list of selected tool IDs + company context, returns a StackAnalysis dataclass.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Set, Tuple, Dict

from data.tool_catalog import (
    TOOL_MAP,
    COVERAGE_DOMAINS,
    DOMAIN_DISPLAY,
    COMPLIANCE_DOMAIN_WEIGHTS,
    Tool,
)


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class OverlapPair:
    tool_a: Tool
    tool_b: Tool
    shared_domains: List[str]
    estimated_wasted_cost_k: int

    def display(self) -> str:
        domains = ", ".join(DOMAIN_DISPLAY[d] for d in self.shared_domains)
        return (
            f"{self.tool_a.name}  ×  {self.tool_b.name}\n"
            f"  Shared coverage : {domains}\n"
            f"  Redundant spend : ~${self.estimated_wasted_cost_k}K/yr "
            f"(retire the cheaper tool to recover this)"
        )


@dataclass
class CoverageGap:
    domain: str
    compliance_weight: int      # 0 if not in the selected framework
    recommended_tools: List[str]

    def display(self) -> str:
        risk = "HIGH" if self.compliance_weight >= 2 else ("MEDIUM" if self.compliance_weight == 1 else "LOW")
        recs = ", ".join(self.recommended_tools[:3]) if self.recommended_tools else "No catalog match"
        return (
            f"{DOMAIN_DISPLAY[self.domain]}  [{risk} RISK]\n"
            f"  Suggested tools : {recs}"
        )


@dataclass
class StackAnalysis:
    # Inputs (echoed back for reporting)
    industry: str
    size: str
    compliance: str
    budget_k: int
    selected_tools: List[Tool]

    # Computed
    total_spend_k: int
    overlap_pairs: List[OverlapPair]
    coverage_gaps: List[CoverageGap]
    covered_domains: Set[str]

    # Scores (0–100)
    efficiency_score: int
    coverage_score: int
    compliance_score: int
    overall_score: int

    # Financial
    wasted_spend_k: int
    recoverable_spend_k: int
    budget_utilization_pct: int

    # Narrative placeholder (filled by LLM layer)
    narrative: str = ""


# ── Domain → recommended tools index ─────────────────────────────────────────

def _build_domain_tool_index() -> Dict[str, List[str]]:
    index: Dict[str, List[str]] = {d: [] for d in COVERAGE_DOMAINS}
    for tool in TOOL_MAP.values():
        for domain in tool.coverage:
            if domain in index:
                index[domain].append(tool.name)
    return index


_DOMAIN_TOOL_INDEX = _build_domain_tool_index()


# ── Core analysis function ────────────────────────────────────────────────────

def analyze_stack(
    selected_ids: List[str],
    industry: str,
    size: str,
    compliance: str,
    budget_k: int,
) -> StackAnalysis:
    """
    Run the full rationalization analysis.
    Returns a StackAnalysis with all scores and findings populated.
    """
    selected_tools = [TOOL_MAP[tid] for tid in selected_ids if tid in TOOL_MAP]

    # ── Spend ─────────────────────────────────────────────────────────────
    total_spend_k = sum(t.annual_cost_k for t in selected_tools)
    budget_utilization_pct = round((total_spend_k / budget_k) * 100) if budget_k else 0

    # ── Overlap detection ─────────────────────────────────────────────────
    selected_set: Set[str] = set(selected_ids)
    seen_pairs: Set[Tuple[str, str]] = set()
    overlap_pairs: List[OverlapPair] = []

    for tool in selected_tools:
        for oid in tool.overlaps_with:
            if oid not in selected_set:
                continue
            pair_key = tuple(sorted([tool.id, oid]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            other = TOOL_MAP[oid]
            shared = [d for d in tool.coverage if d in other.coverage]
            if not shared:
                continue

            wasted = min(tool.annual_cost_k, other.annual_cost_k)
            overlap_pairs.append(OverlapPair(
                tool_a=tool,
                tool_b=other,
                shared_domains=shared,
                estimated_wasted_cost_k=wasted,
            ))

    wasted_spend_k = sum(op.estimated_wasted_cost_k for op in overlap_pairs)
    # Conservative: assume 60% of wasted spend is genuinely recoverable
    recoverable_spend_k = round(wasted_spend_k * 0.6)

    # ── Coverage analysis ─────────────────────────────────────────────────
    covered_domains: Set[str] = set()
    for tool in selected_tools:
        covered_domains.update(tool.coverage)

    weights = COMPLIANCE_DOMAIN_WEIGHTS.get(compliance, {})
    coverage_gaps: List[CoverageGap] = []
    for domain in COVERAGE_DOMAINS:
        if domain not in covered_domains:
            coverage_gaps.append(CoverageGap(
                domain=domain,
                compliance_weight=weights.get(domain, 0),
                recommended_tools=_DOMAIN_TOOL_INDEX.get(domain, []),
            ))

    # Sort gaps: compliance-weighted first
    coverage_gaps.sort(key=lambda g: g.compliance_weight, reverse=True)

    # ── Scores ────────────────────────────────────────────────────────────
    coverage_score = round((len(covered_domains) / len(COVERAGE_DOMAINS)) * 100)

    max_compliance_score = sum(weights.values()) or 1
    achieved_compliance = sum(
        w for domain, w in weights.items() if domain in covered_domains
    )
    compliance_score = round((achieved_compliance / max_compliance_score) * 100)

    # Overlap penalty: each pair costs 8 points
    overlap_penalty = min(40, len(overlap_pairs) * 8)
    efficiency_score = max(10, coverage_score - overlap_penalty)

    # Weighted overall
    overall_score = round(
        efficiency_score * 0.40
        + coverage_score  * 0.35
        + compliance_score * 0.25
    )

    return StackAnalysis(
        industry=industry,
        size=size,
        compliance=compliance,
        budget_k=budget_k,
        selected_tools=selected_tools,
        total_spend_k=total_spend_k,
        overlap_pairs=overlap_pairs,
        coverage_gaps=coverage_gaps,
        covered_domains=covered_domains,
        efficiency_score=efficiency_score,
        coverage_score=coverage_score,
        compliance_score=compliance_score,
        overall_score=overall_score,
        wasted_spend_k=wasted_spend_k,
        recoverable_spend_k=recoverable_spend_k,
        budget_utilization_pct=budget_utilization_pct,
    )


# ── Consolidation roadmap ─────────────────────────────────────────────────────

@dataclass
class RoadmapStep:
    priority: int
    action: str
    rationale: str
    estimated_savings_k: int
    effort: str   # "Low" / "Medium" / "High"


def generate_roadmap(analysis: StackAnalysis) -> List[RoadmapStep]:
    """
    Produce a prioritized consolidation roadmap from a StackAnalysis.
    Deterministic — no LLM call needed.
    """
    steps: List[RoadmapStep] = []
    priority = 1

    # 1. Kill overlapping tools (highest ROI, quickest win)
    for pair in analysis.overlap_pairs:
        retire = pair.tool_b if pair.tool_b.annual_cost_k <= pair.tool_a.annual_cost_k else pair.tool_a
        keep   = pair.tool_a if retire is pair.tool_b else pair.tool_b
        steps.append(RoadmapStep(
            priority=priority,
            action=f"Retire {retire.name} — keep {keep.name}",
            rationale=(
                f"Both cover {', '.join(pair.shared_domains[:2])}. "
                f"{keep.name} provides a superset of capabilities."
            ),
            estimated_savings_k=retire.annual_cost_k,
            effort="Low",
        ))
        priority += 1

    # 2. Fill high-compliance-weight gaps
    high_gaps = [g for g in analysis.coverage_gaps if g.compliance_weight >= 2]
    for gap in high_gaps:
        rec = gap.recommended_tools[0] if gap.recommended_tools else "Evaluate vendors"
        steps.append(RoadmapStep(
            priority=priority,
            action=f"Add coverage for {gap.domain.replace('_', ' ').title()}",
            rationale=(
                f"Required for {analysis.compliance} compliance (weight {gap.compliance_weight}). "
                f"Recommended: {rec}."
            ),
            estimated_savings_k=0,
            effort="Medium",
        ))
        priority += 1

    # 3. Consider MSSP for remaining gaps
    low_gaps = [g for g in analysis.coverage_gaps if g.compliance_weight < 2]
    if low_gaps:
        gap_names = ", ".join(g.domain.replace("_", " ") for g in low_gaps[:3])
        steps.append(RoadmapStep(
            priority=priority,
            action="Engage Shieldient MDR/Advisory for residual gaps",
            rationale=(
                f"Remaining gaps ({gap_names}) can be absorbed by an MSSP "
                f"without additional tool licenses. Estimated recovery from "
                f"overlap consolidation: ${analysis.recoverable_spend_k}K — "
                f"redirect toward MSSP retainer."
            ),
            estimated_savings_k=0,
            effort="Low",
        ))

    return steps
