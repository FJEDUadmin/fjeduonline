# Backend: DNA Adductomics API

FastAPI backend for:

- adduct bank ingestion
- LC-MS MRM/NL transition analysis
- candidate adduct identification
- pathway enrichment scoring

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn adductomics_api.main:app --reload
```
