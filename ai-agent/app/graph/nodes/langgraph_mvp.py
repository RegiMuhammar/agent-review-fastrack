"""
LangGraph MVP — Proof of Concept
=================================
Mini graph sederhana yang mengevaluasi konten markdown essay pendek
menggunakan LLM (Groq) dan mengembalikan hasil evaluasi sebagai
structured output (Pydantic) — dijamin valid JSON, tanpa text tambahan.

Cara run:
    cd ai-agent
    python -m app.graph.nodes.langgraph_mvp
"""

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from pydantic import BaseModel, Field
from typing import Literal, TypedDict
from langgraph.graph import StateGraph, START, END
from app.prompts.essay import ESSAY_SYSTEM_PROMPT

import json

# ── ENV & LLM ────────────────────────────────────────────────────────
load_dotenv()

llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)


# ── PYDANTIC MODELS (Structured Output) ─────────────────────────────
class DimensionScore(BaseModel):
    """Skor untuk satu dimensi evaluasi."""
    key: str = Field(description="Key identifier dimensi, misal: tesis_argumen")
    name: str = Field(description="Nama dimensi, misal: Tesis & Argumen")
    score: float = Field(description="Skor 1-10 untuk dimensi ini", ge=1, le=10)
    weight: float = Field(description="Bobot dimensi (0-1), misal: 0.25")
    feedback: str = Field(description="Feedback konstruktif untuk dimensi ini")


class EssayEvaluation(BaseModel):
    """Hasil evaluasi lengkap sebuah essay."""
    dimensions: list[DimensionScore] = Field(
        description="Daftar skor per dimensi evaluasi"
    )
    overall_feedback: str = Field(
        description="Feedback keseluruhan tentang essay"
    )
    summary: str = Field(
        description="Ringkasan singkat isi essay"
    )
    strengths: list[str] = Field(
        description="Daftar kekuatan essay"
    )
    improvements: list[str] = Field(
        description="Daftar saran perbaikan essay"
    )


# ── LLM with Structured Output ──────────────────────────────────────
# .with_structured_output() memaksa LLM mengembalikan HANYA JSON
# yang sesuai schema Pydantic — tidak ada text tambahan sama sekali.
structured_llm = llm.with_structured_output(EssayEvaluation)


# ── STATE ────────────────────────────────────────────────────────────
class MvpState(TypedDict):
    """State minimal untuk POC."""
    markdown_content: str                                  # isi essay markdown
    doc_type: Literal["essay", "research", "bizplan"]      # tipe dokumen
    evaluation_result: dict                                # hasil evaluasi (dict, bukan str lagi)


# ── NODES ────────────────────────────────────────────────────────────
def essay_evaluator_node(state: MvpState) -> dict:
    """Node yang mengevaluasi essay menggunakan structured LLM output."""
    print("\n[essay_evaluator_node] Memulai evaluasi essay...")

    markdown_content = state["markdown_content"]
    doc_type = state["doc_type"]

    # Bangun messages untuk LLM
    messages = [
        SystemMessage(content=ESSAY_SYSTEM_PROMPT),
        HumanMessage(content=(
            f"Tipe Dokumen: {doc_type}\n\n"
            f"--- KONTEN ESSAY ---\n\n"
            f"{markdown_content}\n\n"
            f"--- AKHIR KONTEN ---\n\n"
            f"Evaluasi essay di atas berdasarkan rubrik yang sudah ditentukan."
        )),
    ]

    # Panggil structured LLM — langsung return Pydantic object
    result: EssayEvaluation = structured_llm.invoke(messages)

    print("[essay_evaluator_node] Evaluasi selesai!")

    # Convert Pydantic model ke dict untuk disimpan di state
    return {"evaluation_result": result.model_dump()}


# ── GRAPH BUILDER ────────────────────────────────────────────────────
def build_mvp_graph():
    """Membangun dan meng-compile graph MVP."""
    graph_builder = StateGraph(MvpState)

    # Tambah node
    graph_builder.add_node("essay_evaluator", essay_evaluator_node)

    # Tambah edge: START -> essay_evaluator -> END
    graph_builder.add_edge(START, "essay_evaluator")
    graph_builder.add_edge("essay_evaluator", END)

    # Compile
    graph = graph_builder.compile()
    return graph


# ── SAMPLE INPUT ─────────────────────────────────────────────────────
SAMPLE_ESSAY = """
# Dampak Kecerdasan Buatan terhadap Dunia Pendidikan

## Pendahuluan

Kecerdasan buatan (AI) telah mengalami perkembangan pesat dalam dekade terakhir.
Teknologi ini tidak hanya mengubah industri manufaktur dan kesehatan, tetapi juga
merambah ke dunia pendidikan. Essay ini mengargumentasikan bahwa AI memiliki potensi
besar untuk meningkatkan kualitas pendidikan, namun diperlukan regulasi yang tepat
agar manfaatnya dapat dirasakan secara merata.

## Argumen Utama

### Personalisasi Pembelajaran

AI memungkinkan terciptanya sistem pembelajaran yang adaptif. Platform seperti
Khan Academy dan Duolingo telah menggunakan algoritma machine learning untuk
menyesuaikan materi dengan kemampuan masing-masing siswa. Menurut penelitian
Holmes et al. (2019), siswa yang belajar dengan sistem adaptif menunjukkan
peningkatan prestasi sebesar 30% dibandingkan metode konvensional.

### Efisiensi Administratif

Proses administratif seperti penilaian, absensi, dan penjadwalan dapat diotomatisasi
menggunakan AI. Hal ini membebaskan waktu guru untuk fokus pada interaksi langsung
dengan siswa. Sebuah studi oleh McKinsey (2020) menunjukkan bahwa otomatisasi dapat
menghemat hingga 20 jam kerja guru per bulan.

### Tantangan dan Risiko

Meskipun menjanjikan, penerapan AI dalam pendidikan juga memiliki tantangan.
Kesenjangan digital antara daerah perkotaan dan pedesaan dapat memperlebar
ketimpangan akses pendidikan. Selain itu, ketergantungan berlebihan pada teknologi
dapat mengurangi kemampuan berpikir kritis siswa.

## Kesimpulan

AI memiliki potensi transformatif dalam dunia pendidikan. Namun, penerapannya harus
disertai dengan kebijakan yang inklusif dan pelatihan yang memadai bagi para pendidik.
Dengan pendekatan yang tepat, AI dapat menjadi katalis untuk menciptakan sistem
pendidikan yang lebih adil dan efektif.

## Referensi

- Holmes, W., et al. (2019). *Artificial Intelligence in Education*. Springer.
- McKinsey & Company. (2020). *How AI Can Help Teachers*.
"""


# ── MAIN (untuk testing langsung) ────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("LangGraph MVP -- Essay Evaluator POC (Structured Output)")
    print("=" * 60)

    # Build graph
    graph = build_mvp_graph()

    # Input state
    input_state = {
        "markdown_content": SAMPLE_ESSAY,
        "doc_type": "essay",
    }

    print(f"\n[Doc Type] : {input_state['doc_type']}")
    print(f"[Essay]    : {SAMPLE_ESSAY[:80].strip()}...")
    print("-" * 60)

    # Invoke graph
    result = graph.invoke(input_state)

    # Print hasil — sudah pasti dict, langsung pretty print
    print("\n" + "=" * 60)
    print("HASIL EVALUASI (Structured Output):")
    print("=" * 60)

    evaluation = result["evaluation_result"]
    print(json.dumps(evaluation, indent=2, ensure_ascii=False))

    # Hitung weighted score
    total = sum(d["score"] * d["weight"] for d in evaluation["dimensions"])
    print(f"\n[SKOR AKHIR] : {total:.2f} / 10")

    print(f"[TYPE]       : {type(evaluation).__name__}")
    print("[DONE] MVP Proof of Concept selesai!")