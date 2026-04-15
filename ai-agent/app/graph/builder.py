from typing import Literal
from langgraph.graph import StateGraph, END

from app.graph.state import ReviewEngineState
from app.graph.nodes.extract import extract_node
from app.graph.nodes.essay_agent import essay_agent_node
from app.graph.nodes.score import score_node
from app.graph.nodes.generate import generate_node

def route_by_doc_type(state: ReviewEngineState) -> Literal["essay_agent", "end_with_error"]:
    """
    Conditional edge: rute arah node berdasarkan 'doc_type'.
    """
    # Jika gagal dari proses extract
    if not state.get("is_valid", False):
        return "end_with_error"
    
    # Check state doc_type, default = "essay"
    doc_type = state.get("doc_type", "essay")
    
    # Mapping untuk MVP, semuanya diarahkan ke 'essay_agent'
    # Nanti di Fase 3 kita akan tambahkan research_agent & bizplan_agent
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
    graph.add_node("essay_agent", essay_agent_node)
    # graph.add_node("research_agent", research_agent_node)  # Nanti Fase 3
    # graph.add_node("bizplan_agent", bizplan_agent_node)    # Nanti Fase 3
    graph.add_node("score", score_node)
    graph.add_node("generate", generate_node)
    
    # 2. Definisikan Titik Awal
    graph.set_entry_point("extract")
    
    # 3. Conditional Edge setelah extract
    # Dari extract, akan menjalankan state mapping `route_by_doc_type`
    graph.add_conditional_edges(
        "extract",
        route_by_doc_type,
        {
            "essay_agent": "essay_agent",
            # "research_agent": "research_agent", # Fase 3
            # "bizplan_agent": "bizplan_agent", # Fase 3
            "end_with_error": END, # Jika PDF rusak/is_valid False, langsung END graph
        }
    )
    
    # 4. Alur Lurus Agent -> Score -> Generate
    graph.add_edge("essay_agent", "score")
    graph.add_edge("score", "generate")
    graph.add_edge("generate", END)
    
    # 5. Compile!
    return graph.compile()

# Instansi global siap pakai saat route `post /evaluate` dipanggil
review_pipeline = build_graph()
