import os
from pathlib import Path

# Load .env from the project root (two levels up from this file) explicitly —
# load_dotenv() with no args relies on caller-frame inspection that can fail
# silently under uvicorn reload, leaving env vars unset.
try:
    from dotenv import load_dotenv
    _ENV_PATH = Path(__file__).resolve().parents[1] / '.env'
    load_dotenv(_ENV_PATH)
except ImportError:
    pass

#api metadata
APP_TITLE='ATS RESUME ANALYZER API'
APP_VERSION='1.0.0'
APP_DESCRIPTION='analyse resumes against job description using nlp + ml'

ALLOWED_ORIGINS = [
    'https://appapppy-ktwxupi73vqhjzweksze9d.streamlit.app',
    'http://localhost:8501'
]  

#file 
MAX_FILE_SIZE_MB=5
MAX_FILE_SIZE_BYTES=MAX_FILE_SIZE_MB*1024*1024

#Supported MIME types and their short names
SUPPORTED_MIME_TYPES = {
    'application/pdf': 'pdf',
    'application/msword': 'doc',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
}

SUPPORTED_EXTENSIONS = {'.pdf', '.doc', '.docx'}

# small model by default: ~3x less RAM than _md, and the code only needs entities + noun chunks.
SPACY_MODEL_PRIMARY   = os.getenv("SPACY_MODEL", "en_core_web_sm")
SPACY_MODEL_SECONDARY = "en_core_web_md"      # fallback if the primary is not installed
SENTENCE_TRANSFORMER_MODEL = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")

# Score component weights — this is business logic treated as config
SCORE_WEIGHTS = {
    "formatting": 20, "keywords": 25, "content": 25,
    "skill_validation": 15, "ats_compatibility": 15,
    
}

JD_KEYWORD_WEIGHT=0.6
JD_SEMANTIC_WEIGHT=0.4

def _env(name: str) -> str:
    """Read an env var and strip stray whitespace, quotes and <angle brackets> (a common paste mistake)."""
    return os.getenv(name, '').strip().strip('\'"<> \t')


SUPABASE_URL       = _env('SUPABASE_URL')
SUPABASE_KEY       = _env('SUPABASE_KEY')          # service_role — DB writes (bypasses RLS)
SUPABASE_ANON_KEY  = _env('SUPABASE_ANON_KEY')     # public anon — frontend auth calls
SUPABASE_JWT_SECRET= _env('SUPABASE_JWT_SECRET')   # used by backend to verify access tokens
GROQ_API_KEY       = os.getenv('GROQ_API_KEY', '')

