"""
Stage 1: Project Profile Extraction
"""

import json
import re
from llm_utils import query_llama_json

def extract_project_profile(description: str):
    """Orchestrates the extraction and sanitization of the project profile."""
    
    # Define prompt for LLM
    prompt = f"""
You are an expert cloud architect.

Extract a STRICT JSON object from the project description below.

RULES:
- Output ONLY valid JSON (no markdown, no comments, no extra text)
- Do NOT invent technologies
- Extract ONLY technologies explicitly mentioned in the description
- budget_inr_per_month MUST be an integer

REQUIRED JSON STRUCTURE:
{{
  "name": "Concise project name (2–4 words)",
  "budget_inr_per_month": 0,
  "description": "One-line summary of the project",
  "tech_stack": {{
  }},
  "non_functional_requirements": []
}}

TECH STACK RULES:
- Populate tech_stack as dynamic key-value pairs
- Example: if React is mentioned -> "frontend": "React"
- Do NOT include unused or missing technologies
- Do NOT add empty values

NON-FUNCTIONAL REQUIREMENTS RULES:
- Extract explicitly mentioned REQUIREMENTS and METRICS (very important)
- Look for: Data volume (TB/PB), Traffic patterns (High/Low), Compliance (HIPAA), or Usage (Video/Static)
- ONLY include requirements explicitly stated in the text.
- If nothing is mentioned, return an empty list [].
- Use Title Case strings

BUDGET RULE:
- If explicitly mentioned, extract exactly
- Otherwise estimate: Small = 10000, Medium = 50000

Project Description:
{description}

Return ONLY the JSON object.
"""

    print("Analyzing description...")
    raw_profile = query_llama_json(prompt, max_tokens=800)

    if not raw_profile:
        print("LLM extraction failed.")
        return None

    # Validate structure
    required = ["name", "budget_inr_per_month", "description", "tech_stack", "non_functional_requirements"]
    if not all(k in raw_profile for k in required):
        print("Invalid JSON structure.")
        return None

    return _sanitize_profile(raw_profile, description)


def _sanitize_profile(profile, raw_text):
    """Cleans up the profile to ensure accuracy against the source text."""
    text_lower = raw_text.lower()

    # 1. Budget Extraction (Regex Preference)
    budget_match = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+)", text_lower)
    if not budget_match:
        budget_match = re.search(r"([\d,]+)\s*(?:rupees|rs)", text_lower)
    
    if budget_match:
        try:
            profile["budget_inr_per_month"] = int(budget_match.group(1).replace(',', ''))
        except ValueError:
            pass # Keep LLM estimate if regex fails

    # 2. Requirement Validation
    # Only keep NFRs if their key terms actually appear in the user's text.
    valid_nfrs = []
    # Map high-level concepts to synonyms found in text
    concepts = {
        "scalability": ["scalab", "scale", "scalable", "scalability"],
        "cost efficiency": ["cost", "cost efficiency", "cost-effective", "cost efficient"],
        "high availability": ["availability", "high availability", "high-availability"],
        "security": ["security", "secure", "authentication", "authorization"],
        "disaster recovery": ["disaster", "recovery", "backup", "failover"],
        "monitoring": ["monitor", "monitoring", "uptime", "observability"],
    }

    for nfr in profile.get("non_functional_requirements", []):
        nfr_clean = nfr.lower().strip()
        
        # Check specific metrics (e.g. "100TB")
        nums = re.findall(r'\d+', nfr_clean)
        if nums and all(n in text_lower for n in nums):
            valid_nfrs.append(nfr)
            continue

        # Check concept existence
        is_valid = False
        for concept, keywords in concepts.items():
            if concept in nfr_clean or any(k in nfr_clean for k in keywords):
                # If the concept matches, verify at least one related keyword is in the raw text
                if any(k in text_lower for k in keywords + [concept]):
                    valid_nfrs.append(nfr.title())
                    is_valid = True
                    break
        
        # Fallback: exact string match
        if not is_valid and nfr_clean in text_lower:
            valid_nfrs.append(nfr)

    profile["non_functional_requirements"] = list(set(valid_nfrs))

    # 3. Tech Stack Validation
    # If the tool isn't in the text, mark it 'Not Specified'
    cleaned_stack = {}
    for layer, tool in profile.get("tech_stack", {}).items():
        if tool and str(tool).lower() in text_lower:
            cleaned_stack[layer] = tool
        else:
            cleaned_stack[layer] = "Not Specified"
    profile["tech_stack"] = cleaned_stack

    # 4. Concise Description
    # Use the first sentence of the user's input as the description
    sentences = re.split(r'[\.\n]', raw_text)
    if sentences:
        profile["description"] = sentences[0].strip()

    return profile

def save_project_description(description: str, filename="project_description.txt"):
    """Save raw project description to file."""
    with open(filename, "w", encoding="utf-8") as f:
        f.write(description)
    print(f"Saved project description to {filename}")

def save_project_profile(profile: dict, filename="project_profile.json"):
    """Save extracted project profile to JSON file."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2, ensure_ascii=False)
    print(f"Saved project profile to {filename}")

def run_profile_extraction():
    print("\n--- Stage 1: Profile Extraction ---")
    
    print("Enter project description (double enter to finish):")
    lines = []
    while True:
        line = input()
        if not line and (not lines or not lines[-1]): break
        lines.append(line)
    
    desc = "\n".join(lines).strip()
    if not desc: return None

    with open("project_description.txt", "w", encoding="utf-8") as f:
        f.write(desc)

    profile = extract_project_profile(desc)
    
    if profile:
        with open("project_profile.json", "w", encoding="utf-8") as f:
            json.dump(profile, f, indent=2)
        print("\nProfile generated:")
        print(json.dumps(profile, indent=2))
        return profile
    
    return None

if __name__ == "__main__":
    run_profile_extraction()
