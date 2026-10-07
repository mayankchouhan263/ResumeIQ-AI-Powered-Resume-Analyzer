# 🚀 ResumeIQ — AI-Powered Resume Analyzer

<p align="center">
  <strong>AI-powered resume analysis with intelligent scoring, NLP-based matching, and actionable feedback.</strong>
</p>

<p align="center">
  <a href="https://resumeiq-ai-powered-resume-analyzer.streamlit.app">
    🌐 Live Demo
  </a>
  &nbsp;&nbsp;•&nbsp;&nbsp;
  <a href="https://github.com/mayankchouhan263/ResumeIQ-AI-Powered-Resume-Analyzer">
    💻 GitHub Repository
  </a>
</p>

---

## 📌 Overview

**ResumeIQ** is an AI-powered resume analysis platform designed to help candidates understand how well their resume aligns with a target job description.

Instead of simply providing a generic resume review, ResumeIQ analyzes the relationship between the **resume and job requirements** and generates meaningful insights that candidates can use to improve their applications.

The application combines:

- Natural Language Processing (NLP)
- Semantic similarity
- Resume parsing
- Skill and keyword analysis
- Intelligent scoring
- LLM-powered recommendations
- FastAPI backend services
- Streamlit frontend
- Authentication and analysis history

The primary goal is to transform resume analysis from a **black-box score into an explainable and actionable process**.

---

## ✨ Key Features

### 📄 Resume Upload & Parsing

Upload your resume and let ResumeIQ process its contents automatically.

Supported document formats include:

- `.pdf`
- `.docx`
- `.doc`

The system extracts relevant resume information and prepares it for downstream NLP and AI analysis.

---

### 🎯 Resume–Job Description Matching

ResumeIQ evaluates how closely a resume matches a given job description.

The system analyzes relevant information such as:

- Technical skills
- Keywords
- Projects
- Experience
- Technologies
- Resume content
- Job requirements

This helps candidates understand whether their resume is aligned with the position they are targeting.

---

### 📊 Intelligent Resume Scoring

ResumeIQ generates an overall analysis score based on the relationship between the resume and the target requirements.

Rather than relying exclusively on exact keyword matching, the system incorporates NLP and semantic analysis to identify meaningful relationships between resume content and job requirements.

---

### 🔑 Skill & Keyword Analysis

The platform identifies relevant skills and keywords from the resume and compares them with the requirements of the target role.

This helps users identify:

- Relevant skills already present
- Important keywords
- Potential skill gaps
- Technical terminology that may need improvement

---

### 🧠 Semantic Similarity

ResumeIQ uses **Sentence Transformers** to perform semantic analysis.

Semantic similarity allows the system to understand that two pieces of text can have related meanings even when they don't use exactly the same words.

This makes the analysis more robust than simple keyword matching.

---

### 🤖 LLM-Powered Recommendations

ResumeIQ integrates the **Groq API** to generate intelligent feedback and recommendations.

The LLM layer can help transform analysis results into practical suggestions for improving the resume.

This creates a hybrid architecture combining:

```text
Traditional NLP
       +
Semantic Similarity
       +
Rule-Based Analysis
       +
Large Language Models
       ↓
Actionable Resume Feedback
```

---

### 💡 Actionable Feedback

ResumeIQ focuses on helping candidates understand **what they should improve**.

The analysis can provide feedback related to:

- Missing or weak keywords
- Skill alignment
- Resume content
- Job compatibility
- Resume structure
- Areas requiring improvement

---

### 🔐 Authentication & Resume History

ResumeIQ includes authentication functionality and supports persistent analysis history.

Users can authenticate and access previously generated resume analyses.

Authentication and history management are handled using **Supabase**.

---

## 🎯 Why ResumeIQ?

Traditional resume analyzers often provide a score without giving enough context behind the result.

ResumeIQ focuses on answering a more useful question:

> **"How well does my resume match this role, and what can I improve?"**

The analysis pipeline combines multiple AI and NLP techniques to provide a more meaningful evaluation.

```text
Resume
   │
   ▼
Document Parsing
   │
   ▼
Text Extraction
   │
   ▼
NLP Processing
   │
   ├───────────────┐
   ▼               ▼
Skills &        Semantic
Keywords        Similarity
   │               │
   └───────┬───────┘
           ▼
    Resume/JD Analysis
           │
           ▼
      Scoring Engine
           │
           ▼
   LLM-Powered Feedback
           │
           ▼
    Actionable Results
```

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │        User          │
                    │   Uploads Resume     │
                    │   + Job Description  │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │      Streamlit       │
                    │       Frontend       │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       FastAPI        │
                    │       Backend        │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       ┌────────────┐   ┌─────────────┐   ┌────────────┐
       │   Resume   │   │     NLP     │   │    Groq    │
       │   Parser   │   │   Analysis  │   │     LLM    │
       └─────┬──────┘   └──────┬──────┘   └─────┬──────┘
             │                 │                │
             └─────────────────┼────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │    Scoring Engine    │
                    │                      │
                    │ • Skills             │
                    │ • Keywords           │
                    │ • Semantic Match     │
                    │ • Content            │
                    │ • Job Alignment      │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Analysis & Feedback │
                    └──────────┬───────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │       Supabase       │
                    │ Auth + History       │
                    └──────────────────────┘
```

---

# 🛠️ Tech Stack

## Frontend

- **Streamlit**
- HTML
- CSS
- Custom Streamlit UI

## Backend

- **Python**
- **FastAPI**
- **Uvicorn**

## AI / Machine Learning

- **spaCy**
- **Sentence Transformers**
- **FastEmbed**
- **ONNX Runtime**
- Natural Language Processing
- Semantic Similarity
- Rule-based analysis

## Generative AI

- **Groq API**
- LLM-powered analysis
- AI-generated recommendations

## Resume Processing

- **pdfplumber**
- **PyPDF2**
- DOCX processing

## Authentication & Database

- **Supabase**
- Email/Password Authentication
- Google OAuth
- Resume Analysis History

## UI/UX

- Figma
- Custom HTML/CSS
- Streamlit

## Deployment

- Streamlit Cloud
- Render

---

# 📂 Project Structure

```text
ResumeIQ-AI-Powered-Resume-Analyzer/
│
├── backend/
│   ├── main.py
│   │
│   ├── core/
│   │   └── config.py
│   │
│   ├── services/
│   │   ├── embedder.py
│   │   ├── parser.py
│   │   ├── scorer.py
│   │   └── ...
│   │
│   └── requirements.txt
│
├── frontend/
│   ├── streamlit_app.py
│   │
│   ├── views/
│   │   ├── scorer.py
│   │   ├── history.py
│   │   └── ...
│   │
│   ├── services/
│   │   └── supabase_client.py
│   │
│   └── ...
│
├── .devcontainer/
│
├── Dockerfile
├── .dockerignore
├── .gitignore
├── requirements.txt
├── requirements-backend.txt
└── README.md
```

---

# ⚙️ Installation & Setup

## 1. Clone the Repository

```bash
git clone https://github.com/mayankchouhan263/ResumeIQ-AI-Powered-Resume-Analyzer.git
```

Navigate into the project:

```bash
cd ResumeIQ-AI-Powered-Resume-Analyzer
```

---

## 2. Create a Virtual Environment

### Windows

```bash
python -m venv .venv
```

Activate the environment:

```bash
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Dependencies

Install the main dependencies:

```bash
pip install -r requirements.txt
```

For backend-specific dependencies:

```bash
pip install -r requirements-backend.txt
```

---

## 4. Install the spaCy Model

ResumeIQ uses a spaCy language model for NLP processing.

```bash
python -m spacy download en_core_web_md
```

---

# 🔐 Environment Variables

Create the required environment configuration for local development.

Example:

```env
GROQ_API_KEY=your_groq_api_key

SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key

AUTH_REDIRECT_URL=http://localhost:8501
```

> **Important:** Never commit API keys, database credentials, OAuth secrets, or other sensitive information to GitHub.

Make sure sensitive files are included in `.gitignore`:

```text
.env
.streamlit/secrets.toml
*.key
*.pem
```

---

# ▶️ Running Locally

ResumeIQ consists of two major services:

```text
Frontend → Streamlit
Backend  → FastAPI
```

Both services should be running during local development.

---

## Start the Backend

From the project root:

```bash
uvicorn backend.main:app --reload
```

The backend will be available at:

```text
http://127.0.0.1:8000
```

FastAPI documentation is typically available at:

```text
http://127.0.0.1:8000/docs
```

---

## Start the Frontend

Open another terminal and activate the virtual environment.

Then run:

```bash
streamlit run frontend/streamlit_app.py
```

The frontend will be available at:

```text
http://localhost:8501
```

---

# 🔄 How ResumeIQ Works

### Step 1 — Upload Resume

The user uploads a resume in a supported document format.

```text
PDF / DOC / DOCX
```

### Step 2 — Resume Parsing

The backend extracts text and relevant information from the uploaded document.

### Step 3 — NLP Processing

The extracted resume content is processed using NLP techniques.

The system identifies information such as:

- Skills
- Keywords
- Projects
- Experience
- Resume sections
- Technical terminology

### Step 4 — Job Description Analysis

The target job description is analyzed to identify relevant requirements and terminology.

### Step 5 — Semantic Analysis

Sentence Transformer-based embeddings are used to compare the semantic relationship between resume content and job requirements.

### Step 6 — Scoring

The scoring pipeline evaluates the alignment between the resume and the target role.

### Step 7 — AI Analysis

The Groq-powered LLM layer generates additional analysis and recommendations.

### Step 8 — Results

The user receives an analysis containing relevant insights and actionable feedback.

### Step 9 — History

Authenticated users can save and revisit their previous analyses.

---

# 🧠 AI Pipeline

ResumeIQ follows a hybrid AI architecture rather than depending entirely on an LLM.

```text
                Resume
                  │
                  ▼
          Document Extraction
                  │
                  ▼
             NLP Pipeline
                  │
        ┌─────────┴─────────┐
        │                   │
        ▼                   ▼
   Skill/Keyword       Text Embeddings
    Extraction              │
        │                   ▼
        │             Semantic Similarity
        │                   │
        └─────────┬─────────┘
                  ▼
          Resume/JD Scoring
                  │
                  ▼
             Groq LLM
                  │
                  ▼
       Recommendations & Feedback
```

This approach combines deterministic processing with machine learning and generative AI.

---

# 📊 Core AI/ML Concepts Demonstrated

ResumeIQ demonstrates practical implementation of several AI/ML concepts:

### Natural Language Processing

Used for processing and extracting information from resume text.

### Named Entity Recognition

spaCy-based NLP capabilities are used for identifying relevant entities and information.

### Semantic Similarity

Sentence Transformer embeddings allow the system to compare text based on semantic meaning rather than only exact word matches.

### Text Embeddings

Resume and job-description content can be transformed into vector representations for similarity analysis.

### Rule-Based Analysis

Deterministic rules complement ML-based analysis for structured resume evaluation.

### Large Language Models

Groq-powered LLMs are used to generate contextual analysis and recommendations.

### Hybrid AI Architecture

The system combines:

```text
NLP
+
Machine Learning
+
Semantic Search
+
Rule-Based Logic
+
LLM
```

to produce the final analysis.

---

# 🎨 UI/UX Design

ResumeIQ follows a product-oriented interface rather than a basic machine-learning dashboard.

The interface focuses on:

- Clear navigation
- Simple resume upload
- Visual analysis results
- Easy-to-understand feedback
- Structured information
- Clean UI
- Actionable recommendations

The UI/UX was designed using **Figma** and implemented using **Streamlit with custom HTML/CSS**.

---

# ☁️ Deployment

ResumeIQ is designed using a separated frontend/backend architecture.

```text
                    Internet
                       │
             ┌─────────┴─────────┐
             ▼                   ▼
       Streamlit Cloud         Render
          Frontend             Backend
             │                   │
             └─────────┬─────────┘
                       │
                       ▼
                  ResumeIQ
```

### Frontend

**Streamlit Cloud**

🌐 Live Application:

https://resumeiq-ai-powered-resume-analyzer.streamlit.app

### Backend

**Render**

Backend service:

https://resumeiq-ai-powered-resume-analyzer.onrender.com

---

# 🔐 Authentication Flow

ResumeIQ uses Supabase for authentication and persistent analysis history.

```text
              User
                │
                ▼
         Resume Analysis
                │
        ┌───────┴───────┐
        │               │
        ▼               ▼
    Analyze          Save Result
                        │
                        ▼
                 Authentication
                        │
                        ▼
                    Supabase
                        │
                        ▼
                 Resume History
```

Supported authentication methods include:

- Email & Password
- Google OAuth

---

# 📸 Screenshots

Add screenshots of the application to the repository for a stronger GitHub presentation.

Recommended structure:

```text
screenshots/
├── home.png
├── upload.png
├── analysis.png
├── score.png
└── history.png
```

Then add them to this section:

### 🏠 Home Page

![ResumeIQ Home](screenshots/home.png)

### 📊 Resume Analysis

![ResumeIQ Analysis](screenshots/analysis.png)

### 🎯 Resume Score

![ResumeIQ Score](screenshots/score.png)

### 📜 Analysis History

![ResumeIQ History](screenshots/history.png)

---

# 🚀 Future Improvements

Potential future improvements include:

- 🎯 Job-description-based resume optimization
- 📊 More advanced ATS scoring
- 🤖 Improved LLM recommendations
- 📈 Resume version comparison
- 📝 AI-assisted resume rewriting
- 🎯 Job-specific keyword optimization
- 📄 Additional document format support
- ⚡ Faster model initialization
- 📱 Improved mobile responsiveness
- 🔎 More advanced skill validation
- 📊 Resume analytics and trends
- 🎯 Personalized career recommendations

---

# 🎓 Project Background

ResumeIQ was developed as part of the:

**Prime AIML Bootcamp — Apna College**

The project provided hands-on experience across multiple areas of software and AI engineering:

- Artificial Intelligence
- Machine Learning
- Natural Language Processing
- Generative AI
- Semantic Similarity
- Backend Development
- Frontend Development
- Authentication
- Database Management
- Cloud Deployment
- UI/UX Design

The project follows a complete development lifecycle:

```text
Idea
  ↓
Research
  ↓
UI/UX Design
  ↓
AI/ML Development
  ↓
Backend Development
  ↓
Frontend Development
  ↓
Authentication
  ↓
Cloud Deployment
  ↓
Live Product
```

---

# 💡 Project Highlights

### 🔍 Explainable Analysis

Focuses on providing meaningful information behind resume evaluation rather than only presenting a score.

### 🧠 Hybrid AI Architecture

Combines traditional NLP, semantic similarity, rule-based processing, and LLM capabilities.

### 🎯 Resume–Job Alignment

Analyzes how well resume content corresponds to the requirements of a target position.

### ⚡ Full-Stack AI Application

Combines:

```text
AI/ML
  +
NLP
  +
FastAPI
  +
Streamlit
  +
Supabase
  +
LLM
  +
Cloud Deployment
```

into a single application.

### 🛠️ Production-Oriented Architecture

The project separates frontend and backend responsibilities, making the system easier to maintain and deploy.

---

# 🤝 Contributing

Contributions, suggestions, and improvements are welcome.

### 1. Fork the repository

```bash
git fork
```

### 2. Clone your fork

```bash
git clone https://github.com/YOUR_USERNAME/ResumeIQ-AI-Powered-Resume-Analyzer.git
```

### 3. Create a feature branch

```bash
git checkout -b feature/your-feature
```

### 4. Make your changes

Implement and test your changes locally.

### 5. Commit your changes

```bash
git add .
git commit -m "Add: your feature"
```

### 6. Push your branch

```bash
git push origin feature/your-feature
```

### 7. Open a Pull Request

Submit your pull request with a clear description of the changes.

---

# 📬 Feedback

Feedback and suggestions are welcome.

Areas for improvement include:

- AI analysis
- Resume scoring
- NLP processing
- Semantic matching
- UI/UX
- Performance
- Resume recommendations
- New features

---

# 👨‍💻 Author

## Mayank Chouhan

**B.Tech — Computer Science & Engineering (AI & ML)**

Interested in:

- Artificial Intelligence
- Machine Learning
- Generative AI
- Natural Language Processing
- Software Engineering

---

# 🔗 Links

### 🌐 Live Demo

https://resumeiq-ai-powered-resume-analyzer.streamlit.app

### 💻 GitHub Repository

https://github.com/mayankchouhan263/ResumeIQ-AI-Powered-Resume-Analyzer

### ⚙️ Backend

https://resumeiq-ai-powered-resume-analyzer.onrender.com

---

# ⭐ Support

If you find **ResumeIQ** useful or interesting, consider giving the repository a ⭐ on GitHub.

Feedback, suggestions, and contributions are always welcome.

---

<p align="center">
  🚀 Built with Python, FastAPI, Streamlit, NLP, Generative AI & ❤️
</p>
