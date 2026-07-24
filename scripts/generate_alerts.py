#!/usr/bin/env python3
"""
Generate CLI alerts from processed EBA regulatory updates.
Supports different audiences: workfloor, management, C-level.
"""

import os
import sqlite3
import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# Constants
DB_PATH = "data/processed/regulatory_updates.db"

# Audience-specific templates
AUDIENCE_TEMPLATES = {
    "workfloor": {
        "header": "🔧 WORKFLOOR ALERT: Technical Action Required",
        "format": """
📌 **Title**: {title}
📅 **Date**: {date}
🏷️ **Risk Area**: {risk_area}
⚠️ **Urgency**: {urgency}

📝 **Summary**:
{summary}

🔗 **Action Items**:
- Review the full update: {file_path}
- Implement technical controls as described.
- Document compliance measures.

💡 **Key Takeaways**:
{key_takeaways}
        """,
    },
    "management": {
        "header": "📊 MANAGEMENT ALERT: Compliance Update",
        "format": """
📌 **Title**: {title}
📅 **Date**: {date}
🏷️ **Risk Area**: {risk_area}
⚠️ **Urgency**: {urgency}

📈 **Business Impact**:
{business_impact}

🎯 **Strategic Actions**:
- Assign ownership for compliance.
- Allocate resources for implementation.
- Monitor deadlines and milestones.

📉 **Risk Assessment**:
{risk_assessment}
        """,
    },
    "c-level": {
        "header": "🚨 C-LEVEL ALERT: Regulatory Risk",
        "format": """
📌 **Title**: {title}
📅 **Date**: {date}
🏷️ **Risk Area**: {risk_area}
⚠️ **Urgency**: {urgency}

💼 **Executive Summary**:
{executive_summary}

🌍 **Strategic Implications**:
{strategic_implications}

📋 **Board-Level Actions**:
- Approve budget for compliance initiatives.
- Ensure alignment with corporate strategy.
- Communicate with regulators if needed.

🔮 **Long-Term Outlook**:
{long_term_outlook}
        """,
    },
}


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}. Run process_updates.py first.")
        exit(1)
    return sqlite3.connect(DB_PATH)


def generate_summary(text: str, max_length: int = 200) -> str:
    """Generate a short summary from the raw text."""
    if not text:
        return "No summary available."
    
    # Simple summary: first non-empty paragraph
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if paragraphs:
        summary = paragraphs[0][:max_length] + "..." if len(paragraphs[0]) > max_length else paragraphs[0]
        return summary
    
    return text[:max_length] + "..." if len(text) > max_length else text


def generate_key_takeaways(text: str, risk_area: str) -> str:
    """Generate key takeaways for workfloor audience."""
    # Placeholder: In a real implementation, use LLM (e.g., Mistral-7B via Ollama)
    takeaways = []
    
    if "cybersecurity" in risk_area.lower():
        takeaways.append("- Review cybersecurity controls and policies.")
        takeaways.append("- Update incident response procedures.")
    elif "ai" in risk_area.lower():
        takeaways.append("- Assess AI model compliance with new guidelines.")
        takeaways.append("- Document AI governance frameworks.")
    else:
        takeaways.append("- Review the full regulatory update for technical requirements.")
        takeaways.append("- Implement necessary controls and documentation.")
    
    return "\n".join(takeaways)


def generate_business_impact(text: str, risk_area: str) -> str:
    """Generate business impact for management audience."""
    # Placeholder: Replace with LLM-generated content
    impacts = []
    
    if "dora" in risk_area.lower() or "operational resilience" in risk_area.lower():
        impacts.append("- Potential impact on digital operational resilience.")
        impacts.append("- May require updates to ICT risk management frameworks.")
    elif "compliance" in risk_area.lower():
        impacts.append("- Non-compliance could result in fines or sanctions.")
        impacts.append("- May affect multiple business units.")
    else:
        impacts.append("- Review business processes for alignment with new regulations.")
        impacts.append("- Allocate budget for compliance activities.")
    
    return "\n".join(impacts)


def generate_risk_assessment(text: str, urgency: str) -> str:
    """Generate risk assessment for management audience."""
    if urgency == "Urgent":
        return "- **Risk Level**: Critical\n- **Likelihood**: High\n- **Impact**: Severe"
    elif urgency == "High":
        return "- **Risk Level**: High\n- **Likelihood**: Medium\n- **Impact**: Significant"
    else:
        return "- **Risk Level**: Medium\n- **Likelihood**: Low\n- **Impact**: Moderate"


def generate_executive_summary(text: str, risk_area: str) -> str:
    """Generate executive summary for C-level audience."""
    # Placeholder: Replace with LLM-generated content
    return f"This update from the EBA addresses {risk_area}. It requires strategic attention to ensure compliance and mitigate regulatory risk."


def generate_strategic_implications(text: str, risk_area: str) -> str:
    """Generate strategic implications for C-level audience."""
    implications = []
    
    if "ai" in risk_area.lower():
        implications.append("- May impact AI adoption strategy and innovation roadmap.")
        implications.append("- Consider partnerships with fintech firms for compliance.")
    elif "cybersecurity" in risk_area.lower():
        implications.append("- Strengthen cybersecurity posture to avoid reputational damage.")
        implications.append("- Invest in advanced threat detection and response.")
    else:
        implications.append("- Align regulatory compliance with long-term business goals.")
        implications.append("- Ensure competitive advantage through proactive compliance.")
    
    return "\n".join(implications)


def generate_long_term_outlook(text: str, risk_area: str) -> str:
    """Generate long-term outlook for C-level audience."""
    return f"The {risk_area} landscape is evolving. Stay ahead by monitoring EBA updates and engaging with industry working groups."


def get_updates_since_days(conn: sqlite3.Connection, days: int) -> List[Dict]:
    """Get updates from the database published in the last N days."""
    cursor = conn.cursor()
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT id, title, publication_date, risk_area, urgency_level, raw_text, file_path
        FROM updates
        WHERE publication_date >= ? AND is_processed = 1
        ORDER BY publication_date DESC
    """, (cutoff_date,))
    
    columns = [col[0] for col in cursor.description]
    updates = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    return updates


def format_alert(update: Dict, audience: str) -> str:
    """Format an alert for the specified audience."""
    template = AUDIENCE_TEMPLATES.get(audience, AUDIENCE_TEMPLATES["workfloor"])
    
    # Generate audience-specific content
    summary = generate_summary(update["raw_text"])
    
    if audience == "workfloor":
        key_takeaways = generate_key_takeaways(update["raw_text"], update["risk_area"])
        alert = template["format"].format(
            title=update["title"],
            date=update["publication_date"],
            risk_area=update["risk_area"],
            urgency=update["urgency_level"],
            summary=summary,
            file_path=update["file_path"],
            key_takeaways=key_takeaways,
        )
    elif audience == "management":
        business_impact = generate_business_impact(update["raw_text"], update["risk_area"])
        risk_assessment = generate_risk_assessment(update["raw_text"], update["urgency_level"])
        alert = template["format"].format(
            title=update["title"],
            date=update["publication_date"],
            risk_area=update["risk_area"],
            urgency=update["urgency_level"],
            business_impact=business_impact,
            risk_assessment=risk_assessment,
        )
    else:  # C-level
        executive_summary = generate_executive_summary(update["raw_text"], update["risk_area"])
        strategic_implications = generate_strategic_implications(update["raw_text"], update["risk_area"])
        long_term_outlook = generate_long_term_outlook(update["raw_text"], update["risk_area"])
        alert = template["format"].format(
            title=update["title"],
            date=update["publication_date"],
            risk_area=update["risk_area"],
            urgency=update["urgency_level"],
            executive_summary=executive_summary,
            strategic_implications=strategic_implications,
            long_term_outlook=long_term_outlook,
        )
    
    return f"{template['header']}\n\n{alert}"


def main():
    parser = argparse.ArgumentParser(description="Generate CLI alerts from EBA regulatory updates.")
    parser.add_argument("--days", type=int, default=7, help="Look for updates in the last N days (default: 7).")
    parser.add_argument("--audience", type=str, choices=["workfloor", "management", "c-level"], 
                        default="workfloor", help="Target audience for the alerts (default: workfloor).")
    parser.add_argument("--all", action="store_true", help="Show all updates (ignore --days).")
    parser.add_argument("--urgent-only", action="store_true", help="Only show urgent/high urgency updates.")
    args = parser.parse_args()
    
    conn = get_db_connection()
    
    if args.all:
        updates = get_updates_since_days(conn, 365 * 10)  # 10 years
    else:
        updates = get_updates_since_days(conn, args.days)
    
    if args.urgent_only:
        updates = [u for u in updates if u["urgency_level"] in ["Urgent", "High"]]
    
    if not updates:
        print(f"❌ No updates found in the last {args.days} days.")
        return
    
    print(f"📢 Generating {len(updates)} alert(s) for {args.audience} audience...\n")
    print("=" * 80)
    
    for i, update in enumerate(updates, 1):
        alert = format_alert(update, args.audience)
        print(alert)
        print("\n" + "=" * 80 + "\n")
    
    conn.close()


if __name__ == "__main__":
    main()
