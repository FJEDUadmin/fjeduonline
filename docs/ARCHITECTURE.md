# Architecture: DNA Adductomics Platform

## Design Principles

1. **Reproducibility-first**: every analysis run should be re-runnable.
2. **Plugin-ready ingestion**: each databank connector is isolated and testable.
3. **Transparent scoring**: candidate ranking must be explainable.
4. **Publication-oriented traceability**: retain parameter provenance.

## Logical Layers

### A) Ingestion Layer

- Connector interface (CSV today, external databanks next)
- HMDB, MassBank, METLIN, PubChem, and literature supplementary CSV connectors implemented as formal databank adapters
- Tool parser hub for MS-DIAL, MZmine, and Skyline exports
- Source normalization to canonical `AdductRecord`
- Version-tagged ingestion pipeline

### B) Core Analysis Layer

- Transition parsing (MRM + neutral loss)
- Candidate retrieval by m/z and optional neutral loss constraints
- Multi-factor confidence scoring (v3: precursor/product/NL/RT/isotope + confidence levels)
- Pathway enrichment from matched candidates
- Run provenance metadata for reproducibility
- R statistics runner interface with report artifact output

### C) Service Layer

- REST API for ingestion and analysis
- Upload-first endpoints for browser workflows
- Structured request/response payloads for downstream visualization
- Dashboard UI (static SPA) for no-code operation
- One-click demo execution endpoint for web onboarding

### D) Persistence Layer

- SQLite baseline for local development
- Schema designed to migrate to PostgreSQL in production
- Production deployment path includes reverse proxy and HTTPS termination

## Planned Scale-up Path

1. Move repository implementation to SQLAlchemy + PostgreSQL
2. Add async worker queue for large batch analyses
3. Add object storage for run artifacts
4. Introduce authn/authz and role-based access control
5. Add knowledge graph for pathway and adduct relationships

## AI-Assisted Development Strategy

To avoid "改了後面忘記前面設計", enforce:

- Architecture docs in repo (`docs/`)
- Typed schemas and tests as contract
- CI checks on every merge request
- Prompt templates that always include architecture constraints
