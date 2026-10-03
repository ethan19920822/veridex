from typing import Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high", "critical", "review"]


class RegulatoryAnalysis(BaseModel):
    summary: str
    change_type: str = "unknown"
    effective_date: str | None = None
    affected_entities: list[str] = Field(default_factory=list)
    topics: list[str] = Field(default_factory=list)
    obligations: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    risk_level: RiskLevel = "review"
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    rationale: str = ""
    requires_human_review: bool = True


class ApplicabilityAnalysis(BaseModel):
    applicability: Literal["applicable", "possibly_applicable", "not_applicable", "review"] = "review"
    score: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = ""
    actions: list[str] = Field(default_factory=list)
