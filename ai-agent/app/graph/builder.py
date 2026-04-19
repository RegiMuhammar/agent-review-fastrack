from typing import Literal
from langgraph.graph import StateGraph, END

from app.graph.state import ReviewEngineState
from app.graph.nodes.extract import extract_node
from app.graph.nodes.metadata_extract import metadata_extract_node
from app.graph.nodes.essay_document_profile import essay_document_profile_node
from app.graph.nodes.research_document_profile import research_document_profile_node
from app.graph.nodes.bizplan_document_profile import bizplan_document_profile_node
from app.graph.nodes.retrieval_prep import retrieval_prep_node
from app.graph.nodes.search_execute import search_execute_node
from app.graph.nodes.search_rank import search_rank_node
from app.graph.nodes.evidence_select import evidence_select_node
from app.graph.nodes.research_agent import research_agent_node
from app.graph.nodes.essay_agent import essay_agent_node
from app.graph.nodes.score import score_node
from app.graph.nodes.generate import generate_node

def route_after_extract(state: ReviewEngineState) -> Literal["metadata_extract", "end_with_error"]:
    if not state.get("is_valid", False):
        return "end_with_error"
    return "metadata_extract"


def route_by_doc_type(state: ReviewEngineState) -> Literal["essay_document_profile", "research_document_profile", "bizplan_document_profile"]:
    doc_type = state.get("doc_type", "essay")
    route_map = {
        "essay": "essay_document_profile",
        "research": "research_document_profile",
        "bizplan": "bizplan_document_profile",
    }
    return route_map.get(doc_type, "essay_document_profile")

def route_after_essay_profile(state: ReviewEngineState) -> Literal["retrieval_prep", "essay_agent"]:
    if state.get("run_essay_web_search", False):
        return "retrieval_prep"
    return "essay_agent"

def route_after_evidence(state: ReviewEngineState) -> Literal["research_agent", "essay_agent"]:
    doc_type = state.get("doc_type", "research")
    if doc_type == "essay":
        return "essay_agent"
    return "research_agent"

def build_graph() -> StateGraph:
    graph = StateGraph(ReviewEngineState)
    
    # 1. Daftarkan Semua Node
    graph.add_node("extract", extract_node)
    graph.add_node("metadata_extract", metadata_extract_node)
    graph.add_node("essay_document_profile", essay_document_profile_node)
    graph.add_node("research_document_profile", research_document_profile_node)
    graph.add_node("bizplan_document_profile", bizplan_document_profile_node)
    graph.add_node("retrieval_prep", retrieval_prep_node)
    graph.add_node("search_execute", search_execute_node)
    graph.add_node("search_rank", search_rank_node)
    graph.add_node("evidence_select", evidence_select_node)
    graph.add_node("research_agent", research_agent_node)
    graph.add_node("essay_agent", essay_agent_node)
    graph.add_node("score", score_node)
    graph.add_node("generate", generate_node)
    
    # 2. Definisikan Titik Awal
    graph.set_entry_point("extract")
    
    # 3. Conditional Edge setelah extract
    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "metadata_extract": "metadata_extract",
            "end_with_error": END,
        }
    )
    
    # 4. Conditional Edge setelah metadata_extract
    graph.add_conditional_edges(
        "metadata_extract",
        route_by_doc_type,
        {
            "essay_document_profile": "essay_document_profile",
            "research_document_profile": "research_document_profile",
            "bizplan_document_profile": "bizplan_document_profile",
        }
    )
    
    # 5. Jalur Research (Mulai dari research profile)
    graph.add_edge("research_document_profile", "retrieval_prep")
    
    # 6. Jalur Essay Profile Conditional
    graph.add_conditional_edges(
        "essay_document_profile",
        route_after_essay_profile,
        {
            "retrieval_prep": "retrieval_prep",
            "essay_agent": "essay_agent",
        }
    )
    
    # 7. Subgraph Retrieval (Bisa dipanggil oleh research atau essay)
    graph.add_edge("retrieval_prep", "search_execute")
    graph.add_edge("search_execute", "search_rank")
    graph.add_edge("search_rank", "evidence_select")
    
    # 8. Keluar dari Retrieval Subgraph
    graph.add_conditional_edges(
        "evidence_select",
        route_after_evidence,
        {
            "research_agent": "research_agent",
            "essay_agent": "essay_agent",
        }
    )
    
    # 9. Jalur Akhir menuju Score
    graph.add_edge("bizplan_document_profile", "score")
    graph.add_edge("research_agent", "score")
    graph.add_edge("essay_agent", "score")
    graph.add_edge("score", "generate")
    graph.add_edge("generate", END)
    
    return graph.compile()

review_pipeline = build_graph()
