from __future__ import annotations

import time
from datetime import UTC, datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from signalbrief.extraction import (
    build_summary,
    extract_key_facts,
    extract_metrics,
    identify_opportunities,
    identify_risks,
    score_sentiment,
)
from signalbrief.models import (
    AgentEvent,
    Briefing,
    ExtractedFact,
    Metric,
    Opportunity,
    Risk,
    Sentiment,
    SourceDocument,
)
from signalbrief.rag import EvidenceIndex
from signalbrief.search import SearchPlan, build_search_plan, collect_sources


class ResearchState(TypedDict, total=False):
    topic: str
    plan: SearchPlan
    sources: list[SourceDocument]
    index: EvidenceIndex
    key_facts: list[ExtractedFact]
    metrics: list[Metric]
    risks: list[Risk]
    opportunities: list[Opportunity]
    sentiment: Sentiment
    executive_summary: str
    agent_events: list[AgentEvent]


def _event(agent: str, detail: str, latency_ms: int = 0) -> AgentEvent:
    return AgentEvent(agent=agent, status="complete", detail=detail, latency_ms=latency_ms)


def _timed(agent: str, detail: str, fn):
    start = time.perf_counter()
    result = fn()
    latency_ms = int((time.perf_counter() - start) * 1000)
    return result, _event(agent, detail, latency_ms)


def planner_node(state: ResearchState) -> ResearchState:
    plan, event = _timed(
        "Planner",
        "Converted the topic into targeted research queries.",
        lambda: build_search_plan(state["topic"]),
    )
    return {"plan": plan, "agent_events": state.get("agent_events", []) + [event]}


def searcher_node(state: ResearchState) -> ResearchState:
    sources, event = _timed(
        "Search Agent",
        "Collected live or demo web sources and deduplicated them.",
        lambda: collect_sources(state["plan"]),
    )
    return {"sources": sources, "agent_events": state.get("agent_events", []) + [event]}


def reader_node(state: ResearchState) -> ResearchState:
    index, event = _timed(
        "Reader / RAG Agent",
        "Chunked documents and built a retrieval index over source evidence.",
        lambda: EvidenceIndex(state["sources"]),
    )
    return {"index": index, "agent_events": state.get("agent_events", []) + [event]}


def extractor_node(state: ResearchState) -> ResearchState:
    def run():
        return extract_key_facts(state["topic"], state["index"]), extract_metrics(state["sources"])

    (facts, metrics), event = _timed(
        "Extraction Agent",
        "Pulled facts and numeric signals into typed Pydantic objects.",
        run,
    )
    return {"key_facts": facts, "metrics": metrics, "agent_events": state.get("agent_events", []) + [event]}


def analyst_node(state: ResearchState) -> ResearchState:
    def run():
        return (
            identify_risks(state["index"]),
            identify_opportunities(state["index"]),
            score_sentiment(state["sources"]),
        )

    (risks, opportunities, sentiment), event = _timed(
        "Risk / Opportunity Agent",
        "Scored downside, upside, and sentiment drivers from retrieved evidence.",
        run,
    )
    return {
        "risks": risks,
        "opportunities": opportunities,
        "sentiment": sentiment,
        "agent_events": state.get("agent_events", []) + [event],
    }


def writer_node(state: ResearchState) -> ResearchState:
    summary, event = _timed(
        "Briefing Writer",
        "Synthesised the final executive summary from structured evidence.",
        lambda: build_summary(state["topic"], state["key_facts"], state["sentiment"]),
    )
    return {"executive_summary": summary, "agent_events": state.get("agent_events", []) + [event]}


def build_graph():
    graph = StateGraph(ResearchState)
    graph.add_node("planner", planner_node)
    graph.add_node("searcher", searcher_node)
    graph.add_node("reader", reader_node)
    graph.add_node("extractor", extractor_node)
    graph.add_node("analyst", analyst_node)
    graph.add_node("writer", writer_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "searcher")
    graph.add_edge("searcher", "reader")
    graph.add_edge("reader", "extractor")
    graph.add_edge("extractor", "analyst")
    graph.add_edge("analyst", "writer")
    graph.add_edge("writer", END)
    return graph.compile()


def run_briefing(topic: str) -> Briefing:
    cleaned = topic.strip()
    if not cleaned:
        raise ValueError("A company name or research topic is required.")

    final_state: ResearchState = build_graph().invoke({"topic": cleaned, "agent_events": []})
    return Briefing(
        topic=cleaned,
        generated_at=datetime.now(UTC),
        executive_summary=final_state["executive_summary"],
        key_facts=final_state["key_facts"],
        metrics=final_state["metrics"],
        risks=final_state["risks"],
        opportunities=final_state["opportunities"],
        sentiment=final_state["sentiment"],
        sources=final_state["sources"],
        agent_events=final_state["agent_events"],
    )
