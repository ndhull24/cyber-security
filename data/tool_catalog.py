"""
Vendor tool catalog.
Each tool entry defines coverage domains, estimated annual cost (USD thousands),
and which other tools it functionally overlaps with.
All data is public-knowledge — no external API needed.
"""

from dataclasses import dataclass, field
from typing import List

COVERAGE_DOMAINS = [
    "endpoint_protection",
    "threat_detection",
    "siem_log_management",
    "network_firewall",
    "identity_access",
    "mfa",
    "vulnerability_management",
    "email_security",
    "cloud_security",
    "ueba",
    "soar_automation",
    "data_loss_prevention",
]

DOMAIN_DISPLAY = {
    "endpoint_protection":      "Endpoint Protection",
    "threat_detection":         "Threat Detection & Response",
    "siem_log_management":      "SIEM / Log Management",
    "network_firewall":         "Network / Firewall",
    "identity_access":          "Identity & Access Management",
    "mfa":                      "Multi-Factor Authentication",
    "vulnerability_management": "Vulnerability Management",
    "email_security":           "Email Security",
    "cloud_security":           "Cloud Security",
    "ueba":                     "User & Entity Behavior Analytics",
    "soar_automation":          "SOAR / Automation",
    "data_loss_prevention":     "Data Loss Prevention",
}

COMPLIANCE_DOMAIN_WEIGHTS = {
    "SOX": {
        "siem_log_management":      3,
        "identity_access":          2,
        "mfa":                      2,
        "ueba":                     2,
        "vulnerability_management": 1,
        "endpoint_protection":      1,
    },
    "HIPAA": {
        "endpoint_protection":      3,
        "identity_access":          3,
        "mfa":                      2,
        "email_security":           2,
        "data_loss_prevention":     2,
        "vulnerability_management": 1,
    },
    "PCI-DSS": {
        "network_firewall":         3,
        "vulnerability_management": 3,
        "siem_log_management":      2,
        "identity_access":          2,
        "mfa":                      2,
        "endpoint_protection":      1,
    },
    "NIST CSF": {
        "endpoint_protection":      2,
        "siem_log_management":      2,
        "identity_access":          2,
        "vulnerability_management": 2,
        "network_firewall":         1,
        "threat_detection":         1,
        "soar_automation":          1,
    },
    "ISO 27001": {
        "siem_log_management":      2,
        "identity_access":          2,
        "vulnerability_management": 2,
        "data_loss_prevention":     2,
        "endpoint_protection":      1,
        "mfa":                      1,
        "email_security":           1,
    },
    "None": {},
}


@dataclass
class Tool:
    id: str
    name: str
    vendor: str
    category: str
    annual_cost_k: int                  # USD thousands per year (list price estimate)
    coverage: List[str]
    overlaps_with: List[str] = field(default_factory=list)
    notes: str = ""


TOOL_CATALOG: List[Tool] = [
    # ── EDR / XDR ────────────────────────────────────────────────────────
    Tool(
        id="crowdstrike",
        name="CrowdStrike Falcon",
        vendor="CrowdStrike",
        category="EDR / XDR",
        annual_cost_k=120,
        coverage=["endpoint_protection", "threat_detection", "ueba"],
        overlaps_with=["sentinelone", "defender_edr", "carbon_black"],
        notes="Industry-leading EDR; strong threat intelligence integration.",
    ),
    Tool(
        id="sentinelone",
        name="SentinelOne Singularity",
        vendor="SentinelOne",
        category="EDR / XDR",
        annual_cost_k=95,
        coverage=["endpoint_protection", "threat_detection", "ueba", "soar_automation"],
        overlaps_with=["crowdstrike", "defender_edr", "carbon_black"],
        notes="Autonomous AI-driven response; strong SOAR integration.",
    ),
    Tool(
        id="defender_edr",
        name="Microsoft Defender for Endpoint",
        vendor="Microsoft",
        category="EDR / XDR",
        annual_cost_k=45,
        coverage=["endpoint_protection", "threat_detection", "identity_access"],
        overlaps_with=["crowdstrike", "sentinelone", "carbon_black"],
        notes="Cost-effective if already in Microsoft ecosystem.",
    ),
    Tool(
        id="carbon_black",
        name="VMware Carbon Black",
        vendor="VMware",
        category="EDR / XDR",
        annual_cost_k=85,
        coverage=["endpoint_protection", "threat_detection"],
        overlaps_with=["crowdstrike", "sentinelone", "defender_edr"],
        notes="Strong in on-prem environments; legacy enterprise base.",
    ),

    # ── SIEM ─────────────────────────────────────────────────────────────
    Tool(
        id="splunk",
        name="Splunk Enterprise Security",
        vendor="Splunk",
        category="SIEM",
        annual_cost_k=220,
        coverage=["siem_log_management", "threat_detection", "soar_automation", "ueba"],
        overlaps_with=["sentinel_siem", "securonix", "exabeam"],
        notes="Market-leading SIEM; high licensing cost; strong ecosystem.",
    ),
    Tool(
        id="sentinel_siem",
        name="Microsoft Sentinel",
        vendor="Microsoft",
        category="SIEM",
        annual_cost_k=155,
        coverage=["siem_log_management", "threat_detection", "soar_automation"],
        overlaps_with=["splunk", "securonix", "exabeam"],
        notes="Cloud-native SIEM; cost-effective in Azure environments.",
    ),
    Tool(
        id="securonix",
        name="Securonix Unified Defense SIEM",
        vendor="Securonix",
        category="SIEM",
        annual_cost_k=185,
        coverage=["siem_log_management", "ueba", "threat_detection", "soar_automation"],
        overlaps_with=["splunk", "sentinel_siem", "exabeam"],
        notes="Shieldient's foundational SIEM partner; strong UEBA and MSSP capabilities.",
    ),
    Tool(
        id="exabeam",
        name="Exabeam Fusion SIEM",
        vendor="Exabeam",
        category="SIEM",
        annual_cost_k=160,
        coverage=["siem_log_management", "ueba", "threat_detection"],
        overlaps_with=["splunk", "sentinel_siem", "securonix"],
        notes="UEBA-first SIEM; strong insider threat detection.",
    ),

    # ── Network / Firewall ────────────────────────────────────────────────
    Tool(
        id="paloalto_ngfw",
        name="Palo Alto NGFW",
        vendor="Palo Alto Networks",
        category="Network Security",
        annual_cost_k=110,
        coverage=["network_firewall", "threat_detection", "cloud_security"],
        overlaps_with=["fortinet", "checkpoint"],
        notes="Gold standard NGFW; Prisma extends to cloud.",
    ),
    Tool(
        id="fortinet",
        name="Fortinet FortiGate",
        vendor="Fortinet",
        category="Network Security",
        annual_cost_k=80,
        coverage=["network_firewall", "threat_detection"],
        overlaps_with=["paloalto_ngfw", "checkpoint"],
        notes="Strong price-performance; broad SD-WAN integration.",
    ),
    Tool(
        id="checkpoint",
        name="Check Point NGFW",
        vendor="Check Point",
        category="Network Security",
        annual_cost_k=90,
        coverage=["network_firewall", "threat_detection", "cloud_security"],
        overlaps_with=["paloalto_ngfw", "fortinet"],
        notes="Strong in financial services; mature compliance reporting.",
    ),

    # ── IAM ──────────────────────────────────────────────────────────────
    Tool(
        id="okta",
        name="Okta Workforce Identity",
        vendor="Okta",
        category="IAM",
        annual_cost_k=75,
        coverage=["identity_access", "mfa"],
        overlaps_with=["azure_ad", "ping_identity"],
        notes="Best-of-breed SSO and MFA; dominant in mid-market.",
    ),
    Tool(
        id="azure_ad",
        name="Microsoft Entra ID (Azure AD)",
        vendor="Microsoft",
        category="IAM",
        annual_cost_k=35,
        coverage=["identity_access", "mfa"],
        overlaps_with=["okta", "ping_identity"],
        notes="Bundled with M365; cost-effective for Microsoft shops.",
    ),
    Tool(
        id="ping_identity",
        name="Ping Identity",
        vendor="Ping Identity",
        category="IAM",
        annual_cost_k=80,
        coverage=["identity_access", "mfa"],
        overlaps_with=["okta", "azure_ad"],
        notes="Strong in regulated industries; good hybrid support.",
    ),

    # ── Vulnerability Management ──────────────────────────────────────────
    Tool(
        id="tenable",
        name="Tenable.io",
        vendor="Tenable",
        category="Vulnerability Management",
        annual_cost_k=65,
        coverage=["vulnerability_management"],
        overlaps_with=["qualys", "rapid7"],
        notes="Market leader; strong cloud and OT scanning.",
    ),
    Tool(
        id="qualys",
        name="Qualys VMDR",
        vendor="Qualys",
        category="Vulnerability Management",
        annual_cost_k=58,
        coverage=["vulnerability_management", "cloud_security"],
        overlaps_with=["tenable", "rapid7"],
        notes="SaaS-native; strong compliance reporting built-in.",
    ),
    Tool(
        id="rapid7",
        name="Rapid7 InsightVM",
        vendor="Rapid7",
        category="Vulnerability Management",
        annual_cost_k=60,
        coverage=["vulnerability_management", "threat_detection"],
        overlaps_with=["tenable", "qualys"],
        notes="Integrates with Metasploit; strong pen-test correlation.",
    ),

    # ── Email Security ────────────────────────────────────────────────────
    Tool(
        id="proofpoint",
        name="Proofpoint Email Security",
        vendor="Proofpoint",
        category="Email Security",
        annual_cost_k=55,
        coverage=["email_security", "data_loss_prevention"],
        overlaps_with=["mimecast", "defender_email"],
        notes="Best-in-class threat protection and DLP for email.",
    ),
    Tool(
        id="mimecast",
        name="Mimecast Email Security",
        vendor="Mimecast",
        category="Email Security",
        annual_cost_k=48,
        coverage=["email_security"],
        overlaps_with=["proofpoint", "defender_email"],
        notes="Strong archiving and continuity capabilities.",
    ),
    Tool(
        id="defender_email",
        name="Microsoft Defender for Office 365",
        vendor="Microsoft",
        category="Email Security",
        annual_cost_k=30,
        coverage=["email_security"],
        overlaps_with=["proofpoint", "mimecast"],
        notes="Included in M365 E3/E5; sufficient for low-risk environments.",
    ),

    # ── Cloud Security ────────────────────────────────────────────────────
    Tool(
        id="prisma_cloud",
        name="Prisma Cloud (Palo Alto)",
        vendor="Palo Alto Networks",
        category="Cloud Security",
        annual_cost_k=130,
        coverage=["cloud_security", "vulnerability_management", "data_loss_prevention"],
        overlaps_with=["wiz", "defender_cloud"],
        notes="Comprehensive CNAPP; strong in multi-cloud environments.",
    ),
    Tool(
        id="wiz",
        name="Wiz Cloud Security",
        vendor="Wiz",
        category="Cloud Security",
        annual_cost_k=120,
        coverage=["cloud_security", "vulnerability_management"],
        overlaps_with=["prisma_cloud", "defender_cloud"],
        notes="Agentless scanning; rapid adoption in cloud-native orgs.",
    ),
    Tool(
        id="defender_cloud",
        name="Microsoft Defender for Cloud",
        vendor="Microsoft",
        category="Cloud Security",
        annual_cost_k=40,
        coverage=["cloud_security", "vulnerability_management"],
        overlaps_with=["prisma_cloud", "wiz"],
        notes="Bundled with Azure; good baseline for Azure-first shops.",
    ),
]

TOOL_MAP = {t.id: t for t in TOOL_CATALOG}
