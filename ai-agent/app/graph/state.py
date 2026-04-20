from __future__ import annotations
import operator
from typing import Annotated, Literal, TypedDict

class ReviewEngineState(TypedDict):
    
    # Input (dari Laravel — user memilih doc_type saat upload)
    analysis_id: str
    file_url: str
    doc_type: Literal["essay", "research", "bizplan"]

    # Extraction
    raw_markdown:   str
    page_count:     int
    title:          str | None
    is_valid:       bool
    error:          str | None

    # Metadata (Fase 1 — diisi oleh metadata_extract node)
    abstract:       str
    authors:        list[str]
    keywords:       list[str]
    year:           int | None   # Tahun publikasi dokumen
    document_head:  str          # ~3000-4000 karakter awal dokumen
    document_tail:  str          # ~1000-2000 karakter akhir dokumen

    # Bizplan metadata (Fase 4A)
    company_name:      str | None
    industry:          str | None
    target_customer:   list[str]
    geography:         str | None
    business_stage:    str | None
    funding_ask:       str | None
    traction_signals:  list[str]
    pricing_signals:   list[str]

    # Document Profile (Fase 3 — diisi oleh research_document_profile node)
    domain:           str | None           # e.g. "computer_science", "medicine"
    sub_domain:       str | None           # e.g. "natural_language_processing"
    paper_type:       str | None           # e.g. "empirical", "survey", "method"
    retrieval_focus:  list[str]            # e.g. ["prior_work", "benchmark"]

    # Bizplan financials (Fase 4B)
    revenue_model:          list[str]
    pricing:                list[str]
    financial_metrics:      dict[str, object]
    burn_rate:              str | None
    runway_months:          float | None
    break_even_timeline:    str | None
    unit_economics_signals: dict[str, object]
    financial_red_flags:    list[str]
    external_market_evidence: list[dict]
    competitive_evidence:    list[dict]
    market_validation_status: str | None
    market_validation:        dict[str, object]
    competition_insights:     dict[str, object]
    market_red_flags:         list[str]

    # Agent prep
    agent_context: str
    search_queries: dict[str, list[str]]   # {"semanticscholar": [...], "arxiv": [...], "tavily": [...]}
    run_essay_web_search: bool             # Flag apakah essay lulus heuristik search

    # Search (Fase 5 — diisi oleh search_execute node)
    search_results: list[dict]             # Hasil search terdedup dari semua sumber

    # Ranking (Fase 6 — diisi oleh search_rank node)
    ranked_results:  list[dict]            # Semua hasil search setelah diranking
    top_references:  list[dict]            # 3-5 referensi terbaik untuk context LLM

    # Evidence (Fase 7 — diisi oleh evidence_select node)
    evidence_chunks: list[dict]            # Potongan internal dokumen per section
    review_context:  str                   # Context final untuk LLM scoring (metadata+evidence+refs)

    # Tools
    tool_results: Annotated[list[dict], operator.add]

    # Scoring
    dimension_scores:    dict[str, float]
    score_overall:       float | None
    dimensions_feedback: list[dict]
    overall_feedback:    str
    summary:             str

    # Final
    final_result: dict | None
