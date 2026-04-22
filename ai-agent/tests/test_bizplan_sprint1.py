import asyncio


def test_bizplan_metadata_extract_sanitizes_contaminated_title_and_industry():
    from app.graph.nodes.bizplan_metadata_extract import bizplan_metadata_extract_node

    state = {
        "analysis_id": "biz-sprint1-meta",
        "title": "EduCycle Industry: Education technology, circular economy, SaaS Geography: Indonesia",
        "document_head": (
            "EduCycle\n"
            "Company Name: EduCycle\n"
            "Industry: Education technology, circular economy, SaaS\n"
            "Geography: Indonesia\n"
            "Business Stage: Seed\n"
            "Funding Ask: IDR 4.8 miliar untuk 18 bulan runway\n"
        ),
        "raw_markdown": (
            "EduCycle menyediakan smart kiosk dan dashboard SaaS untuk kampus. "
            "Kami bermitra dengan logistics partner untuk pengangkutan material. "
            "Target customer: sustainability office kampus, koperasi kampus, universitas swasta menengah. "
            "Pilot traction: 12 campus pilots dan 18,400 users."
        ),
        "keywords": ["education technology", "saas", "circular economy"],
    }

    result = asyncio.run(bizplan_metadata_extract_node(state))  # type: ignore[arg-type]
    assert result["company_name"] == "EduCycle"
    assert result["industry"] == "Pendidikan"
    assert result["funding_ask"] == "IDR 4.8 miliar untuk 18 bulan runway"


def test_bizplan_metadata_extract_filters_ocr_artifact_from_pricing_signals():
    from app.graph.nodes.bizplan_metadata_extract import bizplan_metadata_extract_node

    state = {
        "analysis_id": "biz-sprint1-pricing-meta",
        "title": "CampusLoop",
        "document_head": "",
        "raw_markdown": (
            "Pricing: Starter Rp 7.5 jt, Growth Rp 18 jt, Enterprise Rp 45 jt per tahun. "
            "Start of picture text pricing benchmark <br> Waste diverted MRR LOI 186 ton Rp 128 jt 27 kampus "
            "End of picture text. "
            "MRR saat ini Rp 128.000.000 dari 9 kampus berbayar."
        ),
        "keywords": ["edtech"],
    }

    result = asyncio.run(bizplan_metadata_extract_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["pricing_signals"])
    assert "Start of picture text" not in joined
    assert "Waste diverted" not in joined
    assert "Starter Rp 7.5 jt" in joined


def test_bizplan_metadata_extract_excludes_tam_and_margin_from_pricing_signals():
    from app.graph.nodes.bizplan_metadata_extract import bizplan_metadata_extract_node

    state = {
        "analysis_id": "biz-sprint1-pricing-meta-specific",
        "title": "EduCycle",
        "document_head": "",
        "raw_markdown": (
            "TAM diperkirakan Rp7.2 triliun per tahun dari institusi pendidikan. "
            "Subscription: paket Starter Rp7.500.000 per tahun dan Growth Rp18.000.000. "
            "Gross Margin: 68% setelah biaya logistics partner."
        ),
        "keywords": ["education technology"],
    }

    result = asyncio.run(bizplan_metadata_extract_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["pricing_signals"])
    assert "Starter Rp7.500.000 per tahun" in joined
    assert "TAM diperkirakan" not in joined
    assert "Gross Margin" not in joined


def test_bizplan_financials_filters_ocr_artifact_from_pricing_signals():
    from app.graph.nodes.bizplan_financials import bizplan_financials_node

    state = {
        "analysis_id": "biz-sprint1-pricing-fin",
        "raw_markdown": (
            "Pricing: Starter Rp 7.5 jt, Growth Rp 18 jt, Enterprise Rp 45 jt per tahun. "
            "Start of picture text pricing benchmark <br> Waste diverted MRR LOI 186 ton Rp 128 jt 27 kampus "
            "End of picture text. "
            "Burn rate: Rp215.000.000 per bulan. Runway: 18 bulan."
        ),
        "document_tail": "",
        "pricing_signals": [],
        "funding_ask": "IDR 4.8 miliar",
    }

    result = asyncio.run(bizplan_financials_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["pricing"])
    assert "Start of picture text" not in joined
    assert "Waste diverted" not in joined
    assert "Starter Rp 7.5 jt" in joined


def test_bizplan_financials_prefers_explicit_price_not_tam_or_mrr():
    from app.graph.nodes.bizplan_financials import bizplan_financials_node

    state = {
        "analysis_id": "biz-sprint1-pricing-specific",
        "raw_markdown": (
            "Harga paket dimulai dari Rp499.000 per sekolah per bulan. "
            "MRR saat ini Rp128.000.000 dari 9 kampus berbayar. "
            "TAM diperkirakan Rp7.2 triliun per tahun. "
            "SAM sebesar Rp2.1 triliun."
        ),
        "document_tail": "",
        "pricing_signals": [],
        "funding_ask": "Rp2 miliar",
    }

    result = asyncio.run(bizplan_financials_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["pricing"])
    assert "Rp499.000 per sekolah per bulan" in joined
    assert "TAM diperkirakan" not in joined
    assert "SAM sebesar" not in joined


def test_bizplan_financials_excludes_burn_rate_from_pricing():
    from app.graph.nodes.bizplan_financials import bizplan_financials_node

    state = {
        "analysis_id": "biz-sprint1-pricing-burn",
        "raw_markdown": (
            "Setup fee: Rp6.000.000 untuk instalasi awal. "
            "License: Rp1.500.000 per bulan untuk dashboard analytics. "
            "Burn Rate: Rp215.000.000 per bulan. "
            "Runway: 18 bulan."
        ),
        "document_tail": "",
        "pricing_signals": [],
        "funding_ask": "Rp2 miliar",
    }

    result = asyncio.run(bizplan_financials_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["pricing"])
    assert "Rp1.500.000 per bulan" in joined
    assert "Burn Rate" not in joined


def test_bizplan_financials_extracts_explicit_risk_sentence():
    from app.graph.nodes.bizplan_financials import bizplan_financials_node

    state = {
        "analysis_id": "biz-sprint1-risk",
        "raw_markdown": (
            "Model pendapatan kami berbasis subscription. "
            "Harga paket dimulai dari Rp499.000 per bulan. "
            "Burn rate: Rp75.000.000 per bulan. "
            "Runway: 8 bulan. "
            "Risiko utama adalah kebutuhan modal kerja dapat naik jika sponsor reimbursement melambat lebih dari 45 hari."
        ),
        "document_tail": "",
        "pricing_signals": [],
        "funding_ask": "Rp2 miliar",
    }

    result = asyncio.run(bizplan_financials_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["financial_red_flags"])
    assert "reimbursement" in joined.lower()
    assert "modal kerja" in joined.lower()


def test_bizplan_financials_ignores_kpi_and_budget_lines_in_risk_flags():
    from app.graph.nodes.bizplan_financials import bizplan_financials_node

    state = {
        "analysis_id": "biz-sprint1-risk-noise",
        "raw_markdown": (
            "Financial Red Flag yang masih dipantau: kebutuhan modal kerja bisa naik jika sponsor reimbursement melambat lebih dari 45 hari. "
            "Operational KPI: sponsor reimbursement cycle < 30 hari. "
            "Working capital - 20% dari penggunaan dana."
        ),
        "document_tail": "",
        "pricing_signals": [],
        "funding_ask": "Rp2 miliar",
    }

    result = asyncio.run(bizplan_financials_node(state))  # type: ignore[arg-type]
    joined = " | ".join(result["financial_red_flags"])
    assert "modal kerja bisa naik" in joined.lower()
    assert "operational kpi" not in joined.lower()
    assert "working capital - 20%" not in joined.lower()


def test_generate_node_bizplan_produces_improvements_without_low_threshold_only():
    from app.graph.nodes.generate import generate_node

    state = {
        "analysis_id": "biz-sprint1-generate",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "page_count": 8,
        "score_overall": 8.1,
        "summary": "Rencana bisnis menjanjikan dengan beberapa asumsi yang perlu dipertajam.",
        "dimensions_feedback": [
            {
                "key": "problem_solution",
                "label": "Masalah & Solusi",
                "score": 8.6,
                "feedback": "Masalah yang diangkat nyata dan solusi cukup terukur. Namun, perlu dijelaskan lebih rinci mekanisme implementasi di kampus mitra.",
            },
            {
                "key": "market_size",
                "label": "Ukuran Pasar",
                "score": 7.8,
                "feedback": "Ukuran pasar terlihat menarik. Namun, perlu validasi lebih tajam untuk asumsi konversi dari LOI ke kontrak berbayar.",
            },
            {
                "key": "team",
                "label": "Kesiapan Eksekusi",
                "score": 6.5,
                "feedback": "Tim memiliki pengalaman relevan. Namun, masih perlu diperjelas rencana penambahan kapasitas operasional saat ekspansi lintas kota.",
            },
        ],
        "overall_feedback": "Layak diteruskan dengan penguatan validasi eksekusi.",
    }

    result = asyncio.run(generate_node(state))  # type: ignore[arg-type]
    final_result = result["final_result"]
    assert len(final_result["strengths"]) >= 1
    assert len(final_result["improvements"]) >= 2
    assert any("perlu" in item.lower() or "masih" in item.lower() for item in final_result["improvements"])


def test_bizplan_market_synthesis_marks_partial_when_results_not_relevant():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint1-market",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas swasta"],
        "top_references": [
            {
                "title": "Logistics cost report Southeast Asia",
                "url": "https://example.com/logistics-report",
                "source": "tavily",
                "snippet": "Regional logistics costs remain high for manufacturing and fleet operations.",
            },
            {
                "title": "Warehouse benchmark 2025",
                "url": "https://example.com/warehouse",
                "source": "tavily",
                "snippet": "Pricing benchmark for warehouse operators and freight distribution centers.",
            },
            {
                "title": "Fleet routing study",
                "url": "https://example.com/fleet",
                "source": "tavily",
                "snippet": "Study on route optimization for logistics fleets in industrial zones.",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    assert result["market_validation_status"] == "partial"
    assert any("belum cukup relevan" in item.lower() for item in result["market_red_flags"])


def test_bizplan_search_prep_compacts_pricing_signal_into_general_query():
    from app.graph.nodes.bizplan_search_prep import bizplan_search_prep_node

    state = {
        "analysis_id": "biz-sprint1-search-prep",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas swasta"],
        "revenue_model": ["Langganan", "Komisi"],
        "pricing_signals": [
            "Subscription: paket Starter Rp 7.500.000 per tahun, Growth Rp 18.000.000, Enterprise Rp 45.000.000."
        ],
    }

    result = asyncio.run(bizplan_search_prep_node(state))  # type: ignore[arg-type]
    queries = result["search_queries"]["tavily"]
    assert any("pricing benchmark" in query.lower() for query in queries)
    assert all("rp 7.500.000" not in query.lower() for query in queries)


def test_bizplan_search_prep_uses_topic_keywords_to_avoid_overly_generic_queries():
    from app.graph.nodes.bizplan_search_prep import bizplan_search_prep_node

    state = {
        "analysis_id": "biz-sprint2-search-topic",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas swasta"],
        "revenue_model": ["Langganan", "Komisi"],
        "pricing_signals": ["Subscription: paket Starter Rp 7.500.000 per tahun."],
        "keywords": ["Circular Economy", "Sustainability", "Education Technology", "Indonesia"],
    }

    result = asyncio.run(bizplan_search_prep_node(state))  # type: ignore[arg-type]
    queries = " | ".join(result["search_queries"]["tavily"]).lower()
    assert "circular economy" in queries or "sustainability" in queries or "education technology" in queries
    assert "campus software" in queries


def test_bizplan_search_prep_adds_direct_competitor_discovery_query():
    from app.graph.nodes.bizplan_search_prep import bizplan_search_prep_node

    state = {
        "analysis_id": "biz-sprint4-search-competitor",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["universitas", "kampus negeri"],
        "revenue_model": ["Langganan"],
        "pricing_signals": ["Subscription: mulai dari Rp 12.000.000 per tahun."],
        "keywords": ["Sustainability", "Campus Operations", "Education Technology"],
    }

    result = asyncio.run(bizplan_search_prep_node(state))  # type: ignore[arg-type]
    queries = " | ".join(result["search_queries"]["tavily"]).lower()
    assert "campus sustainability software competitors indonesia" in queries
    assert "best campus sustainability software providers indonesia" in queries
    assert "top higher education software vendors indonesia" in queries


def test_search_rank_bizplan_filters_off_position_results_and_preserves_role_diversity():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint2-rank",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["education technology", "campus sustainability", "saas"],
        "search_results": [
            {
                "title": "Indonesia edtech market growth report",
                "url": "https://example.com/market",
                "source": "tavily",
                "snippet": "Indonesia education technology market keeps growing as universities digitize campus services.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Campus sustainability software competitors in Southeast Asia",
                "url": "https://example.com/competition",
                "source": "tavily",
                "snippet": "Competitors in university sustainability software compete on analytics and implementation.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "University software pricing benchmark Indonesia",
                "url": "https://example.com/pricing",
                "source": "tavily",
                "snippet": "Annual SaaS pricing benchmark for Indonesian universities and campus operations software.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Warehouse logistics cost benchmark Indonesia",
                "url": "https://example.com/logistics",
                "source": "tavily",
                "snippet": "Freight, warehouse, and fleet pricing benchmark for industrial logistics operators.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    top_refs = result["top_references"]
    joined_titles = " | ".join(ref["title"] for ref in top_refs)

    assert "Warehouse logistics cost benchmark" not in joined_titles
    assert any(ref.get("reference_role") == "market" for ref in top_refs)
    assert any(ref.get("reference_role") == "competition" for ref in top_refs)
    assert any(ref.get("reference_role") == "pricing" for ref in top_refs)


def test_search_rank_bizplan_penalizes_low_signal_domains():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint2-domain-prior",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "keywords": ["circular economy", "education technology", "sustainability"],
        "search_results": [
            {
                "title": "Circular economy for campuses in Indonesia",
                "url": "https://www.linkedin.com/posts/example",
                "source": "tavily",
                "snippet": "A post about circular economy opportunities for campuses.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Indonesia education market size report",
                "url": "https://www.statista.com/example",
                "source": "tavily",
                "snippet": "Education market report for Indonesia with adoption and demand signals.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    ranked = result["ranked_results"]
    assert ranked[0]["url"] == "https://www.statista.com/example"


def test_search_rank_bizplan_excludes_social_domains_from_top_references():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint3-domain-exclude",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "keywords": ["circular economy", "education technology", "sustainability"],
        "search_results": [
            {
                "title": "Campus sustainability software competitor overview",
                "url": "https://www.linkedin.com/posts/example-competitor",
                "source": "tavily",
                "snippet": "Competitor overview for campus sustainability software.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "University Management Software in Indonesia",
                "url": "https://openeducat.org/university-management-software-in-indonesia/",
                "source": "tavily",
                "snippet": "University management software for Indonesia with admissions, operations, and reporting modules.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    assert all("linkedin.com" not in ref["url"] for ref in result["top_references"])


def test_search_rank_bizplan_marks_listicle_vendor_pages_as_competition():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint4-rank-competition",
        "doc_type": "bizplan",
        "title": "GreenCampus",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["sustainability", "campus operations", "education technology"],
        "search_results": [
            {
                "title": "Best Campus Sustainability Software Providers in Indonesia",
                "url": "https://example.com/vendors",
                "source": "tavily",
                "snippet": "Compare OpenEduCat, Ellucian, and CampusKloud for university sustainability and operations teams.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Indonesia higher education market report",
                "url": "https://example.com/market-2",
                "source": "tavily",
                "snippet": "Higher education digitization continues to grow in Indonesia.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    vendor_ref = next(ref for ref in result["ranked_results"] if ref["url"] == "https://example.com/vendors")
    assert vendor_ref["reference_role"] == "competition"


def test_search_rank_bizplan_treats_competitive_landscape_market_report_as_market():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint4-rank-market-report",
        "doc_type": "bizplan",
        "title": "GreenCampus",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["sustainability", "campus operations", "education technology"],
        "search_results": [
            {
                "title": "Indonesia Circular Economy Market",
                "url": "https://example.com/circular-market",
                "source": "tavily",
                "snippet": "Indonesia Circular Economy Market Overview with market segmentation and competitive landscape.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    ranked = result["ranked_results"][0]
    assert ranked["reference_role"] == "market"


def test_search_rank_bizplan_penalizes_investor_and_payroll_noise():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint4-rank-noise",
        "doc_type": "bizplan",
        "title": "GreenCampus",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["sustainability", "campus operations", "education technology"],
        "search_results": [
            {
                "title": "Campus management software pricing benchmark Indonesia",
                "url": "https://example.com/campus-pricing",
                "source": "tavily",
                "snippet": "Campus management software pricing for universities in Indonesia.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Top Sustainability Startup Investors in Indonesia",
                "url": "https://example.com/investors",
                "source": "tavily",
                "snippet": "A list of investors for sustainability startups in Indonesia.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Software payroll terbaik di Indonesia",
                "url": "https://example.com/payroll",
                "source": "tavily",
                "snippet": "Payroll software pricing for HR and attendance workflows.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    ranked_urls = [item["url"] for item in result["ranked_results"]]
    assert ranked_urls[0] == "https://example.com/campus-pricing"


def test_search_rank_bizplan_prefers_software_directory_over_press_release():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint5-rank-directory",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["sustainability", "education technology", "saas"],
        "search_results": [
            {
                "title": "University management software in Indonesia",
                "url": "https://openeducat.org/university-management-software-in-indonesia/",
                "source": "tavily",
                "snippet": "University management software for admissions, campus operations, and student workflows.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Indonesia edtech market size, share, growth, industry analysis",
                "url": "https://www.openpr.com/news/4232079/indonesia-edtech-market-size-share-growth-industry-analysis",
                "source": "tavily",
                "snippet": "Press release about Indonesia edtech market growth.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    ranked_urls = [item["url"] for item in result["ranked_results"]]
    assert ranked_urls[0] == "https://openeducat.org/university-management-software-in-indonesia/"


def test_search_rank_bizplan_penalizes_broad_market_without_category_fit():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint6-rank-market-fit",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["circular economy", "education technology", "sustainability"],
        "search_results": [
            {
                "title": "Indonesia Waste-to-Energy & Circular Economy Market",
                "url": "https://example.com/circular-market",
                "source": "tavily",
                "snippet": "Circular economy market overview, market segmentation, and industry analysis in Indonesia.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Indonesia Edtech Market Size Report",
                "url": "https://example.com/edtech-market",
                "source": "tavily",
                "snippet": "Indonesia edtech market growth as universities digitize campus operations and student services.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    ranked_urls = [item["url"] for item in result["ranked_results"]]
    assert ranked_urls[0] == "https://example.com/edtech-market"


def test_search_rank_bizplan_ignores_generic_price_article_as_pricing():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint6-price-false-positive",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "keywords": ["education technology", "sustainability"],
        "search_results": [
            {
                "title": "Peterson Indonesia: Sustainability Consultant",
                "url": "https://www.petersonindonesia.com/",
                "source": "tavily",
                "snippet": "Plastic Price Surge: Geopolitical shock or a turning point for sustainable packaging?",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Campus cloud software pricing",
                "url": "https://campuskloud.io/pricing",
                "source": "tavily",
                "snippet": "Monthly and annual plans for campus management software.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    roles = {item["url"]: item["reference_role"] for item in result["ranked_results"]}
    assert roles["https://www.petersonindonesia.com/"] != "pricing"
    assert roles["https://campuskloud.io/pricing"] == "pricing"


def test_bizplan_market_synthesis_excludes_consulting_site_from_substitutes():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint8-substitute-noise",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Peterson Indonesia: Sustainability Consultant",
                "url": "https://www.petersonindonesia.com/",
                "source": "tavily",
                "snippet": "Consulting services for sustainability reporting and CSR mapping.",
                "relevance_score": 0.66,
                "reference_role": "general",
            },
            {
                "title": "Pricing for Campus Cloud management software",
                "url": "https://campuskloud.io/pricing",
                "source": "tavily",
                "snippet": "Campus cloud software pricing and modules for university operations.",
                "relevance_score": 0.78,
                "reference_role": "pricing",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    substitutes = result["competition_insights"]["substitutes"]
    assert "Campuskloud" in substitutes
    assert all("Peterson" not in item for item in substitutes)


def test_search_rank_bizplan_ignores_event_competition_as_competitor():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint6-competition-false-positive",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "keywords": ["education technology", "sustainability"],
        "search_results": [
            {
                "title": "Urban Design Competition - Monash University, Indonesia",
                "url": "https://www.monash.edu/indonesia/competition/urban-design-competition",
                "source": "tavily",
                "snippet": "A competition for students to design sustainable cities.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Campus sustainability software competitors in Southeast Asia",
                "url": "https://example.com/competition",
                "source": "tavily",
                "snippet": "Competitors in university sustainability software compete on analytics and implementation.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    roles = {item["url"]: item["reference_role"] for item in result["ranked_results"]}
    assert roles["https://www.monash.edu/indonesia/competition/urban-design-competition"] != "competition"
    assert roles["https://example.com/competition"] == "competition"


def test_search_rank_bizplan_excludes_weak_directory_competition_from_top_references():
    from app.graph.nodes.search_rank import search_rank_node

    state = {
        "analysis_id": "biz-sprint9-weak-directory",
        "doc_type": "bizplan",
        "title": "EduCycle",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus", "universitas"],
        "keywords": ["education technology", "sustainability", "saas"],
        "search_results": [
            {
                "title": "Indonesia Edtech Market Size, Share | Forecast 2034 - IMARC Group",
                "url": "https://www.imarcgroup.com/indonesia-edtech-market",
                "source": "tavily",
                "snippet": "Indonesia edtech market size and growth as universities digitize student and campus services.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Pricing for Campus Cloud management software",
                "url": "https://campuskloud.io/pricing",
                "source": "tavily",
                "snippet": "Monthly and annual plans for campus management software.",
                "year": 2025,
                "authors": [],
            },
            {
                "title": "Top 20+ Education Companies in Indonesia (2026)",
                "url": "https://techbehemoths.com/companies/education/indonesia",
                "source": "tavily",
                "snippet": "Discover top education companies in Indonesia and explore featured agencies.",
                "year": 2025,
                "authors": [],
            },
        ],
    }

    result = asyncio.run(search_rank_node(state))  # type: ignore[arg-type]
    assert all("techbehemoths.com" not in ref["url"] for ref in result["top_references"])


def test_bizplan_market_synthesis_requires_market_and_competition_coverage_for_validated():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint2-market-coverage",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Indonesia edtech market growth report",
                "url": "https://example.com/market-1",
                "source": "tavily",
                "snippet": "Education technology market in Indonesia continues to grow among universities.",
                "relevance_score": 0.74,
                "reference_role": "market",
            },
            {
                "title": "University software pricing benchmark Indonesia",
                "url": "https://example.com/pricing-1",
                "source": "tavily",
                "snippet": "Pricing benchmark for campus software subscriptions in Indonesia.",
                "relevance_score": 0.71,
                "reference_role": "pricing",
            },
            {
                "title": "General campus digitization outlook",
                "url": "https://example.com/general",
                "source": "tavily",
                "snippet": "Universities continue to digitize student and operational workflows.",
                "relevance_score": 0.68,
                "reference_role": "general",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    assert result["market_validation_status"] == "partial"
    assert any("kompetisi" in item.lower() for item in result["market_red_flags"])


def test_bizplan_market_synthesis_rejects_broad_market_evidence_without_category_fit():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint6-market-fit",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Indonesia Waste-to-Energy & Circular Economy Market",
                "url": "https://example.com/circular-market",
                "source": "tavily",
                "snippet": "Circular economy market overview and segmentation in Indonesia.",
                "relevance_score": 0.72,
                "reference_role": "market",
                "market_fit_score": 0.0,
            },
            {
                "title": "Pricing for Campus Cloud management software",
                "url": "https://campuskloud.io/pricing",
                "source": "tavily",
                "snippet": "Campus cloud software pricing and modules for university operations.",
                "relevance_score": 0.76,
                "reference_role": "pricing",
                "market_fit_score": 0.16,
            },
            {
                "title": "College Management Software in Indonesia - OpenEduCat",
                "url": "https://openeducat.org/college-management-software-in-indonesia/",
                "source": "tavily",
                "snippet": "OpenEduCat helps universities digitize admissions and campus operations.",
                "relevance_score": 0.84,
                "reference_role": "competition",
                "market_fit_score": 0.20,
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    assert result["market_validation_status"] == "partial"
    assert len(result["market_validation"]["evidence"]) == 1
    assert result["market_validation"]["evidence"][0]["url"] == "https://campuskloud.io/pricing"
    assert any("kategori bisnis inti" in item.lower() for item in result["market_red_flags"])


def test_bizplan_market_synthesis_dedupes_market_evidence_and_requires_explicit_competition_role():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint2-market-dedupe",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Indonesia Online Education Market Statistics & Outlook 2034",
                "url": "https://example.com/market",
                "source": "tavily",
                "snippet": "Online education market in Indonesia continues to grow.",
                "relevance_score": 0.80,
                "reference_role": "market",
            },
            {
                "title": "Indonesia Online Education Market Statistics & Outlook 2034",
                "url": "https://example.com/market",
                "source": "tavily",
                "snippet": "Online education market in Indonesia continues to grow.",
                "relevance_score": 0.80,
                "reference_role": "market",
            },
            {
                "title": "(PDF) Notions of Non-Mainstream Educational Provision",
                "url": "https://example.com/general-paper",
                "source": "tavily",
                "snippet": "A general paper about educational provision.",
                "relevance_score": 0.70,
                "reference_role": "general",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    assert result["market_validation_status"] == "partial"
    assert len(result["market_validation"]["evidence"]) == 1
    assert result["competition_insights"]["direct_competitors"] == []


def test_bizplan_market_synthesis_extracts_substitutes_when_direct_competitors_missing():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint3-substitutes",
        "company_name": "EduCycle",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "University Management Software in Indonesia",
                "url": "https://openeducat.org/university-management-software-in-indonesia/",
                "source": "tavily",
                "snippet": "Software for campus administration, reporting, and student operations.",
                "relevance_score": 0.72,
                "reference_role": "general",
            },
            {
                "title": "Pricing for Campus Cloud management software",
                "url": "https://campuskloud.io/pricing",
                "source": "tavily",
                "snippet": "Campus cloud software pricing and modules for university operations.",
                "relevance_score": 0.76,
                "reference_role": "pricing",
            },
            {
                "title": "Indonesia education market size report",
                "url": "https://www.statista.com/example",
                "source": "tavily",
                "snippet": "Education market demand in Indonesia continues to grow.",
                "relevance_score": 0.71,
                "reference_role": "market",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    substitutes = result["competition_insights"]["substitutes"]
    assert any("software" in item.lower() for item in substitutes)
    assert result["competition_insights"]["direct_competitors"] == []


def test_bizplan_market_synthesis_extracts_named_competitors_from_vendor_snippet():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint4-market-competitors",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Best Campus Sustainability Software Providers in Indonesia",
                "url": "https://example.com/vendors",
                "source": "tavily",
                "snippet": "This comparison highlights OpenEduCat, Ellucian, and CampusKloud for university sustainability teams.",
                "relevance_score": 0.81,
                "reference_role": "competition",
            },
            {
                "title": "Indonesia education market size report",
                "url": "https://www.statista.com/example",
                "source": "tavily",
                "snippet": "Education market demand in Indonesia continues to grow.",
                "relevance_score": 0.71,
                "reference_role": "market",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    competitors = " | ".join(result["competition_insights"]["direct_competitors"])
    assert "OpenEduCat" in competitors
    assert "Ellucian" in competitors
    assert "CampusKloud" in competitors


def test_bizplan_market_synthesis_prefers_vendor_brand_over_generic_product_title():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint5-market-brand-clean",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "College Management Software in Indonesia - OpenEduCat",
                "url": "https://openeducat.org/college-management-software-in-indonesia/",
                "source": "tavily",
                "snippet": "OpenEduCat helps universities digitize admissions, campus operations, and student workflows. Start FreeTalk today.",
                "relevance_score": 0.84,
                "reference_role": "competition",
            },
            {
                "title": "Indonesia edtech market report",
                "url": "https://example.com/market",
                "source": "tavily",
                "snippet": "Indonesia edtech demand continues to grow.",
                "relevance_score": 0.71,
                "reference_role": "market",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    competitors = result["competition_insights"]["direct_competitors"]
    assert "OpenEduCat" in competitors
    assert all("Start FreeTalk" not in item for item in competitors)
    assert all("College Management Software in Indonesia - OpenEduCat" not in item for item in competitors)


def test_bizplan_market_synthesis_avoids_generic_directory_title_as_competitor():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint6-directory-clean",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Top 20+ Education Companies in Indonesia (2026) - TechBehemoths",
                "url": "https://techbehemoths.com/companies/education/indonesia",
                "source": "tavily",
                "snippet": "There are 11 Companies in Indonesia. Techgropse is a leading mobile app and web development company.",
                "relevance_score": 0.82,
                "reference_role": "competition",
            },
            {
                "title": "Indonesia edtech market report",
                "url": "https://example.com/market",
                "source": "tavily",
                "snippet": "Indonesia edtech demand continues to grow.",
                "relevance_score": 0.71,
                "reference_role": "market",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    competitors = result["competition_insights"]["direct_competitors"]
    assert all("TechBehemoths" not in item for item in competitors)
    assert all("Top 20+ Education Companies" not in item for item in competitors)
    assert all("Explore Top" not in item for item in competitors)
    assert all("Discover Top" not in item for item in competitors)


def test_bizplan_market_synthesis_uses_vendor_domain_as_substitute_when_only_pricing_page_exists():
    from app.graph.nodes.bizplan_market_synthesis import bizplan_market_synthesis_node

    state = {
        "analysis_id": "biz-sprint4-market-substitute-domain",
        "company_name": "GreenCampus",
        "industry": "Pendidikan",
        "geography": "Indonesia",
        "target_customer": ["kampus"],
        "top_references": [
            {
                "title": "Pricing for Campus Cloud management software",
                "url": "https://campuskloud.io/pricing",
                "source": "tavily",
                "snippet": "Campus cloud software pricing and modules for university operations.",
                "relevance_score": 0.78,
                "reference_role": "pricing",
            },
            {
                "title": "Indonesia edtech market report",
                "url": "https://example.com/market",
                "source": "tavily",
                "snippet": "Indonesia edtech demand continues to grow.",
                "relevance_score": 0.71,
                "reference_role": "market",
            },
        ],
    }

    result = asyncio.run(bizplan_market_synthesis_node(state))  # type: ignore[arg-type]
    substitutes = " | ".join(result["competition_insights"]["substitutes"])
    assert "Campuskloud" in substitutes
