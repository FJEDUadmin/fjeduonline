# Backend: DNA Adductomics API

FastAPI backend for:

- adduct bank ingestion
- HMDB CSV connector ingestion
- MassBank CSV connector ingestion
- tool export parser hub (MS-DIAL, MZmine, Skyline)
- LC-MS MRM/NL transition analysis
- candidate adduct identification (confidence v3 levels)
- pathway enrichment scoring with confidence model v3
- browser dashboard for upload/analysis workflows
- run-level provenance metadata (`run_id`, parameters, scoring version)
- R statistics module trigger and report artifact generation

Run locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn adductomics_api.main:app --reload
```

One-shot production bootstrap:

```bash
cp .env.prod.example .env.prod
# edit DOMAIN / ACME_EMAIL
bash deploy/bootstrap_prod.sh
```

Open:

- API docs: `http://127.0.0.1:8000/docs`
- Dashboard: `http://127.0.0.1:8000/`

Phase A endpoints:

- `POST /api/v1/demo/run`
- `POST /api/v1/analyze/tool-csv`
- `POST /api/v1/analyze/tool/upload-csv`
- `GET /api/v1/stats/r-module/health`
- `POST /api/v1/stats/r-report`

HMDB CSV expected column aliases:

- `accession`, `hmdb_id`, or `accession_id`
- `name`, `metabolite_name`, `common_name`, or `chemical_name`
- `monoisotopic_molecular_weight` (or `exact_mass`, `monoisotopic_mass`, `molecular_weight`)
- optional: `chemical_formula`, `smiles`, `pathways`

Notes:
- Header matching is case-insensitive.
- Spaces/hyphens/dots in header names are tolerated.
- CSV encoding fallback is automatic (UTF-8, UTF-8-SIG, Big5/CP950, CP1252, GB18030, Latin-1).

Tool export support:

- MS-DIAL alignment table exports
- MZmine feature table exports
- Skyline transition report exports

R package onboarding (one-shot build):

- CRAN list: `r_modules/cran_packages.txt` (one package per line)
- Bioconductor list: `r_modules/bioc_packages.txt` (one package per line)
- Local tarballs: place `*.tar.gz` into `r_modules/packages/`
- During Docker production build, these packages are auto-installed.

MassBank CSV expected column aliases:

- `record_id` / `accession` / `mb_id`
- `compound_name` / `name`
- `precursor_mz` (or `mz`, `exact_mass`)
- optional: `product_mz`, `retention_time`, `isotope_ratio`, `formula`, `pathway`

Production deployment:

- `docker-compose.prod.yml` + `deploy/Caddyfile` for reverse proxy and HTTPS
- copy `.env.prod.example` to `.env.prod` and set `DOMAIN` + `ACME_EMAIL`
