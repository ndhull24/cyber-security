"""
CLI entry point.
Run:  python main.py
"""

from __future__ import annotations
import sys
import os

# Make sure the project root is on the path regardless of cwd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.rule import Rule
from rich import box
from rich.text import Text

from data.tool_catalog import (
    TOOL_CATALOG,
    COMPLIANCE_DOMAIN_WEIGHTS,
    DOMAIN_DISPLAY,
)
from agent.scoring import analyze_stack, generate_roadmap
from agent.llm import generate_narrative
from agent.report import generate_pdf

console = Console()

INDUSTRIES = [
    "Financial Services / Insurance",
    "Healthcare / Life Sciences",
    "Manufacturing / OT",
    "Retail / E-Commerce",
    "Technology / SaaS",
    "Government / Public Sector",
    "Energy / Utilities",
]

SIZES = [
    "1–50 employees (Startup)",
    "50–500 employees (SMB)",
    "500–2,000 employees (Mid-market)",
    "2,000+ employees (Enterprise)",
]

BUDGETS = {
    "Under $100K":    100,
    "$100K – $500K":  500,
    "$500K – $1M":   1000,
    "$1M+":          2000,
}


def print_banner():
    console.print()
    console.print(Panel.fit(
        "[bold white]Cybersecurity Vendor Stack Rationalization Agent[/bold white]\n"
        "[dim]Powered by Shieldient · Built with Claude[/dim]",
        border_style="cyan",
        padding=(1, 4),
    ))
    console.print()


def gather_inputs() -> dict:
    """Interactive questionnaire — returns raw user choices."""
    console.print("[bold]Step 1 of 3[/bold] — Company context\n", style="dim")

    industry = questionary.select(
        "Industry vertical:",
        choices=INDUSTRIES,
    ).ask()

    size = questionary.select(
        "Company size:",
        choices=SIZES,
    ).ask()

    compliance = questionary.select(
        "Primary compliance framework:",
        choices=list(COMPLIANCE_DOMAIN_WEIGHTS.keys()),
    ).ask()

    budget_label = questionary.select(
        "Annual security budget:",
        choices=list(BUDGETS.keys()),
    ).ask()

    console.print()
    console.print("[bold]Step 2 of 3[/bold] — Current vendor stack\n", style="dim")
    console.print("[dim]Use SPACE to select tools, ENTER when done.[/dim]\n")

    # Group tools by category for readability
    categories: dict[str, list] = {}
    for tool in TOOL_CATALOG:
        categories.setdefault(tool.category, []).append(tool)

    choices = []
    for cat, tools in categories.items():
        choices.append(questionary.Separator(f"── {cat} ──"))
        for t in tools:
            choices.append(
                questionary.Choice(
                    title=f"{t.name:40s}  ~${t.annual_cost_k}K/yr",
                    value=t.id,
                )
            )

    selected_ids = questionary.checkbox(
        "Select all currently deployed tools:",
        choices=choices,
    ).ask()

    if not selected_ids:
        console.print("[red]No tools selected. Exiting.[/red]")
        sys.exit(0)

    return {
        "industry": industry,
        "size": size,
        "compliance": compliance,
        "budget_k": BUDGETS[budget_label],
        "selected_ids": selected_ids,
    }


def display_results(analysis, roadmap):
    """Render analysis results to the terminal using Rich."""
    console.print()
    console.rule("[bold cyan]Analysis Results[/bold cyan]")
    console.print()

    # ── Score summary ─────────────────────────────────────────────────────
    score_table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    score_table.add_column("Metric", style="dim")
    score_table.add_column("Score", justify="right")
    score_table.add_column("Bar", no_wrap=True)

    def score_bar(score: int, width: int = 30) -> Text:
        filled = round(score / 100 * width)
        color = "green" if score >= 75 else ("yellow" if score >= 50 else "red")
        bar = Text()
        bar.append("█" * filled, style=color)
        bar.append("░" * (width - filled), style="dim")
        return bar

    score_table.add_row("Overall Stack Score",       f"[bold]{analysis.overall_score}/100[/bold]",    score_bar(analysis.overall_score))
    score_table.add_row("Stack Efficiency",           f"{analysis.efficiency_score}/100",              score_bar(analysis.efficiency_score))
    score_table.add_row("Coverage Completeness",      f"{analysis.coverage_score}/100",                score_bar(analysis.coverage_score))
    score_table.add_row("Compliance Alignment",       f"{analysis.compliance_score}/100",              score_bar(analysis.compliance_score))
    console.print(score_table)

    # ── Financial summary ─────────────────────────────────────────────────
    fin_table = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 2))
    fin_table.add_column("", style="dim")
    fin_table.add_column("", justify="right", style="bold")
    fin_table.add_row("Tools deployed",           str(len(analysis.selected_tools)))
    fin_table.add_row("Estimated annual spend",   f"${analysis.total_spend_k}K")
    fin_table.add_row("Redundant spend (overlaps)", f"[red]${analysis.wasted_spend_k}K[/red]")
    fin_table.add_row("Conservatively recoverable", f"[green]${analysis.recoverable_spend_k}K[/green]")
    fin_table.add_row("Budget utilization",        f"{analysis.budget_utilization_pct}%")
    console.print(fin_table)
    console.print()

    # ── Overlaps ──────────────────────────────────────────────────────────
    if analysis.overlap_pairs:
        console.print(Rule("[yellow]Functional Overlaps[/yellow]"))
        for pair in analysis.overlap_pairs:
            console.print(f"  [yellow]⚠[/yellow]  [bold]{pair.tool_a.name}[/bold] + [bold]{pair.tool_b.name}[/bold]")
            shared = ", ".join(DOMAIN_DISPLAY[d] for d in pair.shared_domains)
            console.print(f"     Shared: {shared}")
            console.print(f"     Redundant spend: [red]~${pair.estimated_wasted_cost_k}K/yr[/red]")
            console.print()
    else:
        console.print("[green]✓ No functional overlaps detected.[/green]\n")

    # ── Coverage gaps ─────────────────────────────────────────────────────
    if analysis.coverage_gaps:
        console.print(Rule("[red]Coverage Gaps[/red]"))
        for gap in analysis.coverage_gaps:
            risk = "[bold red]HIGH[/bold red]" if gap.compliance_weight >= 2 else (
                "[yellow]MEDIUM[/yellow]" if gap.compliance_weight == 1 else "[dim]LOW[/dim]"
            )
            recs = ", ".join(gap.recommended_tools[:2]) if gap.recommended_tools else "—"
            console.print(f"  [red]✗[/red]  [bold]{DOMAIN_DISPLAY[gap.domain]}[/bold]  {risk}")
            console.print(f"     Suggested: [dim]{recs}[/dim]")
            console.print()
    else:
        console.print("[green]✓ All coverage domains addressed.[/green]\n")

    # ── Narrative ─────────────────────────────────────────────────────────
    if analysis.narrative:
        console.print(Rule("[cyan]Executive Summary[/cyan]"))
        console.print(Panel(analysis.narrative, border_style="dim", padding=(1, 2)))
        console.print()

    # ── Roadmap ───────────────────────────────────────────────────────────
    if roadmap:
        console.print(Rule("[cyan]Consolidation Roadmap[/cyan]"))
        for step in roadmap:
            effort_color = {"Low": "green", "Medium": "yellow", "High": "red"}.get(step.effort, "white")
            savings = f"  [green]Saves ${step.estimated_savings_k}K/yr[/green]" if step.estimated_savings_k else ""
            console.print(f"  [bold cyan]{step.priority}.[/bold cyan]  [bold]{step.action}[/bold]")
            console.print(f"     [dim]{step.rationale}[/dim]")
            console.print(f"     Effort: [{effort_color}]{step.effort}[/{effort_color}]{savings}")
            console.print()


def main():
    print_banner()

    inputs = gather_inputs()

    console.print()
    console.print("[bold]Step 3 of 3[/bold] — Running analysis\n", style="dim")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        t1 = progress.add_task("Scoring stack...", total=None)
        analysis = analyze_stack(**inputs)
        progress.remove_task(t1)

        t2 = progress.add_task("Generating roadmap...", total=None)
        roadmap = generate_roadmap(analysis)
        progress.remove_task(t2)

        t3 = progress.add_task("Generating executive narrative (Claude API)...", total=None)
        analysis.narrative = generate_narrative(analysis)
        progress.remove_task(t3)

    display_results(analysis, roadmap)

    # ── PDF export prompt ─────────────────────────────────────────────────
    export = questionary.confirm("Export full report to PDF?", default=True).ask()
    if export:
        output_path = f"reports/stack_report_{analysis.compliance.replace(' ', '_').replace('-', '')}_{len(analysis.selected_tools)}tools.pdf"
        with Progress(SpinnerColumn(), TextColumn("{task.description}"), transient=True) as progress:
            progress.add_task("Generating PDF...", total=None)
            try:
                path = generate_pdf(analysis, roadmap, output_path)
                console.print(f"\n[green]✓ Report saved:[/green] [bold]{path}[/bold]\n")
            except ImportError as e:
                console.print(f"[red]PDF generation failed:[/red] {e}\n")

    console.print("[dim]Analysis complete. Powered by Shieldient.[/dim]\n")


if __name__ == "__main__":
    main()
