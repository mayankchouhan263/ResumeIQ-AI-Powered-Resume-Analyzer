"""Cheap, offline check that an uploaded document is actually a resume.

Runs BEFORE any LLM call, so non-resumes (papers, invoices, job descriptions, cover
letters, books...) are rejected with a clear message instead of getting a meaningless
low score, or burning tokens and hitting Groq's rate limit.
"""
import os
import re
from dataclasses import dataclass, field
from typing import Dict, List

# -- section headings (a heading is a short line that is just the section name) --------
_SECTION_PATTERNS: Dict[str, str] = {
    'summary':        r'(?:professional |career |executive )?(?:summary|profile|objective)|career objective|about me|personal statement',
    'education':      r'education(?:al)?(?: (?:background|qualifications?|details))?|academics?(?: (?:background|qualifications?|profile))?|academic qualifications?',
    'experience':     r'(?:work|professional|relevant|industrial|industry|internship)? ?experience|employment(?: history)?|work history|internships?|career history',
    'skills':         r'(?:technical |core |key |it )?skills?(?: summary| set)?|technical proficiency|core competencies|technologies|tools(?: (?:and|&) technologies)?|tech stack',
    'projects':       r'(?:academic |personal |key |major |selected |technical )?projects?',
    'certifications': r'certifications?|certificates?|licen[cs]es?(?: (?:and|&) certifications?)?|courses|training|courses? (?:and|&) certifications?',
    'achievements':   r'achievements?|accomplishments?|awards?(?: (?:and|&) (?:honou?rs|achievements?|recognition))?|honou?rs|extra-?curricular(?: activities)?|activities|positions? of responsibility|leadership|volunteer(?:ing)?(?: experience)?|publications?|languages?|interests|hobbies|coding profiles?|competitive programming',
}
_SECTION_RES = {k: re.compile(rf'^[\W_]*(?:{v})[\W_]*$', re.IGNORECASE) for k, v in _SECTION_PATTERNS.items()}
# "Achievements & Certifications", "Skills and Tools" ...
_COMBINED_RE = re.compile(r'^[\W_]*([a-z ]{3,25})\s*(?:&|and|/)\s*([a-z ]{3,25})[\W_]*$', re.IGNORECASE)

_EMAIL_RE   = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
_PHONE_RE   = re.compile(r'(?<!\d)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3,5}\)?[\s.-]?)\d{3,5}[\s.-]?\d{3,5}(?!\d)')
_LINK_RE    = re.compile(r'linkedin\.com|github\.com|gitlab\.com|kaggle\.com|leetcode\.com|portfolio|behance\.net', re.IGNORECASE)
_DATE_RANGE = re.compile(
    r'(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?(?:19|20)\d{2}\s*(?:-|–|—|to)\s*'
    r'(?:(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?\s+)?(?:19|20)\d{2}|present|current|ongoing|now)',
    re.IGNORECASE)
_YEAR_RE    = re.compile(r'\b(?:19|20)\d{2}\b')
_DEGREE_RE  = re.compile(r'\b(?:b\.?\s?tech|m\.?\s?tech|b\.?e\.?|b\.?sc|m\.?sc|b\.?a\.?|m\.?a\.?|bca|mca|mba|bachelor|master|ph\.?d|diploma|cgpa|gpa|percentage|class\s+(?:x|xii|10|12)|hsc|ssc|cbse|university|college|institute)\b', re.IGNORECASE)
_BULLET_RE  = re.compile(r'^\s*(?:[•●▪■◦➢➤►▶\-–—*·]|\d+[.)])\s+\S')
_ACTION_RE  = re.compile(r'\b(?:developed|built|designed|implemented|created|led|managed|improved|deployed|integrated|optimi[sz]ed|achieved|engineered|collaborated|analy[sz]ed|trained|automated)\b', re.IGNORECASE)

# things that are clearly NOT a resume
_JD_MARKERS = re.compile(
    r'\b(?:responsibilities|requirements|qualifications|what we offer|what you.ll do|who you are|about the (?:role|job|team|company|position)|'
    r'we are (?:looking|hiring)|apply (?:now|today)|equal opportunity|job (?:type|description|summary|title)|benefits|perks|'
    r'about us|nice to have|preferred qualifications|years of experience required|the ideal candidate|you will)\b', re.IGNORECASE)
_COVER_MARKERS = re.compile(r'\b(?:dear (?:sir|madam|hiring|recruiter|team)|sincerely|yours (?:faithfully|sincerely)|i am writing (?:to|in)|kind regards|respected sir)\b', re.IGNORECASE)
_OTHER_MARKERS = re.compile(
    r'\b(?:abstract|table of contents|chapter\s+\d+|invoice(?: no| number|#)?|bill to|terms and conditions|lorem ipsum|all rights reserved|'
    r'copyright|et al\.|doi:|isbn|purchase order|receipt|ingredients|preheat|syllabus|question paper|marks obtained|hall ticket|admit card)\b', re.IGNORECASE)

PASS_SCORE = 40


@dataclass
class ResumeVerdict:
    is_resume: bool
    score: int
    kind: str                          # resume | job_description | cover_letter | too_short | too_long | other
    message: str = ''
    sections_found: List[str] = field(default_factory=list)
    signals: Dict[str, object] = field(default_factory=dict)


def _find_sections(lines: List[str]) -> List[str]:
    found: List[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or len(line) > 48 or len(line.split()) > 6:
            continue
        for name, rx in _SECTION_RES.items():
            if rx.match(line):
                if name not in found:
                    found.append(name)
                break
        else:
            m = _COMBINED_RE.match(line)
            if m:
                for part in m.groups():
                    for name, rx in _SECTION_RES.items():
                        if rx.match(part.strip()) and name not in found:
                            found.append(name)
    return found


def assess_resume(text: str) -> ResumeVerdict:
    if os.getenv('RESUME_CHECK', 'on').strip().lower() in ('off', '0', 'false', 'no'):
        return ResumeVerdict(True, 100, 'resume')

    text = text or ''
    words = len(re.findall(r'\w+', text))

    if len(text.strip()) < 100 or words < 25:
        return ResumeVerdict(
            False, 0, 'too_short',
            'There is almost no readable text in this file, so I can\'t analyze it. If it is a scanned or '
            'image-only PDF, export your resume as a text-based PDF or DOCX and try again.',
            signals={'words': words})

    lines = [l for l in text.splitlines() if l.strip()]
    sections = _find_sections(lines)
    has_email = bool(_EMAIL_RE.search(text))
    has_phone = bool(_PHONE_RE.search(text))
    has_link  = bool(_LINK_RE.search(text))
    date_ranges = len(_DATE_RANGE.findall(text))
    years = len(_YEAR_RE.findall(text))
    degree = bool(_DEGREE_RE.search(text))
    bullets = sum(1 for l in lines if _BULLET_RE.match(l))
    actions = len(_ACTION_RE.findall(text))
    jd_hits = len({m.group(0).lower() for m in _JD_MARKERS.finditer(text)})
    cover_hits = len({m.group(0).lower() for m in _COVER_MARKERS.finditer(text)})
    other_hits = len({m.group(0).lower() for m in _OTHER_MARKERS.finditer(text)})
    avg_words_per_line = words / max(len(lines), 1)

    score = 0
    score += min(len(sections), 5) * 12
    score += 10 if has_email else 0
    score += 8 if has_phone else 0
    score += 4 if has_link else 0
    score += 8 if date_ranges else (4 if years >= 2 else 0)
    score += 5 if degree else 0
    score += 5 if bullets >= 3 else 0
    score += 3 if actions >= 2 else 0

    # penalties
    if other_hits:
        score -= min(other_hits, 2) * 15
    if cover_hits:
        score -= 20
    if jd_hits >= 3:
        score -= 25
    if avg_words_per_line > 18 and bullets < 3:
        score -= 15                                   # long paragraphs of prose
    if words > 5000:
        score -= 30
    elif words > 3000:
        score -= 10

    signals = {'words': words, 'sections': sections, 'email': has_email, 'phone': has_phone, 'links': has_link,
               'date_ranges': date_ranges, 'bullets': bullets, 'jd_markers': jd_hits,
               'cover_markers': cover_hits, 'other_markers': other_hits}
    score = max(0, min(100, score))

    if score >= PASS_SCORE:
        return ResumeVerdict(True, score, 'resume', sections_found=sections, signals=signals)

    # decide what it most likely is, to give a useful message
    if jd_hits >= 3 and not (has_email and has_phone):
        kind, msg = 'job_description', ('This looks like a job description, not a resume. Upload your resume here, and paste '
                                        'the job description into the "Job Description" box in JD Comparison mode.')
    elif cover_hits:
        kind, msg = 'cover_letter', ('This looks like a cover letter rather than a resume. Please upload your resume '
                                     '(Education, Experience/Projects, Skills...).')
    elif words > 3000:
        kind, msg = 'too_long', (f'This document is very long (about {words:,} words) and doesn\'t read like a resume. '
                                 'Resumes are usually 1-2 pages. Please upload your resume.')
    else:
        found = ', '.join(s.title() for s in sections) if sections else 'none'
        contact = 'no email or phone number' if not (has_email or has_phone) else 'some contact details'
        kind, msg = 'other', ('This doesn\'t look like a resume . '
                              f'I found {len(sections)} of the usual resume sections ({found}) and {contact}. '
                              'Please upload your resume as a PDF or DOCX with headings such as Education, '
                              'Experience or Projects, and Skills.')
    return ResumeVerdict(False, score, kind, msg, sections, signals)
