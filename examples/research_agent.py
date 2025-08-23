"""
Research Agent Example

Shows how to build a research pipeline using LambdaCat's agent framework.
"""

import re
import time
from dataclasses import dataclass, field
from typing import Any

from LambdaCat.agents.actions import Task, parallel, sequence
from LambdaCat.agents.runtime import compile_plan
from LambdaCat.core.fp.instances.result import Result
from LambdaCat.core.fp.kleisli import Kleisli


@dataclass(frozen=True)
class ResearchQuery:
    question: str
    domain: str = "general"
    depth: str = "comprehensive"
    sources: set[str] = field(default_factory=lambda: {"academic", "web"})


@dataclass(frozen=True)
class ResearchEvidence:
    content: str
    source: str
    confidence: float
    relevance_score: float
    timestamp: float

    def quality_score(self) -> float:
        return (self.confidence * 0.6 + self.relevance_score * 0.4)


@dataclass(frozen=True)
class KnowledgeSource:
    name: str
    reliability: float
    latency: float
    specialties: set[str]


# Mock data sources
KNOWLEDGE_SOURCES = {
    "academic": KnowledgeSource(
        "Academic Papers",
        reliability=0.95,
        latency=2.0,
        specialties={"science", "technology"}
    ),
    "web": KnowledgeSource(
        "Web Search",
        reliability=0.65,
        latency=1.0,
        specialties={"news", "general"}
    ),
    "expert": KnowledgeSource(
        "Expert Network",
        reliability=0.85,
        latency=5.0,
        specialties={"industry", "analysis"}
    )
}


# Research functions
def parse_query(query_text: str) -> ResearchQuery:
    """Parse natural language into structured query."""
    domain = "general"
    if any(term in query_text.lower() for term in ["AI", "machine learning"]):
        domain = "artificial_intelligence"
    elif any(term in query_text.lower() for term in ["quantum", "physics"]):
        domain = "physics"
    
    return ResearchQuery(
        question=query_text.strip(),
        domain=domain,
        sources={"academic", "web", "expert"}
    )


def extract_concepts(query: ResearchQuery) -> set[str]:
    """Extract key concepts from query."""
    stop_words = {"the", "a", "an", "is", "are", "what", "how", "why"}
    words = re.findall(r'\b\w{3,}\b', query.question.lower())
    return {word for word in words if word not in stop_words}


def search_source(source_name: str, concepts: set[str]) -> list[ResearchEvidence]:
    """Search a knowledge source for information."""
    source = KNOWLEDGE_SOURCES.get(source_name)
    if not source:
        return []
    
    # Simulate search
    time.sleep(source.latency * 0.1)  # Reduced for demo
    
    evidence = []
    for concept in list(concepts)[:3]:  # Limit for demo
        confidence = min(source.reliability + (hash(concept) % 20) / 100, 1.0)
        relevance = max(0.3, (hash(f"{source_name}{concept}") % 100) / 100)
        
        content = f"Research from {source.name} on '{concept}': " \
                 f"Key findings show relevant insights for the field."
        
        evidence.append(ResearchEvidence(
            content=content,
            source=source.name,
            confidence=confidence,
            relevance_score=relevance,
            timestamp=time.time()
        ))
    
    return evidence


def synthesize_findings(evidence_list: list[ResearchEvidence]) -> dict[str, Any]:
    """Combine research findings into summary."""
    if not evidence_list:
        return {"summary": "No evidence found", "confidence": 0.0}
    
    # Sort by quality
    sorted_evidence = sorted(evidence_list, key=lambda e: e.quality_score(), reverse=True)
    evidence_to_use = [e for e in sorted_evidence if e.quality_score() > 0.5][:10]
    
    sources = {e.source for e in evidence_to_use}
    avg_confidence = sum(e.quality_score() for e in evidence_to_use) / len(evidence_to_use)
    
    summary = f"Analysis of {len(evidence_to_use)} pieces of evidence from " \
             f"{len(sources)} sources reveals consistent patterns in the research domain."
    
    return {
        "summary": summary,
        "confidence": avg_confidence,
        "sources": list(sources),
        "evidence_count": len(evidence_to_use)
    }


# Agent actions
def create_actions():
    """Create action registry for research agent."""
    return {
        "parse_query": parse_query,
        "extract_concepts": extract_concepts,
        "search_academic": lambda concepts: search_source("academic", concepts),
        "search_web": lambda concepts: search_source("web", concepts),
        "search_expert": lambda concepts: search_source("expert", concepts),
        "combine_evidence": lambda evidence_lists: [
            item for sublist in evidence_lists 
            for item in (sublist if isinstance(sublist, list) else [sublist])
        ],
        "synthesize": synthesize_findings,
    }


# Example plans
def basic_plan():
    """Simple sequential research plan."""
    return sequence(
        Task("parse_query"),
        Task("extract_concepts"),
        Task("search_academic"),
        Task("synthesize")
    )


def parallel_plan():
    """Parallel search across multiple sources."""
    return sequence(
        Task("parse_query"),
        Task("extract_concepts"),
        parallel(
            Task("search_academic"),
            Task("search_web"),
            Task("search_expert")
        ),
        Task("combine_evidence"),
        Task("synthesize")
    )


# Kleisli pipeline with error handling
def create_kleisli_pipeline():
    """Create monadic research pipeline."""
    
    def safe_parse(text: str) -> Result[ResearchQuery, str]:
        if not text.strip():
            return Result.err("Empty query")
        return Result.ok(parse_query(text))
    
    def safe_extract(query: ResearchQuery) -> Result[set[str], str]:
        concepts = extract_concepts(query)
        if not concepts:
            return Result.err("No concepts found")
        return Result.ok(concepts)
    
    def safe_search(concepts: set[str]) -> Result[list[ResearchEvidence], str]:
        all_evidence = []
        for source_name in ["academic", "web", "expert"]:
            evidence = search_source(source_name, concepts)
            all_evidence.extend(evidence)
        
        if not all_evidence:
            return Result.err("No evidence found")
        return Result.ok(all_evidence)
    
    parse_kleisli = Kleisli(safe_parse)
    extract_kleisli = Kleisli(safe_extract)
    search_kleisli = Kleisli(safe_search)
    
    return search_kleisli.compose(extract_kleisli).compose(parse_kleisli)


def demo_basic():
    """Demo basic research functionality."""
    print("Basic Research Demo")
    print("=" * 30)
    
    query = "What are the latest developments in quantum computing?"
    
    actions = create_actions()
    plan = basic_plan()
    executable = compile_plan(actions, plan)
    result = executable(query)
    
    print(f"Query: {query}")
    print(f"Summary: {result.get('summary', '')[:100]}...")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print()


def demo_parallel():
    """Demo parallel research."""
    print("Parallel Research Demo")
    print("=" * 30)
    
    query = "How is AI being applied in climate research?"
    
    actions = create_actions()
    plan = parallel_plan()
    
    def combine_evidence_lists(evidence_lists):
        combined = []
        for evidence_list in evidence_lists:
            if isinstance(evidence_list, list):
                combined.extend(evidence_list)
        return combined
    
    executable = compile_plan(actions, plan, aggregate_fn=combine_evidence_lists)
    result = executable(query)
    
    print(f"Query: {query}")
    print(f"Sources: {result.get('sources', [])}")
    print(f"Evidence count: {result.get('evidence_count', 0)}")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print()


def demo_kleisli():
    """Demo monadic pipeline with error handling."""
    print("Kleisli Pipeline Demo")
    print("=" * 30)
    
    pipeline = create_kleisli_pipeline()
    
    # Valid query
    valid_result = pipeline("What are the environmental impacts of renewable energy?")
    if valid_result.is_ok():
        evidence = valid_result.get_or_else([])
        print(f"✅ Success: Found {len(evidence)} pieces of evidence")
    else:
        print(f"❌ Error: {valid_result}")
    
    # Invalid query
    invalid_result = pipeline("")
    if invalid_result.is_err():
        print(f"❌ Expected error: {invalid_result}")
    else:
        print("❌ Should have failed")
    
    print()


def main():
    """Run research agent demos."""
    print("Research Agent Example")
    print("=" * 40)
    print("Shows LambdaCat agent composition for research workflows\n")
    
    demo_basic()
    demo_parallel()
    demo_kleisli()
    
    print("✅ Demo complete!")
    print("\nFeatures shown:")
    print("• Sequential and parallel execution plans")
    print("• Error handling with Result types")
    print("• Kleisli composition for monadic pipelines")


if __name__ == "__main__":
    main()