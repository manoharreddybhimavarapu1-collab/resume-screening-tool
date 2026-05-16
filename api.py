"""
FastAPI REST API — Resume Screening Tool
Endpoints:
  POST /parse       → parse a resume PDF/DOCX
  POST /rank        → rank candidates against a job description
  GET  /candidates  → list all stored candidates
  GET  /health      → health check
"""

import os
import shutil
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.parser import parse_resume
from app.ranker import rank_candidates
from db.models import SessionLocal, Candidate, init_db


app = FastAPI(
    title="Resume Screening API",
    description="LLM-powered resume parsing and candidate ranking system.",
    version="1.0.0"
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

UPLOAD_DIR = Path("data/resumes")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
init_db()


# ── Schemas ────────────────────────────────────────────────
class RankRequest(BaseModel):
    job_description: str
    candidate_ids: List[int] = []


# ── Endpoints ──────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok", "service": "Resume Screening API"}


@app.post("/parse", summary="Upload and parse a resume (PDF or DOCX)")
async def upload_resume(file: UploadFile = File(...)):
    allowed = {".pdf", ".docx", ".doc"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '{ext}'.")

    dest = UPLOAD_DIR / file.filename
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        parsed = parse_resume(str(dest))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

    db = SessionLocal()
    candidate = Candidate(
        name=parsed["candidate"].get("name", ""),
        email=parsed["candidate"].get("email", ""),
        experience_years=parsed.get("experience_years", 0),
        skills=str(parsed.get("skills", {})),
        raw_json=str(parsed)
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    db.close()

    return {"message": "✅ Resume parsed successfully.", "candidate_id": candidate.id, "data": parsed}


@app.post("/rank", summary="Rank candidates against a job description")
def rank(request: RankRequest):
    db = SessionLocal()
    query = db.query(Candidate)
    if request.candidate_ids:
        query = query.filter(Candidate.id.in_(request.candidate_ids))
    candidates_db = query.all()
    db.close()

    if not candidates_db:
        raise HTTPException(status_code=404, detail="No candidates found.")

    import ast
    candidates = [ast.literal_eval(c.raw_json) for c in candidates_db]

    try:
        results = rank_candidates(candidates, request.job_description)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ranking failed: {str(e)}")

    return {"job_description": request.job_description[:200] + "...", "rankings": results}


@app.get("/candidates", summary="List all stored candidates")
def list_candidates():
    db = SessionLocal()
    candidates = db.query(Candidate).all()
    db.close()
    return [{"id": c.id, "name": c.name, "email": c.email, "experience_years": c.experience_years} for c in candidates]
