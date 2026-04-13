# -*- coding: utf-8 -*-
"""
scripts/preview_extraction.py
==============================
Script cepat untuk melihat hasil ekstraksi markdown dari PDF contoh.
Output disimpan ke: scripts/output_preview.md  → bisa dibuka di VS Code.

Cara run (dari folder ai-agent/):
    uv run python scripts/preview_extraction.py
"""

import asyncio
import io
import json
import sys
from pathlib import Path

# Fix Windows terminal encoding (cp1252 → utf-8)
if sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Tambah root ke path agar import 'app' bisa bekerja
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.graph.nodes.extract import extract_node, _get_example_pdf

OUTPUT_FILE = Path(__file__).parent / "output_preview.md"


async def main():
    pdf = _get_example_pdf()
    print(f"Mengekstrak: {pdf.name}")
    print("Mohon tunggu...")

    state = {"analysis_id": "preview", "file_path": str(pdf)}
    result = await extract_node(state)

    if not result["is_valid"]:
        print(f"\n[ERROR] Ekstraksi gagal: {result['error']}")
        return

    markdown = result["raw_markdown"]

    # ── Simpan ke file ──────────────────────────────────────────
    OUTPUT_FILE.write_text(markdown, encoding="utf-8")

    # ── Ringkasan di terminal ───────────────────────────────────
    sep = "=" * 60
    print(f"\n{sep}")
    print("  RAW STATE RETURN (Data untuk Node Berikutnya):")
    print(f"{sep}")
    
    # Buat copy result tanpa raw_markdown yang super panjang agar tidak memenuhi layar
    print_res = result.copy()
    print_res["raw_markdown"] = f"{len(markdown):,} characters (hidden in preview)"
    print(json.dumps(print_res, indent=4))
    
    print(f"\n{sep}")
    print(f"  KONTEKSTUAL:")
    print(f"  File    : {pdf.name}")
    print(sep)
    print("\n[Preview - 500 karakter pertama]\n")
    print(markdown[:500])
    print(f"\n{'-'*60}")
    print(f"Output lengkap disimpan ke:\n  {OUTPUT_FILE}")
    print(sep)


if __name__ == "__main__":
    asyncio.run(main())
