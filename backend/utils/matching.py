import re
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Set

from rapidfuzz import fuzz

SKILL_ALIASES: Dict[str, str] = {
    'reactjs':       'react',
    'react.js':      'react',
    'angularjs':     'angular',
    'vuejs':         'vue',
    'vue.js':        'vue',
    'nextjs':        'next.js',
    'nodejs':        'node.js',
    'node':          'node.js',
    'expressjs':     'express',
    'express.js':    'express',
    'springboot':    'spring boot',
    'golang':        'go',
    'ml':            'machine learning',
    'dl' :            'deep learning',
    'ai':            'artificial intelligence',
    'nlp':           'natural language processing',
    'cv':            'computer vision',
    'k8s':           'kubernetes',
    'sklearn':       'scikit-learn',
    'postgres':      'postgresql',
    'dotnet':        '.net',
    'tailwindcss':   'tailwind',
    'amazon web services': 'aws',
    'google cloud':  'gcp',
    'pyspark':       'spark',
    'huggingface':   'hugging face',
}


def normalize_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    return SKILL_ALIASES.get(cleaned, cleaned)


def fuzzy_match_keywords(
    resume_keywords: List[str],
    jd_keywords: List[str],
    threshold: int = 80,
) -> Dict[str, List[str]]:
    resume_normalized = {normalize_skill(kw): kw for kw in resume_keywords}
    jd_normalized     = {normalize_skill(kw): kw for kw in jd_keywords}

    matched_jd_originals = []
    missing_jd_originals = []

    for jd_canon, jd_original in jd_normalized.items():
        # 1. Exact canonical match
        if jd_canon in resume_normalized:
            matched_jd_originals.append(jd_original)
            continue

        # 2. Fuzzy match against all resume canonical names
        best_score = 0
        for resume_canon in resume_normalized:
            score = fuzz.token_sort_ratio(jd_canon, resume_canon)
            best_score = max(best_score, score)

        if best_score >= threshold:
            matched_jd_originals.append(jd_original)
        else:
            missing_jd_originals.append(jd_original)

    return {
        'matched': sorted(matched_jd_originals),
        'missing': missing_jd_originals,
    }

# ===========================================================================================
# Resume <-> job-description term matching
#
# A JD term counts as COVERED when the resume really contains it: the term (or an equivalent,
# e.g. "Artificial Intelligence" <-> "AI", "APIs" <-> "REST APIs"/"FastAPI") appears in the full
# resume text, or in the resume's skills/keywords. Generic filler ("collaboration", "3 to 6 months",
# "a degree") is ignored instead of being reported as a missing skill.
# ===========================================================================================

# Each set is a family of interchangeable terms. Lookup is NOT transitive: a JD term only pulls in
# the families that contain that term itself.
_EQUIVALENT_GROUPS: List[Set[str]] = [
    {'artificial intelligence', 'ai', 'a.i.', 'ai/ml', 'aiml', 'ai ml', 'ml/ai'},
    {'machine learning', 'ml', 'ai/ml', 'aiml', 'ai ml', 'ml/ai'},
    {'deep learning', 'dl'},
    {'natural language processing', 'nlp'},
    {'computer vision', 'cv', 'opencv'},
    {'computer science', 'cs', 'cse', 'computer science and engineering', 'computer science & engineering',
     'computer science engineering'},
    {'api', 'apis', 'rest api', 'rest apis', 'restful api', 'restful apis', 'api development',
     'fastapi', 'flask', 'django rest framework', 'django rest'},
    {'data preprocessing', 'data pre-processing', 'data preparation', 'data cleaning', 'data cleansing',
     'data wrangling', 'data munging', 'preprocessing', 'pre-processing'},
    {'large language models', 'large language model', 'llm', 'llms'},
    {'retrieval augmented generation', 'retrieval-augmented generation', 'rag'},
    {'object oriented programming', 'object-oriented programming', 'object oriented', 'oop', 'oops'},
    {'data structures and algorithms', 'data structures & algorithms', 'dsa', 'data structures'},
    {'javascript', 'js'},
    {'typescript', 'ts'},
    {'node.js', 'nodejs', 'node'},
    {'postgresql', 'postgres'},
    {'ci/cd', 'cicd', 'ci cd', 'continuous integration'},
    {'amazon web services', 'aws'},
    {'google cloud platform', 'gcp', 'google cloud'},
    {'scikit-learn', 'sklearn', 'scikit learn'},
    {'version control', 'git', 'github', 'gitlab'},
    {'database', 'databases', 'sql', 'mysql', 'postgresql', 'sqlite', 'dbms', 'database management'},
]

# Boilerplate that says nothing about skills; never reported as missing or counted in the match %.
_GENERIC_JD_TERMS: Set[str] = {
    'collaboration', 'communication', 'teamwork', 'team', 'teams', 'documentation', 'ability', 'abilities',
    'knowledge', 'experience', 'skills', 'strong', 'excellent', 'responsibilities', 'requirements',
    'candidate', 'candidates', 'role', 'position', 'company', 'organization', 'work', 'working', 'building',
    'assist', 'support', 'basic use', 'degree', 'a degree', 'bachelor', "bachelor's degree", "master's degree",
    'internship', 'intern', 'full-time', 'part-time', 'remote', 'on-site', 'onsite', 'site', 'hybrid',
    'stipend', 'duration', 'location', 'problem solving', 'problem-solving', 'analytical skills',
    'attention to detail', 'fast-paced', 'self-starter', 'quick learner', 'team player', 'interpersonal skills',
    'leadership', 'opportunity', 'environment', 'projects', 'project', 'tasks', 'task', 'tools', 'tool',
    'use', 'basic', 'understanding', 'familiarity', 'preferred', 'required', 'plus', 'etc',
}

_TIME_RE = re.compile(r'\b\d+\s*(?:to|-|–)?\s*\d*\s*(?:weeks?|months?|years?|days?|hours?|yrs?)\b', re.IGNORECASE)


def clean_jd_term(raw) -> str:
    """Tidy a JD term; returns '' for junk such as '-site', '3 to 6 months', '2+'."""
    t = re.sub(r'\s+', ' ', str(raw or '')).strip(' \t\n-–—•*·:;,.()[]')
    if len(t) < 2 or _TIME_RE.search(t) or re.fullmatch(r'[\d\W]+', t):
        return ''
    return t


@lru_cache(maxsize=4096)
def _variant_regex(variant: str):
    words = [re.escape(w) for w in re.split(r'[\s\-]+', variant.strip()) if w]
    body = r'[\s\-]*'.join(words)
    if len(variant) > 3 and variant[-1].isalpha():
        body += r'(?:s|es)?'                          # plural tolerant: "pipeline" ~ "pipelines"
    return re.compile(r'(?<![a-z0-9])' + body + r'(?![a-z0-9])')


def _term_variants(term: str) -> Set[str]:
    seed = {term.lower().strip(), normalize_skill(term)}
    variants = set(seed)
    for group in _EQUIVALENT_GROUPS:
        if seed & group:
            variants |= group
    return variants


def _is_covered(term: str, text_low: str, resume_norm: Set[str], fuzzy_threshold: int) -> bool:
    if term.lower() in resume_norm or normalize_skill(term) in resume_norm:
        return True
    for variant in _term_variants(term):
        if variant and _variant_regex(variant).search(text_low):
            return True
    base = normalize_skill(term)
    return any(fuzz.token_sort_ratio(base, rt) >= fuzzy_threshold for rt in resume_norm)


def match_terms_against_resume(
    jd_terms: Iterable[str],
    resume_text: str,
    resume_terms: Optional[Iterable[str]] = None,
    fuzzy_threshold: int = 90,
) -> Dict[str, List[str]]:
    """Split JD terms into matched / missing / ignored (generic or junk) against the real resume."""
    text_low = (resume_text or '').lower()
    resume_norm = {normalize_skill(t) for t in (resume_terms or []) if str(t).strip()}
    matched, missing, ignored, seen = [], [], [], set()
    for raw in jd_terms or []:
        term = clean_jd_term(raw)
        if not term:
            ignored.append(str(raw))
            continue
        key = term.lower()
        if key in seen:
            continue
        seen.add(key)
        if key in _GENERIC_JD_TERMS:
            ignored.append(term)
            continue
        (matched if _is_covered(term, text_low, resume_norm, fuzzy_threshold) else missing).append(term)
    return {'matched': sorted(matched), 'missing': missing, 'ignored': ignored}
