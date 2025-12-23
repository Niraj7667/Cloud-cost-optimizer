import json
import os
from llm_utils import query_llama_with_validation

# Stage 3: Cost Analysis
# Analyzes billing data and generates recommendations via LLM

def analyze_costs_and_generate_recommendations(profile, billing):
    """
    Main function to analyze costs and get 8-10 recommendations.
    """
    
    # 1. Handle SQLite (Runs on Compute, so remove DB costs)
    tech_stack = profile.get("tech_stack", {}) or {}
    db_name = str(tech_stack.get("database", "")).lower()
    is_sqlite = "sqlite" in db_name
    
    if is_sqlite:
        db_cost = sum(r["cost_inr"] for r in billing if r["service"] == "Database")
        billing = [r for r in billing if r["service"] != "Database"]
        
        # Add that cost back to Compute (since SQLite uses the VM's resources)
        compute_recs = [r for r in billing if r["service"] == "Compute"]
        if compute_recs and db_cost > 0:
            avg_add = db_cost / len(compute_recs)
            for r in compute_recs: r["cost_inr"] += avg_add

    # 2. Financials
    total_cost = sum(r.get("cost_inr", 0) for r in billing)
    months = len({r["month"] for r in billing}) or 1
    avg_monthly = total_cost / months
    
    # Service Breakdown
    services = {}
    for r in billing:
        svc = r.get("service", "Unknown")
        services[svc] = services.get(svc, 0) + r.get("cost_inr", 0)
    avg_breakdown = {k: v/months for k, v in services.items()}

    budget = profile.get("budget_inr_per_month", 0)
    variance = avg_monthly - budget

    # 3. LLM Generation
    prompt = _get_analysis_prompt(profile, avg_monthly, budget, avg_breakdown, tech_stack)
    
    def validate(recs):
        if not isinstance(recs, list) or len(recs) < 5: return False, "Need 5+ items"
        required = ["title", "service", "current_cost", "potential_savings"]
        for i, r in enumerate(recs):
            if not all(k in r for k in required): return False, f"Missing fields at index {i}"
            # Logic check: No DB recs for SQLite projects
            if is_sqlite and r.get("service") == "Database": return False, "No DB recs for SQLite"
        return True, None

    print("Generating recommendations...")
    raw_recs = query_llama_with_validation(prompt, validate, max_retries=3) or []

    # 4. Post-Process (Filter & Fill Gaps)
    final_recs = _process_recs(raw_recs, profile, is_sqlite, avg_monthly)

    # 5. Final Calculations
    total_save = sum(r["potential_savings"] for r in final_recs)
    save_pct = (total_save / avg_monthly * 100) if avg_monthly else 0
    
    # Cap overly optimistic savings at 35%
    if save_pct > 35:
        scale = 35 / save_pct
        for r in final_recs: r["potential_savings"] = int(r["potential_savings"] * scale)
        save_pct = 35.0

    # Identifies high cost services (Top 3)
    sorted_services = sorted(avg_breakdown.items(), key=lambda x: x[1], reverse=True)[:3]
    high_cost_services = {k: round(v, 2) for k, v in sorted_services}

    return {
        "project_name": profile.get("name"),
        "analysis": {
            "total_monthly_cost": round(avg_monthly, 2),
            "budget": budget,
            "budget_variance": round(variance, 2),
            "service_costs": {k: round(v, 2) for k, v in avg_breakdown.items()},
            "high_cost_services": high_cost_services,
            "is_over_budget": variance > 0
        },
        "recommendations": final_recs
    }

def _process_recs(recs, profile, is_sqlite, total_cost):
    """Clean up recommendations and ensure we have at least 8."""
    cleaned = []
    seen = set()
    
    for r in recs:
        # Basic cleanup
        r["current_cost"] = int(r.get("current_cost", 0))
        r["potential_savings"] = int(r.get("potential_savings", 0))
        if "description" not in r: r["description"] = f"Optimization for {r.get('service')}."
        
        # Filter logic
        title = r.get("title", "").strip()
        if not title: continue
        
        key = title[:15].lower()
        if key in seen: continue
        
        # Banned list
        if "transfer acceleration" in title.lower(): continue
        if is_sqlite and r.get("service") == "Database": continue
        
        # Value check (keep positive savings OR governance items)
        is_gov = "governance" in r.get("recommendation_type", "").lower()
        if r["potential_savings"] > 0 or is_gov:
            cleaned.append(r)
            seen.add(key)
            
    recs = sorted(cleaned, key=lambda x: x["potential_savings"], reverse=True)

    # Ensure minimum number of recommendations
    if len(recs) < 6:
        print(f"Only found {len(recs)} items. Adding defaults to meet report requirements.")
        # Compact list of safe defaults
        defaults = [
            {"title": "Configure Cloud Budget Alerts", "service": "Governance", "potential_savings": 0, "recommendation_type": "Governance", "cloud_providers": ["AWS", "GCP"], "description": "Set strict budget thresholds.", "steps": ["Create budget", "Set alert @ 80%"], "risk_level": "Low", "implementation_effort": "Low"},
            {"title": "Enable Resource Tagging", "service": "Governance", "potential_savings": 0, "recommendation_type": "Governance", "cloud_providers": ["AWS", "Azure"], "description": "Tag resources by project.", "steps": ["Define tags", "Apply policy"], "risk_level": "Low", "implementation_effort": "Low"},
            {"title": "Enable MFA", "service": "Security", "potential_savings": 0, "recommendation_type": "Security", "cloud_providers": ["AWS"], "description": "Secure root account.", "steps": ["Turn on MFA"], "risk_level": "Low", "implementation_effort": "Low"},
            {"title": "Release Unused IPs", "service": "Networking", "potential_savings": 200, "recommendation_type": "Cleanup", "cloud_providers": ["AWS"], "description": "Release unattached Elastic IPs.", "steps": ["Find IPs", "Release"], "risk_level": "Low", "implementation_effort": "Low"},
            {"title": "Delete Unattached EBS", "service": "Storage", "potential_savings": 500, "recommendation_type": "Cleanup", "cloud_providers": ["AWS"], "description": "Delete orphaned volumes.", "steps": ["Scan volumes", "Delete"], "risk_level": "Low", "implementation_effort": "Low"},
            {"title": "Lease Privilege IAM", "service": "Security", "potential_savings": 0, "recommendation_type": "Security", "cloud_providers": ["AWS"], "description": "Audit permissions.", "steps": ["Review roles"], "risk_level": "Medium", "implementation_effort": "Medium"},
            {"title": "Data Retention Policy", "service": "Governance", "potential_savings": 0, "recommendation_type": "Governance", "cloud_providers": ["AWS"], "description": "Auto-delete old logs.", "steps": ["Set lifecycle"], "risk_level": "Low", "implementation_effort": "Low"}
        ]
        
        for d in defaults:
            if len(recs) >= 6: break
            key = d["title"][:15].lower()
            if key not in seen:
                recs.append(d)
                seen.add(key)
    
    return recs[:10]

def _get_analysis_prompt(profile, monthly_cost, budget, breakdown, stack):
    """Returns the complex LLM prompt."""
    reqs = ", ".join(profile.get("non_functional_requirements", []))
    variance = monthly_cost - budget
    status = "OVER" if variance > 0 else "UNDER"
    
    # Template Structure
    example = """
    [{
      "title": "Migrate MongoDB to Open-Source MongoDB",
      "service": "MongoDB",
      "current_cost": 900,
      "potential_savings": 450,
      "recommendation_type": "open_source",
      "description": "Migrate to open-source MongoDB, reducing costs and improving flexibility.",
      "implementation_effort": "medium",
      "risk_level": "medium",
      "steps": [
        "Assess MongoDB usage and determine if open-source is suitable",
        "Migrate to open-source MongoDB, ensuring data integrity",
        "Update application code to accommodate open-source MongoDB"
      ],
      "cloud_providers": [
        "AWS",
        "Azure",
        "GCP"
      ]
    }]
    """

    # Detect Cloud Provider
    stack_text = str(stack).lower()
    primary_cloud = "AWS" # Default
    if "azure" in stack_text: primary_cloud = "Azure"
    elif "gcp" in stack_text or "google" in stack_text: primary_cloud = "GCP"
    
    return f"""You are a cloud cost optimization expert. Analyze the billing data and generate 8-12 optimization candidates.
    
    Project: {profile.get('name')}
    Stack: {json.dumps(stack)}
    Reqs: {reqs}
    Primary Cloud: {primary_cloud}
    
    Cost Context:
    - Monthly: ₹{monthly_cost:,.0f}
    - Budget: ₹{budget:,.0f} ({status} by {abs(variance):,.0f})
    
    Breakdown: {json.dumps(breakdown, indent=2)}
    
    INSTRUCTIONS:
    1. Generate 8-12 items. Mix Technical, Governance, Security, and Cleanup.
    
    2. CLOUD CONTEXT:
       - For "Rightsizing", "Security", and "Cleanup", usage services native to {primary_cloud} (e.g., if AWS use CloudWatch/EC2; if Azure use Monitor/VMs).
       - For "Alternative Provider", you MUST suggest moving AWAY from {primary_cloud} (e.g. to DigitalOcean or Wasabi).
       
    3. MANDATORY MULTI-CLOUD STRATEGY:
       - For generic advice that applies everywhere, list ["AWS", "Azure", "GCP"].
       - You MUST include at least 2 specific "Alternative Provider" recommendations.
    
    3. Focus on:
       - Free Tier (if budget < 10k)
       - Open Source (if using paid Managed DBs)
       - Rightsizing (for general Compute)
       
    4. Fill gaps with Governance items (Tagging, Alerts) if needed.
    5. Anti-Patterns: No "Transfer Acceleration", No "SQLite DB Optimization".
    
    Output JSON list ONLY. Format:
    {example}
    """

def save_cost_report(report, filename="cost_optimization_report.json"):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Report saved to {filename}")

def display_report_summary(report):
    print("\n" + "="*50)
    print(f"REPORT: {report.get('project_name')}")
    print("="*50)
    
    analysis = report.get("analysis", {})
    total = analysis.get("total_monthly_cost", 0)
    budget = analysis.get("budget", 0)
    is_over = analysis.get("is_over_budget", False)
    
    print(f"Total: ₹{total:,.2f} (Budget: ₹{budget:,.0f})")
    print(f"Status: {'OVER BUDGET' if is_over else 'UNDER BUDGET'}")
    
    recs = report.get("recommendations", [])
    print(f"\nFound {len(recs)} Recommendations. Top 3:")
    
    for i, r in enumerate(recs[:3], 1):
        print(f"{i}. {r.get('title')} (Save: ₹{r.get('potential_savings', 0):,.0f})")

def display_full_recommendations(report):
    recs = report.get("recommendations", [])
    print("\n" + "="*50)
    print(f"RECOMMENDATIONS ({len(recs)})")
    print("="*50)
    
    for i, r in enumerate(recs, 1):
        print(f"\n{i}. {r.get('title')}")
        print(f"   Savings: ₹{r.get('potential_savings', 0):,.0f}")
        print(f"   Action: {r.get('description')}")

def run_cost_analysis():
    print("\n--- Running Stage 3 (Analysis) ---")
    if not os.path.exists("mock_billing.json"):
        print("Missing input files.")
        return None
        
    with open("project_profile.json", 'r') as f: profile = json.load(f)
    with open("mock_billing.json", 'r') as f: billing = json.load(f)
    
    report = analyze_costs_and_generate_recommendations(profile, billing)
    if report:
        save_cost_report(report)
        display_report_summary(report)
        return report
    return None
