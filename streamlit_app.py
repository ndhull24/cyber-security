"""
Streamlit app for Shieldient Vendor Stack Rationalization Agent.

A user-friendly interface to analyze cybersecurity tool stacks and get recommendations.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.tool_catalog import TOOL_CATALOG, DOMAIN_DISPLAY, COMPLIANCE_DOMAIN_WEIGHTS
from agent.scoring import analyze_stack, generate_roadmap
from agent.llm import generate_narrative

# ── Shieldient Color Palette ──────────────────────────────────────────────────
COLORS = {
    "primary": "#1D9E75",      # Teal/Green (Shieldient brand)
    "dark": "#0F172A",         # Near-black
    "accent": "#1E9678",       # Teal variant
    "warning": "#BA751700",    # Amber (transparency)
    "danger": "#A32D2D",       # Red
    "light": "#F5F8FC",        # Light background
}

# ── Page Configuration ────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Shieldient Stack Rationalization",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────

st.markdown(f"""
    <style>
    /* Main theme colors */
    :root {{
        --primary-color: {COLORS['primary']};
        --dark-color: {COLORS['dark']};
    }}
    
    /* Streamlit customization */
    .stApp {{
        background-color: #FAFBFC;
    }}
    
    /* Headers */
    h1, h2, h3 {{
        color: {COLORS['dark']};
        font-weight: 700;
    }}
    
    h1 {{
        border-bottom: 3px solid {COLORS['primary']};
        padding-bottom: 0.5rem;
    }}
    
    /* Buttons */
    .stButton > button {{
        background-color: {COLORS['primary']};
        color: white;
        border: none;
        font-weight: 600;
        border-radius: 6px;
    }}
    
    .stButton > button:hover {{
        background-color: #178060;
        color: white;
    }}
    
    /* Info boxes */
    .info-box {{
        background-color: rgba(29, 158, 117, 0.1);
        border-left: 4px solid {COLORS['primary']};
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }}
    
    .warning-box {{
        background-color: rgba(186, 117, 23, 0.1);
        border-left: 4px solid #BA751700;
        padding: 1rem;
        border-radius: 6px;
        margin: 1rem 0;
    }}
    
    /* Metrics */
    .metric-card {{
        background: white;
        padding: 1.5rem;
        border-radius: 8px;
        border-top: 4px solid {COLORS['primary']};
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }}
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] button {{
        color: {COLORS['dark']};
        font-weight: 500;
    }}
    
    .stTabs [data-baseweb="tab-list"] button[aria-selected="true"] {{
        border-bottom-color: {COLORS['primary']};
        color: {COLORS['primary']};
    }}
    </style>
""", unsafe_allow_html=True)

# ── Helper Functions ──────────────────────────────────────────────────────────

def score_to_color(score: int) -> str:
    """Map score to color."""
    if score >= 75:
        return "#1D9E75"  # Green
    elif score >= 50:
        return "#BA7517"  # Amber
    else:
        return "#A32D2D"  # Red


def render_info_box(title: str, description: str, icon: str = "ℹ️"):
    """Render an information box with explanation."""
    st.markdown(f"""
        <div class="info-box">
            <strong>{icon} {title}</strong><br/>
            {description}
        </div>
    """, unsafe_allow_html=True)


def render_metric_card(label: str, value: str, color: str = None):
    """Render a metric card."""
    if color is None:
        color = COLORS['primary']
    st.markdown(f"""
        <div style="background: white; padding: 1.5rem; border-radius: 8px; 
                    border-top: 4px solid {color}; box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                    margin: 0.5rem 0;">
            <div style="font-size: 0.85rem; color: #666;">
                {label}
            </div>
            <div style="font-size: 1.8rem; font-weight: 700; color: {color}; margin-top: 0.25rem;">
                {value}
            </div>
        </div>
    """, unsafe_allow_html=True)


# ── Session State Management ──────────────────────────────────────────────────

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "roadmap" not in st.session_state:
    st.session_state.roadmap = None

# ── Page Header ───────────────────────────────────────────────────────────────

st.markdown("""
    <div style="background: linear-gradient(135deg, #0F172A 0%, #1D9E75 100%); 
                padding: 2rem; border-radius: 8px; margin-bottom: 2rem;">
        <h1 style="color: white; border: none; margin: 0; display: flex; align-items: center; gap: 1rem;">
            🛡️ Cybersecurity Stack Rationalization
        </h1>
        <p style="color: rgba(255,255,255,0.8); margin: 0.5rem 0 0 0; font-size: 1.1rem;">
            Powered by <strong>Shieldient</strong> — Analyze your security tools for efficiency, coverage, and compliance
        </p>
    </div>
""", unsafe_allow_html=True)

# ── Main Content ──────────────────────────────────────────────────────────────

tabs = st.tabs([
    "📋 Company Profile",
    "🔧 Tool Selection",
    "📊 Analysis Results",
    "🗺️ Consolidation Roadmap",
    "📈 Detailed Insights"
])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1: Company Profile
# ══════════════════════════════════════════════════════════════════════════════

with tabs[0]:
    st.header("Step 1: Company Context")
    render_info_box(
        "What This Step Does",
        "We gather information about your organization to tailor the analysis to your specific regulatory, industry, and budget constraints.",
        "📝"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Organization Details")
        industry = st.selectbox(
            "Industry Vertical",
            [
                "Financial Services / Insurance",
                "Healthcare / Life Sciences",
                "Manufacturing / OT",
                "Retail / E-Commerce",
                "Technology / SaaS",
                "Government / Public Sector",
                "Energy / Utilities",
            ],
            help="Select the industry your organization operates in. This helps contextualize compliance requirements."
        )

        size = st.selectbox(
            "Company Size",
            [
                "1–50 employees (Startup)",
                "50–500 employees (SMB)",
                "500–2,000 employees (Mid-market)",
                "2,000+ employees (Enterprise)",
            ],
            help="Company size influences typical tool deployment and budget allocation."
        )

    with col2:
        st.subheader("Compliance & Budget")
        compliance = st.selectbox(
            "Primary Compliance Framework",
            list(COMPLIANCE_DOMAIN_WEIGHTS.keys()),
            help="Select your primary compliance requirement (SOX, HIPAA, PCI-DSS, NIST CSF, ISO 27001, or None)"
        )

        budget_options = {
            "Under $100K": 100,
            "$100K – $500K": 500,
            "$500K – $1M": 1000,
            "$1M+": 2000,
        }
        budget_label = st.selectbox(
            "Annual Security Budget",
            list(budget_options.keys()),
            help="Your annual security tool and services budget. This helps assess spend efficiency."
        )
        budget_k = budget_options[budget_label]

    st.divider()

    st.markdown("**Summary of your organization:**")
    summary_cols = st.columns(4)
    with summary_cols[0]:
        render_metric_card("Industry", industry.split("/")[0].strip()[:15])
    with summary_cols[1]:
        render_metric_card("Size", size.split("(")[1].rstrip(")"))
    with summary_cols[2]:
        render_metric_card("Compliance", compliance)
    with summary_cols[3]:
        render_metric_card("Budget", f"${budget_k}K")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 2: Tool Selection
# ══════════════════════════════════════════════════════════════════════════════

with tabs[1]:
    st.header("Step 2: Current Vendor Stack")
    render_info_box(
        "What This Step Does",
        "Select all security tools your organization currently uses. We'll analyze them for overlaps, coverage gaps, and efficiency.",
        "🔍"
    )

    st.markdown("**Organize tools by category for easier selection:**")

    # Group tools by category
    categories = {}
    for tool in TOOL_CATALOG:
        if tool.category not in categories:
            categories[tool.category] = []
        categories[tool.category].append(tool)

    selected_tool_ids = []

    for category in sorted(categories.keys()):
        with st.expander(f"**{category}**", expanded=True):
            tools_in_cat = categories[category]
            cols = st.columns(2)
            for idx, tool in enumerate(tools_in_cat):
                with cols[idx % 2]:
                    if st.checkbox(
                        f"{tool.name}",
                        key=f"tool_{tool.id}",
                        help=f"{tool.vendor} — ${tool.annual_cost_k}K/year\n\nCoverage: {', '.join(d.replace('_', ' ').title() for d in tool.coverage[:3])}"
                    ):
                        selected_tool_ids.append(tool.id)

    if selected_tool_ids:
        st.divider()
        st.markdown("**Selected Tools Summary:**")

        selected_tools = [t for t in TOOL_CATALOG if t.id in selected_tool_ids]
        total_cost = sum(t.annual_cost_k for t in selected_tools)
        utilization = round((total_cost / budget_k) * 100)

        summary_cols = st.columns(4)
        with summary_cols[0]:
            render_metric_card("Tools Selected", str(len(selected_tools)))
        with summary_cols[1]:
            render_metric_card("Total Spend", f"${total_cost}K/yr")
        with summary_cols[2]:
            color = "#1D9E75" if utilization <= 100 else "#A32D2D"
            render_metric_card("Budget Used", f"{utilization}%", color)
        with summary_cols[3]:
            render_metric_card("Vendors", str(len(set(t.vendor for t in selected_tools))))

        # Run analysis when we have selected tools
        if st.button("🔬 Analyze Stack", type="primary", use_container_width=True):
            with st.spinner("Analyzing your security stack..."):
                try:
                    analysis = analyze_stack(
                        selected_ids=selected_tool_ids,
                        industry=industry,
                        size=size,
                        compliance=compliance,
                        budget_k=budget_k,
                    )
                    roadmap = generate_roadmap(analysis)
                    analysis.narrative = generate_narrative(analysis)

                    st.session_state.analysis = analysis
                    st.session_state.roadmap = roadmap

                    st.success("✅ Analysis complete! Check the Results tab.")
                except Exception as e:
                    st.error(f"❌ Analysis failed: {str(e)}")
    else:
        st.info("👈 Select at least one tool to proceed with analysis.")

# ══════════════════════════════════════════════════════════════════════════════
# TAB 3: Analysis Results
# ══════════════════════════════════════════════════════════════════════════════

with tabs[2]:
    st.header("Step 3: Analysis Results")
    render_info_box(
        "What You're Seeing",
        "Your stack's overall health score, broken down by efficiency (redundancy), coverage (domain breadth), and compliance alignment.",
        "📊"
    )

    if st.session_state.analysis is None:
        st.warning("⚠️ Please complete the analysis from the Tool Selection tab first.")
    else:
        analysis = st.session_state.analysis

        # Overall Score and breakdown
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            render_metric_card(
                "Overall Score",
                f"{analysis.overall_score}/100",
                score_to_color(analysis.overall_score)
            )

        with col2:
            render_metric_card(
                "Efficiency",
                f"{analysis.efficiency_score}/100",
                score_to_color(analysis.efficiency_score)
            )

        with col3:
            render_metric_card(
                "Coverage",
                f"{analysis.coverage_score}/100",
                score_to_color(analysis.coverage_score)
            )

        with col4:
            render_metric_card(
                "Compliance",
                f"{analysis.compliance_score}/100",
                score_to_color(analysis.compliance_score)
            )

        st.divider()

        # Score visualization
        col_viz1, col_viz2 = st.columns(2)

        with col_viz1:
            st.subheader("Score Breakdown")
            fig_scores = go.Figure(data=[
                go.Bar(
                    x=["Efficiency", "Coverage", "Compliance"],
                    y=[analysis.efficiency_score, analysis.coverage_score, analysis.compliance_score],
                    marker_color=[
                        score_to_color(analysis.efficiency_score),
                        score_to_color(analysis.coverage_score),
                        score_to_color(analysis.compliance_score),
                    ],
                    text=[
                        f"{analysis.efficiency_score}/100",
                        f"{analysis.coverage_score}/100",
                        f"{analysis.compliance_score}/100",
                    ],
                    textposition="outside",
                )
            ])
            fig_scores.update_layout(
                yaxis=dict(range=[0, 100]),
                showlegend=False,
                height=350,
                margin=dict(b=50),
            )
            st.plotly_chart(fig_scores, use_container_width=True)

        with col_viz2:
            st.subheader("Financial Impact")
            financial_data = {
                "Metric": ["Annual Spend", "Wasted Spend", "Recoverable"],
                "Amount ($K)": [
                    analysis.total_spend_k,
                    analysis.wasted_spend_k,
                    analysis.recoverable_spend_k,
                ],
                "Color": ["#1D9E75", "#A32D2D", "#BA7517"],
            }
            fig_financial = go.Figure(data=[
                go.Bar(
                    x=financial_data["Metric"],
                    y=financial_data["Amount ($K)"],
                    marker_color=financial_data["Color"],
                    text=[f"${v}K" for v in financial_data["Amount ($K)"]],
                    textposition="outside",
                )
            ])
            fig_financial.update_layout(
                showlegend=False,
                height=350,
                margin=dict(b=50),
            )
            st.plotly_chart(fig_financial, use_container_width=True)

        st.divider()

        # Overlaps Section
        if analysis.overlap_pairs:
            st.subheader("⚠️ Tool Overlaps Detected")
            st.markdown(f"Your stack has **{len(analysis.overlap_pairs)}** functional overlap(s), representing potential waste:")

            for i, overlap in enumerate(analysis.overlap_pairs, 1):
                with st.expander(
                    f"**Overlap {i}:** {overlap.tool_a.name} × {overlap.tool_b.name}",
                    expanded=(i == 1)
                ):
                    col_overlap1, col_overlap2, col_overlap3 = st.columns(3)

                    with col_overlap1:
                        render_metric_card("Tool A", overlap.tool_a.name[:20], "#1D9E75")

                    with col_overlap2:
                        render_metric_card("Tool B", overlap.tool_b.name[:20], "#1D9E75")

                    with col_overlap3:
                        render_metric_card("Redundant Spend", f"${overlap.estimated_wasted_cost_k}K/yr", "#A32D2D")

                    shared_domains = ", ".join(
                        DOMAIN_DISPLAY[d] for d in overlap.shared_domains
                    )
                    st.markdown(f"**Shared Coverage:** {shared_domains}")
                    st.markdown(
                        f"*Recommendation: Retire the cheaper tool to recover ~${overlap.estimated_wasted_cost_k}K annually.*"
                    )
        else:
            st.success("✅ No tool overlaps detected — your selections are non-redundant.")

        st.divider()

        # Coverage Gaps Section
        if analysis.coverage_gaps:
            st.subheader("🔍 Coverage Gaps")
            st.markdown(f"Your stack has **{len(analysis.coverage_gaps)}** uncovered domain(s):")

            high_gaps = [g for g in analysis.coverage_gaps if g.compliance_weight >= 2]
            medium_gaps = [g for g in analysis.coverage_gaps if g.compliance_weight == 1]
            low_gaps = [g for g in analysis.coverage_gaps if g.compliance_weight == 0]

            if high_gaps:
                st.markdown("**🔴 High Priority (Compliance-Critical):**")
                for gap in high_gaps:
                    recs = ", ".join(gap.recommended_tools[:2]) if gap.recommended_tools else "Evaluate vendors"
                    st.markdown(
                        f"- **{DOMAIN_DISPLAY[gap.domain]}** → Recommended: {recs}"
                    )

            if medium_gaps:
                st.markdown("**🟡 Medium Priority:**")
                for gap in medium_gaps:
                    recs = ", ".join(gap.recommended_tools[:2]) if gap.recommended_tools else "Evaluate vendors"
                    st.markdown(f"- **{DOMAIN_DISPLAY[gap.domain]}** → Recommended: {recs}")

            if low_gaps:
                with st.expander("🟢 Low Priority (Consider for MSSP)"):
                    for gap in low_gaps:
                        recs = ", ".join(gap.recommended_tools[:2]) if gap.recommended_tools else "Evaluate vendors"
                        st.markdown(f"- **{DOMAIN_DISPLAY[gap.domain]}** → Recommended: {recs}")
        else:
            st.success("✅ Complete coverage across all domains detected.")

        st.divider()

        # Executive Narrative
        if analysis.narrative:
            st.subheader("📝 Executive Summary")
            with st.container():
                st.markdown(f"""
                    <div style="background: white; padding: 1.5rem; border-radius: 8px; 
                                border-left: 4px solid {COLORS['primary']};">
                        {analysis.narrative}
                    </div>
                """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TAB 4: Consolidation Roadmap
# ══════════════════════════════════════════════════════════════════════════════

with tabs[3]:
    st.header("Step 4: Consolidation Roadmap")
    render_info_box(
        "What This Step Provides",
        "A prioritized action plan to optimize your stack. Consolidate overlaps first (quick wins), then fill compliance gaps, then engage an MSSP for residual risks.",
        "🗺️"
    )

    if st.session_state.roadmap is None:
        st.warning("⚠️ Please complete the analysis from the Tool Selection tab first.")
    else:
        roadmap = st.session_state.roadmap
        analysis = st.session_state.analysis

        if not roadmap:
            st.info("✅ Your stack is already optimized — no consolidation actions needed.")
        else:
            for step in roadmap:
                effort_color = {
                    "Low": "#1D9E75",
                    "Medium": "#BA7517",
                    "High": "#A32D2D",
                }.get(step.effort, "#666")

                with st.expander(f"**Priority {step.priority}:** {step.action}", expanded=(step.priority == 1)):
                    col_effort, col_savings = st.columns(2)

                    with col_effort:
                        st.markdown(f"**Implementation Effort:**")
                        render_metric_card("Effort Level", step.effort, effort_color)

                    with col_savings:
                        st.markdown(f"**Financial Impact:**")
                        if step.estimated_savings_k > 0:
                            render_metric_card("Savings", f"${step.estimated_savings_k}K/yr", "#1D9E75")
                        else:
                            render_metric_card("No Direct Savings", "Focus: Coverage", "#1D9E75")

                    st.markdown(f"**Rationale:**\n{step.rationale}")

        # Summary section
        st.divider()
        st.subheader("📈 Potential Impact")

        potential_savings = sum(s.estimated_savings_k for s in roadmap)
        col_impact1, col_impact2, col_impact3 = st.columns(3)

        with col_impact1:
            render_metric_card(
                "Total Recoverable",
                f"${analysis.recoverable_spend_k}K/yr",
                "#1D9E75"
            )

        with col_impact2:
            render_metric_card(
                "Timeline",
                "3-6 Months",
                "#1D9E75"
            )

        with col_impact3:
            render_metric_card(
                "Priority Actions",
                str(len(roadmap)),
                "#1D9E75"
            )

        st.info(
            f"💡 By following this roadmap, you can recover ~${analysis.recoverable_spend_k}K annually "
            f"and improve your stack score by closing compliance gaps with strategic tool additions."
        )

# ══════════════════════════════════════════════════════════════════════════════
# TAB 5: Detailed Insights
# ══════════════════════════════════════════════════════════════════════════════

with tabs[4]:
    st.header("Step 5: Detailed Insights")
    render_info_box(
        "What This Contains",
        "Deep-dive data on your selected tools, domain coverage, and metrics to support decision-making.",
        "🔬"
    )

    if st.session_state.analysis is None:
        st.warning("⚠️ Please complete the analysis from the Tool Selection tab first.")
    else:
        analysis = st.session_state.analysis

        # Tools Table
        st.subheader("Selected Tools Inventory")
        tools_data = []
        for tool in analysis.selected_tools:
            tools_data.append({
                "Tool Name": tool.name,
                "Vendor": tool.vendor,
                "Category": tool.category,
                "Annual Cost": f"${tool.annual_cost_k}K",
                "Coverage Domains": len(tool.coverage),
            })

        df_tools = pd.DataFrame(tools_data)
        st.dataframe(df_tools, use_container_width=True, hide_index=True)

        st.divider()

        # Domain Coverage Heatmap
        st.subheader("Domain Coverage Matrix")
        st.markdown("Which domains does each tool cover? (✓ = covered)")

        coverage_matrix = []
        for tool in analysis.selected_tools:
            row = {"Tool": tool.name}
            for domain in sorted(DOMAIN_DISPLAY.keys()):
                row[DOMAIN_DISPLAY[domain]] = "✓" if domain in tool.coverage else ""
            coverage_matrix.append(row)

        df_coverage = pd.DataFrame(coverage_matrix)
        st.dataframe(df_coverage, use_container_width=True, hide_index=True)

        st.divider()

        # Compliance Alignment
        st.subheader("Compliance Framework Alignment")
        st.markdown(f"**Framework:** {analysis.compliance}")

        compliance_weights = COMPLIANCE_DOMAIN_WEIGHTS.get(analysis.compliance, {})
        if compliance_weights:
            compliance_data = []
            for domain, weight in sorted(compliance_weights.items(), key=lambda x: x[1], reverse=True):
                is_covered = domain in analysis.covered_domains
                status = "✓ Covered" if is_covered else "✗ Gap"
                compliance_data.append({
                    "Domain": DOMAIN_DISPLAY.get(domain, domain),
                    "Weight": weight,
                    "Status": status,
                })

            df_compliance = pd.DataFrame(compliance_data)
            st.dataframe(df_compliance, use_container_width=True, hide_index=True)
        else:
            st.info("No compliance framework selected for detailed analysis.")

        st.divider()

        # Key Metrics
        st.subheader("Key Metrics Summary")
        metrics_cols = st.columns(4)

        metrics = [
            ("Tools Deployed", str(len(analysis.selected_tools))),
            ("Domains Covered", f"{len(analysis.covered_domains)}/12"),
            ("Domains Covered %", f"{analysis.coverage_score}%"),
            ("Budget Utilization", f"{analysis.budget_utilization_pct}%"),
        ]

        for idx, (label, value) in enumerate(metrics):
            with metrics_cols[idx % 4]:
                render_metric_card(label, value)

# ══════════════════════════════════════════════════════════════════════════════
# Footer
# ══════════════════════════════════════════════════════════════════════════════

st.divider()
st.markdown("""
    <div style="text-align: center; color: #666; padding: 2rem 0; font-size: 0.9rem;">
        <p>🛡️ <strong>Shieldient</strong> — Your Shield for a Resilient, AI-First World</p>
        <p>This tool demonstrates vendor stack rationalization capabilities. For enterprise deployments, 
        <a href="mailto:explore@shieldient.com">contact Shieldient</a>.</p>
        <p style="font-size: 0.8rem; margin-top: 1rem;">
            © 2025 Shieldient Inc. | Built with Streamlit
        </p>
    </div>
""", unsafe_allow_html=True)
