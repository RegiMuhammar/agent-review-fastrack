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
    route_after_search_rank,
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
        assert route_by_doc_type(state) == "essay_document_profile"

    def test_research_goes_to_document_profile(self):
        """Research → document_profile (bukan essay_agent setelah Fase 3)."""
        state: ReviewEngineState = {"doc_type": "research"}  # type: ignore
        assert route_by_doc_type(state) == "research_document_profile"

    def test_bizplan_goes_to_essay_agent(self):
        """Bizplan sekarang masuk ke metadata khusus bizplan."""
        state: ReviewEngineState = {"doc_type": "bizplan"}  # type: ignore
        assert route_by_doc_type(state) == "bizplan_metadata_extract"

    def test_unknown_goes_to_essay_agent(self):
        """Doc type tidak dikenal → fallback ke essay_document_profile."""
        state: ReviewEngineState = {"doc_type": "unknown"}  # type: ignore
        assert route_by_doc_type(state) == "essay_document_profile"


# ── GRAPH STRUCTURE TESTS ────────────────────────────────────────────────────

class TestRouteAfterSearchRank:
    """Test routing setelah ranking retrieval."""

    def test_essay_skips_evidence_select(self):
        state: ReviewEngineState = {"doc_type": "essay"}  # type: ignore
        assert route_after_search_rank(state) == "essay_agent"

    def test_research_continues_to_evidence_select(self):
        state: ReviewEngineState = {"doc_type": "research"}  # type: ignore
        assert route_after_search_rank(state) == "evidence_select"

    def test_bizplan_continues_to_market_synthesis(self):
        state: ReviewEngineState = {"doc_type": "bizplan"}  # type: ignore
        assert route_after_search_rank(state) == "bizplan_market_synthesis"


class TestGraphStructure:
    """Test graph compiled dengan benar setelah Fase 0-9."""

    def test_graph_compiles(self):
        """Graph harus compile tanpa error."""
        assert review_pipeline is not None

    def test_node_count(self):
        """Harus ada 15 nodes termasuk start dan end."""
        nodes = list(review_pipeline.get_graph().nodes.keys())
        assert len(nodes) == 20

    def test_expected_nodes_present(self):
        """Semua node yang diharapkan harus terdaftar."""
        nodes = set(review_pipeline.get_graph().nodes.keys())
        expected = {
            "__start__", "__end__",
            "extract", "metadata_extract", "bizplan_metadata_extract", "bizplan_financials",
            "bizplan_search_prep", "bizplan_market_synthesis",
            "essay_document_profile", "research_document_profile", "bizplan_document_profile",
            "retrieval_prep", "search_execute",
            "search_rank", "evidence_select", "bizplan_agent",
            "research_agent", "essay_agent", "score", "generate",
        }
        assert expected.issubset(nodes), f"Missing nodes: {expected - nodes}"

    def test_essay_path_edges(self):
        """Essay path: extract → metadata_extract → essay_agent → score → generate."""
        edges = review_pipeline.get_graph().edges
        edge_pairs = {(e.source, e.target) for e in edges}

        assert ("search_rank", "essay_agent") in edge_pairs
        assert ("essay_agent", "score") in edge_pairs
        assert ("score", "generate") in edge_pairs

    def test_research_path_edges(self):
        """Research path: profile → prep → search → rank → evidence → conditional → research_agent → score."""
        edges = review_pipeline.get_graph().edges
        edge_pairs = {(e.source, e.target) for e in edges}

        assert ("research_document_profile", "retrieval_prep") in edge_pairs
        assert ("retrieval_prep", "search_execute") in edge_pairs
        assert ("search_execute", "search_rank") in edge_pairs
        assert ("search_rank", "evidence_select") in edge_pairs
        assert ("research_agent", "score") in edge_pairs

    def test_bizplan_path_edges(self):
        """Bizplan path: profile â†’ bizplan_agent â†’ score."""
        edges = review_pipeline.get_graph().edges
        edge_pairs = {(e.source, e.target) for e in edges}

        assert ("bizplan_metadata_extract", "bizplan_financials") in edge_pairs
        assert ("bizplan_financials", "bizplan_document_profile") in edge_pairs
        assert ("bizplan_document_profile", "bizplan_search_prep") in edge_pairs
        assert ("bizplan_search_prep", "search_execute") in edge_pairs
        assert ("search_rank", "bizplan_market_synthesis") in edge_pairs
        assert ("bizplan_market_synthesis", "bizplan_agent") in edge_pairs
        assert ("bizplan_agent", "score") in edge_pairs


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

    def test_temporal_alignment_prefers_contemporary_references(self):
        """Ranking temporal harus lebih menyukai referensi yang dekat dengan tahun paper target."""
        from app.graph.nodes.search_rank import _temporal_alignment_score

        older_but_contemporary = _temporal_alignment_score(2016, 2017)
        much_newer = _temporal_alignment_score(2024, 2017)
        assert older_but_contemporary > much_newer

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
                {"key": "thesis_clarity", "label": "Tesis", "score": 9.2, "feedback": "Bagus"},
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

    def test_essay_agent_uses_external_references_not_internal_chunks(self):
        """Essay agent tidak boleh salah menyebut evidence_chunks internal sebagai bukti web."""
        from app.graph.nodes.essay_agent import essay_agent_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "essay-search",
            "agent_context": "Esai membahas dampak AI pada pendidikan.",
            "run_essay_web_search": True,
            "evidence_chunks": [
                {"section": "head", "content": "Ini potongan internal dokumen."}
            ],
            "top_references": [
                {
                    "title": "AI in Education Review",
                    "source": "tavily",
                    "year": 2024,
                    "snippet": "Recent review of AI adoption in classrooms.",
                }
            ],
        }  # type: ignore

        result = asyncio.run(essay_agent_node(state))
        review_context = result["review_context"]
        assert "AI in Education Review" in review_context
        assert "Ini potongan internal dokumen." not in review_context

    def test_bizplan_agent_fallback_builds_context(self):
        """Bizplan agent harus tetap membangun context meski section tidak terdeteksi."""
        from app.graph.nodes.bizplan_agent import bizplan_agent_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "bizplan-test",
            "title": "Edu SaaS Expansion",
            "raw_markdown": (
                "Kami membangun platform SaaS pendidikan untuk sekolah menengah. "
                "Target pengguna adalah sekolah swasta di kota tier-2. "
                "Pendapatan berasal dari langganan tahunan dan pelatihan implementasi. "
                "Tim terdiri dari founder produk, sales, dan engineer. "
                "Proyeksi pendapatan tumbuh 40 persen per tahun."
            ),
            "keywords": ["education", "saas"],
            "year": 2026,
            "company_name": "Edu SaaS Expansion",
            "industry": "Pendidikan",
            "target_customer": ["Sekolah swasta"],
            "geography": "Indonesia",
            "business_stage": "Seed",
            "funding_ask": "Rp2 miliar",
            "revenue_model": ["Langganan"],
            "pricing": ["Rp499.000 per sekolah per bulan"],
            "runway_months": 8.0,
            "break_even_timeline": "18 bulan",
            "financial_red_flags": ["CAC belum dicantumkan."],
            "document_head": "",
            "document_tail": "",
        }  # type: ignore

        result = asyncio.run(bizplan_agent_node(state))
        assert "agent_context" in result
        assert "RINGKASAN BUSINESS PLAN" in result["agent_context"]
        assert "EVIDENSI BUSINESS PLAN" in result["agent_context"]
        assert isinstance(result["evidence_chunks"], list)
        assert len(result["evidence_chunks"]) >= 1

    def test_bizplan_metadata_extract_parses_business_signals(self):
        """Metadata bizplan harus menangkap identitas bisnis utama."""
        from app.graph.nodes.bizplan_metadata_extract import bizplan_metadata_extract_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "biz-meta",
            "title": "NusaFleet",
            "raw_markdown": (
                "# NusaFleet\n"
                "Nama perusahaan: NusaFleet\n"
                "Kami adalah startup logistik SaaS tahap seed yang berfokus di Indonesia.\n"
                "Target customer: distributor FMCG, UMKM logistik, dan armada kecil.\n"
                "Pendanaan yang dicari: Rp2 miliar.\n"
                "Kami memiliki 12 pelanggan pilot dan pertumbuhan pengguna 18% per bulan.\n"
                "Harga langganan dimulai dari Rp499.000 per armada per bulan.\n"
            ),
            "document_head": "",
            "keywords": ["logistics", "saas"],
        }  # type: ignore

        result = asyncio.run(bizplan_metadata_extract_node(state))
        assert result["company_name"] == "NusaFleet"
        assert result["industry"] in {"Logistik", "SaaS"}
        assert result["business_stage"] == "Seed"
        assert result["funding_ask"] is not None
        assert "Indonesia" in (result["geography"] or "")
        assert len(result["target_customer"]) >= 1

    def test_bizplan_financials_extract_metrics_and_red_flags(self):
        """Node finansial harus mengekstrak metrik dan tetap memberi red flag yang relevan."""
        from app.graph.nodes.bizplan_financials import bizplan_financials_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "biz-fin",
            "raw_markdown": (
                "Model pendapatan kami berbasis subscription dan biaya setup. "
                "Harga paket dimulai dari Rp499.000 per bulan. "
                "CAC: Rp850.000. "
                "LTV: Rp5.100.000. "
                "Gross margin: 68%. "
                "Burn rate: Rp75.000.000 per bulan. "
                "Runway: 8 bulan. "
                "Break-even: 18 bulan."
            ),
            "document_tail": "",
            "pricing_signals": [],
            "funding_ask": "Rp2 miliar",
        }  # type: ignore

        result = asyncio.run(bizplan_financials_node(state))
        assert "Langganan" in result["revenue_model"]
        assert result["burn_rate"] is not None
        assert result["runway_months"] == 8.0
        assert result["break_even_timeline"] is not None
        assert result["unit_economics_signals"]["ltv_cac_ratio"] == 6.0
        assert isinstance(result["financial_red_flags"], list)

    def test_bizplan_search_prep_builds_tavily_queries(self):
        """Search prep bizplan harus hanya menyiapkan query Tavily yang relevan."""
        from app.graph.nodes.bizplan_search_prep import bizplan_search_prep_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "biz-search",
            "title": "NusaFleet",
            "company_name": "NusaFleet",
            "industry": "Logistik",
            "geography": "Indonesia",
            "target_customer": ["Distributor FMCG", "UMKM logistik"],
            "revenue_model": ["Langganan"],
            "pricing_signals": ["Rp499.000 per armada per bulan"],
        }  # type: ignore

        result = asyncio.run(bizplan_search_prep_node(state))
        assert list(result["search_queries"].keys()) == ["tavily"]
        assert len(result["search_queries"]["tavily"]) >= 3
        assert any("Logistik" in query for query in result["search_queries"]["tavily"])

    def test_bizplan_market_synthesis_builds_validation_payload(self):
        """Sintesis pasar bizplan harus mengubah hasil ranking jadi payload yang siap ditampilkan."""
        from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "biz-market",
            "company_name": "NusaFleet",
            "industry": "Logistik",
            "geography": "Indonesia",
            "top_references": [
                {
                    "title": "Indonesia logistics market growth report",
                    "url": "https://example.com/market",
                    "source": "tavily",
                    "snippet": "The logistics market in Indonesia continues to grow with strong SME demand.",
                },
                {
                    "title": "Top logistics software competitors in Indonesia",
                    "url": "https://example.com/competitors",
                    "source": "tavily",
                    "snippet": "Competitors include major route optimization and fleet management platforms.",
                },
                {
                    "title": "SME logistics pricing benchmark Southeast Asia",
                    "url": "https://example.com/pricing",
                    "source": "tavily",
                    "snippet": "Pricing benchmarks show monthly SaaS fees and implementation costs.",
                },
            ],
        }  # type: ignore

        result = asyncio.run(bizplan_market_synthesis_node(state))
        assert result["market_validation_status"] == "validated"
        assert len(result["external_market_evidence"]) >= 1
        assert "market_size_summary" in result["market_validation"]
        assert "direct_competitors" in result["competition_insights"]

    def test_generate_node_bizplan_adds_business_payload(self):
        """Output bizplan harus additive dan aman untuk frontend/backend."""
        from app.graph.nodes.generate import generate_node
        import asyncio

        state: ReviewEngineState = {
            "analysis_id": "biz-generate",
            "doc_type": "bizplan",
            "title": "NusaFleet",
            "page_count": 10,
            "score_overall": 7.9,
            "summary": "Business plan menjanjikan tetapi unit economics belum lengkap.",
            "dimensions_feedback": [
                {"key": "problem_solution", "label": "Masalah-Solusi", "score": 8.2, "feedback": "Masalah yang dibahas nyata."},
                {"key": "financial", "label": "Kesehatan Finansial", "score": 5.9, "feedback": "CAC dan runway perlu dipertajam."},
            ],
            "overall_feedback": "Layak dilanjutkan dengan revisi finansial.",
            "company_name": "NusaFleet",
            "industry": "Logistik",
            "geography": "Indonesia",
            "business_stage": "Seed",
            "target_customer": ["Distributor FMCG"],
            "funding_ask": "Rp2 miliar",
            "traction_signals": ["12 pelanggan pilot"],
            "pricing_signals": ["Rp499.000 per bulan"],
            "revenue_model": ["Langganan"],
            "pricing": ["Rp499.000 per bulan"],
            "burn_rate": "Rp75.000.000 per bulan",
            "runway_months": 8.0,
            "break_even_timeline": "18 bulan",
            "financial_metrics": {
                "pricing": ["Rp499.000 per bulan"],
                "revenue_model": ["Langganan"],
                "cac": None,
                "ltv": None,
                "gross_margin": "68%",
                "burn_rate": "Rp75.000.000 per bulan",
                "runway_months": 8.0,
                "break_even_timeline": "18 bulan",
                "funding_needed": "Rp2 miliar",
            },
            "financial_red_flags": ["CAC belum dicantumkan."],
            "unit_economics_signals": {"cac": None, "ltv": None, "ltv_cac_ratio": None},
            "market_validation": {
                "status": "partial",
                "market_size_summary": "Pasar logistik Indonesia tumbuh dan kompetitif.",
                "evidence": [{"title": "Market report", "url": "https://example.com"}],
            },
            "competition_insights": {
                "direct_competitors": ["Competitor A", "Competitor B"],
                "substitutes": [],
                "key_risk": "Biaya pindah pelanggan rendah.",
            },
            "market_red_flags": ["Kompetitor langsung perlu divalidasi lebih dalam."],
        }  # type: ignore

        result = asyncio.run(generate_node(state))
        fr = result["final_result"]
        assert fr["doc_type"] == "bizplan"
        assert fr["metadata"]["company_name"] == "NusaFleet"
        assert fr["profile"]["funding_ask"] == "Rp2 miliar"
        assert fr["business_snapshot"]["industry"] == "Logistik"
        assert fr["financial_metrics"]["burn_rate"] == "Rp75.000.000 per bulan"
        assert fr["financial_red_flags"] == ["CAC belum dicantumkan."]
        assert fr["market_validation"]["status"] == "partial"
        assert fr["competition_insights"]["direct_competitors"][0] == "Competitor A"
