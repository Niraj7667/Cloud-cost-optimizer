"""
Stage 2: Synthetic Billing Generation
Generates realistic billing records via LLM and enforces strict budget alignment.
"""

import json
import os
import random
from datetime import datetime
from dateutil.relativedelta import relativedelta
from llm_utils import query_llama_json

def get_recent_months(n=4):
    """Returns list of last n months (YYYY-MM)."""
    now = datetime.now().replace(day=1)
    return [(now - relativedelta(months=i)).strftime("%Y-%m") for i in reversed(range(n))]

def generate_mock_billing(profile):
    """
    Orchestrates billing generation: Prompts LLM -> Validates -> Normalizes Costs.
    """
    budget = profile.get("budget_inr_per_month", 5000)
    
    # 1. Setup Context
    tech_stack = profile.get("tech_stack", {})
    is_sqlite = "sqlite" in str(tech_stack.get("database", "")).lower()
    months = get_recent_months(4)
    
    # 2. Call LLM
    prompt = _get_billing_prompt(profile, budget, months, is_sqlite)
    print("Generating billing records...")
    
    # Validation: Ensure it returns a list
    raw_recs = query_llama_json(prompt, max_tokens=2500)
    
    # 3. Validate & Sanitize
    if not raw_recs or not isinstance(raw_recs, list):
        print("LLM error. Using fallback data.")
        return _generate_fallback(budget, months)

    valid_recs = []
    required = ["month", "service", "cost_inr"]
    
    for r in raw_recs:
        # Basic data repair
        if not all(k in r for k in required): continue
        r.setdefault("region", "ap-south-1")
        r.setdefault("usage_type", "Standard")
        r.setdefault("desc", f"{r['service']} usage")
        
        try:
            r["cost_inr"] = int(float(r["cost_inr"]))
            valid_recs.append(r)
        except: continue

    if not valid_recs:
        return _generate_fallback(budget, months)

    # 4. Budget Normalization
    # Scale costs to roughly match the budget
    records_by_month = {m: [] for m in months}
    for r in valid_recs:
        if r["month"] in records_by_month:
            records_by_month[r["month"]].append(r)

    final_records = []
    for month, recs in records_by_month.items():
        if not recs: continue
        
        current_total = sum(r["cost_inr"] for r in recs) or 1
        target = budget * random.uniform(0.97, 1.03)
        scale = target / current_total
        
        for r in recs:
            r["cost_inr"] = max(10, int(r["cost_inr"] * scale))
            final_records.append(r)
            
    # Return limited number of records
    return final_records[:20]

def _generate_fallback(budget, months):
    """Deterministic fallback data generation."""
    recs = []
    # Distribute budget: Compute 40%, DB 30%, Storage 15%, Net 10%, Monitor 5%
    for m in months:
        # 1. Compute
        recs.append({
            "month": m, "service": "Compute", "cost_inr": int(budget*0.4), 
            "desc": "App Server Fleet", "region": "ap-south-1",
            "resource_id": "i-app-prod-01", "usage_type": "On-Demand Linux", "unit": "hours", "usage_quantity": 720
        })
        # 2. Database
        recs.append({
            "month": m, "service": "Database", "cost_inr": int(budget*0.3), 
            "desc": "Primary DB Instance", "region": "ap-south-1",
            "resource_id": "db-prod-01", "usage_type": "RDS Standard", "unit": "hours", "usage_quantity": 720
        })
        # 3. Storage
        recs.append({
            "month": m, "service": "Storage", "cost_inr": int(budget*0.15), 
            "desc": "Object Storage", "region": "ap-south-1",
            "resource_id": "vol-data-01", "usage_type": "Standard Storage", "unit": "GB-Mo", "usage_quantity": 500
        })
        # 4. Networking
        recs.append({
            "month": m, "service": "Networking", "cost_inr": int(budget*0.1), 
            "desc": "Data Transfer", "region": "ap-south-1",
            "resource_id": "net-nat-01", "usage_type": "Data Transfer Out", "unit": "GB", "usage_quantity": 1000
        })
        # 5. Monitoring
        recs.append({
            "month": m, "service": "Monitoring", "cost_inr": int(budget*0.05), 
            "desc": "Cloud Watcher", "region": "ap-south-1",
            "resource_id": "mon-main-01", "usage_type": "Metrics", "unit": "Reqs", "usage_quantity": 1000000
        })
    return recs[:20]

def _get_billing_prompt(profile, budget, months, is_sqlite):
    """Constructs the prompt."""
    tech_str = json.dumps(profile.get("tech_stack", {}) or {})
    months_str = ", ".join(months)

    # Detect Cloud Provider
    stack_text = str(profile.get("tech_stack", {})).lower()
    primary_cloud = "AWS" # Default
    if "azure" in stack_text: primary_cloud = "Azure"
    elif "gcp" in stack_text or "google" in stack_text: primary_cloud = "GCP"
    elif "digitalocean" in stack_text or "ocean" in stack_text: primary_cloud = "DigitalOcean"
    elif "oracle" in stack_text: primary_cloud = "Oracle Cloud"
    
    return f"""
    You are a Cloud Billing Simulation Engine.
    Generate a realistic JSON billing invoice for a cloud project.
    
    PROJECT CONTEXT:
    - Name: "{profile.get('name')}"
    - Tech Stack: {tech_str}
    - Budget Goal: ~{budget} INR/month (Total ~{budget * 4} for 4 months)
    - Months to Cover: {months_str}
    - Uses SQLite? {"Yes (No Database costs)" if is_sqlite else "No"}
    - PRIMARY CLOUD PROVIDER: {primary_cloud}
    
    INSTRUCTIONS:
    1. Generate exactly 15-20 billing records distributed across the 4 months.
    2. STRICTLY usage services valid for {primary_cloud} (e.g., if AWS use EC2/S3/RDS; if Azure use VMs/Blob/SQL).
    3. VARY usage and costs slightly month-to-month (don't make them identical).
    3. Use REALISTIC resource names and descriptions (e.g., "db-prod-replica-01", "High-IOPS SSD").
    4. Services to Include: Compute, Storage, Networking, Monitoring. {"(AND Database)" if not is_sqlite else ""}
    5. COSTING: Try to aim for the monthly budget, but accuracy isn't critical (math will be fixed later).
    
    REQUIRED JSON STRUCTURE:
    [
      {{
        "month": "2025-01",
        "service": "EC2",
        "resource_id": "i-ecommerce-web-01",
        "region": "ap-south-1",
        "usage_type": "Linux/UNIX (on-demand)",
        "usage_quantity": 720,
        "unit": "hours",
        "cost_inr": 900,
        "desc": "Ecommerce web server"
      }},
      {{
        "month": "2025-01",
        "service": "EC2",
        "resource_id": "i-ecommerce-api-01",
        "region": "ap-south-1",
        "usage_type": "Linux/UNIX (on-demand)",
        "usage_quantity": 360,
        "unit": "hours",
        "cost_inr": 450,
        "desc": "Ecommerce API server"
      }},
      ...
    ]
    
    Return ONLY the JSON array.
    """

def save_mock_billing(records, filename="mock_billing.json"):
    """Helper to save billing records to JSON."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)
    print(f"Generated {len(records)} records. Saved to {filename}")
    
    # Quick Summary
    totals = {}
    for r in records: 
        totals[r["month"]] = totals.get(r["month"], 0) + r.get("cost_inr", 0)
    print("Summary:", {k: f"₹{v:,}" for k, v in totals.items()})

def run_billing_generation():
    print("\n--- Stage 2: Billing Generation ---")
    
    if not os.path.exists("project_profile.json"):
        print("Missing project_profile.json")
        return

    with open("project_profile.json", "r") as f:
        profile = json.load(f)

    print(f"Project: {profile.get('name')} | Budget: ₹{profile.get('budget_inr_per_month', 0):,}")
    
    records = generate_mock_billing(profile)
    
    if records:
        save_mock_billing(records)
        return records
    else:
        print("Generation failed.")
        return None

if __name__ == "__main__":
    run_billing_generation()
