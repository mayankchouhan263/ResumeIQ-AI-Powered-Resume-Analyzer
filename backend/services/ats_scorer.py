import re
import spacy
import numpy as np
from backend.services.embedder import OnnxEmbedder
from typing import Dict, List, Optional, Tuple

from backend.utils.file_utils import log_warning
from backend.core.config import SENTENCE_TRANSFORMER_MODEL
from backend.utils.matching import fuzzy_match_keywords, match_terms_against_resume

ZIP_CODE_PATTERN = r'\b\d{5}(?:-\d{4})?\b'

STREET_ADDRESS_PATTERN = (
    r'\b\d+\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+'
    r'(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Lane|Ln|Drive|Dr|Court|Ct|Circle|Cir|Way|Place|Pl)\b'
)

def _tier_score(n: float, tiers:list)-> float:
    for threshold, pts in tiers:
        if n>=threshold:
            return pts
    
    return 0.0

#Location/privacy detection
def detect_location_info(text: str, nlp: spacy.Language) -> Dict:
    locations = []

    #method01: spacy NER
    doc = nlp(text)
    for ent in doc.ents:
        if ent.label_ in ['GPE', 'LOC']:
            locations.append({'text': ent.text, 'type': ent.label_.lower(), 'start': ent.start_char})

    #moetod02: street address regx
    for match in re.finditer(STREET_ADDRESS_PATTERN, text, re.IGNORECASE):
        locations.append({'text': match.group(), 'type': 'address', 'start': match.start()})

    #method03: ZIP/PIN CODE REGEX PATTERN
    for match in re.finditer(ZIP_CODE_PATTERN, text):
        locations.append({'text': match.group(), 'type': 'zip', 'start': match.start()})

    has_address = any(loc['type'] == 'address' for loc in locations)
    has_zip     = any(loc['type'] == 'zip'     for loc in locations)

    if has_address and has_zip:
        privacy_risk, penalty = 'high', 5.0
    elif has_address or has_zip:
        privacy_risk, penalty = 'high', 4.0
    elif len(locations) > 3:
        privacy_risk, penalty = 'medium', 3.0
    elif locations:
        privacy_risk, penalty = 'low', 0.0   # a plain city/college location is fine
    else:
        privacy_risk, penalty = 'none', 0.0

    recommendations = []
    if not locations:
        recommendations.append(" No privacy concerns detected.")
    if has_address:
        recommendations.append(" Remove full street addresses — ATS systems don't need this and it's a privacy risk.")
    if has_zip:
        recommendations.append(" Remove zip codes — this level of location detail is unnecessary.")
    if privacy_risk in ('low', 'medium') and not has_address and not has_zip:
        recommendations.append(" Consider reducing location mentions. 'City, State' in the contact header is sufficient.")

    return {
        'location_found':     len(locations) > 0,
        'detected_locations': locations,
        'privacy_risk':       privacy_risk,
        'recommendations':    recommendations,
        'penalty_applied':    penalty,
    }

def _calculate_semantic_similarity(skill: str, text: str, embedder: OnnxEmbedder) -> float:
    #similarity = (A · B) / (|A| × |B|)
    if not skill or not text:
        return 0.0
    try:
        skill_vec  = embedder.encode(skill, convert_to_tensor=False)
        text_vec   = embedder.encode(text,  convert_to_tensor=False)

        similarity = np.dot(skill_vec, text_vec) / (
            np.linalg.norm(skill_vec) * np.linalg.norm(text_vec)
        )

        return float(max(0.0, min(1.0, similarity)))
    except Exception as e:
        log_warning(f"Similarity error for '{skill}': {e}", context='ats_scorer')
        return 0.0

def _skill_matches(skill: str, text: str, embedder: OnnxEmbedder, threshold: float) -> Tuple[bool, float]:

    #fast, o(n) directly check if skill is a substring of the text (case-insensitive)
    if skill.lower() in text.lower():
        return True, 1.0
    
    #slow, semantic similarity check using sentence embeddings
    sim = _calculate_semantic_similarity(skill, text, embedder)
    return sim >= threshold, sim

# -- Skill validation ---------------------------------------------------------
# A skill is "validated" when the resume shows evidence of using it:
#   1. it appears (as a whole word / known alias) in a project's title, description
#      or technologies list, or in the experience section
#   2. a link in the resume proves it (a GitHub/GitLab link proves Git; a
#      streamlit.app / vercel.app / huggingface.co link proves that platform)
#   3. fallback: a sentence in a project/experience is semantically close to the skill
# Soft skills (teamwork, communication...) cannot be proven by a project, so they are
# left out of the score instead of counting as "unvalidated".

_ALIAS_GROUPS = [
    {'machine learning', 'ml'}, {'deep learning', 'dl'},
    {'natural language processing', 'nlp'}, {'scikit-learn', 'sklearn', 'scikit learn'},
    {'postgresql', 'postgres'}, {'javascript', 'js', 'ecmascript'}, {'typescript', 'ts'},
    {'react', 'react.js', 'reactjs'}, {'node.js', 'nodejs'}, {'next.js', 'nextjs'},
    {'vue.js', 'vuejs', 'vue'}, {'tensorflow', 'tf'}, {'mongodb', 'mongo'},
    {'amazon web services', 'aws'}, {'google cloud platform', 'gcp', 'google cloud'},
    {'ci/cd', 'cicd'}, {'rest api', 'rest apis', 'restful api', 'restful apis'},
    {'html', 'html5'}, {'css', 'css3'}, {'c++', 'cpp'}, {'c#', 'csharp'},
    {'power bi', 'powerbi'}, {'ms excel', 'microsoft excel', 'excel'},
    {'large language models', 'large language model', 'llm', 'llms'},
    {'generative ai', 'genai', 'gen ai'},
    {'object oriented programming', 'object-oriented programming', 'oop', 'oops'},
    {'data structures and algorithms', 'dsa'}, {'k-means', 'kmeans'},
    {'opencv', 'open cv'}, {'hugging face', 'huggingface'}, {'fastapi', 'fast api'},
    {'express.js', 'expressjs'}, {'spring boot', 'springboot'},
]
_ALIAS_LOOKUP: Dict[str, set] = {}
for _g in _ALIAS_GROUPS:
    for _t in _g:
        _ALIAS_LOOKUP[_t] = _g

_SOFT_SKILLS = {
    'communication', 'teamwork', 'team work', 'team player', 'leadership', 'problem solving',
    'problem-solving', 'time management', 'adaptability', 'collaboration', 'critical thinking',
    'creativity', 'work ethic', 'attention to detail', 'interpersonal skills', 'multitasking',
    'decision making', 'decision-making', 'conflict resolution', 'public speaking',
    'analytical skills', 'analytical thinking', 'self-motivated', 'quick learner',
    'fast learner', 'teamwork and collaboration', 'verbal communication',
    'written communication', 'project management', 'emotional intelligence', 'flexibility',
}

_VCS_WORDS = {'git', 'github', 'gitlab', 'bitbucket'}
_VCS_PHRASES = {'version control', 'source control', 'version control systems'}
_VCS_HOSTS = ('github.com', 'gitlab.com', 'bitbucket.org', 'github.io')
_URL_RE = re.compile(
    r'https?://[^\s<>)\]"\']+|(?:www\.)?(?:github|gitlab|bitbucket)\.(?:com|org)/[^\s<>)\]"\']+',
    re.IGNORECASE,
)
_GENERIC_URL_TOKENS = {
    'com', 'www', 'org', 'net', 'app', 'dev', 'io', 'html', 'http', 'https', 'index', 'blog',
    'pdf', 'the', 'page', 'pages', 'home', 'main', 'master', 'public', 'user', 'users',
}


_DSA_EVIDENCE_RE = re.compile(
    r'\b(?:leetcode|codeforces|codechef|hackerrank|hackerearth|geeksforgeeks|gfg|atcoder|'
    r'interviewbit|coding\s*ninjas|code\s*studio|spoj|topcoder)\b'
    r'|\d[\d,]*\s*\+?\s*(?:(?:dsa|coding|algorithm\w*|programming)\s+(?:problems?|questions?)'
    r'|(?:problems?|questions?)\s+(?:were\s+)?(?:solved|completed)\b)'
    r'|\b(?:solved|completed)\s+(?:over\s+|more\s+than\s+)?\d[\d,]*\s*\+?\s*'
    r'(?:dsa\s+|coding\s+|algorithm\w*\s+)?(?:problems?|questions?)',
    re.IGNORECASE,
)
_DSA_URL_HOSTS = ('leetcode.com', 'codeforces.com', 'codechef.com', 'hackerrank.com',
                  'geeksforgeeks.org', 'hackerearth.com', 'atcoder.jp', 'codingninjas.com')


def _is_dsa_skill(skill: str) -> bool:
    s = re.sub(r'\([^)]*\)', ' ', skill).lower()
    s = re.sub(r'\s+', ' ', s).strip()
    if re.search(r'\bdsa\b|data structures?', s):
        return True
    return s in {'algorithms', 'algorithm', 'algorithm design', 'competitive programming',
                 'algorithms and problem solving', 'algorithmic problem solving'}


def _term_regex(term: str):
    """Whole-word regex for a skill. 1-2 letter terms (R, C, Go, JS) are case-sensitive."""
    t = term.strip()
    if len(t) <= 2:
        body  = '|'.join(re.escape(f) for f in {t, t.upper()})
        flags = 0
    else:
        body  = re.sub(r'(?:\\ |\\-)+', r'[\\s\\-]*', re.escape(t))
        flags = re.IGNORECASE
    return re.compile(r'(?<![A-Za-z0-9+#.])(?:' + body + r')(?![A-Za-z0-9+#])', flags)


def _skill_variants(skill: str) -> List[str]:
    s = skill.strip()
    base = re.sub(r'\([^)]*\)', '', s).strip()
    inner = [x.strip() for x in re.findall(r'\(([^)]*)\)', s) if x.strip()]
    out = set()
    for v in {s, base, *inner}:
        if not v:
            continue
        out.add(v)
        out.update(_ALIAS_LOOKUP.get(v.lower(), ()))
    return sorted(out)


def _is_soft_skill(skill: str) -> bool:
    return re.sub(r'\([^)]*\)', '', skill).strip().lower() in _SOFT_SKILLS


def _is_vcs_skill(skill: str) -> bool:
    s = re.sub(r'\([^)]*\)', '', skill).strip().lower()
    if s in _VCS_PHRASES:
        return True
    parts = [p for p in re.split(r'[^a-z]+', s) if p]
    return bool(parts) and all(p in _VCS_WORDS for p in parts)


def _vcs_evidence(urls: List[str], resume_text: str) -> Optional[str]:
    best = None
    for u in urls:
        low = u.lower()
        if any(h in low for h in _VCS_HOSTS):
            path = re.sub(r'^(?:https?://)?(?:www\.)?[^/]+/?', '', low).strip('/')
            if len([seg for seg in path.split('/') if seg]) >= 2:
                return 'GitHub repo link'
            best = 'GitHub profile link'
    if best:
        return best
    if re.search(r'\b(github|gitlab|bitbucket)\b', resume_text or '', re.IGNORECASE):
        return 'GitHub mention'
    return None


def _link_evidence(variants: List[str], urls: List[str]) -> Optional[str]:
    """A skill named by a link's host/path (streamlit.app, vercel.app, huggingface.co...)."""
    if not urls:
        return None
    compacts = {re.sub(r'[^a-z0-9]', '', v.lower()) for v in variants}
    compacts = {c for c in compacts if len(c) >= 3 and c not in _GENERIC_URL_TOKENS
                and c not in _VCS_WORDS}
    if not compacts:
        return None
    for u in urls:
        tokens = [t for t in re.split(r'[^a-z0-9]+', u.lower()) if t]
        pool = set(tokens) | {a + b for a, b in zip(tokens, tokens[1:])}
        if compacts & pool:
            return 'Project link'
    return None


_SECTION_STOP = (r'education|academic|projects?|personal projects?|skills?|technical skills?|'
                 r'certifications?|licen[cs]es?|courses?|training|achievements?|accomplishments?|awards?|honou?rs|'
                 r'achievements?\s*(?:and|&)\s*[a-z ]+|awards?\s*(?:and|&)\s*[a-z ]+|'
                 r'coding profiles?|competitive programming|positions? of responsibility|'
                 r'publications?|summary|profile|objective|interests?|hobbies|languages?|'
                 r'references?|extracurricular[a-z ]*|(?:work |professional )?experience|internships?|'
                 r'employment(?: history)?')


def _extract_section(resume_text: str, heading_pattern: str) -> str:
    """Raw text of one resume section (heading line up to the next known heading)."""
    if not resume_text:
        return ''
    head = re.compile(rf'^\s*(?:{heading_pattern})\s*:?\s*$', re.IGNORECASE)
    stop = re.compile(rf'^\s*(?:{_SECTION_STOP})\s*:?\s*$', re.IGNORECASE)
    lines, collecting, out = resume_text.splitlines(), False, []
    for line in lines:
        if not collecting:
            if head.match(line):
                collecting = True
            continue
        if stop.match(line) and not head.match(line):
            break
        if re.match(r'^\s*(?:https?://|mailto:|www\.)\S+\s*$', line, re.IGNORECASE):
            break                      # hyperlink list appended after the resume text
        out.append(line)
    return '\n'.join(out).strip()


def _flatten(value) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ', '.join(_flatten(v) for v in value)
    if isinstance(value, dict):
        return ' '.join(_flatten(v) for v in value.values())
    return '' if value is None else str(value)


def _project_text(p: Dict) -> str:
    tech = p.get('technologies') or []
    tech_txt = ', '.join(str(t) for t in tech) if isinstance(tech, list) else str(tech)
    return f"{p.get('title', '')}. {p.get('description', '')}. {tech_txt}"


# Share of listed skills that are backed by evidence -> share of the 15 validation points awarded.
# Concave on purpose: a long skills list with half of it proven is still mostly rewarded, but the
# score only reaches 100% when everything is proven. Linear interpolation between these points.
_VALIDATION_CURVE = [(0.00, 0.00), (0.25, 0.45), (0.50, 0.75), (0.75, 0.90), (1.00, 1.00)]
_MIN_PROVEN_SKILLS = 5     # fewer proven skills than this scales the score down (anti-gaming)


def _validation_fraction(pct: float) -> float:
    pct = max(0.0, min(1.0, pct))
    for (x0, y0), (x1, y1) in zip(_VALIDATION_CURVE, _VALIDATION_CURVE[1:]):
        if pct <= x1:
            return y0 + (y1 - y0) * (pct - x0) / (x1 - x0)
    return 1.0


def validate_skills_with_projects(
    skills: List[str],
    projects: List[Dict],
    experience_entries: List[Dict],
    embedder: Optional[OnnxEmbedder] = None,
    threshold: float = 0.5,
    resume_text: str = '',
    certifications: Optional[List] = None,
) -> Dict:

    def _result(validated, unvalidated, soft):
        total = len(validated) + len(unvalidated)
        pct   = (len(validated) / total) if total else 0.0
        return {
            'validated_skills':      validated,
            'unvalidated_skills':    unvalidated,
            'soft_skills':           soft,
            'validation_percentage': pct,
            'skill_project_mapping': {
                **{v['skill']: v['projects'] for v in validated},
                **{u: [] for u in unvalidated},
            },
            # percentage proven -> lenient curve (50% proven = 75% of the points), then scaled down
            # if fewer than _MIN_PROVEN_SKILLS skills are proven, so 2-of-2 can't look like a strong profile.
            'validation_score':      15.0 * _validation_fraction(pct)
                                     * min(1.0, len(validated) / float(_MIN_PROVEN_SKILLS)),
        }

    if not skills:
        return _result([], [], [])

    soft      = [s for s in skills if _is_soft_skill(s)]
    technical = [s for s in skills if not _is_soft_skill(s)]
    if not technical:
        return _result([], [], soft)

    # Evidence sources: (label, text)
    sources: List[Tuple[str, str]] = []
    for p in projects or []:
        if isinstance(p, dict):
            sources.append((p.get('title') or 'Untitled Project', _project_text(p)))

    # Experience: one source per job so the UI can say which role proves the skill.
    parsed_jobs = 0
    for e in experience_entries or []:
        if isinstance(e, dict):
            text = _flatten({k: v for k, v in e.items()
                             if k not in ('start_date', 'end_date', 'duration_months')}).strip()
            if text:
                title = (e.get('job_title') or '').strip()
                comp  = (e.get('company') or '').strip()
                name  = ' @ '.join(x for x in (title, comp) if x) or 'Role'
                sources.append((f'Experience: {name[:60]}', text))
                parsed_jobs += 1
    # The LLM sometimes misses internships/jobs; fall back to the raw section text.
    if parsed_jobs == 0:
        raw_exp = _extract_section(
            resume_text, r'(?:work |professional )?experience|internships?|employment(?: history)?|work history')
        if raw_exp:
            sources.append(('Experience Section', raw_exp))

    # Achievements / awards / coding profiles: the LLM parser does not extract these, so read the
    # raw section. "Solved 500+ DSA problems on LeetCode" is the evidence for DSA skills.
    raw_ach = _extract_section(
        resume_text,
        r'achievements?|accomplishments?|awards?|honou?rs|achievements?\s*(?:and|&)\s*(?:awards?|activities|honou?rs|certifications?)|'
        r'awards?\s*(?:and|&)\s*(?:achievements?|honou?rs|recognition)|coding profiles?|'
        r'coding achievements?|competitive programming|positions? of responsibility|extracurricular[a-z ]*')
    if raw_ach:
        sources.append(('Achievements Section', raw_ach))

    # Certifications: each one is evidence on its own ("AWS Certified Cloud Practitioner" -> AWS).
    parsed_certs = 0
    for c in certifications or []:
        text = _flatten(c).strip()
        if text:
            sources.append((f'Certification: {text[:60]}', text))
            parsed_certs += 1
    if parsed_certs == 0:
        raw_cert = _extract_section(
            resume_text, r'certifications?|licen[cs]es?(?: (?:and|&) certifications?)?|'
                         r'certifications? (?:and|&) (?:courses|training)|courses|training')
        if raw_cert:
            sources.append(('Certifications Section', raw_cert))

    urls = _URL_RE.findall(resume_text or '')

    status: Dict[str, Dict] = {}
    pending: List[str] = []

    for skill in technical:
        variants = _skill_variants(skill)
        regexes  = [_term_regex(v) for v in variants]
        labels: List[str] = []

        is_dsa = _is_dsa_skill(skill)
        for label, text in sources:
            if label in labels:
                continue
            if any(r.search(text) for r in regexes) or (is_dsa and _DSA_EVIDENCE_RE.search(text)):
                labels.append(label)

        if is_dsa and any(h in u.lower() for u in urls for h in _DSA_URL_HOSTS):
            if 'Coding profile link' not in labels:
                labels.append('Coding profile link')

        if _is_vcs_skill(skill):
            ev = _vcs_evidence(urls, resume_text)
            if ev and ev not in labels:
                labels.append(ev)
        else:
            ev = _link_evidence(variants, urls)
            if ev and ev not in labels:
                labels.append(ev)

        if labels:
            status[skill] = {'skill': skill, 'projects': labels, 'similarity': 1.0}
        else:
            pending.append(skill)

    # Semantic fallback: one batch encode, compare against individual sentences.
    if pending and embedder is not None and sources:
        chunks: List[Tuple[str, str]] = []
        for label, text in sources:
            for part in re.split(r'(?<=[.!?])\s+|\n|;|•', text):
                part = part.strip()
                if len(part) >= 15 or (label.startswith('Certification') and len(part) >= 6):
                    chunks.append((label, part))
        candidates = [s for s in pending if len(s) > 2]
        if chunks and candidates:
            try:
                chunk_vecs = embedder.encode([c[1] for c in chunks], convert_to_numpy=True,
                                             normalize_embeddings=True, show_progress_bar=False)
                skill_vecs = embedder.encode(candidates, convert_to_numpy=True,
                                             normalize_embeddings=True, show_progress_bar=False)
                sims = np.asarray(skill_vecs) @ np.asarray(chunk_vecs).T
                for i, skill in enumerate(candidates):
                    j = int(np.argmax(sims[i]))
                    if float(sims[i][j]) >= threshold:
                        status[skill] = {'skill': skill,
                                         'projects': [f'{chunks[j][0]} (related)'],
                                         'similarity': float(sims[i][j])}
            except Exception as e:
                log_warning(f'Semantic skill validation skipped: {e}', context='ats_scorer')

    validated   = [status[s] for s in technical if s in status]
    unvalidated = [s for s in technical if s not in status]
    return _result(validated, unvalidated, soft)


# -- Grounding & content-depth helpers ---------------------------------------
# The LLM parser can return skills / keywords / jobs that are not in the resume, and generic
# words ("technology", "hardworking") that look like skills. Everything the score counts is
# first checked against the real resume text.

_VAGUE_TERMS = {
    'technology', 'technologies', 'tech', 'computer', 'computers', 'computing', 'it', 'internet',
    'software', 'hardware', 'student', 'students', 'project', 'projects', 'education', 'degree',
    "bachelor's degree", 'bachelors degree', 'bachelor', 'experience', 'resume', 'job', 'company',
    'position', 'learning', 'growth', 'goal', 'hardworking', 'hard working', 'hard-working',
    'sincere', 'dedicated', 'motivated', 'passionate', 'good job', 'reputed company',
}

_WEAK_VERBS = {
    'made', 'make', 'worked', 'work', 'did', 'do', 'done', 'helped', 'help', 'handled', 'assisted',
    'involved', 'completed', 'complete', 'got', 'get', 'used', 'use', 'tried', 'took', 'responsible',
    'participated', 'was', 'were',
}

_GENERIC_RE = re.compile(
    r"\b(?:hard[\s-]?working|sincere|reputed company|good (?:job|position|opportunity)|"
    r"quick learner|fast learner|team player|work(?:ing)? with (?:a )?team|learn(?:ing)? new things|"
    r"looking for (?:a |an )?(?:good|challenging|suitable)|(?:different|various|many|several) things|"
    r"related to (?:computers?|technology)|results?[\s-]oriented|go[\s-]getter|self[\s-]motivated)\b",
    re.IGNORECASE,
)

_ACHIEVEMENT_PATTERNS = [
    r'(?<![\d.])\d[\d,]*(?:\.\d+)?\s*%',                                   # 83.1%, 40 %
    r'[$₹€£]\s?\d[\d,.]*\s*(?:[kKmMbB]\b|lakhs?|crores?)?',                 # $5k, ₹2 lakh
    r'\b\d+(?:\.\d+)?[ ]?[kKmMbB]\b\+?',                                     # 10k, 2M
    r'\b\d+(?:\.\d+)?[ ]?[x×]\b',                                            # 3x faster
    r'\b\d[\d,]*\+?[ \t]*(?:[A-Za-z-]+[ \t]+){0,2}(?:users?|customers?|clients?|projects?|hours?|days?|months?|'
    r'years?|records?|rows|requests?|problems?|questions?|datasets?|images?|models?|apis?|endpoints?|'
    r'services?|students?|members?|engineers?|developers?|orders?|transactions?|participants?|stars|'
    r'downloads|commits|repos|repositories|queries|documents|resumes|samples|tests?)\b',   # 975,800 records, 300+ DSA problems
    r'\b(?:AIR|rank(?:ed)?|top)\b[^\n\d]{0,12}\d[\d,]*',                    # AIR: 18644, top 5
]

_NON_ACHIEVEMENT_SECTIONS = re.compile(
    r'^(?:education|academic|skills?|technical skills?|certifications?|licen[cs]es?|courses?|training|'
    r'languages?|interests?|hobbies|references?)$', re.IGNORECASE)
_ACADEMIC_LINE_RE = re.compile(
    r'\b(?:cgpa|gpa|sgpa|cbse|icse|percentage|class\s+(?:x|xii|10|12)|10th|12th|board)\b', re.IGNORECASE)
_HEADING_RE = re.compile(rf'^\s*({_SECTION_STOP})\s*:?\s*$', re.IGNORECASE)


def _achievement_scope(text: str) -> str:
    """Resume text where achievements can live: drops Education/Skills/Certifications sections and
    academic-score lines (CGPA, 76.6% in Class XII...) so they don't count as achievements."""
    keep, skip = [], False
    for line in (text or '').splitlines():
        m = _HEADING_RE.match(line)
        if m:
            skip = bool(_NON_ACHIEVEMENT_SECTIONS.match(m.group(1).strip()))
            continue
        if skip or _ACADEMIC_LINE_RE.search(line):
            continue
        keep.append(line)
    return '\n'.join(keep)


_IRREGULAR_VERBS = {'built', 'led', 'ran', 'wrote', 'won', 'drove', 'grew', 'cut', 'sent', 'taught', 'found'}
_BULLET_START_RE = re.compile(r'^\s*[•●▪◦·\-\*–]\s*(.+)$')


def _bullet_verbs(text: str) -> List[str]:
    """Action verbs that open a bullet or a sentence inside a bullet ("Built...", "; added...").
    Deterministic, so the verb score doesn't depend on what the LLM chose to list."""
    out, seen = [], set()
    for line in (text or '').splitlines():
        m = _BULLET_START_RE.match(line)
        if not m:
            continue
        for seg in re.split(r'(?<=[.;])\s+', m.group(1)):
            w = re.match(r"[A-Za-z]+", seg.strip())
            if not w:
                continue
            v = w.group(0).lower()
            if v in seen or v in _WEAK_VERBS:
                continue
            if v in _IRREGULAR_VERBS or (v.endswith('ed') and len(v) >= 5):
                seen.add(v)
                out.append(v)
    return out


def generic_phrase_count(text: str) -> int:
    """Number of distinct filler phrases ("hardworking", "reputed company", ...)."""
    return len({m.group(0).lower() for m in _GENERIC_RE.finditer(text or '')})


def _achievement_count(text: str) -> int:
    """Distinct measurable results in the achievement-bearing parts of the resume (overlaps merged)."""
    scope = _achievement_scope(text)
    spans = sorted(m.span() for p in _ACHIEVEMENT_PATTERNS for m in re.finditer(p, scope, re.IGNORECASE))
    merged = []
    for s, e in spans:
        if merged and s < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return len(merged)


def _norm_term(t) -> str:
    return re.sub(r'\s+', ' ', str(t).strip().lower())


def _appears_in(term: str, text: str) -> bool:
    if not _norm_term(term):
        return False
    return any(_term_regex(v).search(text) for v in _skill_variants(term))


def _tokens_in(term: str, text: str) -> bool:
    """All significant words of `term` (plural-tolerant) occur in the text."""
    toks = re.findall(r'[a-z0-9+#]{3,}', str(term).lower())
    low = (text or '').lower()
    return bool(toks) and all(re.search(r'\b' + re.escape(t.rstrip('s')), low) for t in toks)


def _has_experience_heading(text: str) -> bool:
    for line in (text or '').splitlines():
        s = line.strip()
        if not s or s[0] in '•-*◦▪' or s.endswith('.') or len(s.split()) > 5:
            continue
        if re.search(r'\b(?:experience|internships?|employment|work history)\b', s, re.IGNORECASE):
            return True
    return False


def ground_parsed_resume(parsed: Dict, resume_text: str) -> Dict:
    """Return a copy of the LLM-parsed resume containing only what the text actually supports.

    Drops: terms not present in the resume text, vague/filler terms, weak action verbs, experience
    entries when the resume has no experience section, and project technologies that aren't in
    the text. Adds 'technical_skills' (skills minus soft skills)."""
    import copy
    p = copy.deepcopy(parsed or {})
    text = resume_text or ''
    low = text.lower()
    dropped: Dict[str, int] = {}

    def _keep(items, key, loose=False):
        out, seen, n_dropped = [], set(), 0
        for t in items or []:
            t = str(t).strip()
            k = _norm_term(t)
            if not k or k in seen:
                continue
            seen.add(k)
            if (k in _VAGUE_TERMS or generic_phrase_count(t)
                    or not (_appears_in(t, text) or (loose and _tokens_in(t, text)))):
                n_dropped += 1
                continue
            out.append(t)
        dropped[key] = dropped.get(key, 0) + n_dropped
        return out

    p['skills']       = _keep(p.get('skills'), 'skills')
    p['keywords']     = _keep(p.get('keywords'), 'keywords', loose=True)
    llm_verbs = [v for v in _keep(p.get('action_verbs'), 'action_verbs')
                 if _norm_term(v) not in _WEAK_VERBS]
    have = {_norm_term(v) for v in llm_verbs}
    p['action_verbs'] = llm_verbs + [v for v in _bullet_verbs(text) if v not in have]
    p['technical_skills'] = [s for s in p['skills'] if not _is_soft_skill(s)]

    # Experience: only believable when the resume has an experience/internship heading and the
    # company or job title really appears in the text.
    exps = [e for e in (p.get('experience') or []) if isinstance(e, dict)]
    has_heading = _has_experience_heading(text)
    kept = []
    for e in exps:
        title = (e.get('job_title') or '').strip().lower()
        comp  = (e.get('company') or '').strip().lower()
        if has_heading and ((comp and comp in low) or (title and title in low)):
            kept.append(e)
    dropped['experience'] = len(exps) - len(kept)
    p['experience'] = kept

    # Projects: title must appear in the text; technologies must be real, specific terms.
    projects = []
    for pr in (p.get('projects') or []):
        if not isinstance(pr, dict):
            continue
        title = (pr.get('title') or '').strip().lower()
        if title and title not in low:
            dropped['projects'] = dropped.get('projects', 0) + 1
            continue
        techs = pr.get('technologies') or []
        if isinstance(techs, str):
            techs = [techs]
        pr['technologies'] = [t for t in techs
                              if _norm_term(t) not in _VAGUE_TERMS and _appears_in(str(t), text)]
        projects.append(pr)
    p['projects'] = projects

    p['_grounding_dropped'] = dropped
    return p


def _substantive_project(p: Dict) -> bool:
    """A project counts only if it says what was built (>=40 chars) AND with what (a real technology)."""
    return (len(str(p.get('description') or '')) >= 40) and bool(p.get('technologies'))


def assess_content_depth(parsed_resume: Dict, text: str, technical_skills: List[str]) -> Dict:
    projects = [p for p in parsed_resume.get('projects', []) if isinstance(p, dict)]
    exps     = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    evidence = [_project_text(p) for p in projects] + [
        _flatten({k: v for k, v in e.items() if k not in ('start_date', 'end_date', 'duration_months')})
        for e in exps
    ]
    tech_named = any(p.get('technologies') for p in projects) or any(
        _appears_in(s, ev) for s in technical_skills for ev in evidence
    )
    return {
        'tech_named':    tech_named,
        'generic_count': generic_phrase_count(text),
        'achievements':  _achievement_count(text),
        'word_count':    len((text or '').split()),
        'has_experience': bool(exps),
    }


#01: formatting score
def _calc_formatting_score(parsed_resume: Dict, text: str) -> float:

    score = 0.0

    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education', [])  if isinstance(e, dict)]
    skills       = parsed_resume.get('skills', [])
    summary      = parsed_resume.get('professional_summary', '')
    proj_entries = [p for p in parsed_resume.get('projects', [])   if isinstance(p, dict)]
    proj_ok      = [p for p in proj_entries if _substantive_project(p)]
    summary_ok   = len(summary) > 30 and generic_phrase_count(summary) < 2

    if exp_entries and any(e.get('job_title') or e.get('description') for e in exp_entries):
        score += 3.0
    if edu_entries:
        score += 2.0
    if len(skills) >= 3:
        score += 2.0
    if summary_ok:
        score += 1.5
    if proj_ok:
        score += 1.5

    bullet_count = sum(
        1 for line in text.split('\n')
        if re.match(r'^\s*[•\-\*\◦]', line) or re.match(r'^\s*\d+\.', line)
    )
    score += _tier_score(bullet_count, [(15,5.0),(10,4.0),(5,3.0),(3,2.0),(1,1.0)])

    filled = sum(1 for has_it in [
        bool(exp_entries), bool(edu_entries), bool(skills),
        summary_ok, bool(proj_ok),
    ] if has_it)
    score += _tier_score(filled, [(4,5.0),(3,4.0),(2,3.0),(1,2.0)])

    return min(20.0, max(0.0, score))

#02 keyword score
def _calc_keywords_score(
    resume_keywords: List[str],
    skills: List[str],
    jd_keywords: Optional[List[str]] = None,
) -> float:
    score = 0.0

    score += _tier_score(len(resume_keywords), [(20,10.0),(15,8.0),(10,6.0),(5,4.0),(3,2.0)])
    score += _tier_score(len(skills),          [(15,10.0),(10,8.0),(7,6.0),(5,4.0),(3,2.0)])

    if jd_keywords:
        all_resume_terms = list(set(resume_keywords + skills))
        fuzzy_result     = fuzzy_match_keywords(all_resume_terms, jd_keywords, threshold=80)
        match_pct        = len(fuzzy_result['matched']) / len(jd_keywords) if jd_keywords else 0
        score += _tier_score(match_pct, [(0.7,5.0),(0.5,4.0),(0.3,3.0),(0.2,2.0),(0.1,1.0)])
    
    elif len(resume_keywords) >= 10:
        score += 3.0

    return min(25.0, max(0.0, score))

#3. CONTENT QUALITY SCORE
def _calc_content_score(
    text: str,
    action_verbs: List[str],
    grammar_results: Dict,
) -> float:

    score = 0.0

    score += min(10.0, float(len(action_verbs)))          # 1 point per distinct strong verb, 10 verbs = full marks
    score += _tier_score(_achievement_count(text), [(8,5.0),(6,4.0),(4,3.0),(2,2.0),(1,1.0)])   # 8 measurable results = full marks

    if grammar_results.get('_component_status') == 'unavailable':
        # No grammar check ran, so don't hand out its 10 points: rescale verbs+metrics (max 15) to 25.
        score = score / 15.0 * 25.0
    else:
        grammar_penalty = grammar_results.get('penalty_applied', 0.0)
        score += max(0.0, 10.0 - grammar_penalty / 2.0)

    return min(25.0, max(0.0, score))

#4. SKILL VALIDATION SCORE
def _calc_skill_validation_score(validation_results: Dict) -> float:
    return min(15.0, max(0.0, validation_results.get('validation_score', 0.0)))

#5. ATS COMPATIBILITY SCORE
def _calc_ats_compatibility_score(
    text: str,
    location_results: Dict,
    parsed_resume: Dict,
) -> float:
    """Points are earned (max 15): contact info 5, real sections 4, clean characters 2, length 4."""
    text  = text or ''
    score = 0.0

    # contact info (5)
    if re.search(r'[\w.+-]+@[\w-]+\.[\w.-]+', text):
        score += 2.0
    if re.search(r'\+?\d[\d\s().-]{8,}\d', text):
        score += 1.0
    if re.search(r'linkedin\.com|github\.com|gitlab\.com|portfolio', text, re.IGNORECASE):
        score += 2.0

    # sections with real content (4)
    exp_entries  = [e for e in parsed_resume.get('experience', []) if isinstance(e, dict)]
    edu_entries  = [e for e in parsed_resume.get('education', [])  if isinstance(e, dict)]
    proj_entries = [p for p in parsed_resume.get('projects', [])   if isinstance(p, dict)]
    exp_ok = any(len((e.get('description') or '') + (e.get('job_title') or '')) >= 20 for e in exp_entries)
    edu_ok = any(len((e.get('degree') or '') + (e.get('institution') or '')) >= 30 for e in edu_entries)
    skl_ok = len(parsed_resume.get('technical_skills', parsed_resume.get('skills', []))) >= 3
    prj_ok = any(_substantive_project(p) for p in proj_entries)
    score += sum([exp_ok, edu_ok, skl_ok, prj_ok])

    # parser-hostile characters (2)
    special_chars = len(re.findall(r'[│┤├┼┴┬╔╗╚╝═║╠╣╦╩╬]', text))
    score += 0.0 if special_chars > 20 else (1.0 if special_chars > 10 else 2.0)

    # enough text to be a real resume (4)
    score += _tier_score(len(text.split()), [(400, 4.0), (250, 3.0), (150, 2.0), (80, 1.0)])

    # location/privacy deduction (only when the check actually ran)
    score -= location_results.get('penalty_applied', 0.0)

    return min(15.0, max(0.0, score))

#Score aggregation and final interpretation
def calculate_overall_score(
    text: str,
    parsed_resume: Dict,
    skills: List[str],
    keywords: List[str],
    action_verbs: List[str],
    skill_validation_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
    jd_keywords: Optional[List[str]] = None,
    experience_months: int = 0,
) -> Dict:

    grammar_ok = grammar_results.get('_component_status') != 'unavailable'

    formatting_score        = _calc_formatting_score(parsed_resume, text)
    keywords_score          = _calc_keywords_score(keywords, skills, jd_keywords)
    content_score           = _calc_content_score(text, action_verbs, grammar_results)
    skill_validation_score  = _calc_skill_validation_score(skill_validation_results)
    ats_compatibility_score = _calc_ats_compatibility_score(text, location_results, parsed_resume)

    COMPONENT_MAX = {
        'formatting': 20.0, 'keywords': 25.0, 'content': 25.0,
        'skill_validation': 15.0, 'ats_compatibility': 15.0,
    }

    formatting_pct        = (formatting_score        / COMPONENT_MAX['formatting'])        * 100.0
    keywords_pct          = (keywords_score          / COMPONENT_MAX['keywords'])          * 100.0
    content_pct           = (content_score           / COMPONENT_MAX['content'])           * 100.0
    skill_validation_pct  = (skill_validation_score  / COMPONENT_MAX['skill_validation'])  * 100.0
    ats_compatibility_pct = (ats_compatibility_score / COMPONENT_MAX['ats_compatibility']) * 100.0

    skills_keywords_pct = (keywords_pct * 0.6) + (skill_validation_pct * 0.4)

    base_score = (
        skills_keywords_pct   * 0.40 +
        content_pct           * 0.30 +
        formatting_pct        * 0.15 +
        ats_compatibility_pct * 0.15
    )

    penalties = {}
    bonuses   = {}
    score     = base_score

    if grammar_ok and grammar_results.get('penalty_applied', 0.0) > 0:
        penalties['grammar'] = grammar_results['penalty_applied']

    if location_results.get('penalty_applied', 0.0) > 0:
        penalties['location_privacy'] = location_results['penalty_applied']

    # filler language ("hardworking", "reputed company", "different things" ...)
    depth = assess_content_depth(parsed_resume, text, skills)
    filler_penalty = min(6.0, max(0, depth['generic_count'] - 2) * 2.0)
    if filler_penalty > 0:
        penalties['generic_filler_language'] = filler_penalty
        score -= filler_penalty

    validation_pct = skill_validation_results.get('validation_percentage', 0.0)
    n_validated    = len(skill_validation_results.get('validated_skills', []))
    if validation_pct >= 0.9 and n_validated >= _MIN_PROVEN_SKILLS:
        bonuses['excellent_skill_validation'] = 2.0
        score += 2.0
    elif validation_pct >= 0.8 and n_validated >= _MIN_PROVEN_SKILLS:
        bonuses['good_skill_validation'] = 1.0
        score += 1.0

    if grammar_ok and grammar_results.get('total_errors', 0) == 0:
        bonuses['perfect_grammar'] = 1.0
        score += 1.0

    if jd_keywords and len(jd_keywords) > 0:
        all_resume_terms = list(set((keywords or []) + (skills or [])))
        jd_match         = match_terms_against_resume(jd_keywords, text, all_resume_terms)
        considered       = len(jd_match['matched']) + len(jd_match['missing'])   # generic filler excluded
        missing_pct      = (len(jd_match['missing']) / considered) if considered else 0.0

        if missing_pct > 0.7:
            penalties['missing_jd_keywords'] = 15.0
            score -= 15.0
        elif missing_pct > 0.5:
            penalties['missing_jd_keywords'] = 10.0
            score -= 10.0
        elif missing_pct > 0.3:
            penalties['missing_jd_keywords'] = 5.0
            score -= 5.0

    score_before_caps = min(100.0, max(0.0, score))

    # Hard ceilings: a weighted sum can't rescue a resume that lacks the basics.
    caps = {}
    if not skills and not depth['has_experience']:
        caps['no_technical_skills_or_experience'] = 30.0
    if depth['word_count'] < 120:
        caps['very_short_resume'] = 30.0
    elif depth['word_count'] < 200:
        caps['short_resume'] = 55.0
    if not depth['tech_named']:
        caps['no_technology_in_projects_or_experience'] = 40.0
    if depth['achievements'] == 0:
        caps['no_quantified_achievements'] = 65.0
    if skills and len(skill_validation_results.get('validated_skills', [])) < 3:
        caps['skills_not_evidenced'] = 55.0

    overall_score = min([score_before_caps] + list(caps.values()))
    interpretation = _generate_score_interpretation(overall_score)

    return {
        'overall_score':           round(overall_score, 1),
        'formatting_score':        round(formatting_score, 1),
        'keywords_score':          round(keywords_score, 1),
        'content_score':           round(content_score, 1),
        'skill_validation_score':  round(skill_validation_score, 1),
        'ats_compatibility_score': round(ats_compatibility_score, 1),
        'overall_interpretation':  interpretation,
        'penalties':               penalties,
        'bonuses':                 bonuses,
        'score_before_caps':       round(score_before_caps, 1),
        'caps_applied':            caps,}

#Overall score calculation and interpretation
def generate_strengths(
    score_results: Dict,
    skill_validation_results: Dict,
    grammar_results: Dict,
) -> List[str]:

    strengths = []

    if score_results['formatting_score']       >= 16:
        strengths.append(' Well-structured with clear sections and bullet points')
    if score_results['keywords_score']          >= 20:
        strengths.append(' Strong keyword optimization and skills presence')
    if score_results['content_score']           >= 20:
        strengths.append(' Excellent use of action verbs and quantifiable achievements')
    if score_results['skill_validation_score']  >= 12:
        pct = skill_validation_results.get('validation_percentage', 0) * 100
        strengths.append(f' {pct:.0f}% of skills are validated by projects')
    if score_results['ats_compatibility_score'] >= 13:
        strengths.append(' Excellent ATS compatibility with clean formatting')
    if grammar_results.get('_component_status') != 'unavailable' and grammar_results.get('total_errors', 0) == 0:
        strengths.append(' Error-free grammar and spelling')

    if not strengths:
        strengths.append('Your resume has potential - focus on the recommendations below')
    return strengths


#Critical issues that could cause ATS rejection
def generate_critical_issues(
    score_results: Dict,
    grammar_results: Dict,
    location_results: Dict,
) -> List[str]:
    issues = []

    critical_errors = len(grammar_results.get('critical_errors', []))
    if critical_errors > 0:
        issues.append(f' {critical_errors} critical grammar/spelling error(s) detected')
    if location_results.get('privacy_risk') == 'high':
        issues.append('High privacy risk: Remove detailed location information')
    if score_results['formatting_score']       < 10:
        issues.append(' Poor formatting: Add clear sections and bullet points')
    if score_results['keywords_score']         < 12:
        issues.append(' Insufficient keywords and skills')
    if score_results['skill_validation_score'] < 7:
        issues.append(' Most skills lack supporting evidence in projects')

    return issues


#Actionable improvements to enhance ATS performance
def generate_improvements(
    score_results: Dict,
    skill_validation_results: Dict,
) -> List[str]:
    improvements = []

    if 12 <= score_results['formatting_score']       < 16:
        improvements.append('Add more bullet points and improve section organization')
    if 14 <= score_results['keywords_score']          < 20:
        improvements.append('Include more relevant keywords and technical skills')
    if 14 <= score_results['content_score']           < 20:
        improvements.append('Add more quantifiable achievements and action verbs')
    if 7  <= score_results['skill_validation_score']  < 12:
        unvalidated_count = len(skill_validation_results.get('unvalidated_skills', []))
        improvements.append(f'Validate {unvalidated_count} skill(s) by adding relevant project details')
    if 9  <= score_results['ats_compatibility_score'] < 13:
        improvements.append('Simplify formatting for better ATS compatibility')

    return improvements

#Interpretation of overall score
def _generate_score_interpretation(overall_score: float) -> str:
    if overall_score >= 90:    return 'Excellent! Your resume is highly optimized for ATS systems.'
    elif overall_score >= 80:  return 'Great! Your resume should perform well with most ATS systems.'
    elif overall_score >= 70:  return 'Good! Your resume is ATS-friendly with room for minor improvements.'
    elif overall_score >= 60:  return 'Fair. Your resume needs some improvements to be fully ATS-compatible.'
    elif overall_score >= 50:  return 'Below Average. Significant improvements needed for ATS compatibility.'
    else:                      return 'Poor. Your resume requires major revisions to pass ATS screening.'