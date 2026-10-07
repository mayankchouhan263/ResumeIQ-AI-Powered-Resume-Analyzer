# ResumeIQ - Render memory fix (512 MB instance)

Copy everything in this folder into your project root (same folder that contains `backend/` and `requirements.txt`),
overwriting files with the same name. Nothing here touches the `frontend/` folder.

| File | What changed |
|---|---|
| `backend/services/embedder.py` | NEW - ONNX embedder (fastembed), replaces PyTorch/sentence-transformers |
| `backend/main.py` | loads the ONNX embedder and `en_core_web_sm` (lemmatizer disabled) |
| `backend/core/config.py` | spaCy default is now `en_core_web_sm` (override with env `SPACY_MODEL`) |
| `backend/services/ats_scorer.py`, `resume_analyzer.py` | same as the scoring fix, only the embedder import changed |
| `backend/services/jd_matcher.py` | embedder import changed |
| `backend/services/pdf_export.py` | WeasyPrint first, Chromium only as a fallback |
| `requirements.txt` | local dev: `fastembed` instead of `sentence-transformers` |
| `requirements-backend.txt` | NEW - server-only dependencies (no torch, streamlit, playwright) |
| `Dockerfile`, `.dockerignore` | NEW - installs Pango for WeasyPrint, spaCy model and embedding model at build time |

## Deploy on Render (recommended: Docker)
1. Commit and push these files.
2. Create a **new Web Service** from the repo, **Runtime: Docker**, Instance type: Free. (Render fixes a service's runtime at creation, so a new service is the safe route.)
3. Copy your environment variables from the old service (GROQ_API_KEY, Supabase / JWT settings, ALLOWED_ORIGINS, ...).
4. Deploy, then open `/api/v1/health` - both `nlp_loaded` and `embedder_loaded` should be true.

### Alternative: keep the native Python runtime
- Build command: `pip install -r requirements-backend.txt && python -m spacy download en_core_web_sm && python -c "from backend.services.embedder import OnnxEmbedder; OnnxEmbedder()"`
- Start command: unchanged (`uvicorn backend.main:app --host 0.0.0.0 --port $PORT`)
- PDF export only works if the server has Pango; if you see "No PDF engine worked", switch to the Docker route.

## Local development
`pip install -r requirements.txt` then `python -m spacy download en_core_web_sm`. You can `pip uninstall sentence-transformers torch`.
