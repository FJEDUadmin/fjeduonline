# Backend: DNA Adductomics API

FastAPI backend for:

- adduct bank ingestion
- HMDB CSV connector ingestion
- MassBank CSV connector ingestion
- LC-MS MRM/NL transition analysis
- candidate adduct identification
- pathway enrichment scoring with confidence model v2
- browser dashboard for upload/analysis workflows
- run-level provenance metadata (`run_id`, parameters, scoring version)

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn adductomics_api.main:app --reload
```

Open:

- API docs: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8000/`

HMDB CSV expected column aliases:

- `accession` or `hmdb_id`
- `name` or `metabolite_name`
- `monoisotopic_molecular_weight` (or `exact_mass`, `monoisotopic_mass`)
- optional: `chemical_formula`, `smiles`, `pathways`

MassBank CSV expected column aliases:

- `record_id` / `accession` / `mb_id`
- `compound_name` / `name`
- `precursor_mz` (or `mz`, `exact_mass`)
- optional: `product_mz`, `retention_time`, `isotope_ratio`, `formula`, `pathway`
