"""
Synthetic data generator for the Shieldient Stack Rationalization Agent.

Generates realistic company profiles and runs them through the full analysis
pipeline, producing terminal output and PDF reports for each.

Run:
    python generate_data.py                  # generates 5 profiles (default)
    python generate_data.py --count 10       # generates 10 profiles
    python generate_data.py --seed 42        # reproducible output
    python generate_data.py --no-pdf         # skip PDF export
    python generate_data.py --profile fintech  # run one named scenario
"""

from __future__ import annotations
import argparse
import json
import os
import random
import sys
from dataclasses import dataclass, asdict
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.tool_catalog import TOOL_CATALOG, COMPLIANCE_DOMAIN_WEIGHTS, TOOL_MAP
from agent.scoring import analyze_stack, generate_roadmap
from agent.llm import generate_narrative
from agent.report import generate_pdf

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.rule import Rule
from rich import box

console = Console()


# ── Company profile definition ────────────────────────────────────────────────

@dataclass
class CompanyProfile:
    name: str
    industry: str
    size: str
    compliance: str
    budget_k: int
    selected_tool_ids: List[str]
    description: str = ""


# ── Named scenario library ────────────────────────────────────────────────────
# These are realistic, hand-crafted profiles covering common MSSP prospect types.

NAMED_SCENARIOS: dict[str, CompanyProfile] = {
    "fintech": CompanyProfile(
        name="Apex Financial Technologies",
        industry="Financial Services / Insurance",
        size="500–2,000 employees (Mid-market)",
        compliance="PCI-DSS",
        budget_k=800,
        selected_tool_ids=["crowdstrike", "sentinelone", "splunk", "sentinel_siem", "okta", "tenable"],
        description=(
            "A mid-market payments processor with two overlapping EDR tools "
            "and two SIEMs — classic post-acquisition sprawl. Strong on endpoint "
            "but missing email security and cloud security entirely."
        ),
    ),

    "regional_bank": CompanyProfile(
        name="Lone Star Community Bank",
        industry="Financial Services / Insurance",
        size="50–500 employees (SMB)",
        compliance="SOX",
        budget_k=300,
        selected_tool_ids=["defender_edr", "sentinel_siem", "azure_ad", "qualys"],
        description=(
            "A conservative SMB bank running an all-Microsoft stack. "
            "Low redundancy, but significant gaps in email security, "
            "network/firewall, and UEBA — all SOX-relevant."
        ),
    ),

    "hospital": CompanyProfile(
        name="Meridian Health System",
        industry="Healthcare / Life Sciences",
        size="2,000+ employees (Enterprise)",
        compliance="HIPAA",
        budget_k=1500,
        selected_tool_ids=[
            "crowdstrike", "splunk", "paloalto_ngfw", "okta",
            "tenable", "proofpoint", "prisma_cloud",
        ],
        description=(
            "A large hospital network with a mature, well-diversified stack. "
            "No overlaps, strong compliance coverage. Main gap is UEBA and SOAR — "
            "important for detecting insider threats in a healthcare context."
        ),
    ),

    "saas_startup": CompanyProfile(
        name="Velocify SaaS",
        industry="Technology / SaaS",
        size="50–500 employees (SMB)",
        compliance="NIST CSF",
        budget_k=200,
        selected_tool_ids=["sentinelone", "wiz", "okta", "defender_email"],
        description=(
            "A cloud-native startup with a lean, well-chosen stack. "
            "No redundancy. Missing SIEM, vulnerability management, and network "
            "controls — typical for early-stage companies moving fast."
        ),
    ),

    "manufacturer": CompanyProfile(
        name="Kestrel Industrial Group",
        industry="Manufacturing / OT",
        size="500–2,000 employees (Mid-market)",
        compliance="NIST CSF",
        budget_k=600,
        selected_tool_ids=[
            "carbon_black", "crowdstrike", "fortinet", "paloalto_ngfw",
            "splunk", "tenable", "azure_ad",
        ],
        description=(
            "A mid-sized manufacturer with OT environments. "
            "Running both Carbon Black and CrowdStrike (redundant EDR) and "
            "both Fortinet and Palo Alto NGFWs (redundant firewalls) — "
            "likely from separate IT and OT teams with no central oversight."
        ),
    ),

    "retailer": CompanyProfile(
        name="NorthStar Retail Group",
        industry="Retail / E-Commerce",
        size="2,000+ employees (Enterprise)",
        compliance="PCI-DSS",
        budget_k=2000,
        selected_tool_ids=[
            "crowdstrike", "splunk", "exabeam", "securonix",
            "paloalto_ngfw", "checkpoint", "okta", "ping_identity",
            "tenable", "qualys", "proofpoint", "mimecast",
        ],
        description=(
            "A large retailer that has grown through acquisitions. "
            "Severe sprawl: three SIEMs, two IAM platforms, two firewalls, "
            "two vuln scanners, two email security tools. "
            "This is what happens without a centralised security architecture."
        ),
    ),

    "government": CompanyProfile(
        name="Riverton County Government",
        industry="Government / Public Sector",
        size="50–500 employees (SMB)",
        compliance="NIST CSF",
        budget_k=150,
        selected_tool_ids=["defender_edr", "azure_ad", "defender_email", "defender_cloud"],
        description=(
            "A small municipality running an all-Microsoft stack due to budget "
            "constraints. Minimal redundancy but significant gaps. "
            "Good candidate for MSSP engagement to augment thin internal team."
        ),
    ),
}


# ── Random profile generator ──────────────────────────────────────────────────

INDUSTRIES = list(NAMED_SCENARIOS["fintech"].industry.__class__.__mro__)  # just use strings below
_INDUSTRIES = [
    "Financial Services / Insurance",
    "Healthcare / Life Sciences",
    "Manufacturing / OT",
    "Retail / E-Commerce",
    "Technology / SaaS",
    "Government / Public Sector",
    "Energy / Utilities",
]

_SIZES = [
    "50–500 employees (SMB)",
    "500–2,000 employees (Mid-market)",
    "2,000+ employees (Enterprise)",
]

_BUDGETS_BY_SIZE = {
    "50–500 employees (SMB)":            (80,  350),
    "500–2,000 employees (Mid-market)":  (300, 900),
    "2,000+ employees (Enterprise)":     (800, 2500),
}

_COMPLIANCE_BY_INDUSTRY = {
    "Financial Services / Insurance": ["SOX", "PCI-DSS"],
    "Healthcare / Life Sciences":     ["HIPAA"],
    "Manufacturing / OT":             ["NIST CSF", "ISO 27001"],
    "Retail / E-Commerce":            ["PCI-DSS", "NIST CSF"],
    "Technology / SaaS":              ["NIST CSF", "ISO 27001"],
    "Government / Public Sector":     ["NIST CSF"],
    "Energy / Utilities":             ["NIST CSF", "ISO 27001"],
}

# Tool pools by company size — larger companies have bigger stacks
_TOOL_POOLS_BY_SIZE = {
    "50–500 employees (SMB)":            (2, 5),
    "500–2,000 employees (Mid-market)":  (4, 8),
    "2,000+ employees (Enterprise)":     (6, 14),
}

_COMPANY_NAME_PREFIXES = [
    "Apex", "Meridian", "Vanguard", "Kestrel", "Pinnacle", "Horizon",
    "Summit", "Atlas", "Crestview", "Irongate", "Silverline", "Quantum",
]
_COMPANY_NAME_SUFFIXES = [
    "Technologies", "Group", "Systems", "Partners", "Enterprises",
    "Solutions", "Holdings", "Networks", "Capital", "Industries",
]


def generate_random_profile(rng: random.Random, index: int) -> CompanyProfile:
    industry = rng.choice(_INDUSTRIES)
    size = rng.choice(_SIZES)
    compliance = rng.choice(_COMPLIANCE_BY_INDUSTRY[industry])

    budget_min, budget_max = _BUDGETS_BY_SIZE[size]
    budget_k = rng.randint(budget_min // 100, budget_max // 100) * 100

    tool_min, tool_max = _TOOL_POOLS_BY_SIZE[size]
    num_tools = rng.randint(tool_min, tool_max)

    # Bias toward picking tools with categories common for the company size
    all_ids = [t.id for t in TOOL_CATALOG]
    selected_ids = rng.sample(all_ids, min(num_tools, len(all_ids)))

    name = (
        rng.choice(_COMPANY_NAME_PREFIXES)
        + " "
        + rng.choice(_COMPANY_NAME_SUFFIXES)
    )

    return CompanyProfile(
        name=name,
        industry=industry,
        size=size,
        compliance=compliance,
        budget_k=budget_k,
        selected_tool_ids=selected_ids,
        description=f"Auto-generated profile #{index + 1}",
    )


# ── Runner ────────────────────────────────────────────────────────────────────

def run_profile(
    profile: CompanyProfile,
    export_pdf: bool = True,
    export_json: bool = True,
) -> dict:
    """Run one profile through the full agent pipeline. Returns a result dict."""

    console.print()
    console.print(Panel.fit(
        f"[bold white]{profile.name}[/bold white]\n"
        f"[dim]{profile.industry}  ·  {profile.size}  ·  {profile.compliance}[/dim]\n"
        f"[dim]{profile.description}[/dim]",
        border_style="cyan",
        padding=(0, 2),
    ))

    # ── Scoring ───────────────────────────────────────────────────────────
    analysis = analyze_stack(
        selected_ids=profile.selected_tool_ids,
        industry=profile.industry,
        size=profile.size,
        compliance=profile.compliance,
        budget_k=profile.budget_k,
    )
    roadmap = generate_roadmap(analysis)
    analysis.narrative = generate_narrative(analysis)

    # ── Terminal summary table ─────────────────────────────────────────────
    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    t.add_column("", style="dim", width=28)
    t.add_column("", justify="right")

    def score_str(s: int) -> str:
        color = "green" if s >= 75 else ("yellow" if s >= 50 else "red")
        return f"[{color}]{s}/100[/{color}]"

    t.add_row("Tools deployed",         str(len(analysis.selected_tools)))
    t.add_row("Annual spend",           f"${analysis.total_spend_k}K")
    t.add_row("Wasted spend",           f"[red]${analysis.wasted_spend_k}K[/red]" if analysis.wasted_spend_k else "[green]$0K[/green]")
    t.add_row("Recoverable",            f"[green]${analysis.recoverable_spend_k}K[/green]")
    t.add_row("Overall score",          score_str(analysis.overall_score))
    t.add_row("Efficiency score",       score_str(analysis.efficiency_score))
    t.add_row("Coverage score",         score_str(analysis.coverage_score))
    t.add_row("Compliance score",       score_str(analysis.compliance_score))
    t.add_row("Overlaps detected",      str(len(analysis.overlap_pairs)))
    t.add_row("Coverage gaps",          str(len(analysis.coverage_gaps)))
    console.print(t)

    if analysis.overlap_pairs:
        console.print("  [yellow]Overlaps:[/yellow]")
        for pair in analysis.overlap_pairs:
            console.print(f"    ⚠  {pair.tool_a.name} × {pair.tool_b.name}  [dim](${pair.estimated_wasted_cost_k}K/yr)[/dim]")

    if analysis.coverage_gaps:
        high = [g for g in analysis.coverage_gaps if g.compliance_weight >= 2]
        if high:
            console.print("  [red]High-priority gaps:[/red]")
            for g in high:
                from data.tool_catalog import DOMAIN_DISPLAY
                console.print(f"    ✗  {DOMAIN_DISPLAY[g.domain]}")

    if analysis.narrative:
        console.print(f"\n  [dim italic]{analysis.narrative[:200].strip()}...[/dim italic]")

    # ── Exports ───────────────────────────────────────────────────────────
    safe_name = profile.name.replace(" ", "_").replace("/", "-")
    result = {
        "company": profile.name,
        "industry": profile.industry,
        "size": profile.size,
        "compliance": profile.compliance,
        "budget_k": profile.budget_k,
        "tools": [t.name for t in analysis.selected_tools],
        "scores": {
            "overall":    analysis.overall_score,
            "efficiency": analysis.efficiency_score,
            "coverage":   analysis.coverage_score,
            "compliance": analysis.compliance_score,
        },
        "financials": {
            "total_spend_k":      analysis.total_spend_k,
            "wasted_spend_k":     analysis.wasted_spend_k,
            "recoverable_spend_k": analysis.recoverable_spend_k,
            "budget_utilization_pct": analysis.budget_utilization_pct,
        },
        "overlaps": len(analysis.overlap_pairs),
        "gaps":     len(analysis.coverage_gaps),
        "narrative": analysis.narrative,
        "roadmap": [
            {"priority": s.priority, "action": s.action, "effort": s.effort, "savings_k": s.estimated_savings_k}
            for s in roadmap
        ],
    }

    os.makedirs("reports", exist_ok=True)

    if export_json:
        json_path = f"reports/{safe_name}_analysis.json"
        with open(json_path, "w") as f:
            json.dump(result, f, indent=2)
        console.print(f"  [dim]JSON → {json_path}[/dim]")

    if export_pdf:
        try:
            pdf_path = f"reports/{safe_name}_report.pdf"
            generate_pdf(analysis, roadmap, pdf_path)
            console.print(f"  [dim]PDF  → {pdf_path}[/dim]")
        except Exception as e:
            console.print(f"  [red]PDF failed: {e}[/red]")

    return result


def print_summary(results: list[dict]):
    console.print()
    console.rule("[bold cyan]Batch Summary[/bold cyan]")
    t = Table(box=box.SIMPLE_HEAVY, padding=(0, 1))
    t.add_column("Company",    style="bold", max_width=30)
    t.add_column("Industry",   max_width=20)
    t.add_column("Score",      justify="right")
    t.add_column("Spend",      justify="right")
    t.add_column("Wasted",     justify="right")
    t.add_column("Overlaps",   justify="right")
    t.add_column("Gaps",       justify="right")

    for r in results:
        s = r["scores"]["overall"]
        color = "green" if s >= 75 else ("yellow" if s >= 50 else "red")
        t.add_row(
            r["company"],
            r["industry"].split("/")[0].strip(),
            f"[{color}]{s}[/{color}]",
            f"${r['financials']['total_spend_k']}K",
            f"[red]${r['financials']['wasted_spend_k']}K[/red]" if r['financials']['wasted_spend_k'] else "[green]$0[/green]",
            str(r["overlaps"]),
            str(r["gaps"]),
        )
    console.print(t)

    total_wasted = sum(r["financials"]["wasted_spend_k"] for r in results)
    total_recoverable = sum(r["financials"]["recoverable_spend_k"] for r in results)
    avg_score = round(sum(r["scores"]["overall"] for r in results) / len(results))
    console.print(f"\n  Profiles analysed : [bold]{len(results)}[/bold]")
    console.print(f"  Avg overall score : [bold]{avg_score}/100[/bold]")
    console.print(f"  Total wasted spend: [red bold]${total_wasted}K[/red bold]")
    console.print(f"  Total recoverable : [green bold]${total_recoverable}K[/green bold]")
    console.print()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate synthetic company data and run the Shieldient stack agent."
    )
    parser.add_argument(
        "--count", type=int, default=5,
        help="Number of random profiles to generate (default: 5)",
    )
    parser.add_argument(
        "--seed", type=int, default=None,
        help="Random seed for reproducible output",
    )
    parser.add_argument(
        "--no-pdf", action="store_true",
        help="Skip PDF export (faster)",
    )
    parser.add_argument(
        "--no-json", action="store_true",
        help="Skip JSON export",
    )
    parser.add_argument(
        "--profile", type=str, default=None,
        choices=list(NAMED_SCENARIOS.keys()),
        help=f"Run a single named scenario instead of random profiles. Options: {', '.join(NAMED_SCENARIOS.keys())}",
    )
    parser.add_argument(
        "--all-scenarios", action="store_true",
        help="Run all named scenarios (ignores --count)",
    )
    args = parser.parse_args()

    console.print()
    console.print(Panel.fit(
        "[bold white]Shieldient Stack Agent — Data Generator[/bold white]\n"
        "[dim]Creates synthetic company profiles and runs full analysis pipeline[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))

    export_pdf = not args.no_pdf
    export_json = not args.no_json

    # Determine which profiles to run
    if args.profile:
        profiles = [NAMED_SCENARIOS[args.profile]]
        console.print(f"\n[dim]Running named scenario: [bold]{args.profile}[/bold][/dim]")
    elif args.all_scenarios:
        profiles = list(NAMED_SCENARIOS.values())
        console.print(f"\n[dim]Running all {len(profiles)} named scenarios[/dim]")
    else:
        rng = random.Random(args.seed)
        profiles = [generate_random_profile(rng, i) for i in range(args.count)]
        seed_str = f"seed={args.seed}" if args.seed is not None else "random"
        console.print(f"\n[dim]Generating {args.count} random profiles ({seed_str})[/dim]")

    results = []
    for profile in profiles:
        result = run_profile(profile, export_pdf=export_pdf, export_json=export_json)
        results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()
