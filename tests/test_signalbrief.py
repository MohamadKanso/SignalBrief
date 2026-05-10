from signalbrief import run_briefing
from signalbrief.rag import EvidenceIndex
from signalbrief.search import DemoSearchProvider


def test_demo_briefing_returns_structured_sections():
    briefing = run_briefing("NVIDIA AI infrastructure")

    assert briefing.topic == "NVIDIA AI infrastructure"
    assert briefing.executive_summary
    assert len(briefing.sources) >= 3
    assert len(briefing.key_facts) >= 2
    assert briefing.risks
    assert briefing.opportunities
    assert briefing.sentiment.label in {"Bearish", "Mixed", "Constructive", "Bullish"}
    assert {event.agent for event in briefing.agent_events} >= {
        "Planner",
        "Search Agent",
        "Reader / RAG Agent",
        "Extraction Agent",
        "Risk / Opportunity Agent",
        "Briefing Writer",
    }


def test_evidence_index_retrieves_relevant_chunks():
    sources = DemoSearchProvider().search("OpenAI market risks")
    index = EvidenceIndex(sources)
    results = index.search("pricing pressure regulatory scrutiny", k=2)

    assert results
    assert results[0].relevance > 0
    assert "pressure" in results[0].quote.lower() or "scrutiny" in results[0].quote.lower()

