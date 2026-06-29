"""
Scoring engine.
Pure functions — no I/O, no external calls.
Takes a list of selected tool IDs + company context, returns a StackAnalysis dataclass.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, List, Set, Tuple, Dict

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
    confidence: str
    confidence_reason: str

    def display(self) -> str:
        domains = ", ".join(DOMAIN_DISPLAY[d] for d in self.shared_domains)
        return (
            f"{self.tool_a.name}  ×  {self.tool_b.name}\n"
            f"  Shared coverage : {domains}\n"
            f"  Redundant spend : ~${self.estimated_wasted_cost_k}K/yr "
            f"(retire the cheaper tool to recover this)\n"
            f"  Confidence: {self.confidence} — {self.confidence_reason}"
        )


@dataclass
class CoverageGap:
    domain: str
    compliance_weight: int      # 0 if not in the selected framework
    recommended_tools: List[str]
    confidence: str
    confidence_reason: str

    def display(self) -> str:
        risk = "HIGH" if self.compliance_weight >= 2 else ("MEDIUM" if self.compliance_weight == 1 else "LOW")
        recs = ", ".join(self.recommended_tools[:3]) if self.recommended_tools else "No catalog match"
        return (
            f"{DOMAIN_DISPLAY[self.domain]}  [{risk} RISK]\n"
            f"  Suggested tools : {recs}\n"
            f"  Confidence: {self.confidence} — {self.confidence_reason}"
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
    overall_confidence: str

    # Financial
    wasted_spend_k: int
    recoverable_spend_k: int
    budget_utilization_pct: int

    # Explainability / guardrails
    explainability: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

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

def _confidence_label_from_score(score: int) -> str:
    if score >= 75:
        return "HIGH"
    if score >= 50:
        return "MEDIUM"
    return "LOW"


def _build_overlap_confidence(shared: List[str], weights: Dict[str, int]) -> Tuple[str, str]:
    if any(weights.get(domain, 0) >= 2 for domain in shared):
        return (
            "HIGH",
            "Shared domains include compliance-critical controls, so this overlap is a strong consolidation candidate."
        )
    if len(shared) >= 2:
        return (
            "MEDIUM",
            "Multiple shared domains indicate material redundancy, but one of the tools may still provide unique capabilities."
        )
    return (
        "LOW",
        "Overlap is limited to a single domain and may be less impactful, but it still deserves review."
    )


def _build_gap_confidence(compliance_weight: int) -> Tuple[str, str]:
    if compliance_weight >= 2:
        return (
            "HIGH",
            "This gap is in a high-priority compliance domain for the chosen framework."
        )
    if compliance_weight == 1:
        return (
            "MEDIUM",
            "This gap has moderate compliance importance and should be considered in risk planning."
        )
    return (
        "LOW",
        "This gap is outside the selected compliance framework or has lower regulatory impact."
    )

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
    if budget_k <= 0:
        raise ValueError("Budget must be greater than zero.")

    selected_tools = [TOOL_MAP[tid] for tid in selected_ids if tid in TOOL_MAP]
    if not selected_tools:
        raise ValueError("At least one known tool must be selected for analysis.")

    # ── Spend ─────────────────────────────────────────────────────────────
    total_spend_k = sum(t.annual_cost_k for t in selected_tools)
    budget_utilization_pct = round((total_spend_k / budget_k) * 100)

    warnings: List[str] = []
    if total_spend_k > budget_k:
        over_pct = round((total_spend_k - budget_k) / budget_k * 100)
        warnings.append(
            f"Selected tools exceed the budget by {over_pct}% — review spend or increase the budget."
        )

    # ── Overlap detection ─────────────────────────────────────────────────
    selected_set: Set[str] = set(selected_ids)
    seen_pairs: Set[Tuple[str, str]] = set()
    overlap_pairs: List[OverlapPair] = []

    weights = COMPLIANCE_DOMAIN_WEIGHTS.get(compliance, {})
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
            confidence, confidence_reason = _build_overlap_confidence(shared, weights)
            overlap_pairs.append(OverlapPair(
                tool_a=tool,
                tool_b=other,
                shared_domains=shared,
                estimated_wasted_cost_k=wasted,
                confidence=confidence,
                confidence_reason=confidence_reason,
            ))

    wasted_spend_k = sum(op.estimated_wasted_cost_k for op in overlap_pairs)
    recoverable_spend_k = round(wasted_spend_k * 0.6)

    # ── Coverage analysis ─────────────────────────────────────────────────
    covered_domains: Set[str] = set()
    for tool in selected_tools:
        covered_domains.update(tool.coverage)

    coverage_gaps: List[CoverageGap] = []
    for domain in COVERAGE_DOMAINS:
        if domain not in covered_domains:
            confidence, confidence_reason = _build_gap_confidence(weights.get(domain, 0))
            coverage_gaps.append(CoverageGap(
                domain=domain,
                compliance_weight=weights.get(domain, 0),
                recommended_tools=_DOMAIN_TOOL_INDEX.get(domain, []),
                confidence=confidence,
                confidence_reason=confidence_reason,
            ))

    coverage_gaps.sort(key=lambda g: g.compliance_weight, reverse=True)

    # ── Scores ────────────────────────────────────────────────────────────
    coverage_score = round((len(covered_domains) / len(COVERAGE_DOMAINS)) * 100)

    max_compliance_score = sum(weights.values()) or 1
    achieved_compliance = sum(
        w for domain, w in weights.items() if domain in covered_domains
    )
    compliance_score = round((achieved_compliance / max_compliance_score) * 100)

    overlap_penalty = min(40, len(overlap_pairs) * 8)
    efficiency_score = max(10, coverage_score - overlap_penalty)

    overall_score = round(
        efficiency_score * 0.40
        + coverage_score  * 0.35
        + compliance_score * 0.25
    )
    overall_confidence = _confidence_label_from_score(overall_score)

    if not coverage_gaps:
        warnings.append(
            "Your stack fully covers all defined domains; confirm the selected tools are complete and up to date."
        )
    elif compliance != "None" and all(weights.get(domain, 0) == 0 for domain in covered_domains):
        warnings.append(
            f"Selected tools do not cover any compliance-weighted domains for {compliance}."
        )

    explainability: List[str] = [
        f"Coverage score is {coverage_score}/100 based on {len(covered_domains)}/{len(COVERAGE_DOMAINS)} domains covered.",
        f"Compliance score is {compliance_score}/100 based on {achieved_compliance}/{max_compliance_score} weighted compliance controls satisfied.",
        f"Efficiency score is {efficiency_score}/100 after applying an overlap penalty of {overlap_penalty} points for {len(overlap_pairs)} overlap(s).",
        "Overall score is a weighted blend: 40% efficiency, 35% coverage, 25% compliance.",
        f"Overall confidence is {overall_confidence} for the combined stack assessment.",
    ]

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
        overall_confidence=overall_confidence,
        wasted_spend_k=wasted_spend_k,
        recoverable_spend_k=recoverable_spend_k,
        budget_utilization_pct=budget_utilization_pct,
        explainability=explainability,
        warnings=warnings,
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
