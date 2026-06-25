# Cybersecurity Vendor Stack Rationalization Agent

**Built to demonstrate AI agent development for Shieldient** — an AI-first MSSP headquartered in Dallas, TX.

---

## What it does

Takes a company's current security tool stack as input and produces:

- **Overlap detection** — identifies redundant tools covering the same domains, with dollar-quantified wasted spend
- **Coverage gap analysis** — maps uncovered control domains against the selected compliance framework (SOX, HIPAA, PCI-DSS, NIST CSF, ISO 27001)
- **Scored report** — efficiency, coverage, and compliance scores (0–100)
- **AI executive narrative** — Claude generates a 200-word CISO-ready summary via the Anthropic API
- **Consolidation roadmap** — prioritized action plan: retire overlaps first, fill gaps second, engage MSSP for residual risk
- **PDF export** — professional report ready to share

No external data dependencies. All vendor knowledge (tool catalog, coverage domains, compliance weights) is embedded.

---

## Project structure

```
shieldient_agent/
├── main.py                  # CLI entry point
├── requirements.txt
├── .env.example
├── data/
│   └── tool_catalog.py      # Vendor catalog — 22 tools, 12 coverage domains
├── agent/
│   ├── scoring.py           # Core analysis engine (pure functions)
│   ├── llm.py               # Anthropic API call + fallback narrative
│   └── report.py            # PDF generation (fpdf2)
├── tests/
│   └── test_scoring.py      # 20 unit tests
└── reports/                 # PDF outputs land here
```

---

## Setup

### 1. Clone / open in VS Code

```bash
cd shieldient_agent
code .
```

### 2. Create a virtual environment

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Add your Anthropic API key (optional)

```bash
cp .env.example .env
# Edit .env and paste your key
```

The agent runs without a key — it falls back to a template-based narrative. With a key, Claude generates the executive summary.

---

## Run

### Option 1: Interactive CLI

```bash
python main.py
```

Follow the interactive prompts:
1. Select industry, company size, compliance framework, and budget
2. Choose currently deployed tools (SPACE to select, ENTER to confirm)
3. Review the terminal report
4. Optionally export to PDF

### Option 2: Web Interface (Streamlit)

```bash
streamlit run streamlit_app.py
```

This launches a modern web interface with:
- **Step-by-step wizard** — Company profile → Tool selection → Analysis → Roadmap
- **Interactive charts** — Score breakdown, financial impact visualizations
- **Real-time explanations** — Each step explains what you're seeing
- **Professional styling** — Shieldient brand colors (teal accent, dark theme)
- **Detailed insights** — Tool inventory, domain coverage matrix, compliance alignment

The Streamlit app is perfect for:
- Non-technical stakeholders wanting a visual walkthrough
- Exploring multiple "what-if" scenarios quickly
- Sharing results with executives via a web interface
- Integrating into internal dashboards

---

## Generate sample data

```bash
python generate_data.py                    # 5 random profiles (default)
python generate_data.py --count 10         # 10 profiles
python generate_data.py --seed 42          # reproducible output
python generate_data.py --profile fintech  # run one named scenario
python generate_data.py --all-scenarios    # run all 7 built-in scenarios
```

This generates JSON analysis files and PDF reports in `reports/`.

---

## Run tests

```bash
pytest tests/test_scoring.py -v
```

20 tests covering:
- Overlap detection and deduplication
- Coverage gap analysis
- Score calculation and bounds
- Budget utilization
- Compliance-specific scoring (SOX, PCI-DSS)
- Roadmap generation and prioritization

---

## Extending the agent

| What to change | Where |
|---|---|
| Add a new vendor tool | `data/tool_catalog.py` → `TOOL_CATALOG` list |
| Add a compliance framework | `data/tool_catalog.py` → `COMPLIANCE_DOMAIN_WEIGHTS` |
| Change the LLM prompt | `agent/llm.py` → `SYSTEM_PROMPT` |
| Modify scoring weights | `agent/scoring.py` → `analyze_stack()` |
| Change PDF layout | `agent/report.py` → `ReportPDF` class |

---

## Tech stack

| Layer | Library |
|---|---|
| CLI interaction | `questionary` |
| Terminal rendering | `rich` |
| Web interface | `streamlit`, `plotly` |
| Data handling | `pandas` |
| LLM narrative | `anthropic` (claude-sonnet-4-6) |
| PDF generation | `fpdf2` |
| Environment config | `python-dotenv` |
| Testing | `pytest` |
