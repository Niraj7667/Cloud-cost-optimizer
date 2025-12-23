# AI-Powered Cloud Cost Optimizer (LLM-Driven)

This is a Python-based CLI tool that uses Artificial Intelligence (LLM) to simulate and optimize cloud infrastructure costs. It takes a plain-English project description, generates a technical profile, creates realistic billing invoices, and provides actionable cost-saving recommendations.

## Key Features

*   **AI-Driven Analysis**: Uses `meta-llama/Llama-3.1-8B-Instruct` (via Hugging Face API) to understand natural language requirements.
*   **Realistic Billing Simulation**: Generates detailed, cloud-specific billing records (AWS, Azure, GCP) based on the user's tech stack.
    *   **Smart Defaults**: Defaults to **AWS** if no cloud provider is specified, but automatically adapts to Azure or Google Cloud if mentioned.
*   **Cost Optimization Engine**: Analyzes billing data to suggest 6-10 high-value optimizations (Rightsizing, Spot Instances, Architecture changes).
*   **Strict Constraints**: Enforces precise output formatting:
    *   **Billing Records**: 12-20 detailed line items.
    *   **Recommendations**: 6-10 actionable insights.
*   **Robust Fallback System**: Ensures the tool works even if the AI API experiences timeouts or errors.

---

## Installation & Setup

### 1. Prerequisites
*   Python 3.10 or higher
*   A free [Hugging Face API Token](https://huggingface.co/settings/tokens)

### 2. Install Dependencies
```bash
pip install requests python-dotenv
```

### 3. Configure API Key
Create a `.env` file in the project root:
```env
HF_API_KEY=hf_your_actual_api_key_here
```

### 4. Run the Tool
```bash
python main.py
```

---

## Example Walkthrough

Here is an actual scenario from the tool, showing how it transforms a raw idea into structured cost reports.

### Step 1: User Input
The user provides a high-level description of their idea:

> "We are building a food delivery app for 10,000 users per month. Budget: ₹50,000 per month. Tech stack: Node.js backend, PostgreSQL database, object storage for images, monitoring, and basic analytics. Non-functional requirements: scalability, cost efficiency, uptime monitoring."

---

### Step 2: Generated Profile (`project_profile.json`)
The AI analyzes the text and extracts structured metadata:

```json
{
  "name": "Food Delivery App",
  "budget_inr_per_month": 50000,
  "description": "We are building a food delivery app for 10,000 users per month",
  "tech_stack": {
    "backend": "Node.js",
    "database": "PostgreSQL",
    "storage": "object storage",
    "monitoring": "monitoring",
    "analytics": "basic analytics"
  },
  "non_functional_requirements": [
    "Uptime Monitoring",
    "Scalability",
    "Cost Efficiency"
  ]
}
```

---

### Step 3: Mock Billing Data (`mock_billing.json`)
The tool generates realistic billing records (12-20 items) tailored to the budget and tech stack. (Snippet shown below):

```json
[
  {
    "month": "2025-09",
    "service": "RDS",
    "resource_id": "db-prod-replica-01",
    "region": "ap-south-1",
    "usage_type": "PostgreSQL (provisioned)",
    "usage_quantity": 720,
    "unit": "hours",
    "cost_inr": 38497,
    "desc": "Production database replica"
  },
  {
    "month": "2025-09",
    "service": "S3",
    "resource_id": "bucket-food-delivery-prod",
    "region": "ap-south-1",
    "usage_type": "Standard Storage",
    "usage_quantity": 100,
    "unit": "GB",
    "cost_inr": 1069,
    "desc": "Production bucket for food delivery app"
  },
  {
    "month": "2025-09",
    "service": "EC2",
    "resource_id": "i-ecommerce-web-01",
    "region": "ap-south-1",
    "usage_type": "Linux/UNIX (on-demand)",
    "usage_quantity": 720,
    "unit": "hours",
    "cost_inr": 1924,
    "desc": "Ecommerce web server"
  }
]
```

---

### Step 4: Optimization Report (`cost_optimization_report.json`)
Finally, it provides actionable recommendations (6-10 items) to save money:

```json
{
  "project_name": "Food Delivery App",
  "analysis": {
    "total_monthly_cost": 49902.25,
    "budget": 50000,
    "budget_variance": -97.75,
    "service_costs": {
      "RDS": 41339.0,
      "S3": 1502.0,
      "CloudWatch": 3448.5,
      "EC2": 1382.75,
      "EBS": 2230.0
    },
    "high_cost_services": {
      "RDS": 41339.0,
      "CloudWatch": 3448.5,
      "EBS": 2230.0
    },
    "is_over_budget": false
  },
  "recommendations": [
    {
      "title": "Migrate to PostgreSQL Free Tier",
      "service": "RDS",
      "current_cost": 41339,
      "potential_savings": 8226,
      "recommendation_type": "free_tier",
      "description": "Migrate to PostgreSQL free tier, utilizing the free tier for development and testing environments.",
      "implementation_effort": "medium",
      "risk_level": "medium",
      "steps": [
        "Assess RDS usage and determine if free tier is suitable",
        "Migrate to PostgreSQL free tier, ensuring data integrity",
        "Update application code to accommodate free tier"
      ],
      "cloud_providers": [
        "AWS",
        "Azure",
        "GCP"
      ]
    },
    {
      "title": "Use Spot Instances",
      "service": "Compute",
      "potential_savings": 2500,
      "recommendation_type": "Rightsizing",
      "cloud_providers": ["AWS", "Azure", "GCP"],
      "description": "Use Spot instances for fault-tolerant workloads."
    }
  ]
}
```

---

## Project Structure

| File | Description |
| :--- | :--- |
| `main.py` | **CLI Orchestrator**: Handles user interaction and stage coordination. |
| `profile_generator.py` | **Extraction**: Converts text to `project_profile.json`. |
| `billing_engine.py` | **Simulation**: Generates `mock_billing.json`. |
| `analyzer.py` | **Analysis**: Produces `cost_optimization_report.json`. |
| `llm_utils.py` | **AI Gateway**: Manages API calls and JSON validation. |

---

## AI Usage Declaration

This tool leverages Large Language Models (LLMs) to perform complex data generation and analysis tasks.
*   **Profile Extraction**: NLP to structure unstructured text.
*   **Data Simulation**: Creative generation of realistic resource names and usage patterns.
*   **Advisory**: Synthesizing best-practice knowledge for optimization.

All core logic, validation, file handling, and constraint enforcement are implemented in deterministic Python code.
