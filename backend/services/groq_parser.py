import copy
import hashlib
import json
import logging
import os
import re
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

from groq import Groq

logger=logging.getLogger('ats_resume_scorer')


# GROQ_MODEL='llama-3.3-70b-versatile'
GROQ_MODEL = os.getenv('GROQ_MODEL', 'openai/gpt-oss-120b')


_client=None

# -- Determinism helpers ------------------------------------------------------
# An LLM call is never perfectly repeatable (even at temperature 0), and every score
# in this app is computed from what the LLM extracts. So the same resume text must
# always map to the same extraction: we cache it, keyed by a hash of the text.
PARSER_VERSION = 'v2'        # bump when you change the prompts, to invalidate old cache entries
_CACHE_MAX     = 256
_mem_cache = OrderedDict()
_cache_lock    = threading.Lock()
# Optional on-disk cache (survives restarts). Off by default: it would store parsed
# resumes (names, emails, phones) on disk. Set RESUME_PARSE_CACHE_DIR to enable.
_DISK_DIR = os.getenv('RESUME_PARSE_CACHE_DIR')


def _cache_key(kind: str, text: str) -> str:
    norm = re.sub(r'\s+', ' ', text).strip()
    raw  = f'{PARSER_VERSION}|{GROQ_MODEL}|{kind}|{norm}'
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def _cache_put(key: str, value: dict, to_disk: bool = True) -> None:
    with _cache_lock:
        _mem_cache[key] = copy.deepcopy(value)
        _mem_cache.move_to_end(key)
        while len(_mem_cache) > _CACHE_MAX:
            _mem_cache.popitem(last=False)
    if _DISK_DIR and to_disk:
        try:
            Path(_DISK_DIR).mkdir(parents=True, exist_ok=True)
            (Path(_DISK_DIR) / f'{key}.json').write_text(json.dumps(value), encoding='utf-8')
        except Exception as exc:
            logger.warning(f'Could not write parse cache: {exc}')


def _cache_get(key: str):
    with _cache_lock:
        if key in _mem_cache:
            _mem_cache.move_to_end(key)
            return copy.deepcopy(_mem_cache[key])
    if _DISK_DIR:
        f = Path(_DISK_DIR) / f'{key}.json'
        if f.exists():
            try:
                value = json.loads(f.read_text(encoding='utf-8'))
                _cache_put(key, value, to_disk=False)
                return copy.deepcopy(value)
            except Exception:
                return None
    return None


def dedupe_terms(items) -> List[str]:
    """Strip, drop empties, remove case-insensitive duplicates, return in a stable sorted order."""
    seen = {}
    for it in items or []:
        if not isinstance(it, str):
            continue
        t = re.sub(r'\s+', ' ', it).strip()
        if t and t.lower() not in seen:
            seen[t.lower()] = t
    return [seen[k] for k in sorted(seen)]

def _get_client()->Groq:
    global _client
    if _client is None:
        api_key=os.getenv('GROQ_API_KEY')

        if not api_key:
            raise ValueError("GROQ_API_KEY environment variable not set")
        _client=Groq(api_key=api_key)
    return _client

RESUME_SYSTEM_PROMPT = (
    "You are a resume parser. Extract information from the resume "
    "and return ONLY a valid JSON object. No explanation, no markdown."
)

RESUME_USER_PROMPT = """Extract the following from this resume and return as JSON:
{{
  "name": "full name",
  "email": "email address",
  "phone": "phone number",
  "linkedin": "LinkedIn URL if present, otherwise null",
  "github": "GitHub URL if present, otherwise null",
  "professional_summary": "the full text of the Summary, Profile, About Me, Objective, or Professional Summary section at the top of the resume. Copy the ENTIRE paragraph exactly as written. If no such section exists, return an empty string.",
  "skills": ["list", "of", "skills"],
  "experience": [
    {{
      "job_title": "",
      "company": "",
      "start_date": "",
      "end_date": "",
      "duration_months": 0,
      "description": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "year": ""
    }}
  ],
  "certifications": ["list of certifications"],
  "projects": [
    {{
      "title": "project name",
      "description": "what the project does and how it was built",
      "technologies": ["tech", "used"]
    }}
  ],
  "action_verbs": ["strong action verbs used in bullet points, e.g. developed, implemented, designed"],
  "keywords": ["important keywords and phrases from the resume for ATS matching"]
}}

Important instructions:
- For duration_months, calculate the number of months between start_date and end_date. If end_date is "Present" or "Current", calculate from start_date to now.
- For skills, extract ALL technical and soft skills mentioned anywhere in the resume.
- For action_verbs, find verbs that start bullet points or describe achievements.
- For keywords, extract noun phrases and technical terms relevant to ATS matching.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Resume Text:
{raw_text}"""

def _call_groq(client:Groq, system_prompt:str, user_prompt:str)->str:

    kwargs = dict(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        temperature=0.0,
        seed=42,                 # best-effort repeatability on Groq
        max_tokens=4096,
    )
    try:
        response = client.chat.completions.create(
            response_format={'type': 'json_object'}, **kwargs
        )
    except Exception as exc:
        # Some models reject response_format; fall back to the plain call.
        logger.warning(f'Groq call with json_object failed ({exc}); retrying without it')
        response = client.chat.completions.create(**kwargs)

    return response.choices[0].message.content.strip()

def _try_parse_json(text: str) -> dict | None:

    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):

        # Remove opening fence (```json or ```)
        first_newline = cleaned.index("\n") if "\n" in cleaned else len(cleaned)
        cleaned = cleaned[first_newline + 1:]
        # Remove closing fence
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    
def parse_resume(raw_text: str)->Dict:
    key = _cache_key('resume', raw_text)
    cached = _cache_get(key)
    if cached is not None:
        logger.info('Resume parse: cache hit (same text -> same extraction)')
        return cached
    result = _parse_resume_uncached(raw_text)
    _cache_put(key, result)
    return copy.deepcopy(result)


def _parse_resume_uncached(raw_text: str)->Dict:

    client=_get_client()
    prompt=RESUME_USER_PROMPT.format(raw_text=raw_text)
    raw_response=_call_groq(client, RESUME_SYSTEM_PROMPT, prompt)
    result=_try_parse_json(raw_response)

    if result is not None:
        return _validate_resume_result(result)
    

    logger.warning("Groq resume parse: first attempt returned invalid JSON, retrying...")
    strict_prompt = (
        "Your previous response was not valid JSON. "
        "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
        + prompt
    )
    raw_response = _call_groq(client, RESUME_SYSTEM_PROMPT, strict_prompt)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_resume_result(result)

    raise ValueError(
        f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
    )
    
JD_SYSTEM_PROMPT = (
    "You are a job description parser. Extract information and "
    "return ONLY a valid JSON object. No explanation, no markdown."
)

JD_USER_PROMPT = """Extract the following from this job description and return as JSON:
{{
  "job_title": "",
  "required_skills": ["list of must-have skills"],
  "preferred_skills": ["list of nice-to-have skills"],
  "experience_required": "",
  "education_required": "",
  "key_responsibilities": ["list of responsibilities"],
  "keywords": ["important keywords and phrases for ATS matching"]
}}

Important instructions:
- required_skills: skills explicitly stated as required or must-have.
- preferred_skills: skills stated as preferred, nice-to-have, or bonus.
- keywords: extract ALL important terms an ATS system would match against,
  including skills, technologies, certifications, and domain terms.
- Return ONLY valid JSON. No markdown code fences, no explanation.

Job Description Text:
{raw_text}"""

def parse_job_description(raw_text: str) -> Dict:
    key = _cache_key('jd', raw_text)
    cached = _cache_get(key)
    if cached is not None:
        logger.info('JD parse: cache hit')
        return cached
    result = _parse_jd_uncached(raw_text)
    _cache_put(key, result)
    return copy.deepcopy(result)


def _parse_jd_uncached(raw_text: str) -> Dict:
    client = _get_client()
    prompt = JD_USER_PROMPT.format(raw_text=raw_text)

    raw_response = _call_groq(client, JD_SYSTEM_PROMPT, prompt)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_jd_result(result)

    logger.warning("Groq JD parse: first attempt returned invalid JSON, retrying...")
    strict_prompt = (
        "Your previous response was not valid JSON. "
        "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
        + prompt
    )
    raw_response = _call_groq(client, JD_SYSTEM_PROMPT, strict_prompt)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_jd_result(result)

    raise ValueError(
        f"Groq returned unparseable response after retry. Raw response:\n{raw_response[:500]}"
    )

# it will make sure, that the parse json has all the valid fields we expect
def _validate_jd_result(result: dict) -> dict:
    
    defaults = {
        "job_title": "",
        "required_skills": [],
        "preferred_skills": [],
        "experience_required": "",
        "education_required": "",
        "key_responsibilities": [],
        "keywords": [],
    }

    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    for k in ("required_skills", "preferred_skills", "keywords"):
        result[k] = dedupe_terms(result.get(k))

    return result


#to make sure the parse json has all the valid json fields
def _validate_resume_result(result: dict) -> dict:

    defaults = {
        "name": "",
        "email": None,
        "phone": None,
        "linkedin": None,
        "github": None,
        "professional_summary": "",
        "skills": [],
        "experience": [],
        "education": [],
        "certifications": [],
        "projects": [],
        "action_verbs": [],
        "keywords": [],
    }
    for key, default in defaults.items():
        if key not in result or result[key] is None:
            result[key] = default
            
        # Ensure list fields are actually lists
        if isinstance(default, list) and not isinstance(result[key], list):
            result[key] = default

    # Normalise term lists: strip, de-duplicate (case-insensitive), stable order
    for k in ("skills", "keywords", "action_verbs", "certifications"):
        result[k] = dedupe_terms(result.get(k))

    #Validate experience entries
    for exp in result.get("experience", []):
        if not isinstance(exp, dict):
            continue
        exp.setdefault("job_title", "")
        exp.setdefault("company", "")
        exp.setdefault("start_date", "")
        exp.setdefault("end_date", "")
        exp.setdefault("duration_months", 0)
        exp.setdefault("description", "")
        #Ensure duration_months is an int
        try:
            exp["duration_months"] = int(exp["duration_months"])
        except (ValueError, TypeError):
            exp["duration_months"] = 0

    #Validate project entries
    for proj in result.get("projects", []):
        if not isinstance(proj, dict):
            continue
        proj.setdefault("title", "")
        proj.setdefault("description", "")
        proj.setdefault("technologies", [])

    return result

