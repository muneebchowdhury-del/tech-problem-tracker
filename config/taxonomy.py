"""
Single source of truth for the categorization taxonomy.
Keep this in sync with the category list baked into docs/index.html
if you ever change it.
"""

CATEGORIES = [
    "Data Migration & Quality",
    "Integration & API Compatibility",
    "Budget & Timeline",
    "Change Management & Adoption",
    "Skills Gap",
    "Vendor Lock-in",
    "Business Continuity & Downtime",
    "Security & Compliance",
    "Governance & Scope",
]

SEVERITIES = ["critical", "high", "medium"]

SIZES = ["Enterprise", "Mid-market", "SMB / Startup", "Government", "Unspecified"]

TECHS = [
    "SAP",
    "AWS",
    "Azure",
    "GCP",
    "Hyperscalers",
    "Multi-cloud",
    "Legacy",
    "General",
]
