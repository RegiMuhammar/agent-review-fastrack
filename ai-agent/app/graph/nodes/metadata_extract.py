"""
metadata_extract.py — Metadata Extraction Node (Fase 1)
========================================================
Node kedua dalam pipeline, berjalan tepat setelah `extract`.
Mengekstrak metadata terstruktur (title, abstract, authors, keywords)
dari bagian awal dokumen menggunakan LLM.

Desain defensif:
- Hanya mengirim ~3500 karakter awal ke LLM (hemat token).
- Jika LLM gagal, fallback ke nilai default aman — pipeline tetap jalan.
- Title dari metadata_extract akan meng-override title regex dari extract
  hanya jika hasilnya lebih baik.

Flow: extract → metadata_extract → route_by_doc_type → ...
"""

import json
import re

from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage

from app.graph.state import ReviewEngineState
from app.core.config import settings

# ── CONSTANTS ────────────────────────────────────────────────────────────────

HEAD_SIZE = 3500   # Karakter awal dokumen yang dikirim ke LLM
TAIL_SIZE = 1500   # Karakter akhir dokumen yang disimpan untuk referensi

METADATA_SYSTEM_PROMPT = """Kamu adalah ekstraktor metadata akademik yang ahli.
Diberikan bagian awal sebuah dokumen dalam format Markdown, ekstrak metadata kunci.

Jawab HANYA dengan objek JSON valid — tanpa markdown fences, tanpa teks tambahan.

Struktur JSON yang dibutuhkan:
{
  "title": "Judul lengkap dokumen (string)",
  "abstract": "Teks abstrak lengkap (string, kosongkan jika tidak ditemukan)",
  "authors": ["Nama Penulis 1", "Nama Penulis 2"],
  "keywords": ["keyword1", "keyword2", "keyword3"],
  "year": 2024
}

Aturan:
- Untuk "title": gunakan judul utama paper/dokumen, bukan heading bagian
- Untuk "abstract": ekstrak abstrak verbatim jika ada; string kosong jika tidak ada
- Untuk "authors": daftarkan semua nama penulis yang ditemukan di area header; list kosong jika tidak jelas
- Untuk "keywords": ekstrak keywords yang tercantum eksplisit ATAU simpulkan 3-5 topik kunci dari abstrak
- Untuk "year": cari tahun publikasi dokumen (biasanya ada di header, footer, atau dekat publisher info); integer atau null jika tidak ada
- Jangan mengarang informasi; jika field tidak ditemukan, gunakan string kosong atau list kosong
"""


# ── HELPERS ──────────────────────────────────────────────────────────────────

def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """Logging ke Laravel secara best-effort."""
    try:
        import asyncio
        from app.services.laravel_client import log_step
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            asyncio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[metadata_extract][log_step] log gagal (diabaikan): {exc}")


def _extract_title_fallback(markdown: str) -> str:
    """Fallback: ambil judul dari heading pertama di markdown."""
    match = re.search(r"^#+\s+(.+)$", markdown, re.MULTILINE)
    return match.group(1).strip() if match else "Dokumen Tanpa Judul"


def _clean_llm_json(raw: str) -> str:
    """Bersihkan output LLM dari markdown fences jika ada."""
    raw = raw.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    return raw.strip()


# ── NODE UTAMA ───────────────────────────────────────────────────────────────

async def metadata_extract_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Ekstraksi metadata terstruktur dari dokumen.

    Input dari state:
        - raw_markdown : isi dokumen dalam format Markdown (dari extract node).
        - analysis_id  : ID analisis untuk logging.
        - title        : title dari extract (regex heading), bisa None.

    Output (di-merge ke state):
        - title         : judul yang lebih baik (dari LLM, atau fallback).
        - abstract      : teks abstrak.
        - authors       : list nama penulis.
        - keywords      : list keywords.
        - document_head : potongan awal dokumen (~3500 char).
        - document_tail : potongan akhir dokumen (~1500 char).
    """
    analysis_id = state.get("analysis_id", "unknown")
    raw_markdown = state.get("raw_markdown", "")
    existing_title = state.get("title")

    print(f"\n[metadata_extract] Memulai ekstraksi metadata...")
    _safe_log(analysis_id, "metadata", "processing", "Mengekstrak metadata dokumen...")

    # ─── Simpan document_head dan document_tail ──────────────────────────
    document_head = raw_markdown[:HEAD_SIZE] if raw_markdown else ""
    document_tail = raw_markdown[-TAIL_SIZE:] if len(raw_markdown) > TAIL_SIZE else raw_markdown

    # ─── Guard: jika raw_markdown kosong, langsung fallback ─────────────
    if not raw_markdown.strip():
        print("[metadata_extract] WARNING: raw_markdown kosong, skip LLM call")
        _safe_log(analysis_id, "metadata", "done", "Metadata: skip (dokumen kosong)")
        return {
            "title": existing_title or "Dokumen Tanpa Judul",
            "abstract": "",
            "authors": [],
            "keywords": [],
            "document_head": document_head,
            "document_tail": document_tail,
        }

    # ─── LLM call untuk ekstraksi metadata ───────────────────────────────
    llm = ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )

    try:
        response = await llm.ainvoke([
            SystemMessage(content=METADATA_SYSTEM_PROMPT),
            HumanMessage(
                content=f"Ekstrak metadata dari bagian awal dokumen ini:\n\n{document_head}"
            ),
        ])

        cleaned = _clean_llm_json(response.content)
        data = json.loads(cleaned)

        # Parse fields dengan fallback aman
        llm_title = (data.get("title") or "").strip()
        abstract = (data.get("abstract") or "").strip()
        authors = data.get("authors") or []
        keywords = data.get("keywords") or []
        year = data.get("year")
        
        # Coerce year to int if string
        try:
            if year and not isinstance(year, int):
                # Try to extract 4 digit year from string
                match_year = re.search(r"\b(19|20)\d{2}\b", str(year))
                year = int(match_year.group(0)) if match_year else None
        except:
            year = None

        # Gunakan title dari LLM jika lebih baik daripada regex
        # LLM title dianggap "lebih baik" jika tidak kosong dan bukan generic
        final_title = llm_title if llm_title else (existing_title or _extract_title_fallback(raw_markdown))

        print(f"[metadata_extract] Title: {final_title[:80]}")
        print(f"[metadata_extract] Abstract: {len(abstract)} chars")
        print(f"[metadata_extract] Authors: {authors}")
        print(f"[metadata_extract] Keywords: {keywords}")
        print(f"[metadata_extract] Year: {year}")

        _safe_log(
            analysis_id, "metadata", "done",
            f"Metadata diekstrak — Title: \"{final_title[:60]}\" ({year or 'N/A'})",
        )

        return {
            "title": final_title,
            "abstract": abstract,
            "authors": authors,
            "keywords": keywords,
            "year": year,
            "document_head": document_head,
            "document_tail": document_tail,
        }

    except json.JSONDecodeError as exc:
        # Fallback: LLM mengembalikan format yang tidak bisa di-parse
        print(f"[metadata_extract] WARNING: JSON parse gagal: {exc}")
        fallback_title = existing_title or _extract_title_fallback(raw_markdown)
        _safe_log(
            analysis_id, "metadata", "done",
            f"Metadata: fallback (JSON parse error) — Title: \"{fallback_title[:60]}\"",
        )
        return {
            "title": fallback_title,
            "abstract": "",
            "authors": [],
            "keywords": [],
            "year": None,
            "document_head": document_head,
            "document_tail": document_tail,
        }

    except Exception as exc:
        # Fallback: error apapun (network, API key, dll)
        print(f"[metadata_extract] WARNING: LLM call gagal: {exc}")
        fallback_title = existing_title or _extract_title_fallback(raw_markdown)
        _safe_log(
            analysis_id, "metadata", "done",
            f"Metadata: fallback (error) — Title: \"{fallback_title[:60]}\"",
        )
        return {
            "title": fallback_title,
            "abstract": "",
            "authors": [],
            "keywords": [],
            "year": None,
            "document_head": document_head,
            "document_tail": document_tail,
        }
