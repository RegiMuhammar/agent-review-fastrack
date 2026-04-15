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