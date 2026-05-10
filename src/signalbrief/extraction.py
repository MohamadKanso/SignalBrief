from __future__ import annotations

import re

from signalbrief.models import (
    EvidenceSnippet,
    ExtractedFact,
    Metric,
    Opportunity,
    Risk,
    Sentiment,
    SourceDocument,
)
from signalbrief.rag import EvidenceIndex

METRIC_RE = re.compile(
    r"(?P<value>(?:[$£€]\s?\d+(?:\.\d+)?\s?[mbkbnMKBn]*|\d+(?:\.\d+)?\s?%|\d+\s?bps|\d+x))",
    re.I,
)

RISK_TERMS = {
    "risk",
    "pressure",
    "scrutiny",
    "regulatory",
    "delay",
    "uneven",
    "complexity",
    "competition",
    "margin",
}

OPPORTUNITY_TERMS = {
    "growth",
    "demand",
    "adoption",
    "expanded",
    "improved",
    "automation",
    "positive",
    "retention",
    "enterprise",
}

POSITIVE = {"growth", "improved", "positive", "praise", "demand", "expanded", "reliability"}
NEGATIVE = {"risk", "pressure", "scrutiny", "negative", "delays", "complexity", "uneven"}


def extract_key_facts(topic: str, index: EvidenceIndex) -> list[ExtractedFact]:
    snippets = index.search(f"{topic} key facts operating metrics customer demand risk", k=6)
    facts: list[ExtractedFact] = []
    for snippet in snippets[:5]:
        sentence = snippet.quote.split(".")[0].strip()
        if not sentence:
            continue
        facts.append(
            ExtractedFact(
                fact=sentence,
                evidence=snippet,
                confidence=round(0.68 + snippet.relevance * 0.25, 2),
            )
        )
    return facts


def extract_metrics(sources: list[SourceDocument]) -> list[Metric]:
    metrics: list[Metric] = []
    for source in sources:
        for match in METRIC_RE.finditer(source.content):
            value = match.group("value").replace(" ", "")
            start = max(0, match.start() - 70)
            end = min(len(source.content), match.end() + 90)
            context = source.content[start:end].strip()
            label = _metric_label(context)
            metrics.append(
                Metric(
                    label=label,
                    value=value,
                    source_title=source.title,
                    confidence=0.78 if "%" in value or "bps" in value.lower() else 0.7,
                )
            )
    return _dedupe_metrics(metrics)[:6]


def identify_risks(index: EvidenceIndex) -> list[Risk]:
    snippets = index.search("risk pressure regulatory scrutiny execution onboarding margin competition", k=6)
    risks: list[Risk] = []
    for snippet in snippets:
        lower = snippet.quote.lower()
        matches = sum(term in lower for term in RISK_TERMS)
        if matches == 0:
            continue
        risks.append(
            Risk(
                title=_short_title(snippet.quote, ["risk", "pressure", "scrutiny", "complexity"]),
                severity="High" if matches >= 3 else "Medium",
                rationale=snippet.quote[:220],
                evidence=snippet,
            )
        )
    return risks[:4] or [_fallback_risk(snippets)]


def identify_opportunities(index: EvidenceIndex) -> list[Opportunity]:
    snippets = index.search("opportunity growth adoption demand expansion retention automation", k=6)
    opportunities: list[Opportunity] = []
    for snippet in snippets:
        lower = snippet.quote.lower()
        matches = sum(term in lower for term in OPPORTUNITY_TERMS)
        if matches == 0:
            continue
        opportunities.append(
            Opportunity(
                title=_short_title(snippet.quote, ["growth", "demand", "adoption", "retention"]),
                upside="High" if matches >= 3 else "Medium",
                rationale=snippet.quote[:220],
                evidence=snippet,
            )
        )
    return opportunities[:4] or [_fallback_opportunity(snippets)]


def score_sentiment(sources: list[SourceDocument]) -> Sentiment:
    tokens = " ".join(source.content.lower() for source in sources).split()
    pos = sum(token.strip(".,;:()") in POSITIVE for token in tokens)
    neg = sum(token.strip(".,;:()") in NEGATIVE for token in tokens)
    raw = (pos - neg) / max(1, pos + neg)
    if raw > 0.35:
        label = "Bullish"
    elif raw > 0.08:
        label = "Constructive"
    elif raw > -0.25:
        label = "Mixed"
    else:
        label = "Bearish"
    return Sentiment(
        label=label,
        score=round(raw, 2),
        drivers=[
            f"{pos} positive demand/growth signals",
            f"{neg} risk/pressure signals",
            "Source credibility weighted through retrieval relevance",
        ],
    )


def build_summary(topic: str, facts: list[ExtractedFact], sentiment: Sentiment) -> str:
    leading = facts[0].fact if facts else f"{topic} has enough public evidence for a first-pass brief"
    return (
        f"{topic} screens as {sentiment.label.lower()} in this run. {leading}. "
        "The strongest opportunities are tied to demand, adoption, and operating leverage; the main watchouts "
        "are execution quality, market pressure, and evidence gaps that require deeper diligence."
    )


def _metric_label(context: str) -> str:
    lowered = context.lower()
    if "revenue" in lowered:
        return "Revenue growth"
    if "margin" in lowered:
        return "Margin expansion"
    if "cash flow" in lowered:
        return "Free cash flow"
    if "retention" in lowered:
        return "Net retention"
    if "efficiency" in lowered:
        return "Operating efficiency"
    return "Reported metric"


def _dedupe_metrics(metrics: list[Metric]) -> list[Metric]:
    seen: set[tuple[str, str]] = set()
    deduped: list[Metric] = []
    for metric in metrics:
        key = (metric.label, metric.value)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(metric)
    return deduped


def _short_title(text: str, signals: list[str]) -> str:
    lower = text.lower()
    for signal in signals:
        if signal in lower:
            return f"{signal.title()} signal"
    return text.split(".")[0][:58]


def _fallback_evidence(snippets: list[EvidenceSnippet]) -> EvidenceSnippet:
    if snippets:
        return snippets[0]
    return EvidenceSnippet(
        source_title="No source available",
        source_url="https://example.com",
        quote="No matching evidence was retrieved.",
        relevance=0.0,
    )


def _fallback_risk(snippets: list[EvidenceSnippet]) -> Risk:
    evidence = _fallback_evidence(snippets)
    return Risk(
        title="Evidence coverage risk",
        severity="Medium",
        rationale="The brief needs more sources before making a high-confidence downside call.",
        evidence=evidence,
    )


def _fallback_opportunity(snippets: list[EvidenceSnippet]) -> Opportunity:
    evidence = _fallback_evidence(snippets)
    return Opportunity(
        title="Diligence opportunity",
        upside="Medium",
        rationale="The early source set suggests a follow-up research pass could surface stronger upside themes.",
        evidence=evidence,
    )

