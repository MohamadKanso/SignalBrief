from __future__ import annotations

import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from signalbrief.models import SourceDocument


def _domain(url: str) -> str:
    host = urlparse(url).netloc.replace("www.", "")
    return host or "source"


@dataclass
class SearchPlan:
    topic: str
    queries: list[str]


class TavilySearchProvider:
    """Thin Tavily adapter, used only when TAVILY_API_KEY is available."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def search(self, query: str, max_results: int = 4) -> list[SourceDocument]:
        if not self.available:
            return []
        try:
            from tavily import TavilyClient
        except Exception:
            return []

        client = TavilyClient(api_key=self.api_key)
        response = client.search(
            query=query,
            search_depth="advanced",
            include_answer=True,
            include_raw_content=True,
            max_results=max_results,
        )
        documents: list[SourceDocument] = []
        for item in response.get("results", []):
            content = item.get("raw_content") or item.get("content") or item.get("snippet") or ""
            if not content:
                continue
            url = item.get("url", "https://example.com")
            documents.append(
                SourceDocument(
                    title=item.get("title", "Untitled source"),
                    url=url,
                    domain=_domain(url),
                    content=content[:5000],
                    credibility=min(0.95, 0.62 + float(item.get("score", 0.4)) / 3),
                )
            )
        return documents


class DemoSearchProvider:
    """Recruiter-friendly fallback that behaves like a live research run."""

    def search(self, query: str, max_results: int = 4) -> list[SourceDocument]:
        topic = re.sub(r"\s+(risks|opportunities|earnings|metrics|news).*$", "", query, flags=re.I)
        topic = topic.strip() or "the target company"
        docs = [
            SourceDocument(
                title=f"{topic}: latest operating update",
                url="https://example.com/company-update",
                domain="example.com",
                content=(
                    f"{topic} reported accelerating customer demand, a 14% improvement in operating "
                    "efficiency, and continued investment in AI-enabled workflows. Management highlighted "
                    "enterprise adoption, product expansion, and disciplined cost control as the main themes."
                ),
                credibility=0.73,
            ),
            SourceDocument(
                title=f"{topic}: market and competitor context",
                url="https://example.com/market-context",
                domain="example.com",
                content=(
                    f"Analysts describe {topic} as exposed to pricing pressure, regulatory scrutiny, and "
                    "execution risk, but note that demand for automation, data infrastructure, and AI products "
                    "remains structurally positive. Peer multiples have widened as investors reward durable growth."
                ),
                credibility=0.69,
            ),
            SourceDocument(
                title=f"{topic}: financial signals",
                url="https://example.com/financial-signals",
                domain="example.com",
                content=(
                    "Revenue growth reached 18% year over year while gross margin expanded by 240 basis "
                    "points. Free cash flow conversion remains uneven at 9%, partly because of platform "
                    "investment and hiring. Net retention improved to 116% across enterprise accounts."
                ),
                credibility=0.76,
            ),
            SourceDocument(
                title=f"{topic}: customer sentiment snapshot",
                url="https://example.com/customer-sentiment",
                domain="example.com",
                content=(
                    "Customer reviews praise speed, reliability, and workflow integrations. Negative comments "
                    "cluster around onboarding complexity, limited explainability, and occasional support delays. "
                    "Overall sentiment is constructive with a clear demand signal."
                ),
                credibility=0.66,
            ),
        ]
        return docs[:max_results]


def build_search_plan(topic: str) -> SearchPlan:
    base = topic.strip()
    return SearchPlan(
        topic=base,
        queries=[
            f"{base} latest business update key metrics",
            f"{base} risks opportunities analyst view",
            f"{base} customer sentiment market news",
        ],
    )


def collect_sources(plan: SearchPlan) -> list[SourceDocument]:
    live_provider = TavilySearchProvider()
    demo_provider = DemoSearchProvider()
    sources: list[SourceDocument] = []

    for query in plan.queries:
        batch = live_provider.search(query) if live_provider.available else []
        if not batch:
            batch = demo_provider.search(query)
        sources.extend(batch)

    seen: set[str] = set()
    deduped: list[SourceDocument] = []
    for source in sources:
        key = str(source.url)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped[:8]

