from typing import Literal
from langgraph.graph import StateGraph, END

from app.graph.state import ReviewEngineState
from app.graph.nodes.extract import extract_node
from app.graph.nodes.metadata_extract import metadata_extract_node
from app.graph.nodes.essay_agent import essay_agent_node
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


def route_by_doc_type(state: ReviewEngineState) -> Literal["essay_agent", "end_with_error"]:
    """
    Conditional edge setelah metadata_extract: rute berdasarkan 'doc_type'.
    """
    # Check state doc_type, default = "essay"
    doc_type = state.get("doc_type", "essay")
    
    # Mapping untuk MVP, semuanya diarahkan ke 'essay_agent'
    # Nanti di Fase 2 kita akan tambahkan research_agent
    route_map = {
        "essay": "essay_agent",
        "research": "essay_agent",    # fallback ke essay (Fase 2)
        "bizplan": "essay_agent",     # fallback ke essay (Fase 2)
    }
    return route_map.get(doc_type, "essay_agent")

def build_graph() -> StateGraph:
    """Merakit dan meng-compile LangGraph Pipeline."""
    graph = StateGraph(ReviewEngineState)
    
    # 1. Daftarkan Semua Node
    graph.add_node("extract", extract_node)
    graph.add_node("metadata_extract", metadata_extract_node)  # Fase 1
    graph.add_node("essay_agent", essay_agent_node)
    # graph.add_node("research_agent", research_agent_node)  # Nanti Fase 2
    graph.add_node("score", score_node)
    graph.add_node("generate", generate_node)
    
    # 2. Definisikan Titik Awal
    graph.set_entry_point("extract")
    
    # 3. Conditional Edge setelah extract
    # Jika valid → metadata_extract, jika gagal → END
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
            # "research_agent": "research_agent",  # Fase 2
            "end_with_error": END,
        }
    )
    
    # 5. Alur Lurus Agent -> Score -> Generate
    graph.add_edge("essay_agent", "score")
    graph.add_edge("score", "generate")
    graph.add_edge("generate", END)
    
    # 5. Compile!
    return graph.compile()

# Instansi global siap pakai saat route `post /evaluate` dipanggil
review_pipeline = build_graph()
