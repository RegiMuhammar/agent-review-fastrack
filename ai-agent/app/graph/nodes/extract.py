"""
extract.py — PDF Extraction Node
==================================
Node pertama dalam LangGraph pipeline.
Menerima file_url dari Laravel, mendownload PDF, mengekstrak kontennya
menjadi Markdown menggunakan pymupdf4llm, lalu menyimpan hasilnya ke state.

doc_type sudah diberikan oleh user saat upload di Laravel,
sehingga agent dapat langsung memproses dokumen berdasarkan tipenya.

Flow: extract → (validate) → agent → score → generate
"""

import os
import time
import tempfile
import httpx
from pathlib import Path
import pymupdf4llm
import fitz  # PyMuPDF — sudah terinstall bersama pymupdf4llm

from app.graph.state import ReviewEngineState
from app.core.config import settings

# ── HELPER ───────────────────────────────────────────────────────────────────
def _extract_title_from_markdown(markdown: str) -> str | None:
    """
    Coba ambil judul dari baris pertama yang diawali '#' di markdown.
    Kembalikan None jika tidak ditemukan.
    """
    for line in markdown.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.lstrip("#").strip() or None
    return None


def _coerce_bool(value: object, default: bool) -> bool:
    """
    Ubah nilai state / env menjadi bool dengan fallback yang aman.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _should_use_ocr(state: ReviewEngineState) -> bool:
    """
    OCR dimatikan secara default karena jauh lebih lambat pada PDF yang
    sebenarnya sudah memiliki text layer. Bisa dioverride via state atau env.
    """
    state_value = state.get("extract_use_ocr")
    env_value = os.getenv("EXTRACT_USE_OCR")
    if state_value is not None:
        return _coerce_bool(state_value, default=False)
    return _coerce_bool(env_value, default=False)


def _should_force_ocr(state: ReviewEngineState) -> bool:
    """
    Aktifkan OCR penuh jika caller memang meminta akurasi maksimum.
    """
    state_value = state.get("extract_force_ocr")
    env_value = os.getenv("EXTRACT_FORCE_OCR")
    if state_value is not None:
        return _coerce_bool(state_value, default=False)
    return _coerce_bool(env_value, default=False)


def _needs_ocr_fallback(markdown: str, page_count: int) -> bool:
    """
    Tentukan apakah hasil ekstraksi awal terlalu tipis sehingga layak dicoba
    ulang dengan OCR.
    """
    stripped = markdown.strip()
    if not stripped:
        return True

    text_len = len(stripped)
    min_chars = max(80, page_count * 40)
    return text_len < min_chars


def _safe_log(analysis_id: str, step: str, status: str, message: str) -> None:
    """
    Panggil log_step ke Laravel secara best-effort (fire-and-forget sync).
    Tidak raise error jika Laravel tidak bisa dihubungi — supaya node tetap jalan
    saat testing lokal tanpa backend Laravel.
    """
    try:
        import asyncio
        from app.services.laravel_client import log_step

        # Kalau sudah ada event loop yang running (misalnya di dalam async context),
        # kita buat task. Kalau tidak ada loop, kita run langsung.
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(log_step(analysis_id, step, status, message))
        except RuntimeError:
            asyncio.run(log_step(analysis_id, step, status, message))
    except Exception as exc:
        print(f"[extract_node][log_step] Best-effort log gagal (diabaikan): {exc}")


# ── NODE UTAMA ────────────────────────────────────────────────────────────────
async def extract_node(state: ReviewEngineState) -> dict:
    """
    LangGraph node: Ekstraksi PDF → Markdown.

    Input dari state:
        - file_url   : URL file PDF dari Laravel signed URL.
        - analysis_id: ID analisis (untuk logging ke Laravel).

    Output (di-merge ke state):
        - raw_markdown : isi dokumen dalam format Markdown.
        - page_count   : jumlah halaman PDF.
        - title        : judul dokumen (best-guess dari heading pertama).
        - is_valid     : True jika ekstraksi berhasil & konten tidak kosong.
        - error        : pesan error jika gagal, None jika sukses.
    """
    analysis_id: str = state["analysis_id"]

    # 1. Tentukan URL file PDF
    file_url: str = state.get("file_url", "")

    print(f"\n[extract_node] Memulai ekstraksi PDF...")
    print(f"[extract_node] URL: {file_url}")

    if not file_url:
        err = "URL file tidak tersedia di state"
        print(f"[extract_node] ERROR: {err}")
        _safe_log(analysis_id, "extract", "error", err)
        return {
            "raw_markdown": "",
            "page_count": 0,
            "title": None,
            "is_valid": False,
            "error": err,
        }

    _safe_log(analysis_id, "extract", "running", "Mendownload file PDF...")

    # 2. Download file dari Laravel
    headers = {"X-Internal-Key": settings.INTERNAL_KEY}
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(file_url, headers=headers)
            resp.raise_for_status()
    except Exception as exc:
        err = f"Gagal mendownload PDF dari URL: {exc}"
        print(f"[extract_node] ERROR: {err}")
        _safe_log(analysis_id, "extract", "error", err)
        return {
            "raw_markdown": "",
            "page_count": 0,
            "title": None,
            "is_valid": False,
            "error": err,
        }

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(resp.content)
        pdf_path = Path(tmp.name)

    try:

        # 3. Baca jumlah halaman dulu (via PyMuPDF langsung)
        try:
            with fitz.open(str(pdf_path)) as doc:
                page_count: int = len(doc)
        except Exception as exc:
            err = f"Gagal membuka PDF: {exc}"
            print(f"[extract_node] ERROR: {err}")
            _safe_log(analysis_id, "extract", "error", err)
            return {
                "raw_markdown": "",
                "page_count": 0,
                "title": None,
                "is_valid": False,
                "error": err,
            }

        # 4. Ekstraksi ke Markdown menggunakan pymupdf4llm
        prefer_ocr = _should_use_ocr(state)
        force_ocr = _should_force_ocr(state)
        started_at = time.perf_counter()
        try:
            raw_markdown: str = pymupdf4llm.to_markdown(
                str(pdf_path),
                use_ocr=prefer_ocr or force_ocr,
                show_progress=False,
            )
        except Exception as exc:
            err = f"Gagal mengekstrak markdown: {exc}"
            print(f"[extract_node] ERROR: {err}")
            _safe_log(analysis_id, "extract", "error", err)
            return {
                "raw_markdown": "",
                "page_count": page_count,
                "title": None,
                "is_valid": False,
                "error": err,
            }

        ocr_used = prefer_ocr or force_ocr
        if not force_ocr and not prefer_ocr and _needs_ocr_fallback(raw_markdown, page_count):
            print("[extract_node] Hasil ekstraksi tipis, mencoba ulang dengan OCR...")
            try:
                raw_markdown = pymupdf4llm.to_markdown(
                    str(pdf_path),
                    use_ocr=True,
                    show_progress=False,
                )
                ocr_used = True
            except Exception as exc:
                err = f"Gagal fallback OCR: {exc}"
                print(f"[extract_node] ERROR: {err}")
                _safe_log(analysis_id, "extract", "error", err)
                return {
                    "raw_markdown": "",
                    "page_count": page_count,
                    "title": None,
                    "is_valid": False,
                    "error": err,
                }

        # 5. Validasi konten tidak kosong
        if not raw_markdown.strip():
            err = (
                "PDF berhasil dibaca tapi tidak mengandung teks "
                "(mungkin scan/gambar; coba aktifkan OCR)."
            )
            print(f"[extract_node] WARNING: {err}")
            _safe_log(analysis_id, "extract", "error", err)
            return {
                "raw_markdown": raw_markdown,
                "page_count": page_count,
                "title": None,
                "is_valid": False,
                "error": err,
            }

        # 6. Ekstrak judul dari heading pertama di markdown
        title: str | None = _extract_title_from_markdown(raw_markdown)
        elapsed = time.perf_counter() - started_at

        print(
            f"[extract_node] Selesai! Halaman: {page_count} | "
            f"OCR: {'on' if ocr_used else 'off'} | "
            f"Durasi: {elapsed:.2f}s | Judul: {title or '-'}"
        )
        print(f"[extract_node] Panjang markdown: {len(raw_markdown)} karakter")

        _safe_log(
            analysis_id,
            "extract",
            "done",
            f"Ekstraksi selesai — {page_count} halaman, {len(raw_markdown)} karakter",
        )

        return {
            "raw_markdown": raw_markdown,
            "page_count": page_count,
            "title": title,
            "is_valid": True,
            "error": None,
        }
    finally:
        if pdf_path.exists():
            try:
                os.remove(pdf_path)
            except OSError as e:
                print(f"[extract_node] WARNING: Gagal menghapus file temporari {pdf_path}: {e}")
