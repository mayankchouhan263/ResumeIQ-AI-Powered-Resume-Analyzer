import os
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# api metadata
APP_TITLE = 'RESUME ANALYZER API'
APP_VERSION = '1.0.0'
APP_DESCRIPTION = 'analyse resumes against job description using nlp + ml '

ALLOWED_ORIGINS = [
    "http://localhost:5173",# Vite dev server (React)
    "http://localhost:3000",# Create React App fallback
    "http://127.0.0.1:5173",    
]

# file 
MAX_FILE_SIZE_MB = 5
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# supported MIME types and their short names
SUPPORTED_MIME_TYPES = {
    'application/pdf': '.pdf',
    'application/msword': '.doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document':'.docx'
}

SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

SPACY_MODEL_PRIMARY = "en_core_web_md" # Better Accuracy
SPACY_MODEL_SECONDRY = "en_core_web_sm"
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL","all-MiniLM-L6-v2")

# Score component weights - this is business logic treated as config

SCORE_WEIGHTS = {
    "formatting": 20,
    "keywords": 25,
    "content": 25,
    "skill_validation": 15,
    "ats_compatibility": 15,
}

JD_KEYWORD_WEIGHTS = 0.6
JD_SEMANTIC_WEIGHTS = 0.4

GROQ_API_KEY = os.getenv('GROQ_API_KEY' , '')