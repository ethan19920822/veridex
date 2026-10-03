# Veridex Alpha

**Global Regulatory Intelligence**

> Know what changed. Know what affects you. Know what to do.

This is the internal alpha for the Veridex concept. It is deliberately small: the first job is to prove that we can discover official regulatory publications, preserve versions, detect meaningful changes, analyse them, and map them to a company profile.

## What works in Alpha 0.1

- Official-source adapters for Australia: AUSTRAC, APRA, ASIC.
- Discovery from official regulator index/tracker pages.
- HTML/PDF retrieval and text normalization.
- SHA-256 versioning: new vs changed documents.
- Version history and unified diffs.
- Optional AI analysis through any OpenAI-compatible `/chat/completions` endpoint.
- Deterministic fallback analysis when no LLM key is configured.
- Company profiles and first-pass applicability scoring.
- FastAPI API + internal dashboard.
- SQLite by default; schema is ready to move to PostgreSQL.

## What this is NOT yet

- Legal advice.
- A guarantee of complete regulatory coverage.
- A production compliance system.
- A replacement for lawyers, auditors, or compliance officers.

Every conclusion must remain traceable to an official source. Human review stays in the loop.

## Quick start

```bash
cd veridex-alpha
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
veridex init
veridex run
veridex serve
```

Open: `http://127.0.0.1:8787`

The first `run` establishes the baseline and records discovered documents. A later run can detect changed content at the same URL. New publications are also recorded as change events.

## Optional AI analysis

Fill in `.env`:

```env
LLM_BASE_URL=https://YOUR_PROVIDER_BASE_URL/v1
LLM_API_KEY=...
LLM_MODEL=...
```

Veridex calls `POST {LLM_BASE_URL}/chat/completions`. If these values are empty, the pipeline still runs using deterministic fallback analysis.

## Architecture

```text
Official Sources
      ↓
Source Adapters
      ↓
Document Fetch + Normalise
      ↓
Version / Hash Store
      ↓
Change Detector
      ↓
Regulatory Analysis
      ↓
Company Applicability
      ↓
Actions / Evidence (next phase)
      ↓
Dashboard + API
```

See `docs/ARCHITECTURE.md` and `docs/ROADMAP.md`.
