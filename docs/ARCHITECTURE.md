# Veridex architecture — Alpha 0.1

## Product invariant

Every machine-generated conclusion must be traceable to official source material. Veridex does not hide source uncertainty.

## Pipeline

1. **Source adapter** discovers candidate official publications.
2. **Fetcher** downloads HTML/PDF and extracts text.
3. **Normalizer** removes presentation noise.
4. **Version store** saves each distinct SHA-256 version.
5. **Change detector** creates NEW_DOCUMENT or UPDATED_DOCUMENT events.
6. **Regulatory analyzer** extracts significance, affected entities, topics, obligations, actions and confidence.
7. **Applicability analyzer** maps a change to a company profile.
8. **API/UI** exposes current changes and provenance.

## Why source adapters

The global product is one engine with jurisdiction-specific connectors. Adding Taiwan or Singapore should mean adding adapters, not rebuilding the product.

## Alpha safety model

- Official sources first.
- AI output is analysis, not authority.
- Explicit confidence score.
- Human review by default.
- Preserve original URL and document version.
- Never silently infer an effective date.

## Next production steps

- PostgreSQL + pgvector.
- Durable task queue and scheduled workers.
- Object storage for raw files.
- Per-source parser tests and source health metrics.
- Authentication, tenant isolation and RBAC.
- Evidence objects and immutable audit log.
- Signed source snapshots / raw content retention.
- Monitoring and alerts when a source adapter stops seeing expected content.
