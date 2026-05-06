# AGENTS.md

## Repository Overview

This is a multi-project repository for an education/science company (飛翔少年 / "Flying Youth"). The `main` branch contains only JPEG image assets (exam question images). All application code lives on **separate feature branches**, each representing an independent project with its own dependencies.

## Branch → Project Map

| Branch | Project | Stack | Port |
|---|---|---|---|
| `cursor/ai-tutor-app-mvp-036d` | AI Tutor Website | Python (FastAPI), SQLite, Jinja2 | 8000 |
| `cursor/dna-adductomic-9447` | DNA Adductomics Platform | Python (FastAPI), SQLite | 8001 |
| `cursor/ms-stats-webapp-acd7` | MS Statistics Web App | Python (Streamlit), OpenAI GPT | 8003 |
| `cursor/scheduling-system-3da6` | Scheduling System | Pure frontend (HTML/CSS/JS) | 8002 |
| `cursor/ml-comparison-module-d08b` | ML Comparison Module | Python (scikit-learn, pandas) | N/A |
| `codex/create-physics-tutoring-materials-program` | Lecture Builder CLI | Python (pytesseract, python-docx) | N/A |

## Cursor Cloud specific instructions

### Multi-branch architecture

- The `main` branch has **no application code** — only 716 JPEG images of exam questions.
- Each feature branch is self-contained with its own `requirements.txt` or `pyproject.toml`.
- To work on a project, check out the relevant branch or use `git worktree add`.

### Running each project

**AI Tutor** (`cursor/ai-tutor-app-mvp-036d`):
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # ALLOW_MOCK_GEMINI=true enables demo without API key
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Tests: python3 -m unittest tests/test_entitlements.py tests/test_tutor_service.py
```

**DNA Adductomics** (`cursor/dna-adductomic-9447`):
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn adductomics_api.main:app --reload --host 0.0.0.0 --port 8001
# Tests: pytest tests/ -v
```

**MS Stats** (`cursor/ms-stats-webapp-acd7`):
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py --server.headless=true --server.port=8003
# Requires OPENAI_API_KEY env var for full functionality
```

**Scheduling System** (`cursor/scheduling-system-3da6`):
```bash
python3 -m http.server 8002
# Pure frontend, no dependencies needed. Open http://localhost:8002/
```

**ML Comparison Module** (`cursor/ml-comparison-module-d08b`):
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m ml_comparison_module.demo
```

### Gotchas and non-obvious notes

- **python3-venv must be installed** on fresh VMs: `apt-get install -y python3.12-venv`
- The AI Tutor works in **mock mode** by default (`ALLOW_MOCK_GEMINI=true` in `.env`), so no Gemini API key is needed for testing. The coaching API (`/coach/start`, `/coach/reply`) returns placeholder guided questions.
- The DNA Adductomics backend uses `pyproject.toml` (not `requirements.txt`); install with `pip install -e ".[dev]"` to get pytest/httpx.
- The MS Stats webapp **requires `OPENAI_API_KEY`** — there is no mock mode. The app starts without it but analysis features will fail.
- The Scheduling System loads SheetJS from a CDN (`https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js`), so network access is needed for full Excel import/export functionality.
- All Python projects target **Python 3.11+**; the VM has Python 3.12.
