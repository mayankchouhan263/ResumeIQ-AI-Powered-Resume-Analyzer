from typing import Dict, List, Optional

import numpy as np
import spacy

from backend.services.embedder import OnnxEmbedder
from backend.utils.matching import match_terms_against_resume


def calculate_semantic_similarity(
    resume_text: str, jd_text: str, embedder: OnnxEmbedder
) -> float:
    resume_emb = embedder.encode(resume_text[:5000], convert_to_tensor=False)
    jd_emb     = embedder.encode(jd_text[:5000], convert_to_tensor=False)

    similarity = np.dot(resume_emb, jd_emb) / (
        np.linalg.norm(resume_emb) * np.linalg.norm(jd_emb)
    )
    return float(np.clip(similarity, 0.0, 1.0))


def identify_matched_keywords(
    resume_keywords: List[str], jd_keywords: List[str], resume_text: str = ''
) -> List[str]:
    return match_terms_against_resume(jd_keywords, resume_text, resume_keywords)['matched']


def identify_missing_keywords(
    resume_keywords: List[str], jd_keywords: List[str], resume_text: str = '', top_n: int = 15
) -> List[str]:
    return match_terms_against_resume(jd_keywords, resume_text, resume_keywords)['missing'][:top_n]


def _noun_chunk_candidates(jd_text: str, nlp: spacy.Language) -> List[str]:
    """Fallback only (used when the LLM returned no required/preferred skills): proper-noun phrases,
    i.e. product / language / tool names. Plain nouns such as 'a degree' or 'building' are not skills."""
    doc = nlp(jd_text[:5000])
    candidates = set()
    for ent in doc.ents:
        if ent.label_ in ('PRODUCT', 'ORG', 'LANGUAGE'):
            candidates.add(ent.text.strip())
    for chunk in doc.noun_chunks:
        toks = [t for t in chunk if not (t.is_stop or t.is_punct or t.like_num)]
        if toks and len(toks) <= 4 and any(t.pos_ == 'PROPN' for t in toks):
            candidates.add(' '.join(t.text for t in toks))
    return sorted(candidates)


def analyze_skills_gap(
    resume_skills: List[str],
    jd_text: str,
    nlp: spacy.Language,
    jd_required_skills: Optional[List[str]] = None,
    jd_preferred_skills: Optional[List[str]] = None,
    resume_text: str = '',
    limit: int = 20,
) -> List[str]:
    """Skills the JD asks for that the resume does not show. Required skills come first."""
    text = resume_text or ' '.join(resume_skills)

    if jd_required_skills or jd_preferred_skills:
        required  = match_terms_against_resume(jd_required_skills or [], text, resume_skills)['missing']
        have      = {t.lower() for t in required}
        preferred = [t for t in match_terms_against_resume(jd_preferred_skills or [], text, resume_skills)['missing']
                     if t.lower() not in have]
        return (required + [f'{t} (nice to have)' for t in preferred])[:limit]

    return match_terms_against_resume(_noun_chunk_candidates(jd_text, nlp), text, resume_skills)['missing'][:limit]


def calculate_match_percentage(
    resume_keywords: List[str],
    jd_keywords: List[str],
    semantic_similarity: float,
    resume_text: str = '',
) -> float:
    if not jd_keywords:
        return 0.0
    m = match_terms_against_resume(jd_keywords, resume_text, resume_keywords)
    considered = len(m['matched']) + len(m['missing'])          # generic filler is not counted
    keyword_overlap = (len(m['matched']) / considered) if considered else semantic_similarity
    match_pct = (keyword_overlap * 0.6 + semantic_similarity * 0.4) * 100
    return float(np.clip(match_pct, 0.0, 100.0))


def compare_resume_with_jd(
    resume_text: str,
    resume_keywords: List[str],
    resume_skills: List[str],
    jd_text: str,
    jd_keywords: List[str],
    embedder: OnnxEmbedder,
    nlp: spacy.Language,
    jd_required_skills: Optional[List[str]] = None,
    jd_preferred_skills: Optional[List[str]] = None,
) -> Dict:
    semantic_similarity = calculate_semantic_similarity(resume_text, jd_text, embedder)
    resume_terms        = list(resume_keywords) + list(resume_skills)
    matched_keywords    = identify_matched_keywords(resume_terms, jd_keywords, resume_text)
    missing_keywords    = identify_missing_keywords(resume_terms, jd_keywords, resume_text)
    skills_gap          = analyze_skills_gap(
        resume_skills, jd_text, nlp, jd_required_skills, jd_preferred_skills, resume_text
    )
    match_percentage    = calculate_match_percentage(
        resume_terms, jd_keywords, semantic_similarity, resume_text
    )

    return {
        'match_percentage':    match_percentage,
        'semantic_similarity': semantic_similarity,
        'matched_keywords':    matched_keywords,
        'missing_keywords':    missing_keywords,
        'skills_gap':          skills_gap,
    }
