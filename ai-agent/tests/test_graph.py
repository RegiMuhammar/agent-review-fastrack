import pytest
from app.graph.state import ReviewEngineState
from app.graph.builder import route_by_doc_type

def test_route_by_doc_type_error_state():
    """Test router logic jika state di-flag is_valid=False"""
    state: ReviewEngineState = {
        "is_valid": False,
        "doc_type": "essay"
    } # type: ignore
    
    # Harusnya diarahkan ke node END
    assert route_by_doc_type(state) == "end_with_error"


def test_route_by_doc_type_essay():
    """Test router logic jika state adalah essay & valid"""
    state: ReviewEngineState = {
        "is_valid": True,
        "doc_type": "essay"
    } # type: ignore
    
    assert route_by_doc_type(state) == "essay_agent"

def test_route_by_doc_type_fallback():
    """Saat ini MVP (Fase 2), doc type research harus falback ke essay_agent"""
    state: ReviewEngineState = {
        "is_valid": True,
        "doc_type": "research"
    } # type: ignore
    
    assert route_by_doc_type(state) == "essay_agent"
