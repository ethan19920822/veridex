from __future__ import annotations

import json
import re
from typing import Any

import httpx

from .config import settings
from .schemas import ApplicabilityAnalysis, RegulatoryAnalysis


SYSTEM_PROMPT = """You are the regulatory change analysis engine for Veridex.
Analyse only the supplied official-source text or diff. Do not invent law, dates, obligations, or affected entities.
This is regulatory intelligence, not legal advice. If evidence is insufficient, say so and require human review.
Return one JSON object only.
"""


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.S)
        if not match:
            raise
        return json.loads(match.group(0))


class Analyzer:
    async def analyse_change(self, regulator: str, title: str, event_type: str, source_text: str) -> RegulatoryAnalysis:
        if settings.llm_enabled:
            return await self._analyse_llm(regulator, title, event_type, source_text)
        return self._analyse_fallback(regulator, title, event_type, source_text)

    async def analyse_applicability(
        self,
        analysis: RegulatoryAnalysis,
        company: dict[str, Any],
        regulator: str,
    ) -> ApplicabilityAnalysis:
        if settings.llm_enabled:
            return await self._applicability_llm(analysis, company, regulator)
        return self._applicability_fallback(analysis, company, regulator)

    async def _chat(self, messages: list[dict[str, str]], temperature: float = 0.1) -> dict[str, Any]:
        base = settings.llm_base_url.rstrip("/")
        url = f"{base}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.llm_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": settings.llm_model,
            "temperature": temperature,
            "messages": messages,
        }
        async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
        content = data["choices"][0]["message"]["content"]
        return _extract_json(content)

    async def _analyse_llm(self, regulator: str, title: str, event_type: str, source_text: str) -> RegulatoryAnalysis:
        schema = RegulatoryAnalysis.model_json_schema()
        prompt = f"""Regulator: {regulator}
Document: {title}
Event: {event_type}

Analyse the regulatory significance of the material below.
- Distinguish binding requirements, guidance, consultation, enforcement/news, and administrative changes.
- effective_date must be null unless explicitly supported.
- recommended_actions should be review-oriented, not legal conclusions.
- confidence reflects evidence quality in the supplied material.
- requires_human_review should normally be true for material compliance decisions.

Return JSON matching this schema:
{json.dumps(schema)}

SOURCE MATERIAL:
{source_text[:30000]}
"""
        try:
            data = await self._chat([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}])
            return RegulatoryAnalysis.model_validate(data)
        except Exception as exc:
            fallback = self._analyse_fallback(regulator, title, event_type, source_text)
            fallback.rationale = f"LLM analysis failed; deterministic fallback used. {type(exc).__name__}: {exc}"
            fallback.confidence = min(fallback.confidence, 0.45)
            return fallback

    def _analyse_fallback(self, regulator: str, title: str, event_type: str, source_text: str) -> RegulatoryAnalysis:
        lower = f"{title}\n{source_text}".lower()
        high_terms = ("must", "required", "in force", "effective from", "obligation", "penalty", "enforcement")
        medium_terms = ("consultation", "guidance", "update", "amend", "reporting", "expectation")
        high_hits = sum(term in lower for term in high_terms)
        medium_hits = sum(term in lower for term in medium_terms)
        if high_hits >= 3:
            risk = "high"
        elif high_hits or medium_hits >= 2:
            risk = "medium"
        else:
            risk = "review"
        topics = []
        topic_map = {
            "aml": "AML/CTF",
            "customer due diligence": "Customer Due Diligence",
            "reporting": "Reporting",
            "operational risk": "Operational Risk",
            "governance": "Governance",
            "capital": "Capital",
            "liquidity": "Liquidity",
            "financial services": "Financial Services",
        }
        for needle, label in topic_map.items():
            if needle in lower:
                topics.append(label)
        summary = f"{regulator} {event_type.lower().replace('_', ' ')} detected for '{title}'. Human review is required to determine legal effect."
        return RegulatoryAnalysis(
            summary=summary,
            change_type="new publication" if event_type == "NEW_DOCUMENT" else "document update",
            topics=topics,
            recommended_actions=["Review the official source", "Confirm applicability to the organisation", "Record the review decision and evidence"],
            risk_level=risk,
            confidence=0.42,
            rationale="Deterministic keyword analysis only; no LLM configured.",
            requires_human_review=True,
        )

    async def _applicability_llm(self, analysis: RegulatoryAnalysis, company: dict[str, Any], regulator: str) -> ApplicabilityAnalysis:
        schema = ApplicabilityAnalysis.model_json_schema()
        prompt = f"""Assess whether this regulatory change may apply to the organisation.
Do not make a final legal determination. Use only the supplied profile and analysis.

REGULATOR: {regulator}
ANALYSIS: {analysis.model_dump_json()}
COMPANY: {json.dumps(company)}

Return JSON matching:
{json.dumps(schema)}
"""
        try:
            data = await self._chat([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}])
            return ApplicabilityAnalysis.model_validate(data)
        except Exception as exc:
            result = self._applicability_fallback(analysis, company, regulator)
            result.reasoning += f" LLM failed: {type(exc).__name__}."
            result.score = min(result.score, 0.55)
            return result

    def _applicability_fallback(self, analysis: RegulatoryAnalysis, company: dict[str, Any], regulator: str) -> ApplicabilityAnalysis:
        regulators = {str(x).upper() for x in company.get("regulators", [])}
        jurisdiction_match = company.get("jurisdiction", "").upper() == "AU"
        regulator_match = regulator.upper() in regulators
        haystack = " ".join(
            [company.get("industry", ""), company.get("entity_type", ""), *company.get("activities", [])]
        ).lower()
        topic_blob = " ".join(analysis.topics + analysis.affected_entities).lower()
        keyword_match = any(token in haystack for token in ("bank", "financial", "aml", "credit", "payment")) and any(
            token in topic_blob for token in ("aml", "financial", "bank", "report", "capital", "liquidity")
        )
        if jurisdiction_match and regulator_match:
            score = 0.78 if keyword_match else 0.66
            status = "possibly_applicable"
            reasoning = f"The company is in Australia and lists {regulator} as a regulator. Subject-matter review is still required."
        elif not jurisdiction_match:
            score = 0.15
            status = "not_applicable"
            reasoning = "The current alpha profile jurisdiction does not match Australia. Cross-border effects are not yet modelled."
        else:
            score = 0.4
            status = "review"
            reasoning = f"The company does not list {regulator}; indirect applicability cannot be excluded."
        return ApplicabilityAnalysis(
            applicability=status,
            score=score,
            reasoning=reasoning,
            actions=["Confirm entity scope", "Review affected obligations", "Assign a human owner if applicable"],
        )
