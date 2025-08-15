from openai import OpenAI
import os
import json
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def llm_evaluate_applicant(applicant_json):
    # Convert JSON to a compact string for exact cache matching
    json_str = json.dumps(applicant_json, separators=(",", ":"))

    prompt = f"""
    You are a recruiting analyst.
    Applicants have already been shortlisted based on their location, preferred rate, availability, and experience (or tier 1 company).

    Applicant JSON:
    {json_str}

    Data units:
    preferred_rate, min_rate are per hour
    availability is in hours per week

    Given this JSON applicant profile, do four things:
    1. Provide a concise 75-word summary.
    2. Rate overall candidate quality from 1-10 (higher is better).
    3. List any data gaps or inconsistencies you notice.
    4. Suggest up to three follow-up questions to clarify gaps.

    Return exactly a json:
    {{
        "summary": "<text>",
        "score": <integer>,
        "issues": "<comma-separated list or 'None'>",
        "follow_ups": "<bullet list>"
    }}
    """

    response = client.responses.create(model="gpt-5-nano", input=prompt)

    text_output = response.output_text.strip()

    try:
        data = json.loads(text_output)
    except json.JSONDecodeError:
        raise ValueError(f"LLM did not return valid JSON: {text_output}")

    # Minimal sanity checks / normalization
    data["summary"] = str(data.get("summary", "")).strip()
    data["issues"] = str(data.get("issues", "None")).strip()
    data["follow_ups"] = str(data.get("follow_ups", "")).strip()
    try:
        data["score"] = int(data.get("score", 0))
    except Exception:
        data["score"] = 0

    return data
