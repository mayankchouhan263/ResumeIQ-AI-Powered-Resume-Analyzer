import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool

from backend.api.auth import get_current_user
from backend.models.schemas import (
    AnalysisResponse,
    ComponentScores,
    JDComparison,
    SaveAnalysisRequest,
    SkillValidationDetails,
)
from backend.utils.file_utils import (
    get_default_grammar_results,
    get_default_location_results,
    get_default_skill_validation_results,
)

logger = logging.getLogger('ats_resume_scorer')

router = APIRouter(prefix='/api/v1', tags=['Analysis'])

def _clean(text: str) -> str:
    for prefix in ('✅', '🌟', '❌', '⚠️', '📝', '🔴', '🟡', '🟢', '🟠', '👍'):
        text = text.lstrip(prefix)
    return text.strip()

@router.post('/analyze-resume', response_model=AnalysisResponse)
async def analyze_resume(
    request: Request,
    resume: UploadFile = File(..., description='Resume file — PDF or DOCX, max 5 MB'),
    job_description: str = Form('', description='Job description text (optional)'),
):
    warnings: List[str] = []


    nlp      = request.app.state.nlp
    embedder = request.app.state.embedder


    try:
        file_bytes = await resume.read()
        filename   = resume.filename or 'resume'

        from backend.services.resume_parser import (
            FileParsingError,
            FileValidationError,
            parse_resume_file,
        )

        resume_text, _metadata = parse_resume_file(file_bytes, filename)
        logger.info(f"Parsed '{filename}': {len(resume_text)} chars extracted")

    except Exception as exc:
        logger.error(f'File parsing failed: {exc}')
        raise HTTPException(
            status_code=422,
            detail=f'Could not read or parse the resume: {exc}',
        )

    # Is this even a resume? Cheap offline check, so we don't spend LLM tokens on invoices,
    # papers, job descriptions, cover letters...
    from backend.services.resume_validator import assess_resume
    verdict = assess_resume(resume_text)
    if not verdict.is_resume:
        logger.info(f"Rejected '{filename}' as non-resume: kind={verdict.kind} score={verdict.score} {verdict.signals}")
        raise HTTPException(status_code=422, detail=verdict.message)

    from backend.services.groq_parser import LLMServiceError

    #Full Analysis Pipeline 
    try:
        from backend.services.resume_analyzer import analyze_full_resume
        
        result = analyze_full_resume(
            resume_text=resume_text,
            nlp=nlp,
            embedder=embedder,
            job_description=job_description
        )
    except LLMServiceError as exc:
        logger.warning(f'LLM service error ({exc.status_code}): {exc}')
        headers = {'Retry-After': str(int(exc.retry_after) + 1)} if exc.retry_after else None
        raise HTTPException(
            status_code=exc.status_code if exc.status_code in (413, 429) else 503,
            detail=str(exc), headers=headers)
    except Exception as exc:
        logger.error(f'Full analysis pipeline failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Analysis pipeline failed: {exc}')

    from backend.models.schemas import ComponentScores

    #Extract jd_comparison details
    jd_comparison_result = None
    if result.get('jd_comparison'):
        jd_comparison_result = JDComparison(
            match_percentage=round(float(result['jd_comparison'].get('match_percentage', 0.0)), 1),
            semantic_similarity=round(float(result['jd_comparison'].get('semantic_similarity', 0.0)), 3),
            matched_keywords=result['jd_comparison'].get('matched_keywords', [])[:20],
            missing_keywords=result['jd_comparison'].get('missing_keywords', [])[:15],
            skills_gap=result['jd_comparison'].get('skills_gap', [])[:10],
        )

    # Convert detailed_feedback objects from prediction into what schema expects
    detailed_fb = result.get('detailed_feedback', [])
    

    svd_raw = result.get('skill_validation_details') or {}
    skill_val_details = SkillValidationDetails(
        validated       = svd_raw.get('validated', []),
        unvalidated     = svd_raw.get('unvalidated', []),
        total           = svd_raw.get('total', 0),
        validated_count = svd_raw.get('validated_count', 0),
        validation_pct  = svd_raw.get('validation_pct', 0.0),
    )

    critical_issues = [
        fb.issue_title for fb in detailed_fb
        if str(getattr(fb, 'severity_level', '')).lower() == 'high'
    ]

    response = AnalysisResponse(
        ATS_score=result['ats_score'],
        component_scores=ComponentScores(**result['component_scores']),
        issues_summary=result['issues_summary'],
        detailed_feedback=detailed_fb,
        jd_match_analysis=jd_comparison_result,
        skill_validation_details=skill_val_details,

        # Retro-compatibility fields
        ats_score=result['ats_score'],
        keyword_match=jd_comparison_result.match_percentage if jd_comparison_result else 0.0,
        missing_keywords=result.get('missing_keywords', []),
        matched_keywords=result.get('matched_keywords', []),
        skills=list(result.get('skills', [])[:20]),
        jd_comparison=jd_comparison_result,
        interpretation=result.get('interpretation', ''),
        strengths=result.get('strengths', []),
        suggestions=[fb.how_to_fix for fb in detailed_fb if getattr(fb, 'how_to_fix', '')],
        critical_issues=critical_issues,
    )


    return response


@router.post('/save-analysis')
async def save_analysis_endpoint(
    payload: SaveAnalysisRequest,
    user_id: str = Depends(get_current_user),
):
    """Save an already-computed analysis to the signed-in user's history (login required)."""
    from backend.database.supabase_db import SupabaseError, save_analysis

    try:
        saved_id = await save_analysis(user_id, payload.filename, payload.analysis.model_dump())
    except SupabaseError as exc:
        raise HTTPException(status_code=500, detail=f'Could not save to history: {exc}')
    if saved_id is None:
        raise HTTPException(status_code=500, detail='Could not save to history: Supabase returned no row id.')
    return {'status': 'saved', 'id': saved_id}


@router.get('/health')
async def health_check(request: Request):
    """Health check — confirms models are loaded and the API is ready."""
    return {
        'status':          'healthy',
        'nlp_loaded':      request.app.state.nlp is not None,
        'embedder_loaded': request.app.state.embedder is not None,
    }

@router.get('/history')
async def get_history(user_id: str = Depends(get_current_user)):
    """Return the signed-in user's past analyses (identity comes from the JWT)."""
    from backend.database.supabase_db import get_user_history
    try:
        return await get_user_history(user_id)
    except Exception as exc:
        logger.error(f'History fetch failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not load history: {exc}')


@router.delete('/history/{analysis_id}')
async def delete_history_entry(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    """Delete one analysis from the signed-in user's history."""
    from backend.database.supabase_db import delete_analysis
    try:
        success = await delete_analysis(analysis_id, user_id)
        if not success:
            raise HTTPException(status_code=404, detail='Analysis not found or not owned by this user.')
        return {'status': 'deleted', 'id': analysis_id}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f'History delete failed: {exc}')
        raise HTTPException(status_code=500, detail=f'Could not delete: {exc}')
    

@router.post('/generate-pdf')
async def generate_pdf(
    data: AnalysisResponse,
):
    from fastapi.responses import Response

    try:
        from backend.services.report_generator import generate_html_reports
        from backend.services.pdf_export import generate_combined_pdf
        html_docs = generate_html_reports(data.model_dump())
        pdf_bytes = await run_in_threadpool(generate_combined_pdf, html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": "attachment; filename=ats_report.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")
    

@router.get('/history/{analysis_id}/pdf')
async def generate_history_pdf(
    analysis_id: str,
    user_id: str = Depends(get_current_user),
):
    from backend.database.supabase_db import get_user_history
    from fastapi.responses import Response

    history = await get_user_history(user_id)
    analysis_data = next((item["analysis_result"] for item in history if item["id"] == analysis_id), None)

    if not analysis_data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    try:
        from backend.services.report_generator import generate_html_reports
        from backend.services.pdf_export import generate_combined_pdf
        html_docs = generate_html_reports(analysis_data)
        pdf_bytes = await run_in_threadpool(generate_combined_pdf, html_docs)

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=ats_report_{analysis_id}.pdf"
            }
        )
    except Exception as e:
        logger.error(f'Failed to generate PDF for history: {e}')
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {e}")