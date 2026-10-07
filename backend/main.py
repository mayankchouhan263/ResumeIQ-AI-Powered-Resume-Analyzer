import os, sys
if sys.platform == "win32":          # local Windows dev only
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import(
    ALLOWED_ORIGINS, 
    APP_DESCRIPTION, 
    APP_TITLE, 
    APP_VERSION, 
    SPACY_MODEL_PRIMARY, 
    SPACY_MODEL_SECONDARY, SENTENCE_TRANSFORMER_MODEL
)
from backend.api.routes import router

logger=logging.getLogger('ats_resume_scorer')

@asynccontextmanager
async def lifespan(app:FastAPI):
    logger.info('Starting ATS Resume Analyzer API...')

    logger.info(f'Loading spaCy NLP model: {SPACY_MODEL_PRIMARY}')
    import spacy
    try:
        # lemmatizer is never used here; skipping it saves a little more memory
        app.state.nlp = spacy.load(SPACY_MODEL_PRIMARY, disable=['lemmatizer'])
        logger.info(f'Loaded {SPACY_MODEL_PRIMARY}')
    except OSError:
        logger.warning(f'{SPACY_MODEL_PRIMARY} not found — falling back to {SPACY_MODEL_SECONDARY}')
        app.state.nlp = spacy.load(SPACY_MODEL_SECONDARY, disable=['lemmatizer'])
        logger.info(f'Loaded {SPACY_MODEL_SECONDARY} (fallback)')

    logger.info(f'Loading ONNX embedder: {SENTENCE_TRANSFORMER_MODEL}')
    from backend.services.embedder import OnnxEmbedder
    app.state.embedder = OnnxEmbedder(SENTENCE_TRANSFORMER_MODEL)
    logger.info(f'Loaded {SENTENCE_TRANSFORMER_MODEL}')

    logger.info('All models loaded. API is ready to serve requests.')

    yield

    logger.info('shutting down the api!!')

app=FastAPI(
    title=APP_TITLE, 
    description=APP_DESCRIPTION, 
    version=APP_VERSION, 
    lifespan=lifespan,
    docs_url='/docs',
    redoc_url='/redoc'
)

@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware, 
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True, 
    allow_methods     = ['*'],
    allow_headers     = ['*'],

)

app.include_router(router)

@app.get('/')
async def root():
    return {
        'name':      'ATS Resume Analyzer API',
        'version':   '2.0.0',
        'endpoints': {
            'POST   /api/v1/analyze-resume': 'Analyze a resume (no login needed)',
            'POST   /api/v1/save-analysis':  'Save an analysis to history (login required)',
            'GET    /api/v1/history':        'Get user history',
            'DELETE /api/v1/history/:id':    'Delete a history entry',
            'GET    /api/v1/health':         'Health check',
            'POST   /api/v1/generate-pdf':   'Generate PDF report from data',
        },
    }

if __name__=='__main__':
    import uvicorn
    uvicorn.run(
        'backend.main:app',
        host    = '0.0.0.0',
        port    = 8000,
        reload  = True,    # Auto-restart on code changes (dev only)
    )