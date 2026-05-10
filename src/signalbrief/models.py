from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class SourceDocument(BaseModel):
    title: str
    url: HttpUrl | str
    domain: str
    content: str
    published_at: str | None = None
    credibility: float = Field(default=0.72, ge=0, le=1)


class AgentEvent(BaseModel):
    agent: str
    status: Literal["queued", "running", "complete"]
    detail: str
    latency_ms: int


class EvidenceSnippet(BaseModel):
    source_title: str
    source_url: HttpUrl | str
    quote: str
    relevance: float = Field(ge=0, le=1)


class ExtractedFact(BaseModel):
    fact: str
    evidence: EvidenceSnippet
    confidence: float = Field(ge=0, le=1)


class Metric(BaseModel):
    label: str
    value: str
    source_title: str
    confidence: float = Field(ge=0, le=1)


class Risk(BaseModel):
    title: str
    severity: Literal["Low", "Medium", "High"]
    rationale: str
    evidence: EvidenceSnippet


class Opportunity(BaseModel):
    title: str
    upside: Literal["Low", "Medium", "High"]
    rationale: str
    evidence: EvidenceSnippet


class Sentiment(BaseModel):
    label: Literal["Bearish", "Mixed", "Constructive", "Bullish"]
    score: float = Field(ge=-1, le=1)
    drivers: list[str]


class Briefing(BaseModel):
    topic: str
    generated_at: datetime
    executive_summary: str
    key_facts: list[ExtractedFact]
    metrics: list[Metric]
    risks: list[Risk]
    opportunities: list[Opportunity]
    sentiment: Sentiment
    sources: list[SourceDocument]
    agent_events: list[AgentEvent]

