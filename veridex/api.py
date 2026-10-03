from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func, select

from .db import SessionLocal
from .engine import initialise, run_monitor
from .models import ChangeEvent, CompanyProfile, Document, Impact, Source


app = FastAPI(title="Veridex Alpha", version="0.1.0")
STATIC_DIR = Path(__file__).with_name("static")


class ProfileIn(BaseModel):
    name: str
    jurisdiction: str
    industry: str
    entity_type: str
    activities: list[str] = []
    regulators: list[str] = []


@app.on_event("startup")
def startup() -> None:
    initialise()


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "product": "Veridex Alpha", "version": "0.1.0"}


@app.get("/api/stats")
def stats() -> dict:
    with SessionLocal() as session:
        return {
            "sources": session.scalar(select(func.count()).select_from(Source)) or 0,
            "documents": session.scalar(select(func.count()).select_from(Document)) or 0,
            "changes": session.scalar(select(func.count()).select_from(ChangeEvent)) or 0,
            "profiles": session.scalar(select(func.count()).select_from(CompanyProfile)) or 0,
            "high_risk": session.scalar(select(func.count()).select_from(ChangeEvent).where(ChangeEvent.risk_level.in_(["high", "critical"]))) or 0,
        }


@app.get("/api/changes")
def changes(limit: int = 50) -> list[dict]:
    limit = max(1, min(limit, 200))
    with SessionLocal() as session:
        rows = session.execute(
            select(ChangeEvent, Document, Source)
            .join(Document, ChangeEvent.document_id == Document.id)
            .join(Source, Document.source_id == Source.id)
            .order_by(ChangeEvent.created_at.desc())
            .limit(limit)
        ).all()
        result = []
        for event, doc, source in rows:
            analysis = json.loads(event.analysis_json or "{}")
            result.append({
                "id": event.id,
                "event_type": event.event_type,
                "risk_level": event.risk_level,
                "confidence": event.confidence,
                "created_at": event.created_at.isoformat(),
                "regulator": source.regulator,
                "jurisdiction": source.jurisdiction,
                "title": doc.title,
                "url": doc.url,
                "summary": analysis.get("summary", ""),
                "topics": analysis.get("topics", []),
                "requires_human_review": analysis.get("requires_human_review", True),
            })
        return result


@app.get("/api/changes/{change_id}")
def change_detail(change_id: int) -> dict:
    with SessionLocal() as session:
        row = session.execute(
            select(ChangeEvent, Document, Source)
            .join(Document, ChangeEvent.document_id == Document.id)
            .join(Source, Document.source_id == Source.id)
            .where(ChangeEvent.id == change_id)
        ).first()
        if not row:
            raise HTTPException(404, "Change not found")
        event, doc, source = row
        impacts = session.execute(
            select(Impact, CompanyProfile)
            .join(CompanyProfile, Impact.company_profile_id == CompanyProfile.id)
            .where(Impact.change_event_id == event.id)
        ).all()
        return {
            "id": event.id,
            "event_type": event.event_type,
            "risk_level": event.risk_level,
            "confidence": event.confidence,
            "created_at": event.created_at.isoformat(),
            "regulator": source.regulator,
            "jurisdiction": source.jurisdiction,
            "title": doc.title,
            "url": doc.url,
            "analysis": json.loads(event.analysis_json or "{}"),
            "diff": event.diff_text,
            "impacts": [
                {
                    "company": company.name,
                    "applicability": impact.applicability,
                    "score": impact.score,
                    "reasoning": impact.reasoning,
                    "actions": json.loads(impact.actions_json or "[]"),
                }
                for impact, company in impacts
            ],
        }


@app.get("/api/profiles")
def profiles() -> list[dict]:
    with SessionLocal() as session:
        rows = list(session.scalars(select(CompanyProfile).order_by(CompanyProfile.name)))
        return [
            {
                "id": x.id,
                "name": x.name,
                "jurisdiction": x.jurisdiction,
                "industry": x.industry,
                "entity_type": x.entity_type,
                "activities": json.loads(x.activities_json or "[]"),
                "regulators": json.loads(x.regulators_json or "[]"),
            }
            for x in rows
        ]


@app.post("/api/profiles")
def create_profile(profile: ProfileIn) -> dict:
    with SessionLocal() as session:
        existing = session.scalar(select(CompanyProfile).where(CompanyProfile.name == profile.name))
        if existing:
            raise HTTPException(409, "Profile name already exists")
        row = CompanyProfile(
            name=profile.name,
            jurisdiction=profile.jurisdiction.upper(),
            industry=profile.industry,
            entity_type=profile.entity_type,
            activities_json=json.dumps(profile.activities),
            regulators_json=json.dumps(profile.regulators),
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"id": row.id, "name": row.name}


@app.post("/api/run")
async def run_now() -> dict:
    return await run_monitor()
