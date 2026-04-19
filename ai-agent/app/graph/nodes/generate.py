"""
generate.py — Generate Final Report Node (Fase 9)
===================================================
Menyusun `final_result` yang informatif untuk frontend dan callback Laravel.

Enrichment untuk research:
- Metadata penting (authors, keywords, domain, paper_type)
- Top references dari pipeline search
- Extracted strengths & improvements dari dimension feedback
- Profile data (domain, sub_domain, paper_type)

Keamanan:
- TIDAK menyertakan `review_context`, `raw_markdown`, atau `agent_context`
- Hanya data yang berguna untuk frontend/display
"""

from app.graph.state import ReviewEngineState


def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """Helper untuk logging progres ke Laravel node Generate"""
    try:
        import asyncio
        from app.services.laravel_client import log_step
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            asyncio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[generate_node][log_step] log gagal: {exc}")


def _extract_strengths_improvements(dimensions: list[dict]) -> tuple[list[str], list[str]]:
    """
    Extract strengths dan improvements dari dimensi feedback.
    
    Strategi sederhana:
    - Dimensi dengan skor >= 7.0 → strength
    - Dimensi dengan skor < 6.0 → improvement
    """
    strengths = []
    improvements = []

    for dim in dimensions:
        key = dim.get("key", "")
        score = float(dim.get("score", 0))
        feedback = dim.get("feedback", "")
        label = dim.get("label", key.replace("_", " ").title())

        if score >= 7.0 and feedback:
            strengths.append(f"{label}: {feedback[:150]}")
        elif score < 6.0 and feedback:
            improvements.append(f"{label}: {feedback[:150]}")

    return strengths, improvements


def _build_references_output(top_references: list[dict]) -> list[dict]:
    """
    Format top_references untuk output frontend.
    Hanya field yang berguna, tanpa snippet panjang atau internal scores.
    """
    refs_output = []
    for ref in top_references[:5]:
        refs_output.append({
            "title": ref.get("title", "Untitled"),
            "authors": ref.get("authors", [])[:4],
            "year": ref.get("year"),
            "url": ref.get("url", ""),
            "source": ref.get("source", ""),
        })
    return refs_output


async def generate_node(state: ReviewEngineState) -> dict:
    """
    Node akhir: Menyusun final_result yang informatif.
    
    Output berbeda per doc_type:
    - Essay/bizplan: basic (title, score, dimensions, feedback)
    - Research: enriched (+ metadata, profile, references, strengths/improvements)
    """
    analysis_id = state.get("analysis_id")
    doc_type = state.get("doc_type", "essay")

    print("\n[generate_node] Menyusun laporan akhir...")
    _safe_log(analysis_id, "generating", "processing", "Menyusun laporan evaluasi akhir...")

    dimensions = state.get("dimensions_feedback", [])

    # Extract strengths & improvements dari dimensi
    strengths, improvements = _extract_strengths_improvements(dimensions)

    # ─── Base result (semua doc_type) ─────────────────────────────────────
    final_result = {
        "analysis_id": analysis_id,
        "doc_type": doc_type,
        "title": state.get("title") or "Dokumen Tanpa Judul",
        "page_count": state.get("page_count", 0),
        "score_overall": state.get("score_overall", 0.0),
        "summary": state.get("summary", ""),
        "dimensions": dimensions,
        "overall_feedback": state.get("overall_feedback", ""),
        "strengths": strengths,
        "improvements": improvements,
    }

    # ─── Enriched metadata (Fase 9 - Always include if available) ─────────
    final_result["metadata"] = {
        "authors": state.get("authors", []),
        "keywords": state.get("keywords", []),
        "abstract": (state.get("abstract") or "")[:500],
    }

    # ─── Research specific enrichment (Profile & References) ──────────────
    if doc_type == "research":
        # Profile
        final_result["profile"] = {
            "domain": state.get("domain"),
            "sub_domain": state.get("sub_domain"),
            "paper_type": state.get("paper_type"),
            "retrieval_focus": state.get("retrieval_focus", []),
        }

        # References dari search pipeline
        top_refs = state.get("top_references") or []
        final_result["references"] = _build_references_output(top_refs)

        # Stats pipeline (untuk debugging/monitoring)
        search_results_count = len(state.get("search_results") or [])
        evidence_chunks_count = len(state.get("evidence_chunks") or [])
        final_result["pipeline_stats"] = {
            "search_results_total": search_results_count,
            "references_selected": len(top_refs),
            "evidence_chunks": evidence_chunks_count,
        }

        print(f"[generate_node] Research enrichment: "
              f"{len(top_refs)} refs, "
              f"{evidence_chunks_count} evidence chunks, "
              f"domain={state.get('domain', '?')}")
    else:
        # Essay/bizplan: references kosong tapi field tetap ada
        final_result["references"] = []
        final_result["profile"] = {
            "domain": state.get("domain"),
            "sub_domain": state.get("sub_domain"),
        }

    _safe_log(analysis_id, "generating", "done", "Laporan evaluasi berhasil disusun.")
    print(f"[generate_node] Selesai — score: {final_result['score_overall']}/10, "
          f"strengths: {len(strengths)}, improvements: {len(improvements)}\n")

    return {"final_result": final_result}