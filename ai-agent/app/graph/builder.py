from typing import Literal
from langgraph.graph import StateGraph, END

from app.graph.state import ReviewEngineState
from app.graph.nodes.extract import extract_node
from app.graph.nodes.metadata_extract import metadata_extract_node
from app.graph.nodes.essay_agent import essay_agent_node
from app.graph.nodes.document_profile import document_profile_node
from app.graph.nodes.retrieval_prep import retrieval_prep_node
from app.graph.nodes.search_execute import search_execute_node
from app.graph.nodes.search_rank import search_rank_node
from app.graph.nodes.evidence_select import evidence_select_node
from app.graph.nodes.research_agent import research_agent_node
from app.graph.nodes.score import score_node
from app.graph.nodes.generate import generate_node

def route_after_extract(state: ReviewEngineState) -> Literal["metadata_extract", "end_with_error"]:
    """
    Conditional edge setelah extract:
    - Jika valid → lanjut ke metadata_extract
    - Jika gagal → langsung END
    """
    if not state.get("is_valid", False):
        return "end_with_error"
    return "metadata_extract"


def route_by_doc_type(state: ReviewEngineState) -> Literal["essay_agent", "document_profile"]:
    """
    Conditional edge setelah metadata_extract: rute berdasarkan 'doc_type'.
    - essay/bizplan → langsung ke essay_agent
    - research → document_profile → research_agent (Fase 3)
    """
    doc_type = state.get("doc_type", "essay")
    
    route_map = {
        "essay": "essay_agent",
        "research": "document_profile",  # Fase 3: profiling dulu sebelum research_agent
        "bizplan": "essay_agent",        # fallback ke essay (belum ada bizplan_agent)
    }
    return route_map.get(doc_type, "essay_agent")

def build_graph() -> StateGraph:
    """Merakit dan meng-compile LangGraph Pipeline."""
    graph = StateGraph(ReviewEngineState)
    
    # 1. Daftarkan Semua Node
    graph.add_node("extract", extract_node)
    graph.add_node("metadata_extract", metadata_extract_node)  # Fase 1
    graph.add_node("essay_agent", essay_agent_node)
    graph.add_node("document_profile", document_profile_node)  # Fase 3
    graph.add_node("retrieval_prep", retrieval_prep_node)      # Fase 4
    graph.add_node("search_execute", search_execute_node)      # Fase 5
    graph.add_node("search_rank", search_rank_node)            # Fase 6
    graph.add_node("evidence_select", evidence_select_node)    # Fase 7
    graph.add_node("research_agent", research_agent_node)      # Fase 2
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
    
    # 4. Conditional Edge setelah metadata_extract → routing berdasarkan doc_type
    graph.add_conditional_edges(
        "metadata_extract",
        route_by_doc_type,
        {
            "essay_agent": "essay_agent",
            "document_profile": "document_profile",
        }
    )
    
    # 5. Jalur research: profile → queries → search → rank → evidence → agent
    graph.add_edge("document_profile", "retrieval_prep")   # Fase 4
    graph.add_edge("retrieval_prep", "search_execute")     # Fase 5
    graph.add_edge("search_execute", "search_rank")        # Fase 6
    graph.add_edge("search_rank", "evidence_select")       # Fase 7
    graph.add_edge("evidence_select", "research_agent")    # Fase 7
    
    # 6. Semua jalur agent → score → generate
    graph.add_edge("essay_agent", "score")
    graph.add_edge("research_agent", "score")
    graph.add_edge("score", "generate")
    graph.add_edge("generate", END)
    
    # 5. Compile!
    return graph.compile()

# Instansi global siap pakai saat route `post /evaluate` dipanggil
review_pipeline = build_graph()
