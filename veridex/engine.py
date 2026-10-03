from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from .analyzer import Analyzer
from .db import SessionLocal, init_db
from .fetcher import Fetcher
from .models import ChangeEvent, CompanyProfile, Document, DocumentVersion, Impact, Source
from .sources.australia import adapters
from .text import content_hash, line_diff


def _json(text: str, default):
    try:
        return json.loads(text)
    except Exception:
        return default


def seed_sources(session: Session) -> None:
    for adapter in adapters():
        spec = adapter.spec
        existing = session.scalar(select(Source).where(Source.key == spec.key))
        if existing:
            existing.name = spec.name
            existing.index_url = spec.index_url
            existing.jurisdiction = spec.jurisdiction
            existing.regulator = spec.regulator
            existing.enabled = True
            continue
        session.add(
            Source(
                key=spec.key,
                name=spec.name,
                jurisdiction=spec.jurisdiction,
                regulator=spec.regulator,
                index_url=spec.index_url,
                enabled=True,
            )
        )
    session.commit()


def seed_demo_profiles(session: Session) -> None:
    if session.scalar(select(CompanyProfile).limit(1)):
        return
    session.add_all(
        [
            CompanyProfile(
                name="Demo Bank Australia",
                jurisdiction="AU",
                industry="Banking",
                entity_type="Foreign ADI",
                activities_json=json.dumps(["deposits", "lending", "international transfers", "customer due diligence"]),
                regulators_json=json.dumps(["APRA", "ASIC", "AUSTRAC"]),
            ),
            CompanyProfile(
                name="Demo Accounting Firm Australia",
                jurisdiction="AU",
                industry="Accounting",
                entity_type="Professional services firm",
                activities_json=json.dumps(["accounting", "company services", "customer onboarding"]),
                regulators_json=json.dumps(["AUSTRAC", "ASIC"]),
            ),
            CompanyProfile(
                name="Demo Software Company Taiwan",
                jurisdiction="TW",
                industry="Software",
                entity_type="Private company",
                activities_json=json.dumps(["SaaS", "software development"]),
                regulators_json=json.dumps([]),
            ),
        ]
    )
    session.commit()


def initialise() -> None:
    init_db()
    with SessionLocal() as session:
        seed_sources(session)
        seed_demo_profiles(session)


async def _analyse_event(session: Session, analyzer: Analyzer, source: Source, event: ChangeEvent, material: str) -> None:
    analysis = await analyzer.analyse_change(source.regulator, event.document.title, event.event_type, material)
    event.analysis_json = analysis.model_dump_json()
    event.risk_level = analysis.risk_level
    event.confidence = analysis.confidence
    session.flush()

    companies = list(session.scalars(select(CompanyProfile)))
    for company in companies:
        company_data = {
            "name": company.name,
            "jurisdiction": company.jurisdiction,
            "industry": company.industry,
            "entity_type": company.entity_type,
            "activities": _json(company.activities_json, []),
            "regulators": _json(company.regulators_json, []),
        }
        app = await analyzer.analyse_applicability(analysis, company_data, source.regulator)
        existing = session.scalar(
            select(Impact).where(
                Impact.change_event_id == event.id,
                Impact.company_profile_id == company.id,
            )
        )
        if not existing:
            existing = Impact(change_event_id=event.id, company_profile_id=company.id)
            session.add(existing)
        existing.applicability = app.applicability
        existing.score = app.score
        existing.reasoning = app.reasoning
        existing.actions_json = json.dumps(app.actions)
    session.commit()


async def run_monitor() -> dict:
    initialise()
    fetcher = Fetcher()
    analyzer = Analyzer()
    stats = {"sources": 0, "discovered": 0, "new": 0, "updated": 0, "unchanged": 0, "errors": []}

    try:
        with SessionLocal() as session:
            source_map = {s.key: s for s in session.scalars(select(Source).where(Source.enabled.is_(True)))}

            for adapter in adapters():
                source = source_map.get(adapter.spec.key)
                if not source:
                    continue
                stats["sources"] += 1
                try:
                    links = await adapter.discover(fetcher)
                except Exception as exc:
                    stats["errors"].append({"source": source.key, "stage": "discover", "error": f"{type(exc).__name__}: {exc}"})
                    continue

                stats["discovered"] += len(links)
                for link in links:
                    try:
                        fetched = await fetcher.fetch_document(link.url, link.title)
                        if len(fetched.text) < 120:
                            raise ValueError("Document text too short after extraction")
                        digest = content_hash(fetched.text)
                        now = datetime.now(timezone.utc)
                        doc = session.scalar(
                            select(Document).where(Document.source_id == source.id, Document.url == link.url)
                        )
                        if not doc:
                            doc = Document(
                                source_id=source.id,
                                url=link.url,
                                title=link.title,
                                current_hash=digest,
                                current_text=fetched.text,
                                first_seen_at=now,
                                last_seen_at=now,
                            )
                            session.add(doc)
                            session.flush()
                            version = DocumentVersion(document_id=doc.id, content_hash=digest, text=fetched.text)
                            session.add(version)
                            session.flush()
                            event = ChangeEvent(
                                document_id=doc.id,
                                event_type="NEW_DOCUMENT",
                                new_version_id=version.id,
                                diff_text="",
                            )
                            session.add(event)
                            session.flush()
                            stats["new"] += 1
                            await _analyse_event(session, analyzer, source, event, fetched.text[:30000])
                            continue

                        doc.last_seen_at = now
                        doc.title = link.title or doc.title
                        if doc.current_hash == digest:
                            stats["unchanged"] += 1
                            session.commit()
                            continue

                        previous = session.scalar(
                            select(DocumentVersion)
                            .where(DocumentVersion.document_id == doc.id)
                            .order_by(DocumentVersion.id.desc())
                            .limit(1)
                        )
                        diff = line_diff(doc.current_text, fetched.text)
                        version = DocumentVersion(document_id=doc.id, content_hash=digest, text=fetched.text)
                        session.add(version)
                        session.flush()
                        event = ChangeEvent(
                            document_id=doc.id,
                            event_type="UPDATED_DOCUMENT",
                            old_version_id=previous.id if previous else None,
                            new_version_id=version.id,
                            diff_text=diff,
                        )
                        session.add(event)
                        doc.current_hash = digest
                        doc.current_text = fetched.text
                        session.flush()
                        stats["updated"] += 1
                        await _analyse_event(session, analyzer, source, event, diff or fetched.text[:30000])
                    except Exception as exc:
                        session.rollback()
                        stats["errors"].append({
                            "source": source.key,
                            "url": link.url,
                            "stage": "fetch/process",
                            "error": f"{type(exc).__name__}: {exc}",
                        })
    finally:
        await fetcher.close()

    return stats
