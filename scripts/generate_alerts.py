#!/usr/bin/env python3
"""
Generate CLI alerts from processed EBA regulatory updates.
Supports different audiences: workfloor, management, C-level.
Uses Ollama (Mistral-7B) for LLM-powered summaries and insights.
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

# LLM Prompts for Ollama
LLM_PROMPTS = {
    "summary": """
    You are a regulatory compliance assistant. Summarize the following regulatory text in 2-3 clear sentences. 
    Focus on the key requirements, changes, or obligations. 
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Summary:
    """,
    "key_takeaways": """
    You are a technical compliance expert. Extract 3-5 actionable key takeaways from the following regulatory text. 
    Focus on technical implementation, controls, and documentation requirements. 
    Use bullet points (-) for each takeaway.
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Key Takeaways:
    """,
    "business_impact": """
    You are a business analyst. Analyze the business impact of the following regulatory text. 
    Focus on operational, financial, and reputational risks. 
    Use bullet points (-) for each impact point.
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Business Impact:
    """,
    "strategic_implications": """
    You are a strategic advisor. Identify the strategic implications of the following regulatory text. 
    Focus on long-term business strategy, competitive positioning, and industry trends. 
    Use bullet points (-) for each implication.
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Strategic Implications:
    """,
    "executive_summary": """
    You are a C-level executive. Provide a concise executive summary (2-3 sentences) of the following regulatory text. 
    Focus on high-level impact, urgency, and strategic importance. 
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Executive Summary:
    """,
    "long_term_outlook": """
    You are a futurist. Provide a long-term outlook (1-2 sentences) based on the following regulatory text. 
    Focus on future trends, opportunities, and risks. 
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Long-Term Outlook:
    """,
    "risk_assessment": """
    You are a risk management expert. Assess the risk level of the following regulatory text. 
    Provide a risk level (Critical/High/Medium/Low), likelihood (High/Medium/Low), and impact (Severe/Significant/Moderate/Minor). 
    Respond in Dutch if the input is in Dutch, otherwise in English.
    
    Text: {text}
    
    Risk Assessment:
    - Risk Level: 
    - Likelihood: 
    - Impact: 
    """,
}


def get_ollama_response(prompt: str, model: str = "mistral", max_length: int = 2000) -> str:
    """
    Get a response from Ollama's LLM (Mistral-7B by default).
    Returns the generated text or a fallback message if Ollama is not available.
    """
    try:
        import ollama
        response = ollama.generate(
            model=model,
            prompt=prompt,
            options={"temperature": 0.3, "max_tokens": max_length},
        )
        return response["response"].strip()
    except ImportError:
        print("⚠️ Ollama is not installed. Install with: pip install ollama")
        return "[LLM summary not available: Ollama not installed]"
    except Exception as e:
        print(f"⚠️ Error generating LLM response: {e}")
        return f"[LLM summary not available: {str(e)}]"


def get_db_connection() -> sqlite3.Connection:
    """Get a connection to the SQLite database."""
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}. Run process_updates.py first.")
        exit(1)
    return sqlite3.connect(DB_PATH)


def generate_llm_summary(text: str) -> str:
    """Generate a summary using Ollama."""
    if not text or len(text) < 50:
        return "No sufficient text available for summary."
    prompt = LLM_PROMPTS["summary"].format(text=text[:4000])  # Limit input length
    return get_ollama_response(prompt)


def generate_llm_key_takeaways(text: str) -> str:
    """Generate key takeaways using Ollama."""
    if not text or len(text) < 50:
        return "- No sufficient text available for key takeaways."
    prompt = LLM_PROMPTS["key_takeaways"].format(text=text[:4000])
    return get_ollama_response(prompt)


def generate_llm_business_impact(text: str) -> str:
    """Generate business impact using Ollama."""
    if not text or len(text) < 50:
        return "- No sufficient text available for business impact analysis."
    prompt = LLM_PROMPTS["business_impact"].format(text=text[:4000])
    return get_ollama_response(prompt)


def generate_llm_strategic_implications(text: str) -> str:
    """Generate strategic implications using Ollama."""
    if not text or len(text) < 50:
        return "- No sufficient text available for strategic implications."
    prompt = LLM_PROMPTS["strategic_implications"].format(text=text[:4000])
    return get_ollama_response(prompt)


def generate_llm_executive_summary(text: str) -> str:
    """Generate executive summary using Ollama."""
    if not text or len(text) < 50:
        return "No sufficient text available for executive summary."
    prompt = LLM_PROMPTS["executive_summary"].format(text=text[:4000])
    return get_ollama_response(prompt)


def generate_llm_long_term_outlook(text: str) -> str:
    """Generate long-term outlook using Ollama."""
    if not text or len(text) < 50:
        return "No sufficient text available for long-term outlook."
    prompt = LLM_PROMPTS["long_term_outlook"].format(text=text[:4000])
    return get_ollama_response(prompt)


def generate_llm_risk_assessment(text: str, urgency: str) -> str:
    """Generate risk assessment using Ollama."""
    if not text or len(text) < 50:
        return f"- **Risk Level**: {urgency}\n- **Likelihood**: Medium\n- **Impact**: Moderate"
    prompt = LLM_PROMPTS["risk_assessment"].format(text=text[:4000])
    return get_ollama_response(prompt)


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


def format_alert(update: Dict, audience: str, use_llm: bool = True) -> str:
    """Format an alert for the specified audience."""
    template = AUDIENCE_TEMPLATES.get(audience, AUDIENCE_TEMPLATES["workfloor"])
    
    # Generate content based on audience
    if use_llm:
        if audience == "workfloor":
            summary = generate_llm_summary(update["raw_text"])
            key_takeaways = generate_llm_key_takeaways(update["raw_text"])
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
            business_impact = generate_llm_business_impact(update["raw_text"])
            risk_assessment = generate_llm_risk_assessment(update["raw_text"], update["urgency_level"])
            alert = template["format"].format(
                title=update["title"],
                date=update["publication_date"],
                risk_area=update["risk_area"],
                urgency=update["urgency_level"],
                business_impact=business_impact,
                risk_assessment=risk_assessment,
            )
        else:  # C-level
            executive_summary = generate_llm_executive_summary(update["raw_text"])
            strategic_implications = generate_llm_strategic_implications(update["raw_text"])
            long_term_outlook = generate_llm_long_term_outlook(update["raw_text"])
            alert = template["format"].format(
                title=update["title"],
                date=update["publication_date"],
                risk_area=update["risk_area"],
                urgency=update["urgency_level"],
                executive_summary=executive_summary,
                strategic_implications=strategic_implications,
                long_term_outlook=long_term_outlook,
            )
    else:
        # Fallback to simple summaries if LLM is not available
        summary = update["raw_text"][:200] + "..." if update["raw_text"] else "No summary available."
        if audience == "workfloor":
            key_takeaways = "- Review the full document for technical requirements.\n- Implement necessary controls."
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
            business_impact = "- Review business processes for compliance.\n- Allocate resources as needed."
            risk_assessment = f"- **Risk Level**: {update['urgency_level']}\n- **Likelihood**: Medium\n- **Impact**: Moderate"
            alert = template["format"].format(
                title=update["title"],
                date=update["publication_date"],
                risk_area=update["risk_area"],
                urgency=update["urgency_level"],
                business_impact=business_impact,
                risk_assessment=risk_assessment,
            )
        else:  # C-level
            executive_summary = f"This {update['risk_area']} update requires strategic attention."
            strategic_implications = "- Align with long-term business goals.\n- Monitor regulatory trends."
            long_term_outlook = "Stay ahead by engaging with industry working groups."
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
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM (Ollama) for summaries.")
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
    
    print(f"📢 Generating {len(updates)} alert(s) for {args.audience} audience...")
    
    # Check if Ollama is available
    use_llm = not args.no_llm
    if use_llm:
        try:
            import ollama
            print("✅ Using Ollama (Mistral-7B) for LLM-powered summaries.")
        except ImportError:
            use_llm = False
            print("⚠️ Ollama not installed. Using fallback summaries. Install with: pip install ollama")
    
    print("=" * 80)
    
    for i, update in enumerate(updates, 1):
        alert = format_alert(update, args.audience, use_llm)
        print(alert)
        print("\n" + "=" * 80 + "\n")
    
    conn.close()


if __name__ == "__main__":
    main()
