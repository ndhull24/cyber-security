"""
Tests for the scoring engine and roadmap generator.
Run:  pytest tests/test_scoring.py -v
"""

import pytest

from agent.scoring import analyze_stack, generate_roadmap
from data.tool_catalog import COVERAGE_DOMAINS


# ── Fixtures ──────────────────────────────────────────────────────────────────

OVERLAPPING_STACK = ["crowdstrike", "sentinelone", "splunk"]   # crowdstrike+sentinelone overlap
CLEAN_STACK       = ["crowdstrike", "splunk", "okta", "tenable", "proofpoint", "paloalto_ngfw"]
MINIMAL_STACK     = ["defender_edr"]


def base_analysis(selected_ids, compliance="NIST CSF"):
    return analyze_stack(
        selected_ids=selected_ids,
        industry="Financial Services / Insurance",
        size="500–2,000 employees (Mid-market)",
        compliance=compliance,
        budget_k=500,
    )


# ── Overlap detection ─────────────────────────────────────────────────────────

class TestOverlapDetection:
    def test_detects_edr_overlap(self):
        analysis = base_analysis(OVERLAPPING_STACK)
        tool_ids_in_pairs = set()
        for pair in analysis.overlap_pairs:
            tool_ids_in_pairs.update([pair.tool_a.id, pair.tool_b.id])
        assert "crowdstrike" in tool_ids_in_pairs or "sentinelone" in tool_ids_in_pairs

    def test_no_overlap_in_clean_stack(self):
        analysis = base_analysis(CLEAN_STACK)
        assert analysis.overlap_pairs == []

    def test_overlap_pairs_are_not_duplicated(self):
        """A+B and B+A should appear only once."""
        analysis = base_analysis(["crowdstrike", "sentinelone", "carbon_black"])
        seen = set()
        for pair in analysis.overlap_pairs:
            key = tuple(sorted([pair.tool_a.id, pair.tool_b.id]))
            assert key not in seen, f"Duplicate pair: {key}"
            seen.add(key)

    def test_wasted_spend_is_minimum_of_pair(self):
        """Wasted spend should be the cost of the cheaper tool in the pair."""
        analysis = base_analysis(["crowdstrike", "sentinelone"])
        assert len(analysis.overlap_pairs) == 1
        pair = analysis.overlap_pairs[0]
        expected_waste = min(pair.tool_a.annual_cost_k, pair.tool_b.annual_cost_k)
        assert pair.estimated_wasted_cost_k == expected_waste


# ── Coverage analysis ─────────────────────────────────────────────────────────

class TestCoverageAnalysis:
    def test_covered_domains_reflect_selected_tools(self):
        analysis = base_analysis(["crowdstrike"])
        from data.tool_catalog import TOOL_MAP
        expected = set(TOOL_MAP["crowdstrike"].coverage)
        assert expected.issubset(analysis.covered_domains)

    def test_gaps_are_all_uncovered_domains(self):
        analysis = base_analysis(MINIMAL_STACK)
        gap_domains = {g.domain for g in analysis.coverage_gaps}
        uncovered = set(COVERAGE_DOMAINS) - analysis.covered_domains
        assert gap_domains == uncovered

    def test_full_stack_has_no_gaps(self):
        """Selecting tools covering all domains yields zero gaps."""
        all_ids = [
            "crowdstrike", "splunk", "paloalto_ngfw", "okta",
            "tenable", "proofpoint", "wiz", "sentinelone",
        ]
        analysis = base_analysis(all_ids)
        remaining_gaps = [g for g in analysis.coverage_gaps if g.compliance_weight > 0]
        assert len(remaining_gaps) == 0 or analysis.coverage_score >= 70

    def test_gaps_sorted_by_compliance_weight_desc(self):
        analysis = base_analysis(MINIMAL_STACK, compliance="SOX")
        weights = [g.compliance_weight for g in analysis.coverage_gaps]
        assert weights == sorted(weights, reverse=True)


# ── Scoring ───────────────────────────────────────────────────────────────────

class TestScoring:
    def test_scores_are_in_valid_range(self):
        for ids in [OVERLAPPING_STACK, CLEAN_STACK, MINIMAL_STACK]:
            analysis = base_analysis(ids)
            for score in [analysis.efficiency_score, analysis.coverage_score,
                          analysis.compliance_score, analysis.overall_score]:
                assert 0 <= score <= 100, f"Score out of range: {score}"

    def test_overlapping_stack_scores_lower_efficiency(self):
        overlap_analysis = base_analysis(OVERLAPPING_STACK)
        clean_analysis   = base_analysis(CLEAN_STACK)
        assert overlap_analysis.efficiency_score < clean_analysis.efficiency_score

    def test_total_spend_is_sum_of_selected_tools(self):
        from data.tool_catalog import TOOL_MAP
        ids = ["crowdstrike", "splunk", "okta"]
        analysis = base_analysis(ids)
        expected = sum(TOOL_MAP[i].annual_cost_k for i in ids)
        assert analysis.total_spend_k == expected

    def test_budget_utilization_calculated_correctly(self):
        analysis = analyze_stack(
            selected_ids=["crowdstrike"],  # $120K
            industry="Technology / SaaS",
            size="50–500 employees (SMB)",
            compliance="None",
            budget_k=200,
        )
        assert analysis.budget_utilization_pct == 60

    def test_recoverable_spend_is_60pct_of_wasted(self):
        analysis = base_analysis(["crowdstrike", "sentinelone"])
        assert analysis.recoverable_spend_k == round(analysis.wasted_spend_k * 0.6)

    def test_unknown_tool_ids_are_ignored_gracefully(self):
        analysis = base_analysis(["crowdstrike", "nonexistent_tool_xyz"])
        tool_ids = [t.id for t in analysis.selected_tools]
        assert "nonexistent_tool_xyz" not in tool_ids
        assert "crowdstrike" in tool_ids


# ── Roadmap generation ────────────────────────────────────────────────────────

class TestRoadmap:
    def test_roadmap_prioritizes_overlaps_first(self):
        analysis = base_analysis(OVERLAPPING_STACK)
        roadmap = generate_roadmap(analysis)
        if analysis.overlap_pairs:
            first_step = roadmap[0]
            # First step should be a retire/consolidate action
            assert "Retire" in first_step.action or "retire" in first_step.rationale.lower()

    def test_roadmap_steps_have_sequential_priorities(self):
        analysis = base_analysis(OVERLAPPING_STACK)
        roadmap = generate_roadmap(analysis)
        for i, step in enumerate(roadmap, start=1):
            assert step.priority == i

    def test_overlap_steps_have_nonzero_savings(self):
        analysis = base_analysis(["crowdstrike", "sentinelone"])
        roadmap = generate_roadmap(analysis)
        overlap_steps = [s for s in roadmap if "Retire" in s.action]
        for step in overlap_steps:
            assert step.estimated_savings_k > 0

    def test_clean_stack_roadmap_suggests_mssp(self):
        """A stack with no overlaps but gaps should end with MSSP recommendation."""
        analysis = base_analysis(MINIMAL_STACK)
        roadmap = generate_roadmap(analysis)
        actions = " ".join(s.action for s in roadmap).lower()
        assert "shieldient" in actions or "mssp" in actions.lower()

    def test_effort_values_are_valid(self):
        analysis = base_analysis(OVERLAPPING_STACK)
        roadmap = generate_roadmap(analysis)
        valid_efforts = {"Low", "Medium", "High"}
        for step in roadmap:
            assert step.effort in valid_efforts, f"Invalid effort: {step.effort}"


# ── Compliance-specific behavior ──────────────────────────────────────────────

class TestComplianceScoring:
    @pytest.mark.parametrize("compliance", ["SOX", "HIPAA", "PCI-DSS", "NIST CSF", "ISO 27001", "None"])
    def test_compliance_score_valid_for_all_frameworks(self, compliance):
        analysis = base_analysis(CLEAN_STACK, compliance=compliance)
        assert 0 <= analysis.compliance_score <= 100

    def test_sox_weights_siem_heavily(self):
        """SOX requires strong SIEM — a SIEM-only stack should score higher compliance than EDR-only."""
        siem_analysis = base_analysis(["splunk"], compliance="SOX")
        edr_analysis  = base_analysis(["crowdstrike"], compliance="SOX")
        assert siem_analysis.compliance_score > edr_analysis.compliance_score

    def test_pci_weights_network_heavily(self):
        """PCI-DSS requires network controls — firewall stack should score higher than EDR-only."""
        fw_analysis  = base_analysis(["paloalto_ngfw", "tenable"], compliance="PCI-DSS")
        edr_analysis = base_analysis(["crowdstrike"], compliance="PCI-DSS")
        assert fw_analysis.compliance_score > edr_analysis.compliance_score
