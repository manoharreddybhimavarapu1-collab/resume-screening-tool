"""
Resume Parser — extracts structured data from PDF/DOCX resumes using GPT-4.
"""

import os
import json
from pathlib import Path
from typing import Dict

import pdfplumber
import docx
from openai import OpenAI


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

EXTRACTION_PROMPT = """You are an expert resume parser. Extract structured information from the resume text below.
Return ONLY valid JSON with this exact structure:
{
  "candidate": {"name": "", "email": "", "phone": "", "location": ""},
  "education": [{"degree": "", "institution": "", "year": 0, "gpa": null}],
  "experience": [{"title": "", "company": "", "duration": "", "description": ""}],
  "skills": {"languages": [], "frameworks": [], "tools": []},
  "experience_years": 0,
  "summary": ""
}

Resume text:
{resume_text}"""


def extract_text_from_pdf(path: str) -> str:
    text = ""
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def extract_text_from_docx(path: str) -> str:
    doc = docx.Document(path)
    return "\n".join([para.text for para in doc.paragraphs])


def parse_resume(file_path: str) -> Dict:
    """Parse a resume PDF or DOCX into structured JSON."""
    path = Path(file_path)

    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(file_path)
    elif path.suffix.lower() in [".docx", ".doc"]:
        text = extract_text_from_docx(file_path)
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": EXTRACTION_PROMPT.format(resume_text=text[:4000])}
        ],
        temperature=0
    )

    raw = response.choices[0].message.content.strip()
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)
