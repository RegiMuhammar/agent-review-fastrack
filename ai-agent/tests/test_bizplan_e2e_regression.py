import asyncio
import json
from pathlib import Path

import fitz

from app.graph.builder import review_pipeline


def _build_bizplan_pdf_bytes() -> bytes:
    doc = fitz.open()

    page1 = doc.new_page()
    text1 = """EduCycle
Company Name: EduCycle
Industry: Education technology, circular economy, SaaS
Geography: Indonesia
Business Stage: Seed
Funding Ask: IDR 4.8 miliar untuk 18 bulan runway
Target Customer: sustainability office kampus, koperasi kampus, universitas swasta menengah

Problem
Kampus kesulitan mengelola sirkulasi buku bekas, pelaporan dampak, dan engagement mahasiswa.

Solution
EduCycle menyediakan smart kiosk dan dashboard SaaS untuk circular campus operations.

Market
TAM diperkirakan Rp 7.2 triliun per tahun dari 4.600 institusi pendidikan.
Pilot traction: 12 campus pilots dan 18.400 users.
"""
    page1.insert_textbox(fitz.Rect(40, 40, 555, 770), text1, fontsize=11)

    page2 = doc.new_page()
    text2 = """Business Model
Subscription: paket Starter Rp 7.500.000 per tahun, Growth Rp 18.000.000, Enterprise Rp 45.000.000.
Commission: 8% transaction fee dari sponsor reward dan marketplace buku bekas.
Setup fee: Rp 6.000.000 untuk instalasi awal kiosk dan training.
License: dashboard analytics tambahan Rp 1.500.000 per bulan untuk kampus multi-faculty.
Pricing benchmark menunjukkan kampus bersedia membayar Rp 15.000.000 sampai Rp 25.000.000 per tahun untuk dashboard compliance.

Financial
CAC: Rp 3.200.000
LTV: Rp 28.800.000
Burn Rate: Rp 215.000.000 per bulan.
Runway: 18 bulan.
Break-even: bulan ke-20.
Financial Red Flag yang masih dipantau: kebutuhan modal kerja bisa naik jika sponsor reimbursement melambat lebih dari 45 hari.
"""
    page2.insert_textbox(fitz.Rect(40, 40, 555, 770), text2, fontsize=11)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


class _FakeDownloadResponse:
    def __init__(self, content: bytes):
        self.content = content

    def raise_for_status(self) -> None:
        return None


class _FakeAsyncClient:
    def __init__(self, *args, **kwargs):
        self._content = _build_bizplan_pdf_bytes()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url: str, headers=None):
        return _FakeDownloadResponse(self._content)


class _FakeMessage:
    def __init__(self, content: str):
        self.content = content


class _FakeMetadataLLM:
    def __init__(self, *args, **kwargs):
        pass

    async def ainvoke(self, messages):
        payload = {
            "title": "EduCycle",
            "abstract": "",
            "authors": [],
            "keywords": ["education technology", "campus sustainability", "saas"],
            "year": 2026,
        }
        return _FakeMessage(json.dumps(payload))


class _FakeScoreLLM:
    def __init__(self, *args, **kwargs):
        pass

    async def ainvoke(self, messages):
        payload = {
            "summary": "Business plan kuat dengan pricing yang jelas dan risiko modal kerja yang teridentifikasi.",
            "overall_feedback": "Layak dilanjutkan dengan penguatan validasi pasar dan mitigasi eksekusi.",
            "dimensions": [
                {
                    "key": "problem_solution",
                    "label": "Masalah & Solusi",
                    "score": 8.6,
                    "feedback": "Masalah yang diangkat nyata dan solusi cukup terukur. Namun, implementasi di kampus mitra masih perlu diperinci.",
                },
                {
                    "key": "market_size",
                    "label": "Ukuran Pasar",
                    "score": 7.8,
                    "feedback": "Ukuran pasar terlihat menarik. Namun, validasi konversi dari pilot ke kontrak berbayar masih perlu diperdalam.",
                },
                {
                    "key": "business_model",
                    "label": "Model Bisnis",
                    "score": 8.1,
                    "feedback": "Skema pendapatan terlihat jelas dan berlapis.",
                },
                {
                    "key": "competitive",
                    "label": "Keunggulan Kompetitif",
                    "score": 7.4,
                    "feedback": "Posisi kompetitif cukup menarik. Namun, pembeda defensible moat masih perlu ditegaskan.",
                },
                {
                    "key": "team",
                    "label": "Kesiapan Eksekusi",
                    "score": 6.7,
                    "feedback": "Tim memiliki pengalaman relevan. Namun, rencana kapasitas operasional lintas kota masih perlu diperjelas.",
                },
                {
                    "key": "financial",
                    "label": "Kesehatan Finansial",
                    "score": 7.5,
                    "feedback": "Asumsi finansial cukup lengkap. Namun, risiko modal kerja dari reimbursement sponsor perlu dimitigasi lebih eksplisit.",
                },
            ],
        }
        return _FakeMessage(json.dumps(payload))


async def _noop_log_step(*args, **kwargs):
    return None


def test_bizplan_review_pipeline_end_to_end_with_stubbed_dependencies(monkeypatch, tmp_path: Path):
    import app.graph.nodes.extract as extract_module
    import app.graph.nodes.metadata_extract as metadata_module
    import app.graph.nodes.score as score_module
    import app.graph.nodes.search_execute as search_execute_module
    import app.graph.nodes.bizplan_document_profile as bizplan_profile_module
    import app.services.laravel_client as laravel_client_module

    monkeypatch.setattr(extract_module.httpx, "AsyncClient", _FakeAsyncClient)
    monkeypatch.setattr(metadata_module, "ChatGroq", _FakeMetadataLLM)
    monkeypatch.setattr(score_module, "ChatGroq", _FakeScoreLLM)
    monkeypatch.setattr(laravel_client_module, "log_step", _noop_log_step)
    monkeypatch.setattr(bizplan_profile_module, "log_step", _noop_log_step)

    monkeypatch.setattr(search_execute_module, "search_semanticscholar", lambda queries, max_results: [])
    monkeypatch.setattr(search_execute_module, "search_arxiv", lambda queries, max_results: [])
    monkeypatch.setattr(
        search_execute_module,
        "search_tavily",
        lambda queries, max_results: [
            {
                "source": "tavily",
                "title": "Indonesia edtech market growth report",
                "url": "https://example.com/edtech-market",
                "snippet": "Indonesia's education technology market continues to expand as universities digitize student services and campus operations.",
                "relevance_score": 0.7,
                "year": 2025,
                "authors": [],
            },
            {
                "source": "tavily",
                "title": "Campus sustainability software competitors in Southeast Asia",
                "url": "https://example.com/campus-saas",
                "snippet": "University-focused sustainability and operations SaaS vendors compete on analytics, reporting, and implementation depth.",
                "relevance_score": 0.7,
                "year": 2025,
                "authors": [],
            },
            {
                "source": "tavily",
                "title": "University software pricing benchmark Indonesia",
                "url": "https://example.com/pricing",
                "snippet": "Annual SaaS contracts for Indonesian universities vary by module count, implementation scope, and campus size.",
                "relevance_score": 0.7,
                "year": 2025,
                "authors": [],
            },
        ],
    )

    result = asyncio.run(
        review_pipeline.ainvoke(
            {
                "analysis_id": "bizplan-e2e-regression",
                "file_url": "https://example.test/business-plan.pdf",
                "doc_type": "bizplan",
            }
        )
    )
    final_result = result["final_result"]

    assert final_result["doc_type"] == "bizplan"
    assert final_result["business_snapshot"]["company_name"] == "EduCycle"
    assert final_result["business_snapshot"]["industry"] == "Pendidikan"
    assert final_result["business_snapshot"]["funding_ask"] == "IDR 4.8 miliar untuk 18 bulan runway"
    assert final_result["market_validation"]["status"] == "validated"
    assert len(final_result["references"]) == 3

    pricing = " | ".join(final_result["financial_metrics"]["pricing"])
    assert "Subscription: paket Starter" in pricing
    assert "TAM diperkirakan" not in pricing
    assert "Burn Rate" not in pricing

    red_flags = " | ".join(final_result["financial_red_flags"])
    assert "reimbursement" in red_flags.lower()
    assert "modal kerja" in red_flags.lower()

    improvements = " | ".join(final_result["improvements"])
    assert "validasi" in improvements.lower() or "perlu" in improvements.lower()
