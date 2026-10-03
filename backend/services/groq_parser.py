import copy
import hashlib
import json
import logging
import os
import re
import threading
import time
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
PARSER_VERSION = 'v3'        # bump when you change the prompts, to invalidate old cache entries
_CACHE_MAX     = 256
_mem_cache = OrderedDict()
_cache_lock    = threading.Lock()
# Optional on-disk cache (survives restarts). Off by default: it would store parsed
# resumes (names, emails, phones) on disk. Set RESUME_PARSE_CACHE_DIR to enable.
_DISK_DIR = os.getenv('RESUME_PARSE_CACHE_DIR')


# -- Token budget -------------------------------------------------------------
# Groq's free tier allows ~8000 tokens/minute PER REQUEST ESTIMATE = prompt tokens + max_tokens.
# (The old code asked for max_tokens=4096, so any input over ~4000 tokens was rejected with a 413.)
# ~3 characters per token is a safe estimate for resumes (lots of symbols and short words).
GROQ_MAX_INPUT_CHARS   = int(os.getenv('GROQ_MAX_INPUT_CHARS', '9000'))      # resume text sent to the LLM
GROQ_JD_MAX_INPUT_CHARS = int(os.getenv('GROQ_JD_MAX_INPUT_CHARS', '5000'))  # job description text
GROQ_MAX_OUTPUT_TOKENS = int(os.getenv('GROQ_MAX_OUTPUT_TOKENS', '3000'))
GROQ_JD_MAX_OUTPUT_TOKENS = int(os.getenv('GROQ_JD_MAX_OUTPUT_TOKENS', '1500'))


class LLMServiceError(Exception):
    """The LLM provider refused or could not serve the request (rate limit, request too large...).
    `str(exc)` is written for end users; the API turns it into a proper HTTP status."""

    def __init__(self, message: str, status_code: int = 503, retry_after=None):
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


def _status_of(exc: Exception):
    code = getattr(exc, 'status_code', None)
    if code is None:
        code = getattr(getattr(exc, 'response', None), 'status_code', None)
    return code


def _retry_after_of(exc: Exception):
    """Seconds to wait, from the Retry-After header or Groq's 'try again in 2.5s' message."""
    headers = getattr(getattr(exc, 'response', None), 'headers', None)
    try:
        if headers is not None and headers.get('retry-after'):
            return float(headers.get('retry-after'))
    except Exception:
        pass
    m = re.search(r'try again in\s+([\d.]+)\s*(ms|s|m)\b', str(exc), re.IGNORECASE)
    if m:
        val, unit = float(m.group(1)), m.group(2).lower()
        return val / 1000 if unit == 'ms' else val * 60 if unit == 'm' else val
    return None


def _condense(text: str, limit: int, tail: int = 1500) -> str:
    """Normalise whitespace; if still too long keep the start and the end (links/achievements)."""
    t = re.sub(r'[ \t]+', ' ', text or '')
    t = re.sub(r'\n\s*\n+', '\n', t).strip()
    if len(t) <= limit:
        return t
    tail = min(tail, limit // 3)
    logger.warning(f'Input truncated for the LLM: {len(t)} -> {limit} chars')
    return t[:limit - tail - 40].rstrip() + '\n[... middle of document omitted for length ...]\n' + t[-tail:].lstrip()


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

def _call_groq(client: Groq, system_prompt: str, user_prompt: str, max_tokens: int = None) -> str:
    kwargs = dict(
        model=GROQ_MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        temperature=0.0,
        seed=42,                                   # best-effort repeatability on Groq
        max_tokens=max_tokens or GROQ_MAX_OUTPUT_TOKENS,
    )
    if 'gpt-oss' in GROQ_MODEL.lower():
        # reasoning model: reasoning tokens count against max_tokens, so keep them small
        kwargs['extra_body'] = {'reasoning_effort': 'low'}

    use_json_mode = True
    rate_limit_retries = 0
    while True:
        call_kwargs = dict(kwargs)
        if use_json_mode:
            call_kwargs['response_format'] = {'type': 'json_object'}
        try:
            response = client.chat.completions.create(**call_kwargs)
            return (response.choices[0].message.content or '').strip()
        except Exception as exc:
            status = _status_of(exc)
            if status == 413:
                raise LLMServiceError('The request was too large for the AI service.', 413) from exc
            if status == 429:
                wait = _retry_after_of(exc)
                rate_limit_retries += 1
                if rate_limit_retries <= 2 and (wait is None or wait <= 20):
                    delay = (wait if wait is not None else 5 * rate_limit_retries) + 0.5
                    logger.warning(f'Groq rate limit hit; waiting {delay:.1f}s (retry {rate_limit_retries}/2)')
                    time.sleep(delay)
                    continue
                secs = int(wait) + 1 if wait else 30
                raise LLMServiceError(
                    f'The AI service is busy (rate limit reached). Please try again in about {secs} seconds.',
                    429, wait) from exc
            if status == 400:
                # only degrade on a real "bad request" - never re-send a request that was rate limited
                if use_json_mode:
                    logger.warning(f'Groq rejected json_object mode ({exc}); retrying without it')
                    use_json_mode = False
                    continue
                if 'extra_body' in kwargs:
                    logger.warning(f'Groq rejected extra_body ({exc}); retrying without it')
                    kwargs.pop('extra_body')
                    continue
            raise


def _call_with_shrink(client, system_prompt, user_template, raw_text, limit, max_tokens):
    """Send the (condensed) text; if the provider says the request is too large, retry once with less."""
    for attempt in range(2):
        prompt = user_template.format(raw_text=_condense(raw_text, limit))
        try:
            return prompt, _call_groq(client, system_prompt, prompt, max_tokens)
        except LLMServiceError as exc:
            if exc.status_code == 413 and attempt == 0:
                limit = int(limit * 0.6)
                logger.warning(f'Groq said the request is too large; retrying with {limit} chars')
                continue
            if exc.status_code == 413:
                raise LLMServiceError(
                    'This document is too long for the AI service\'s current limit, even after shortening it. '
                    'Try a shorter resume (1-2 pages).', 413) from exc
            raise

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
    prompt, raw_response = _call_with_shrink(
        client, RESUME_SYSTEM_PROMPT, RESUME_USER_PROMPT, raw_text,
        GROQ_MAX_INPUT_CHARS, GROQ_MAX_OUTPUT_TOKENS)
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
    prompt, raw_response = _call_with_shrink(
        client, JD_SYSTEM_PROMPT, JD_USER_PROMPT, raw_text,
        GROQ_JD_MAX_INPUT_CHARS, GROQ_JD_MAX_OUTPUT_TOKENS)
    result = _try_parse_json(raw_response)
    if result is not None:
        return _validate_jd_result(result)

    logger.warning("Groq JD parse: first attempt returned invalid JSON, retrying...")
    strict_prompt = (
        "Your previous response was not valid JSON. "
        "Return ONLY the raw JSON object, no markdown, no explanation, no code fences.\n\n"
        + prompt
    )
    raw_response = _call_groq(client, JD_SYSTEM_PROMPT, strict_prompt, GROQ_JD_MAX_OUTPUT_TOKENS)
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

