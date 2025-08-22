"""
🔬 Deep Research Agent - LambdaCat Advanced Example

A sophisticated research agent that demonstrates the power of categorical composition
for building complex, reliable AI systems. This agent can:

1. Parse research queries and extract key concepts
2. Search multiple knowledge sources in parallel
3. Synthesize findings using different reasoning strategies
4. Validate and cross-reference information
5. Generate structured research reports

Key LambdaCat Features Demonstrated:
- Complex agent plans with parallel execution
- Monadic error handling with Result types
- State management for research context
- Lens-based data manipulation
- Natural transformations between data formats
- Kleisli composition for effectful computations
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

# LambdaCat imports
from LambdaCat.agents.actions import Task, sequence, parallel
from LambdaCat.agents.runtime import compile_plan
from LambdaCat.core.fp.instances.result import Result
from LambdaCat.core.fp.typeclasses import Monoid
from LambdaCat.core.fp.kleisli import Kleisli
from LambdaCat.core.diagram import Diagram


# ============================
# Domain Models & Data Types
# ============================

@dataclass(frozen=True)
class ResearchQuery:
    """Structured research query with metadata."""
    question: str
    domain: str = "general"
    depth: str = "comprehensive"  # surface, moderate, comprehensive, deep
    sources: Set[str] = field(default_factory=lambda: {"academic", "web", "datasets"})
    max_results: int = 20
    
    def complexity_score(self) -> float:
        """Calculate query complexity for resource allocation."""
        depth_scores = {"surface": 1.0, "moderate": 2.0, "comprehensive": 3.0, "deep": 4.0}
        return depth_scores.get(self.depth, 2.0) * len(self.sources) * (len(self.question.split()) / 10)


@dataclass(frozen=True)
class KnowledgeSource:
    """Represents a knowledge source with its characteristics."""
    name: str
    reliability: float  # 0.0 - 1.0
    latency: float     # seconds
    specialties: Set[str]
    cost: float = 0.0  # resource cost per query


@dataclass(frozen=True)
class ResearchEvidence:
    """A piece of evidence found during research."""
    content: str
    source: str
    confidence: float
    relevance_score: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def quality_score(self) -> float:
        """Overall quality combining confidence and relevance."""
        return (self.confidence * 0.6 + self.relevance_score * 0.4)


@dataclass
class ResearchContext:
    """Mutable state representing current research progress."""
    query: ResearchQuery
    evidence: List[ResearchEvidence] = field(default_factory=list)
    concepts_explored: Set[str] = field(default_factory=set)
    search_iterations: int = 0
    total_cost: float = 0.0
    synthesis_attempts: int = 0
    
    def add_evidence(self, evidence: ResearchEvidence) -> None:
        """Add new evidence to the context."""
        self.evidence.append(evidence)
        
    def get_best_evidence(self, min_quality: float = 0.7) -> List[ResearchEvidence]:
        """Get high-quality evidence above threshold."""
        return [e for e in self.evidence if e.quality_score() >= min_quality]


@dataclass(frozen=True)
class ResearchReport:
    """Final structured research output."""
    query: ResearchQuery
    executive_summary: str
    key_findings: List[str]
    evidence_quality: float
    confidence_level: str
    recommendations: List[str]
    sources_consulted: List[str]
    research_metadata: Dict[str, Any]


# ===============================
# Knowledge Sources (Simulated)
# ===============================

KNOWLEDGE_SOURCES = {
    "academic_db": KnowledgeSource(
        "Academic Database", 
        reliability=0.95, 
        latency=2.0, 
        specialties={"science", "technology", "medicine", "mathematics"}
    ),
    "expert_network": KnowledgeSource(
        "Expert Network", 
        reliability=0.85, 
        latency=5.0, 
        specialties={"industry", "consulting", "analysis"}
    ),
    "web_crawler": KnowledgeSource(
        "Web Crawler", 
        reliability=0.65, 
        latency=1.0, 
        specialties={"news", "general", "trends"}
    ),
    "patent_db": KnowledgeSource(
        "Patent Database", 
        reliability=0.90, 
        latency=3.0, 
        specialties={"technology", "innovation", "intellectual_property"}
    ),
    "research_papers": KnowledgeSource(
        "Research Papers", 
        reliability=0.98, 
        latency=4.0, 
        specialties={"academic", "peer_reviewed", "scientific"}
    )
}


# ===============================
# Diagram Generation for Research Visualization
# ===============================

def create_research_workflow_diagram() -> Diagram:
    """Create a diagram showing the research workflow process."""
    objects = [
        "Query", "Concepts", "Academic_DB", "Expert_Network", 
        "Web_Crawler", "Patents", "Papers", "Evidence", 
        "Validation", "Synthesis", "Report"
    ]
    
    edges = [
        ("Query", "Concepts", "extract"),
        ("Concepts", "Academic_DB", "search"),
        ("Concepts", "Expert_Network", "search"),
        ("Concepts", "Web_Crawler", "search"),
        ("Concepts", "Patents", "search"),
        ("Concepts", "Papers", "search"),
        ("Academic_DB", "Evidence", "results"),
        ("Expert_Network", "Evidence", "results"),
        ("Web_Crawler", "Evidence", "results"),
        ("Patents", "Evidence", "results"),
        ("Papers", "Evidence", "results"),
        ("Evidence", "Validation", "check"),
        ("Evidence", "Synthesis", "analyze"),
        ("Validation", "Synthesis", "quality_filter"),
        ("Synthesis", "Report", "generate")
    ]
    
    return Diagram.from_edges(objects, edges)


def create_evidence_synthesis_diagram(evidence_list: List[ResearchEvidence]) -> Diagram:
    """Create a diagram showing how evidence from different sources combines."""
    # Group evidence by source
    sources = {}
    for evidence in evidence_list:
        source = evidence.source.replace(" ", "_").replace("-", "_")
        if source not in sources:
            sources[source] = []
        sources[source].append(evidence)
    
    objects = ["Query"]
    edges = []
    
    # Add source nodes
    for source in sources.keys():
        objects.append(source)
        edges.append(("Query", source, "search"))
    
    # Add synthesis nodes based on quality
    high_quality_sources = [s for s, evs in sources.items() 
                           if any(e.quality_score() > 0.8 for e in evs)]
    medium_quality_sources = [s for s, evs in sources.items() 
                             if any(0.6 < e.quality_score() <= 0.8 for e in evs)]
    
    if high_quality_sources:
        objects.append("High_Quality_Evidence")
        for source in high_quality_sources:
            edges.append((source, "High_Quality_Evidence", "contribute"))
    
    if medium_quality_sources:
        objects.append("Medium_Quality_Evidence")
        for source in medium_quality_sources:
            edges.append((source, "Medium_Quality_Evidence", "contribute"))
    
    # Final synthesis
    objects.append("Final_Synthesis")
    if "High_Quality_Evidence" in objects:
        edges.append(("High_Quality_Evidence", "Final_Synthesis", "primary"))
    if "Medium_Quality_Evidence" in objects:
        edges.append(("Medium_Quality_Evidence", "Final_Synthesis", "secondary"))
    
    return Diagram.from_edges(objects, edges)


def create_knowledge_source_reliability_diagram() -> Diagram:
    """Create a diagram showing knowledge source reliability relationships."""
    objects = [
        "Research_Query", "Academic_Sources", "Industry_Sources", 
        "Web_Sources", "High_Reliability", "Medium_Reliability", 
        "Low_Reliability", "Evidence_Pool", "Quality_Filter", "Final_Report"
    ]
    
    edges = [
        ("Research_Query", "Academic_Sources", "route"),
        ("Research_Query", "Industry_Sources", "route"),
        ("Research_Query", "Web_Sources", "route"),
        ("Academic_Sources", "High_Reliability", "classify"),
        ("Industry_Sources", "Medium_Reliability", "classify"),
        ("Web_Sources", "Low_Reliability", "classify"),
        ("High_Reliability", "Evidence_Pool", "priority_1"),
        ("Medium_Reliability", "Evidence_Pool", "priority_2"),
        ("Low_Reliability", "Evidence_Pool", "priority_3"),
        ("Evidence_Pool", "Quality_Filter", "validate"),
        ("Quality_Filter", "Final_Report", "synthesize")
    ]
    
    return Diagram.from_edges(objects, edges)


def create_research_pipeline_diagram(plan_type: str = "parallel") -> Diagram:
    """Create a diagram showing different research pipeline architectures."""
    if plan_type == "sequential":
        objects = ["Input", "Parse", "Extract", "Search", "Synthesize", "Output"]
        edges = [
            ("Input", "Parse", "step1"),
            ("Parse", "Extract", "step2"),
            ("Extract", "Search", "step3"),
            ("Search", "Synthesize", "step4"),
            ("Synthesize", "Output", "step5")
        ]
    elif plan_type == "parallel":
        objects = [
            "Input", "Parse", "Extract", "Search_A", "Search_B", 
            "Search_C", "Search_D", "Combine", "Synthesize", "Output"
        ]
        edges = [
            ("Input", "Parse", "step1"),
            ("Parse", "Extract", "step2"),
            ("Extract", "Search_A", "parallel"),
            ("Extract", "Search_B", "parallel"),
            ("Extract", "Search_C", "parallel"),
            ("Extract", "Search_D", "parallel"),
            ("Search_A", "Combine", "merge"),
            ("Search_B", "Combine", "merge"),
            ("Search_C", "Combine", "merge"),
            ("Search_D", "Combine", "merge"),
            ("Combine", "Synthesize", "process"),
            ("Synthesize", "Output", "generate")
        ]
    else:  # adaptive
        objects = [
            "Input", "Parse", "Extract", "Multi_Search", "Quality_Check",
            "Strategy_A", "Strategy_B", "Strategy_C", "Best_Strategy", "Output"
        ]
        edges = [
            ("Input", "Parse", "step1"),
            ("Parse", "Extract", "step2"),
            ("Extract", "Multi_Search", "search_all"),
            ("Multi_Search", "Quality_Check", "validate"),
            ("Quality_Check", "Strategy_A", "conservative"),
            ("Quality_Check", "Strategy_B", "comprehensive"),
            ("Quality_Check", "Strategy_C", "exploratory"),
            ("Strategy_A", "Best_Strategy", "select"),
            ("Strategy_B", "Best_Strategy", "select"),
            ("Strategy_C", "Best_Strategy", "select"),
            ("Best_Strategy", "Output", "generate")
        ]
    
    return Diagram.from_edges(objects, edges)


# ===============================
# Research Actions (Pure Functions)
# ===============================

def parse_research_query(query_text: str, ctx: Any = None) -> ResearchQuery:
    """Parse natural language into structured research query."""
    # Simulate NLP parsing
    domain = "general"
    if any(term in query_text.lower() for term in ["AI", "machine learning", "neural"]):
        domain = "artificial_intelligence"
    elif any(term in query_text.lower() for term in ["quantum", "physics", "particle"]):
        domain = "physics"
    elif any(term in query_text.lower() for term in ["climate", "environment", "carbon"]):
        domain = "environmental_science"
    
    depth = "moderate"
    if "comprehensive" in query_text.lower() or "detailed" in query_text.lower():
        depth = "comprehensive"
    elif "deep" in query_text.lower() or "thorough" in query_text.lower():
        depth = "deep"
    
    return ResearchQuery(
        question=query_text.strip(),
        domain=domain,
        depth=depth,
        sources={"academic", "web", "expert_network"}
    )


def extract_key_concepts(query: ResearchQuery, ctx: Any = None) -> Set[str]:
    """Extract key concepts from research query for targeted search."""
    # Simulate concept extraction using simple keyword analysis
    stop_words = {"the", "a", "an", "is", "are", "what", "how", "why", "when", "where"}
    words = re.findall(r'\b\w{3,}\b', query.question.lower())
    concepts = {word for word in words if word not in stop_words}
    
    # Add domain-specific concepts
    domain_concepts = {
        "artificial_intelligence": {"algorithm", "neural_network", "deep_learning", "AI"},
        "physics": {"quantum", "particle", "energy", "matter"},
        "environmental_science": {"climate", "ecosystem", "sustainability", "carbon"}
    }
    
    if query.domain in domain_concepts:
        concepts.update(domain_concepts[query.domain])
    
    return concepts


def search_knowledge_source(source_name: str, concepts: Set[str], ctx: Any = None) -> List[ResearchEvidence]:
    """Search a specific knowledge source for relevant information."""
    source = KNOWLEDGE_SOURCES.get(source_name)
    if not source:
        return []
    
    # Simulate search with realistic delays and results
    time.sleep(min(source.latency * 0.1, 0.5))  # Reduced for demo
    
    evidence = []
    for i, concept in enumerate(list(concepts)[:5]):  # Limit for demo
        # Simulate finding evidence with varying quality
        confidence = min(source.reliability + (hash(concept) % 20) / 100, 1.0)
        relevance = max(0.3, (hash(f"{source_name}{concept}") % 100) / 100)
        
        content = f"Research finding from {source.name}: Analysis of '{concept}' shows significant implications for the field. " \
                 f"Key insights include methodological approaches and empirical evidence supporting current theories."
        
        evidence.append(ResearchEvidence(
            content=content,
            source=source.name,
            confidence=confidence,
            relevance_score=relevance,
            timestamp=time.time(),
            metadata={"concept": concept, "source_type": source_name}
        ))
    
    return evidence


def validate_evidence_consistency(evidence_list: List[ResearchEvidence], ctx: Any = None) -> float:
    """Validate consistency across multiple pieces of evidence."""
    if len(evidence_list) < 2:
        return 1.0
    
    # Simulate consistency checking by comparing source reliability and content overlap
    reliability_scores = [e.confidence for e in evidence_list]
    avg_reliability = sum(reliability_scores) / len(reliability_scores)
    
    # Check for contradictions (simplified)
    high_confidence_sources = [e for e in evidence_list if e.confidence > 0.8]
    consistency_score = min(1.0, len(high_confidence_sources) / max(1, len(evidence_list)))
    
    return (avg_reliability + consistency_score) / 2


def synthesize_findings(evidence_list: List[ResearchEvidence], strategy: str = "comprehensive", ctx: Any = None) -> Dict[str, Any]:
    """Synthesize research findings using specified strategy."""
    if not evidence_list:
        return {"summary": "No evidence found", "confidence": 0.0, "key_points": []}
    
    # Sort evidence by quality
    sorted_evidence = sorted(evidence_list, key=lambda e: e.quality_score(), reverse=True)
    
    # Different synthesis strategies
    if strategy == "conservative":
        # Only use high-confidence evidence
        reliable_evidence = [e for e in sorted_evidence if e.confidence > 0.8]
        evidence_to_use = reliable_evidence[:5]
    elif strategy == "comprehensive":
        # Use all reasonable evidence
        evidence_to_use = [e for e in sorted_evidence if e.quality_score() > 0.5][:10]
    else:  # exploratory
        # Include lower-confidence evidence for broader perspective
        evidence_to_use = sorted_evidence[:15]
    
    # Generate synthesis
    key_points = []
    sources = set()
    total_confidence = 0.0
    
    for evidence in evidence_to_use:
        # Extract key insight (simplified)
        concept = evidence.metadata.get("concept", "unknown")
        key_points.append(f"Evidence from {evidence.source} supports understanding of {concept}")
        sources.add(evidence.source)
        total_confidence += evidence.quality_score()
    
    avg_confidence = total_confidence / len(evidence_to_use) if evidence_to_use else 0.0
    
    summary = f"Analysis of {len(evidence_to_use)} pieces of evidence from {len(sources)} sources " \
              f"reveals consistent patterns in the research domain. Key findings support current " \
              f"theoretical frameworks while highlighting areas for further investigation."
    
    return {
        "summary": summary,
        "key_points": key_points,
        "confidence": avg_confidence,
        "sources_used": list(sources),
        "evidence_count": len(evidence_to_use)
    }


def generate_research_report(synthesis: Dict[str, Any], original_query: ResearchQuery, ctx: Any = None) -> ResearchReport:
    """Generate final structured research report."""
    
    # Determine confidence level
    confidence_score = synthesis.get("confidence", 0.0)
    if confidence_score > 0.8:
        confidence_level = "High"
    elif confidence_score > 0.6:
        confidence_level = "Medium"
    else:
        confidence_level = "Low"
    
    # Generate recommendations based on findings
    recommendations = []
    if confidence_score > 0.7:
        recommendations.append("Findings are sufficiently robust for decision-making")
        recommendations.append("Consider implementing insights in practical applications")
    else:
        recommendations.append("Additional research recommended to strengthen evidence base")
        recommendations.append("Focus on higher-reliability sources for critical decisions")
    
    if len(synthesis.get("sources_used", [])) < 3:
        recommendations.append("Expand research to include more diverse source types")
    
    return ResearchReport(
        query=original_query,
        executive_summary=synthesis.get("summary", ""),
        key_findings=synthesis.get("key_points", []),
        evidence_quality=confidence_score,
        confidence_level=confidence_level,
        recommendations=recommendations,
        sources_consulted=synthesis.get("sources_used", []),
        research_metadata={
            "evidence_count": synthesis.get("evidence_count", 0),
            "research_depth": original_query.depth,
            "domain": original_query.domain
        }
    )


# ===============================
# Monadic Research Pipeline
# ===============================

class ResearchLog(Monoid[str]):
    """Monoid for accumulating research logs."""
    
    def empty(self) -> str:
        return ""
    
    def combine(self, a: str, b: str) -> str:
        if not a:
            return b
        if not b:
            return a
        return f"{a}\n{b}"


def create_research_kleisli() -> Dict[str, Kleisli]:
    """Create Kleisli arrows for research pipeline with Result monad."""
    
    def safe_parse_query(text: str) -> Result[ResearchQuery, str]:
        try:
            if not text.strip():
                return Result.err("Empty query provided")
            query = parse_research_query(text)
            return Result.ok(query)
        except Exception as e:
            return Result.err(f"Failed to parse query: {e}")
    
    def safe_extract_concepts(query: ResearchQuery) -> Result[Set[str], str]:
        try:
            concepts = extract_key_concepts(query)
            if not concepts:
                return Result.err("No meaningful concepts extracted from query")
            return Result.ok(concepts)
        except Exception as e:
            return Result.err(f"Concept extraction failed: {e}")
    
    def safe_search_all_sources(concepts: Set[str]) -> Result[List[ResearchEvidence], str]:
        try:
            all_evidence = []
            for source_name in KNOWLEDGE_SOURCES.keys():
                evidence = search_knowledge_source(source_name, concepts)
                all_evidence.extend(evidence)
            
            if not all_evidence:
                return Result.err("No evidence found from any source")
            return Result.ok(all_evidence)
        except Exception as e:
            return Result.err(f"Search failed: {e}")
    
    return {
        "parse": Kleisli(safe_parse_query),
        "extract": Kleisli(safe_extract_concepts), 
        "search": Kleisli(safe_search_all_sources)
    }


# ===============================
# Agent Action Registry
# ===============================

def create_research_actions() -> Dict[str, Any]:
    """Create the complete action registry for research agent."""
    
    return {
        # Core research actions
        "parse_query": lambda text, ctx=None: parse_research_query(text, ctx),
        "extract_concepts": lambda query, ctx=None: extract_key_concepts(query, ctx),
        "search_academic": lambda concepts, ctx=None: search_knowledge_source("academic_db", concepts, ctx),
        "search_expert": lambda concepts, ctx=None: search_knowledge_source("expert_network", concepts, ctx),
        "search_web": lambda concepts, ctx=None: search_knowledge_source("web_crawler", concepts, ctx),
        "search_patents": lambda concepts, ctx=None: search_knowledge_source("patent_db", concepts, ctx),
        "search_papers": lambda concepts, ctx=None: search_knowledge_source("research_papers", concepts, ctx),
        
        # Validation and synthesis
        "validate_consistency": lambda evidence, ctx=None: validate_evidence_consistency(evidence, ctx),
        "synthesize_conservative": lambda evidence, ctx=None: synthesize_findings(evidence, "conservative", ctx),
        "synthesize_comprehensive": lambda evidence, ctx=None: synthesize_findings(evidence, "comprehensive", ctx),
        "synthesize_exploratory": lambda evidence, ctx=None: synthesize_findings(evidence, "exploratory", ctx),
        
        # Report generation
        "generate_report": lambda synthesis_and_query, ctx=None: generate_research_report(
            synthesis_and_query[0], synthesis_and_query[1], ctx
        ),
        
        # Utility actions
        "combine_evidence": lambda evidence_lists, ctx=None: [
            item for sublist in evidence_lists 
            for item in (sublist if isinstance(sublist, list) else [sublist])
        ],
        "filter_high_quality": lambda evidence, ctx=None: [e for e in evidence if e.quality_score() > 0.7],
        "select_best_synthesis": lambda syntheses, ctx=None: max(syntheses, key=lambda s: s.get("confidence", 0)),
    }


# ===============================
# Research Agent Plans
# ===============================

def create_basic_research_plan():
    """Create a basic sequential research plan."""
    return sequence(
        Task("parse_query"),
        Task("extract_concepts"),
        Task("search_academic"),
        Task("synthesize_comprehensive"),
    )


def create_parallel_research_plan():
    """Create a parallel research plan for faster execution."""
    return sequence(
        Task("parse_query"),
        Task("extract_concepts"),
        parallel(
            Task("search_academic"),
            Task("search_expert"), 
            Task("search_web"),
            Task("search_papers")
        ),
        Task("combine_evidence"),
        Task("synthesize_comprehensive")
    )


def create_adaptive_research_plan():
    """Create an adaptive plan that chooses synthesis strategy based on evidence quality."""
    return sequence(
        Task("parse_query"),
        Task("extract_concepts"),
        parallel(
            Task("search_academic"),
            Task("search_expert"),
            Task("search_web"),
            Task("search_papers"),
            Task("search_patents")
        ),
        Task("combine_evidence"),
        Task("filter_high_quality"),
        parallel(
            Task("synthesize_conservative"),
            Task("synthesize_comprehensive"),
            Task("synthesize_exploratory")
        ),
        Task("select_best_synthesis")
    )


# ===============================
# Demo Functions
# ===============================

def demo_basic_research():
    """Demonstrate basic research functionality."""
    print("🔬 DEMO 1: Basic Research Agent")
    print("=" * 50)
    
    query = "What are the latest developments in quantum computing for cryptography?"
    
    actions = create_research_actions()
    plan = create_basic_research_plan()
    
    # Compile and execute
    executable = compile_plan(actions, plan)
    result = executable(query)
    
    print(f"Query: {query}")
    print(f"Result type: {type(result)}")
    print(f"Synthesis summary: {result.get('summary', 'No summary')[:200]}...")
    print(f"Confidence: {result.get('confidence', 0):.2f}")
    print()


def demo_parallel_research():
    """Demonstrate parallel research with multiple sources."""
    print("🚀 DEMO 2: Parallel Multi-Source Research")
    print("=" * 50)
    
    query = "How is artificial intelligence being applied in climate change research?"
    
    actions = create_research_actions()
    plan = create_parallel_research_plan()
    
    def aggregate_evidence_lists(evidence_lists):
        """Aggregate parallel evidence search results."""
        all_evidence = []
        for evidence_list in evidence_lists:
            if isinstance(evidence_list, list):
                all_evidence.extend(evidence_list)
        return all_evidence
    
    start_time = time.time()
    executable = compile_plan(actions, plan, aggregate_fn=aggregate_evidence_lists)
    result = executable(query)
    end_time = time.time()
    
    print(f"Query: {query}")
    print(f"Execution time: {end_time - start_time:.2f} seconds")
    print(f"Evidence sources: {result.get('sources_used', [])}")
    print(f"Evidence count: {result.get('evidence_count', 0)}")
    print(f"Overall confidence: {result.get('confidence', 0):.2f}")
    print()


def demo_kleisli_research():
    """Demonstrate monadic research pipeline with error handling."""
    print("⚡ DEMO 3: Monadic Research Pipeline (Kleisli)")
    print("=" * 50)
    
    kleisli_actions = create_research_kleisli()
    
    # Compose the pipeline
    research_pipeline = (
        kleisli_actions["search"]
        .compose(kleisli_actions["extract"])
        .compose(kleisli_actions["parse"])
    )
    
    # Test with valid query
    print("Testing with valid query:")
    valid_query = "What are the environmental impacts of renewable energy adoption?"
    result1 = research_pipeline(valid_query)
    
    if result1.is_ok():
        evidence = result1.get_or_else([])
        print(f"✅ Success: Found {len(evidence)} pieces of evidence")
        print(f"Top evidence quality: {max((e.quality_score() for e in evidence), default=0):.2f}")
    else:
        print(f"❌ Error: {result1}")
    
    # Test with invalid query
    print("\nTesting with invalid query:")
    invalid_query = ""
    result2 = research_pipeline(invalid_query)
    
    if result2.is_err():
        print(f"❌ Expected error: {result2}")
    else:
        print(f"✅ Unexpected success: {result2}")
    
    print()


def demo_full_research_report():
    """Demonstrate complete research report generation."""
    print("📊 DEMO 4: Complete Research Report Generation")
    print("=" * 50)
    
    query = "What are the potential risks and benefits of large language models in education?"
    
    # Simplified approach: run parallel search and generate report
    actions = create_research_actions()
    
    # Get the components step by step
    parsed_query = actions["parse_query"](query)
    concepts = actions["extract_concepts"](parsed_query)
    
    # Search all sources
    evidence_academic = actions["search_academic"](concepts)
    evidence_expert = actions["search_expert"](concepts)
    evidence_web = actions["search_web"](concepts)
    evidence_papers = actions["search_papers"](concepts)
    
    # Combine all evidence
    all_evidence = evidence_academic + evidence_expert + evidence_web + evidence_papers
    
    # Synthesize findings
    synthesis_result = actions["synthesize_comprehensive"](all_evidence)
    
    # Generate final report
    report = generate_research_report(synthesis_result, parsed_query)
    
    print(f"🎯 Research Query: {report.query.question}")
    print(f"📈 Evidence Quality: {report.evidence_quality:.2f}")
    print(f"🎖️  Confidence Level: {report.confidence_level}")
    print(f"📚 Sources Consulted: {', '.join(report.sources_consulted)}")
    print(f"\n📋 Executive Summary:")
    print(f"   {report.executive_summary}")
    print(f"\n🔑 Key Findings:")
    for i, finding in enumerate(report.key_findings[:3], 1):
        print(f"   {i}. {finding}")
    print(f"\n💡 Recommendations:")
    for i, rec in enumerate(report.recommendations[:2], 1):
        print(f"   {i}. {rec}")
    print()


def demo_research_diagrams():
    """Demonstrate diagram visualization of research workflows."""
    print("📊 DEMO 5: Research Workflow Visualization")
    print("=" * 50)
    
    # 1. Show overall research workflow
    print("🔄 Overall Research Workflow:")
    workflow_diagram = create_research_workflow_diagram()
    print("Mermaid diagram:")
    print(workflow_diagram.to_mermaid())
    print()
    
    # 2. Show different pipeline architectures
    print("🏗️ Pipeline Architecture Comparison:")
    
    print("Sequential Pipeline:")
    seq_diagram = create_research_pipeline_diagram("sequential")
    print(seq_diagram.to_mermaid())
    print()
    
    print("Parallel Pipeline:")
    par_diagram = create_research_pipeline_diagram("parallel")
    print(par_diagram.to_mermaid())
    print()
    
    # 3. Show knowledge source reliability structure
    print("🎯 Knowledge Source Reliability Structure:")
    reliability_diagram = create_knowledge_source_reliability_diagram()
    print("DOT diagram:")
    print(reliability_diagram.to_dot())
    print()
    
    # 4. Show evidence synthesis for a real query
    print("🔬 Evidence Synthesis Visualization:")
    query = "What are the implications of quantum computing for cybersecurity?"
    
    # Generate some evidence for visualization
    actions = create_research_actions()
    parsed_query = actions["parse_query"](query)
    concepts = actions["extract_concepts"](parsed_query)
    
    # Get evidence from multiple sources
    evidence_academic = actions["search_academic"](concepts)
    evidence_expert = actions["search_expert"](concepts)
    evidence_web = actions["search_web"](concepts)
    
    all_evidence = evidence_academic + evidence_expert + evidence_web
    
    # Create synthesis diagram
    synthesis_diagram = create_evidence_synthesis_diagram(all_evidence)
    print(f"Query: {query}")
    print("Evidence synthesis flow:")
    print(synthesis_diagram.to_mermaid())
    print()
    
    print("📈 Diagram Summary:")
    print("✅ Workflow diagrams show research process structure")
    print("✅ Pipeline diagrams compare execution strategies")  
    print("✅ Reliability diagrams illustrate quality prioritization")
    print("✅ Synthesis diagrams track evidence combination")
    print("✅ Both Mermaid and DOT formats supported for different tools")
    print()


def main():
    """Run all research agent demonstrations."""
    print("🧠 LambdaCat Deep Research Agent - Advanced Example")
    print("=" * 60)
    print("Demonstrating sophisticated agent composition using category theory")
    print("for building reliable, composable AI research systems.\n")
    
    # Run demonstrations
    demo_basic_research()
    demo_parallel_research()
    demo_kleisli_research()
    demo_full_research_report()
    demo_research_diagrams()
    
    print("🎉 Deep Research Agent Demonstration Complete!")
    print("=" * 60)
    print("\nKey LambdaCat Features Demonstrated:")
    print("✅ Complex agent plans with parallel execution")
    print("✅ Monadic error handling with Result types")
    print("✅ Kleisli composition for effectful computations")
    print("✅ Type-safe, composable research pipelines")
    print("✅ Functional approach to complex AI workflows")
    print("✅ Diagram visualization of workflows and evidence synthesis")
    print("✅ Multiple output formats (Mermaid, DOT) for different tools")
    print("\nThis research agent showcases how category theory principles")
    print("enable building sophisticated, reliable AI systems with strong")
    print("mathematical foundations and compositional design.")
    print("\nDiagram visualization provides:")
    print("• Clear understanding of research workflow structure")
    print("• Visual comparison of different execution strategies")
    print("• Evidence quality and source reliability tracking")
    print("• Documentation-ready diagrams for system design")


if __name__ == "__main__":
    main()