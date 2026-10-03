from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    jurisdiction: Mapped[str] = mapped_column(String(32), index=True)
    regulator: Mapped[str] = mapped_column(String(64), index=True)
    index_url: Mapped[str] = mapped_column(Text)
    enabled: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    documents: Mapped[list["Document"]] = relationship(back_populates="source")


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (UniqueConstraint("source_id", "url", name="uq_document_source_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    current_hash: Mapped[str] = mapped_column(String(64), index=True)
    current_text: Mapped[str] = mapped_column(Text)
    first_seen_at: Mapped[datetime] = mapped_column(default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(default=utcnow)

    source: Mapped[Source] = relationship(back_populates="documents")
    versions: Mapped[list["DocumentVersion"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    changes: Mapped[list["ChangeEvent"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    document: Mapped[Document] = relationship(back_populates="versions")


class ChangeEvent(Base):
    __tablename__ = "change_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(32), index=True)  # NEW_DOCUMENT / UPDATED_DOCUMENT
    old_version_id: Mapped[int | None] = mapped_column(ForeignKey("document_versions.id"), nullable=True)
    new_version_id: Mapped[int] = mapped_column(ForeignKey("document_versions.id"))
    diff_text: Mapped[str] = mapped_column(Text, default="")
    analysis_json: Mapped[str] = mapped_column(Text, default="{}")
    risk_level: Mapped[str] = mapped_column(String(16), default="review", index=True)
    confidence: Mapped[float] = mapped_column(default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=utcnow, index=True)

    document: Mapped[Document] = relationship(back_populates="changes")
    impacts: Mapped[list["Impact"]] = relationship(back_populates="change", cascade="all, delete-orphan")


class CompanyProfile(Base):
    __tablename__ = "company_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    jurisdiction: Mapped[str] = mapped_column(String(32), index=True)
    industry: Mapped[str] = mapped_column(String(120), index=True)
    entity_type: Mapped[str] = mapped_column(String(120))
    activities_json: Mapped[str] = mapped_column(Text, default="[]")
    regulators_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)


class Impact(Base):
    __tablename__ = "impacts"
    __table_args__ = (UniqueConstraint("change_event_id", "company_profile_id", name="uq_change_profile"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    change_event_id: Mapped[int] = mapped_column(ForeignKey("change_events.id"), index=True)
    company_profile_id: Mapped[int] = mapped_column(ForeignKey("company_profiles.id"), index=True)
    applicability: Mapped[str] = mapped_column(String(32), default="review", index=True)
    score: Mapped[float] = mapped_column(default=0.0)
    reasoning: Mapped[str] = mapped_column(Text, default="")
    actions_json: Mapped[str] = mapped_column(Text, default="[]")

    change: Mapped[ChangeEvent] = relationship(back_populates="impacts")
    company: Mapped[CompanyProfile] = relationship()
