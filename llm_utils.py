"""
LLM Utilities
Handles interactions with Hugging Face Inference API.
"""

import os
import json
import re
import requests
from dotenv import load_dotenv

# Load env immediately
load_dotenv()

# Config
API_URL = "https://router.huggingface.co/v1/chat/completions"
API_KEY = os.getenv("HF_API_KEY")

if not API_KEY:
    # API Key check
    print("WARNING: HF_API_KEY not found in .env")

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

def query_llama(prompt, max_tokens=1000, temperature=0.1):
    """
    Raw API call to Llama 3.1.
    """
    payload = {
        "model": "meta-llama/Llama-3.1-8B-Instruct",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, timeout=60)
        resp.raise_for_status() # Standard way to handle HTTP errors
        
        data = resp.json()
        return data["choices"][0]["message"]["content"]
        
    except Exception as e:
        print(f"API Error: {e}")
        return None

def _parse_json_block(text):
    """
    Extracts JSON block from text.
    """
    if not text: return None
    
    # 1. Try finding a markdown block
    match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if match:
        text = match.group(1)
        
    # 2. Try finding the first/last brace
    try:
        start = re.search(r'[\[\{]', text).start()
        end = max(text.rfind(']'), text.rfind('}')) + 1
        return json.loads(text[start:end])
    except (AttributeError, ValueError, json.JSONDecodeError):
        return None

def query_llama_json(prompt, max_tokens=2000):
    """Returns parsed JSON object or None."""
    raw_text = query_llama(prompt, max_tokens)
    return _parse_json_block(raw_text)

def query_llama_with_validation(prompt, validator_fn, max_retries=3, max_tokens=3000):
    """
    Retry loop that feeds validation errors back to the LLM.
    validator_fn(data) -> (bool, "error message")
    """
    current_prompt = prompt
    
    for i in range(max_retries + 1):
        if i > 0: 
            print(f"   Using retry attempt {i}...")
            
        data = query_llama_json(current_prompt, max_tokens)
        
        if data:
            is_valid, error_msg = validator_fn(data)
            if is_valid:
                return data
            
            # Feedback Loop: Tell LLM what is wrong
            current_prompt = f"{prompt}\n\n PREVIOUS OUTPUT INVALID: {error_msg}\nEnsure strict JSON compliance."
        else:
            current_prompt = f"{prompt}\n\n PREVIOUS OUTPUT WAS NOT JSON.\nReturn ONLY valid JSON."
            
    print("Validation failed after retries.")
    return None
