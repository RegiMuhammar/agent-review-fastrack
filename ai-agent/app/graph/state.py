from __future__ import annotations
import operator
from typing import Annotated, Literal, TypedDict

class ReviewEngineState(TypedDict):
    # Input
    analysis_id: str
    file_path: str
    doc_type_hint: str | None

    # Extraction
    raw_markdown:   str
    page_count:     int
    title:          str | None
    is_valid:       bool
    error:          str | None

    # Classification [ini bisa dicut jadi tidak perlu klasifikasi layer karna udah ada input dari user saat submit dokumne]
    doc_type: Literal["essay", "research", "bizplan"] | None
    classify_confidence: float

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