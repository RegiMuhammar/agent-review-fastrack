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
    document_head:  str          # ~3000-4000 karakter awal dokumen
    document_tail:  str          # ~1000-2000 karakter akhir dokumen

    # Document Profile (Fase 3 — diisi oleh document_profile node)
    domain:           str | None           # e.g. "computer_science", "medicine"
    sub_domain:       str | None           # e.g. "natural_language_processing"
    paper_type:       str | None           # e.g. "empirical", "survey", "method"
    retrieval_focus:  list[str]            # e.g. ["prior_work", "benchmark"]


    # Agent prep
    agent_context: str
    search_queries: list[str]

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