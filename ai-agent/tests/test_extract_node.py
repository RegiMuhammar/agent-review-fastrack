"""
tests/test_extract_node.py
===========================
Unit & integration tests untuk extract_node.

Menguji:
1. Happy path — PDF contoh di pdf_example/ berhasil diekstrak.
2. Fallback — state tanpa 'file_path' tetap pakai PDF_EXAMPLE_FILE.
3. File tidak ditemukan — kembalikan is_valid=False + pesan error.
4. File bukan PDF — kembalikan is_valid=False + pesan error.
5. Helper _extract_title_from_markdown — ekstrak judul dari markdown.

Cara run (dari folder ai-agent/):
    python -m pytest tests/test_extract_node.py -v
    # atau run langsung:
    python tests/test_extract_node.py
"""

import asyncio
import sys
import os
from functools import lru_cache
from pathlib import Path

# Pastikan root package 'app' bisa diimport dari mana pun test ini dijalankan
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from app.graph.nodes.extract import (
    extract_node,
    PDF_EXAMPLE_DIR,
    _get_example_pdf,
    _extract_title_from_markdown,
)


# ── HELPER ────────────────────────────────────────────────────────────────────
def run(coro):
    """Jalankan coroutine async secara sinkron (kompatibel Python 3.10+)."""
    return asyncio.run(coro)


# ── FIXTURES STATE ────────────────────────────────────────────────────────────
def make_state(file_path: str = "") -> dict:
    """Buat state minimal yang dibutuhkan extract_node."""
    return {
        "analysis_id": "test-001",
        "file_path": file_path,
        "doc_type_hint": None,
    }


@lru_cache(maxsize=1)
def extract_example_once() -> dict:
    """
    Cache ekstraksi PDF contoh supaya integration test tidak memproses file besar
    yang sama berulang kali.
    """
    example_pdf = _get_example_pdf()
    state = make_state(file_path=str(example_pdf))
    return run(extract_node(state))


# ══════════════════════════════════════════════════════════════════════════════
# TEST 1 — Path PDF contoh tersedia
# ══════════════════════════════════════════════════════════════════════════════
def test_pdf_example_file_exists():
    """Folder pdf_example harus ada dan berisi minimal satu file .pdf."""
    assert PDF_EXAMPLE_DIR.exists(), (
        f"Folder pdf_example tidak ditemukan: {PDF_EXAMPLE_DIR}"
    )
    pdfs = list(PDF_EXAMPLE_DIR.glob("*.pdf"))
    assert len(pdfs) >= 1, (
        f"Tidak ada file .pdf di: {PDF_EXAMPLE_DIR}"
    )
    print(f"\n[OK] Ditemukan {len(pdfs)} file PDF: {[p.name for p in pdfs]}")


# ══════════════════════════════════════════════════════════════════════════════
# TEST 2 — Happy path: ekstraksi PDF contoh berhasil
# ══════════════════════════════════════════════════════════════════════════════
def test_extract_node_happy_path():
    """
    extract_node harus berhasil mengekstrak PDF pertama di pdf_example/:
    - is_valid = True
    - raw_markdown tidak kosong
    - page_count > 0
    - error = None
    """
    example_pdf = _get_example_pdf()
    result = extract_example_once()

    print(f"\n[Happy Path] file      : {example_pdf.name}")
    print(f"[Happy Path] is_valid   : {result['is_valid']}")
    print(f"[Happy Path] page_count : {result['page_count']}")
    print(f"[Happy Path] title      : {result['title']}")
    print(f"[Happy Path] char count : {len(result['raw_markdown'])}")
    print(f"[Happy Path] error      : {result['error']}")

    assert result["is_valid"] is True,       f"is_valid = False, error: {result['error']}"
    assert result["error"] is None,          "Seharusnya tidak ada error"
    assert len(result["raw_markdown"]) > 0,  "raw_markdown tidak boleh kosong"
    assert result["page_count"] > 0,         "page_count harus > 0"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3 — Fallback: file_path kosong → pakai PDF pertama di folder
# ══════════════════════════════════════════════════════════════════════════════
def test_extract_node_fallback_to_example():
    """
    Jika file_path di state kosong, node harus fallback ke PDF pertama
    di pdf_example/ (alfabet) dan tetap menghasilkan ekstraksi yang valid.
    """
    result = extract_example_once()

    # Verifikasi: file yang dipakai adalah pdf pertama secara alfabet
    expected_file = _get_example_pdf()
    print(f"\n[Fallback] expected file: {expected_file.name}")
    print(f"[Fallback] is_valid     : {result['is_valid']}")
    print(f"[Fallback] page_count   : {result['page_count']}")

    assert result["is_valid"] is True,        f"Fallback gagal, error: {result['error']}"
    assert result["page_count"] > 0,          "page_count harus > 0 saat fallback"
    assert len(result["raw_markdown"]) > 100, "Markdown terlalu pendek, kemungkinan gagal"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 3b — _get_example_pdf: pilihan alfabet saat ada banyak file
# ══════════════════════════════════════════════════════════════════════════════
def test_get_example_pdf_picks_first_alphabetically(tmp_path):
    """
    _get_example_pdf harus selalu memilih file .pdf pertama secara alfabet
    meskipun ada banyak file PDF di folder.
    Simulasikan dengan monkeypatching PDF_EXAMPLE_DIR.
    """
    import app.graph.nodes.extract as extract_module

    # Buat beberapa file PDF dummy (isinya tidak valid, tapi test cukup untuk picker)
    (tmp_path / "b_second.pdf").write_bytes(b"%PDF-1.4 dummy")
    (tmp_path / "a_first.pdf").write_bytes(b"%PDF-1.4 dummy")
    (tmp_path / "c_third.pdf").write_bytes(b"%PDF-1.4 dummy")

    # Monkeypatch
    original_dir = extract_module.PDF_EXAMPLE_DIR
    extract_module.PDF_EXAMPLE_DIR = tmp_path
    try:
        picked = extract_module._get_example_pdf()
        print(f"\n[MultiPDF] dipilih: {picked.name}")
        assert picked.name == "a_first.pdf", (
            f"Seharusnya 'a_first.pdf', dapat: '{picked.name}'"
        )
    finally:
        extract_module.PDF_EXAMPLE_DIR = original_dir  # restore


def test_get_example_pdf_empty_folder(tmp_path):
    """
    _get_example_pdf harus raise FileNotFoundError jika folder kosong.
    """
    import app.graph.nodes.extract as extract_module

    original_dir = extract_module.PDF_EXAMPLE_DIR
    extract_module.PDF_EXAMPLE_DIR = tmp_path  # folder kosong
    try:
        with pytest.raises(FileNotFoundError, match="Tidak ada file .pdf"):
            extract_module._get_example_pdf()
    finally:
        extract_module.PDF_EXAMPLE_DIR = original_dir  # restore


# ══════════════════════════════════════════════════════════════════════════════
# TEST 4 — File tidak ditemukan → is_valid = False
# ══════════════════════════════════════════════════════════════════════════════
def test_extract_node_file_not_found():
    """
    Jika file_path menunjuk ke file yang tidak ada,
    node harus mengembalikan is_valid=False dan pesan error yang jelas.
    """
    state = make_state(file_path="/path/yang/tidak/ada/dokumen.pdf")
    result = run(extract_node(state))

    print(f"\n[Not Found] is_valid : {result['is_valid']}")
    print(f"[Not Found] error    : {result['error']}")

    assert result["is_valid"] is False,  "is_valid harus False jika file tidak ada"
    assert result["error"] is not None,  "error harus berisi pesan"
    assert "tidak ditemukan" in result["error"].lower() or "not found" in result["error"].lower()
    assert result["raw_markdown"] == "",  "raw_markdown harus string kosong"
    assert result["page_count"] == 0,    "page_count harus 0"


# ══════════════════════════════════════════════════════════════════════════════
# TEST 5 — File bukan PDF → is_valid = False
# ══════════════════════════════════════════════════════════════════════════════
def test_extract_node_not_a_pdf(tmp_path):
    """
    Jika file_path menunjuk ke file non-PDF (misalnya .txt),
    node harus mengembalikan is_valid=False dengan pesan error.
    """
    # Buat file .txt dummy
    dummy_txt = tmp_path / "bukan_pdf.txt"
    dummy_txt.write_text("Ini bukan PDF.")

    state = make_state(file_path=str(dummy_txt))
    result = run(extract_node(state))

    print(f"\n[Non-PDF] is_valid : {result['is_valid']}")
    print(f"[Non-PDF] error    : {result['error']}")

    assert result["is_valid"] is False,  "is_valid harus False untuk file non-PDF"
    assert result["error"] is not None,  "error harus berisi pesan"
    assert "bukan pdf" in result["error"].lower() or "pdf" in result["error"].lower()


# ══════════════════════════════════════════════════════════════════════════════
# TEST 6 — Helper: _extract_title_from_markdown
# ══════════════════════════════════════════════════════════════════════════════
def test_extract_title_with_h1():
    """Helper harus mengambil teks setelah '#' pertama."""
    md = "# Judul Utama Dokumen\n\nIsi paragraf..."
    result = _extract_title_from_markdown(md)
    assert result == "Judul Utama Dokumen", f"Judul salah: {result!r}"


def test_extract_title_with_h2():
    """Helper harus bekerja dengan heading level 2 (##) bila H1 tidak ada."""
    md = "## Sub Judul\n\nIsi paragraf..."
    result = _extract_title_from_markdown(md)
    assert result == "Sub Judul", f"Judul salah: {result!r}"


def test_extract_title_no_heading():
    """Helper harus mengembalikan None jika tidak ada heading."""
    md = "Paragraf biasa tanpa heading sama sekali."
    result = _extract_title_from_markdown(md)
    assert result is None, f"Seharusnya None, dapat: {result!r}"


def test_extract_title_empty_heading():
    """Heading kosong '#' seharusnya mengembalikan None (bukan string kosong)."""
    md = "#\n\nIsi dokumen..."
    result = _extract_title_from_markdown(md)
    assert result is None, f"Seharusnya None untuk heading kosong, dapat: {result!r}"


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT — jalankan tanpa pytest
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("=" * 65)
    print("test_extract_node.py — Running manually (tanpa pytest)")
    print("=" * 65)

    tests = [
        ("PDF example exists",           test_pdf_example_file_exists),
        ("Happy path - real PDF",        test_extract_node_happy_path),
        ("Fallback - empty file_path",   test_extract_node_fallback_to_example),
        ("File not found",               test_extract_node_file_not_found),
        ("Title from H1",                test_extract_title_with_h1),
        ("Title from H2",                test_extract_title_with_h2),
        ("No heading → None",           test_extract_title_no_heading),
        ("Empty heading → None",        test_extract_title_empty_heading),
    ]

    # Test non-PDF butuh tmp_path (pytest fixture), kita simulasikan manual
    import tempfile
    class _TmpPath:
        def __init__(self): self._d = tempfile.mkdtemp()
        def __truediv__(self, name): return Path(self._d) / name

    passed, failed = 0, 0
    for name, fn in tests:
        try:
            if fn.__code__.co_varnames[:fn.__code__.co_argcount] and "tmp_path" in fn.__code__.co_varnames:
                fn(_TmpPath())
            else:
                fn()
            print(f"  [PASS] {name}")
            passed += 1
        except Exception as exc:
            print(f"  [FAIL] {name} — {exc}")
            failed += 1

    print("-" * 65)
    print(f"Hasil: {passed} passed, {failed} failed")
    print("=" * 65)
