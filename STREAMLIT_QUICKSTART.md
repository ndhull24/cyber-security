# Streamlit App Quick Start Guide

Welcome to the **Shieldient Vendor Stack Rationalization** web interface!

---

## Getting Started

### 1. Install Dependencies (if not already done)

```bash
pip install -r requirements.txt
```

### 2. Launch the App

```bash
streamlit run streamlit_app.py
```

The app will open automatically at **http://localhost:8501**

---

## How to Use

### Step 1️⃣: Company Profile

Fill in your organization details:
- **Industry Vertical** — Select your sector (Finance, Healthcare, Tech, etc.)
- **Company Size** — Choose your headcount range
- **Compliance Framework** — Pick your primary regulatory requirement (SOX, HIPAA, PCI-DSS, NIST CSF, ISO 27001)
- **Annual Budget** — Enter your security tool budget

💡 **Why?** This context helps us tailor recommendations and prioritize compliance-critical gaps.

---

### Step 2️⃣: Tool Selection

Check all security tools your organization currently uses:

**Tools are grouped by category for easy browsing:**
- EDR / XDR (endpoint protection)
- SIEM (centralized log management)
- Network Security (firewalls)
- IAM (identity & access)
- Vulnerability Management
- Email Security
- Cloud Security

After selecting, you'll see:
- Total number of tools
- Annual spend
- Budget utilization percentage
- Number of vendors

👉 **Click "🔬 Analyze Stack"** to run the full analysis.

---

### Step 3️⃣: Analysis Results

You'll see four key metrics:

| Metric | What It Means |
|--------|---|
| **Overall Score** | Your stack's health (0-100) |
| **Efficiency Score** | How well you're avoiding redundancy |
| **Coverage Score** | How many security domains you cover |
| **Compliance Score** | Alignment with your regulatory framework |

**Charts visualize:**
- 📊 Score breakdown across the three dimensions
- 💰 Financial impact (annual spend, wasted spend, recoverable amount)

**Key findings:**
- 🔴 **Overlaps Detected** — Tools doing the same job (costly waste!)
- 🔍 **Coverage Gaps** — Security domains you're not covering
  - High priority (🔴) = Required by your compliance framework
  - Medium priority (🟡) = Important but not mandated
  - Low priority (🟢) = Can be handled by an MSSP

**Executive Summary** — AI-generated analysis of your stack (if API key is configured).

---

### Step 4️⃣: Consolidation Roadmap

A prioritized action plan to improve your stack:

**Priority 1** → Retire overlapping tools (fastest ROI)
**Priority 2** → Fill high-priority compliance gaps
**Priority 3** → Engage an MSSP for residual low-priority gaps

Each action shows:
- Implementation effort (Low / Medium / High)
- Potential savings ($K per year)
- Business rationale

💡 **Bottom line:** Following this roadmap can recover ~$XXK annually and improve your stack score.

---

### Step 5️⃣: Detailed Insights

Deep-dive data for stakeholders:

**Tool Inventory** — Table of all selected tools with cost and coverage
**Domain Coverage Matrix** — Which tools cover which security domains
**Compliance Alignment** — Your framework's requirements vs. actual coverage
**Key Metrics** — Summary statistics

---

## Tips

✅ **Do:**
- Select **all** tools you currently use (including cheap ones)
- Be honest about budget — this helps us assess spend efficiency
- Export the PDF report for stakeholder meetings

❌ **Don't:**
- Mix test tools with production tools
- Change selections mid-analysis without re-running
- Use outdated tool lists

---

## Sharing Your Results

### Export Options

**For executives:**
1. Screenshot the "Analysis Results" tab
2. Share the "Executive Summary" text

**For technical teams:**
1. Share the "Detailed Insights" tab
2. Use the Tool Inventory table to align purchasing

**For CFO:**
1. Share the "Financial Impact" visualization
2. Reference the "Recoverable Spend" metric

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| App won't start | `pip install streamlit plotly pandas` |
| Analysis is slow | Normal for first run (loading AI model) |
| No tools appear | Scroll down in the tool category sections |
| Charts aren't showing | Try refreshing the browser (F5) |
| "API not available" warning | That's OK — the app still works without Anthropic key |

---

## Next Steps

### Export to PDF (CLI)

Want a professional PDF report? Run:

```bash
python generate_data.py --count 1
```

This generates sample reports in `reports/` (great for templates).

### Integrate Into Your Workflow

- **Weekly sync:** Re-run when tools change
- **Budget planning:** Use the "Financial Impact" section
- **Vendor reviews:** Reference the "Consolidation Roadmap"

### Get Help

- 📧 Contact: explore@shieldient.com
- 🌐 Visit: https://shieldient.com
- 📞 Phone: +1 213-753-1933

---

## Design & Branding

This app uses **Shieldient's official brand colors:**
- Primary: **#1D9E75** (Teal/Green)
- Dark: **#0F172A** (Navy)
- Accent text: Professional cybersecurity styling

All metrics and explanations align with Shieldient's **AI-first, vendor-neutral** approach to cybersecurity.

---

**Enjoy analyzing your stack! 🛡️**
