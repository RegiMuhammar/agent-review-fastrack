"""
test_graph.py — Unit Tests untuk Graph Structure & Routing (Fase 10)
=====================================================================
Memastikan routing, graph structure, dan node registration benar
setelah refactor Fase 0-9.
"""

import pytest
from app.graph.state import ReviewEngineState
from app.graph.builder import (
    route_after_extract,
    route_by_doc_type,
    review_pipeline,
)


# ── ROUTING TESTS ────────────────────────────────────────────────────────────

class TestRouteAfterExtract:
    """Test routing setelah extract node."""

    def test_invalid_goes_to_end(self):
        """Jika is_valid=False → end_with_error."""
        state: ReviewEngineState = {"is_valid": False, "doc_type": "essay"}  # type: ignore
        assert route_after_extract(state) == "end_with_error"

    def test_valid_goes_to_metadata(self):
        """Jika is_valid=True → metadata_extract."""
        state: ReviewEngineState = {"is_valid": True, "doc_type": "essay"}  # type: ignore
        assert route_after_extract(state) == "metadata_extract"


class TestRouteByDocType:
    """Test routing berdasarkan doc_type setelah metadata_extract."""

    def test_essay_goes_to_essay_agent(self):
        state: ReviewEngineState = {"doc_type": "essay"}  # type: ignore
        assert route_by_doc_type(state) == "essay_agent"

    def test_research_goes_to_document_profile(self):
        """Research → document_profile (bukan essay_agent setelah Fase 3)."""
        state: ReviewEngineState = {"doc_type": "research"}  # type: ignore
        assert route_by_doc_type(state) == "document_profile"

    def test_bizplan_goes_to_essay_agent(self):
        """Bizplan fallback ke essay_agent (belum ada bizplan_agent)."""
        state: ReviewEngineState = {"doc_type": "bizplan"}  # type: ignore
        assert route_by_doc_type(state) == "essay_agent"

    def test_unknown_goes_to_essay_agent(self):
        """Doc type tidak dikenal → fallback ke essay_agent."""
        state: ReviewEngineState = {"doc_type": "unknown"}  # type: ignore
        assert route_by_doc_type(state) == "essay_agent"


# ── GRAPH STRUCTURE TESTS ────────────────────────────────────────────────────

class TestGraphStructure:
    """Test graph compiled dengan benar setelah Fase 0-9."""

    def test_graph_compiles(self):
        """Graph harus compile tanpa error."""
        assert review_pipeline is not None

    def test_node_count(self):
        """Harus ada 12 nodes (+ __start__ dan __end__)."""
        nodes = list(review_pipeline.get_graph().nodes.keys())
        # __start__, extract, metadata_extract, essay_agent,
        # document_profile, retrieval_prep, search_execute,
        # search_rank, evidence_select, research_agent,
        # score, generate, __end__
        assert len(nodes) == 13

    def test_expected_nodes_present(self):
        """Semua node yang diharapkan harus terdaftar."""
        nodes = set(review_pipeline.get_graph().nodes.keys())
        expected = {
            "__start__", "__end__",
            "extract", "metadata_extract",
            "essay_agent", "document_profile",
            "retrieval_prep", "search_execute",
            "search_rank", "evidence_select",
            "research_agent", "score", "generate",
        }
        assert expected.issubset(nodes), f"Missing nodes: {expected - nodes}"

    def test_essay_path_edges(self):
        """Essay path: extract → metadata_extract → essay_agent → score → generate."""
        edges = review_pipeline.get_graph().edges
        edge_pairs = {(e.source, e.target) for e in edges}

        assert ("essay_agent", "score") in edge_pairs
        assert ("score", "generate") in edge_pairs

    def test_research_path_edges(self):
        """Research path: profile → prep → search → rank → evidence → agent → score."""
        edges = review_pipeline.get_graph().edges
        edge_pairs = {(e.source, e.target) for e in edges}

        assert ("document_profile", "retrieval_prep") in edge_pairs
        assert ("retrieval_prep", "search_execute") in edge_pairs
        assert ("search_execute", "search_rank") in edge_pairs
        assert ("search_rank", "evidence_select") in edge_pairs
        assert ("evidence_select", "research_agent") in edge_pairs
        assert ("research_agent", "score") in edge_pairs


# ── NODE FALLBACK TESTS ──────────────────────────────────────────────────────

class TestNodeFallbacks:
    """Test bahwa node-node baru bisa handle input kosong/minimal."""

    def test_evidence_select_empty_markdown(self):
        """evidence_select harus survive dengan raw_markdown kosong."""
        from app.graph.nodes.evidence_select import evidence_select_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "test",
            "raw_markdown": "",
            "title": "Test Paper",
            "abstract": "",
            "authors": [],
            "keywords": [],
            "domain": None,
            "sub_domain": None,
            "paper_type": None,
            "retrieval_focus": [],
            "top_references": [],
            "document_head": "",
            "document_tail": "",
        }  # type: ignore

        result = asyncio.run(evidence_select_node(state))
        assert "evidence_chunks" in result
        assert "review_context" in result
        assert isinstance(result["evidence_chunks"], list)
        assert isinstance(result["review_context"], str)

    def test_search_rank_empty_results(self):
        """search_rank harus survive dengan search_results kosong."""
        from app.graph.nodes.search_rank import search_rank_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "test",
            "search_results": [],
            "title": "Test",
            "abstract": "",
            "keywords": [],
            "domain": None,
        }  # type: ignore

        result = asyncio.run(search_rank_node(state))
        assert result["ranked_results"] == []
        assert result["top_references"] == []

    def test_generate_node_essay(self):
        """generate_node harus bekerja untuk essay (backward compat)."""
        from app.graph.nodes.generate import generate_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "test-essay",
            "doc_type": "essay",
            "title": "Test Essay",
            "page_count": 5,
            "score_overall": 7.5,
            "summary": "Good essay",
            "dimensions_feedback": [
                {"key": "thesis_clarity", "label": "Tesis", "score": 8.0, "feedback": "Bagus"},
                {"key": "writing_style_clarity", "label": "Gaya", "score": 5.0, "feedback": "Perlu perbaikan"},
            ],
            "overall_feedback": "Overall OK",
        }  # type: ignore

        result = asyncio.run(generate_node(state))
        fr = result["final_result"]
        assert fr["doc_type"] == "essay"
        assert fr["score_overall"] == 7.5
        assert len(fr["strengths"]) >= 1  # score 8.0 → strength
        assert len(fr["improvements"]) >= 1  # score 5.0 → improvement
        assert fr["references"] == []  # essay = no references

    def test_generate_node_research(self):
        """generate_node harus include metadata, profile, references untuk research."""
        from app.graph.nodes.generate import generate_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "test-research",
            "doc_type": "research",
            "title": "Deep Learning Paper",
            "page_count": 12,
            "score_overall": 7.8,
            "summary": "Solid research",
            "dimensions_feedback": [],
            "overall_feedback": "Good paper",
            "authors": ["John Doe"],
            "keywords": ["NLP", "BERT"],
            "abstract": "This paper presents...",
            "domain": "computer_science",
            "sub_domain": "nlp",
            "paper_type": "empirical",
            "retrieval_focus": ["prior_work"],
            "top_references": [
                {"title": "BERT", "authors": ["Devlin"], "year": 2019, "url": "http://x", "source": "arxiv", "snippet": "A model"}
            ],
            "search_results": [{"title": "a"}, {"title": "b"}],
            "evidence_chunks": [{"section": "intro"}, {"section": "method"}],
        }  # type: ignore

        result = asyncio.run(generate_node(state))
        fr = result["final_result"]
        assert fr["doc_type"] == "research"
        assert "metadata" in fr
        assert "profile" in fr
        assert len(fr["references"]) == 1
        assert fr["references"][0]["title"] == "BERT"
        assert "pipeline_stats" in fr
        assert fr["pipeline_stats"]["references_selected"] == 1
