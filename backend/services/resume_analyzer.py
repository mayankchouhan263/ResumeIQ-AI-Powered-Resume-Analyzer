import spacy
from backend.services.embedder import OnnxEmbedder
from typing import Dict, List, Optional
from backend.models.schemas import IssueDetail
from backend.services.groq_parser import parse_resume, parse_job_description, dedupe_terms
from backend.services.jd_matcher import compare_resume_with_jd
from backend.services.feedback_engine import analyze_issues, generate_issues_summary
from backend.services.ats_scorer import (
    calculate_overall_score, validate_skills_with_projects,
    ground_parsed_resume, detect_location_info, generic_phrase_count, _substantive_project,
)


def analyze_full_resume(
    resume_text: str,
    nlp: spacy.Language,
    embedder: OnnxEmbedder,
    job_description: Optional[str] = None,
) -> Dict:
    import logging
    logger = logging.getLogger('ats_resume_scorer')
    parsed_resume = parse_resume(resume_text)
    # Keep only what the resume text actually supports (the LLM can invent skills/jobs).
    parsed_resume = ground_parsed_resume(parsed_resume, resume_text)
    logger.info(f"Grounding dropped: {parsed_resume.get('_grounding_dropped')}")
    logger.info(f"Groq parsed summary: {parsed_resume.get('professional_summary', '')[:100]!r}")
    logger.info(f"Groq parsed skills count: {len(parsed_resume.get('skills', []))}")
    logger.info(f"Groq parsed experience count: {len(parsed_resume.get('experience', []))}")

    skills          = parsed_resume.get('skills', [])            # shown to the user (includes soft skills)
    technical_skills = parsed_resume.get('technical_skills', skills)  # what the score counts
    projects        = parsed_resume.get('projects', [])
    keywords        = parsed_resume.get('keywords', [])
    action_verbs    = parsed_resume.get('action_verbs', [])

    experience_months = sum(
        int(e.get('duration_months', 0))
        for e in parsed_resume.get('experience', [])
        if isinstance(e, dict)
    )

    contact_info = {
        'email':     parsed_resume.get('email'),
        'phone':     parsed_resume.get('phone'),
        'linkedin':  parsed_resume.get('linkedin'),
        'github':    parsed_resume.get('github'),
        'portfolio': None,
    }
    skill_validation = validate_skills_with_projects(
        skills=skills,
        projects=projects,
        experience_entries=parsed_resume.get('experience', []),
        embedder=embedder,
        resume_text=resume_text,
        certifications=parsed_resume.get('certifications', []),
    )

    jd_comparison_result = None
    jd_keywords = None
    if job_description and job_description.strip():
        parsed_jd = parse_job_description(job_description.strip())
        jd_required  = parsed_jd.get('required_skills', [])
        jd_preferred = parsed_jd.get('preferred_skills', [])
        jd_keywords = dedupe_terms(                      # required skills first, so they lead the lists
            jd_required + jd_preferred + parsed_jd.get('keywords', [])
        )
        jd_comparison_result = compare_resume_with_jd(
            resume_text=resume_text,
            resume_keywords=keywords,
            resume_skills=skills,
            jd_text=job_description.strip(),
            jd_keywords=jd_keywords,
            embedder=embedder,
            nlp=nlp,
            jd_required_skills=jd_required,
            jd_preferred_skills=jd_preferred,
        )

    from backend.utils.file_utils import (
        get_default_grammar_results, get_default_location_results,
    )
    grammar_results  = get_default_grammar_results()   # no grammar checker wired in yet; scorer rescales
    try:
        location_results = detect_location_info(resume_text, nlp)
    except Exception as exc:
        logger.warning(f'Location detection failed, skipping: {exc}')
        location_results = get_default_location_results()

    scores = calculate_overall_score(
        text=resume_text,
        parsed_resume=parsed_resume,
        skills=technical_skills,
        keywords=keywords,
        action_verbs=action_verbs,
        skill_validation_results=skill_validation,
        grammar_results=grammar_results,
        location_results=location_results,
        jd_keywords=jd_keywords,
        experience_months=experience_months,
    )
    logger.info(
        'SCORE BREAKDOWN overall=%s before_caps=%s components=%s caps=%s penalties=%s bonuses=%s '
        'skills_kept=%d validated=%d/%d verbs=%d keywords=%d experience=%d dropped_by_grounding=%s',
        scores['overall_score'], scores.get('score_before_caps'),
        {k: scores[k] for k in ('formatting_score', 'keywords_score', 'content_score',
                                'skill_validation_score', 'ats_compatibility_score')},
        scores.get('caps_applied'), scores.get('penalties'), scores.get('bonuses'),
        len(technical_skills), len(skill_validation.get('validated_skills', [])),
        len(skill_validation.get('validated_skills', [])) + len(skill_validation.get('unvalidated_skills', [])),
        len(action_verbs), len(keywords), len(parsed_resume.get('experience', [])),
        parsed_resume.get('_grounding_dropped'),
    )
    detailed_feedback = analyze_issues(
        resume_text=resume_text,
        parsed_resume=parsed_resume,
        skills=skills,
        projects=projects,
        action_verbs=action_verbs,
        skill_validation=skill_validation,
        scores=scores,
        contact_info=contact_info,
    )

    issues_summary = generate_issues_summary(detailed_feedback)

    validated_raw   = skill_validation.get('validated_skills', [])
    unvalidated_raw = skill_validation.get('unvalidated_skills', [])
    total_skills    = len(validated_raw) + len(unvalidated_raw)
    val_pct         = round((len(validated_raw) / total_skills * 100) if total_skills > 0 else 0, 1)

    skill_validation_details = {
        "validated": [
            {
                "skill":    item['skill'],
                "projects": item.get('projects', []),
            }
            for item in validated_raw
        ],
        "unvalidated":     unvalidated_raw,
        "total":           total_skills,
        "validated_count": len(validated_raw),
        "validation_pct":  val_pct,
    }

    return {
        "ATS_score":          scores['overall_score'],
        "ats_score":          scores['overall_score'],
        "component_scores": {
            "formatting":       scores['formatting_score'],
            "keywords":         scores['keywords_score'],
            "content":          scores['content_score'],
            "skill_validation": scores['skill_validation_score'],
            "ats_compatibility": scores['ats_compatibility_score'],
        },
        "issues_summary":    issues_summary,
        "detailed_feedback": detailed_feedback,
        "jd_match_analysis": jd_comparison_result,
        "jd_comparison":     jd_comparison_result,
        "skills":            skills,
        "matched_keywords":  (
            jd_comparison_result['matched_keywords']
            if jd_comparison_result else list(keywords[:20])
        ),
        "missing_keywords":  (
            jd_comparison_result['missing_keywords']
            if jd_comparison_result else []
        ),
        "strengths": _generate_strengths(parsed_resume, skills, projects, action_verbs, skill_validation, scores),
        "interpretation":    scores.get('overall_interpretation', ''),
        "score_caps":        scores.get('caps_applied', {}),
        "score_penalties":   scores.get('penalties', {}),
        "skill_validation_details": skill_validation_details,
        "experience_months": experience_months,
    }


def _generate_strengths(
    parsed_resume: Dict, skills: List, projects: List,
    action_verbs: List, skill_validation: Dict, scores: Dict,
) -> List[str]:
    """Generate a list of things the resume does well, based on actual structured data."""
    strengths = []

    if parsed_resume.get('experience'):
        strengths.append("Has a dedicated Experience section")
    if any(_substantive_project(p) for p in projects if isinstance(p, dict)):
        strengths.append("Includes a Projects section showcasing applied skills")
    if parsed_resume.get('education'):
        strengths.append("Education section is present")
    if parsed_resume.get('skills'):
        strengths.append("Clear Skills section with listed technologies")
    summary = parsed_resume.get('professional_summary', '').strip()
    if summary and generic_phrase_count(summary) < 2:
        strengths.append("Professional Summary provides a quick overview")

    if len(skills) >= 8:
        strengths.append(f"Strong skill set — {len(skills)} skills detected")
    if len(action_verbs) >= 5:
        strengths.append(f"Uses {len(action_verbs)} strong action verbs in bullet points")

    validated = skill_validation.get('validated_skills', [])
    if len(validated) >= 3:
        strengths.append(f"{len(validated)} skills are backed by project/experience evidence")

    if scores.get('formatting_score', 0) >= 16:
        strengths.append("Well-formatted and ATS-friendly structure")
    if scores.get('content_score', 0) >= 20:
        strengths.append("Content quality is high with measurable achievements")

    return strengths