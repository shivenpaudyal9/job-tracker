"""
LLM-powered structured extraction for raw job postings.
Uses Groq llama-3.1-70b-versatile at temperature=0 for deterministic output.
Retries up to 3 times on JSON parse failure before skipping the posting.
"""

import json
import logging
import os
import re
from typing import Optional

from groq import Groq

logger = logging.getLogger(__name__)

_client: Optional[Groq] = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        _client = Groq(api_key=os.environ["GROQ_API_KEY"])
    return _client


EXTRACTION_PROMPT = """\
Extract structured data from this job posting. Return ONLY valid JSON, no other text.

Job Title: {title}
Company: {company}
Description: {description}

Return this exact schema:
{{
  "skills_required": [],
  "skills_nice_to_have": [],
  "seniority": "",
  "salary_min": null,
  "salary_max": null,
  "salary_currency": "USD",
  "visa_sponsorship": null,
  "role_category": ""
}}

Rules:
- skills_required: hard technical skills explicitly required. Examples: Python, PyTorch, TensorFlow, SQL, Spark, AWS, Docker, Kubernetes, LLMs, RAG, embeddings, React. Never include soft skills.
- skills_nice_to_have: skills mentioned as "preferred", "nice to have", or "plus".
- seniority: one of intern / junior / mid / senior / staff / principal. Infer from title and description.
- salary_min / salary_max: integers in USD. null if not mentioned.
- visa_sponsorship: true / false / null if not mentioned.
- role_category: one of ml_engineer / data_scientist / mlops / analytics / applied_scientist / research.
"""


def _clean_json_response(text: str) -> str:
    text = text.strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def extract(title: str, company: str, description: str, max_retries: int = 3) -> Optional[dict]:
    client = _get_client()
    # Truncate description to avoid token limits
    description_trimmed = description[:3000] if len(description) > 3000 else description

    prompt = EXTRACTION_PROMPT.format(
        title=title,
        company=company,
        description=description_trimmed,
    )

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=512,
            )
            raw = response.choices[0].message.content or ""
            cleaned = _clean_json_response(raw)
            parsed = json.loads(cleaned)

            # Validate required keys
            required = {"skills_required", "skills_nice_to_have", "seniority",
                        "salary_min", "salary_max", "salary_currency",
                        "visa_sponsorship", "role_category"}
            if not required.issubset(parsed.keys()):
                raise ValueError(f"Missing keys: {required - parsed.keys()}")

            return parsed

        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Extract attempt %d/%d failed for '%s': %s", attempt, max_retries, title, e)
        except Exception as e:
            logger.error("Groq API error for '%s': %s", title, e)
            return None

    logger.error("All %d extraction attempts failed for '%s' at %s", max_retries, title, company)
    return None
