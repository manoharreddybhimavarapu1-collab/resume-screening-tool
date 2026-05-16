"""
Candidate Ranker — ranks candidates against a job description using LLM embeddings.
"""

import os
import json
import numpy as np
from typing import List, Dict
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RANKING_PROMPT = """You are a senior technical recruiter. Given the job description and candidate profile below,
evaluate the candidate and return ONLY valid JSON:
{{
  "match_score": 0.0,
  "recommendation": "STRONG HIRE | HIRE | MAYBE | NO HIRE",
  "reasoning": "",
  "strengths": [],
  "gaps": [],
  "suggested_interview_questions": []
}}

Job Description:
{job_description}

Candidate Profile:
{candidate_profile}"""


def get_embedding(text: str) -> List[float]:
    """Get OpenAI embedding for a text."""
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text[:8000]
    )
    return response.data[0].embedding


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a, b = np.array(a), np.array(b)
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def rank_candidate(candidate: Dict, job_description: str) -> Dict:
    """Score and rank a single candidate against a job description."""
    candidate_text = json.dumps(candidate, indent=2)

    # Embedding similarity score
    jd_emb        = get_embedding(job_description)
    candidate_emb = get_embedding(candidate_text)
    similarity    = cosine_similarity(jd_emb, candidate_emb)

    # GPT-4 evaluation
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{
            "role": "user",
            "content": RANKING_PROMPT.format(
                job_description=job_description,
                candidate_profile=candidate_text[:3000]
            )
        }],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    evaluation = json.loads(raw)

    # Blend embedding similarity + LLM score
    blended_score = (similarity * 0.3 + evaluation["match_score"] / 100 * 0.7) * 100
    evaluation["match_score"] = round(blended_score, 1)
    evaluation["candidate"]   = candidate.get("candidate", {}).get("name", "Unknown")

    return evaluation


def rank_candidates(candidates: List[Dict], job_description: str) -> List[Dict]:
    """Rank a list of candidates and return sorted results."""
    results = [rank_candidate(c, job_description) for c in candidates]
    return sorted(results, key=lambda x: x["match_score"], reverse=True)
