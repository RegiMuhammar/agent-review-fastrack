BIZPLAN_EVALUATION_FRAMEWORK = """### FRAMEWORK EVALUASI BUSINESS PLAN

Gunakan framework evaluasi bisnis berikut untuk menganalisis dokumen:

#### 1. Value Proposition & Problem-Solution Fit
Evalusi apakah masalah yang diangkat nyata dan mendesak. Apakah solusi yang ditawarkan unik dan memberikan nilai tambah yang jelas dibanding kompetitor?

#### 2. Market Analysis & Target Audience
Analisis apakah pasar yang dituju cukup besar (TAM/SAM/SOM). Apakah ada bukti riset pasar yang kuat atau hanya asumsi?

#### 3. Business Model & Revenue Stream
Evaluasi cara bisnis menghasilkan uang. Apakah model bisnisnya berkelanjutan (sustainable) dan masuk akal (feasible)?

#### 4. Competitive Landscape
Evaluasi pemahaman penulis terhadap kompetitor. Apakah ada strategi defensif (moat) yang jelas?

---

### ANALYTIC SCORING (6 Dimensi)

PENTING: 
- Feedback WAJIB spesifik. JANGAN memberikan pujian atau saran umum. 
- RUJUK bagian tertentu dalam dokumen (misal: "Proyeksi keuangan di tahun ke-2...", "Analisis kompetitor di bagian pasar...").
- Setiap dimensi WAJIB menyertakan SATU poin konkret yang bisa diperbaiki oleh penulis untuk menaikkan skornya.

1. **Problem & Solution** (key: `problem_solution`, 25%) — Validasi masalah dan ketajaman solusi.
2. **Market Size & Opportunity** (key: `market_size`, 20%) — Analisis potensi pasar dan segmentasi pelanggan.
3. **Business Model** (key: `business_model`, 20%) — Kelayakan cara monetisasi dan strategi harga.
4. **Competitive Advantage** (key: `competitive`, 15%) — Keunikan dan daya saing di pasar.
5. **Team & Execution** (key: `team`, 10%) — Rencana operasional dan kapabilitas tim (jika disebutkan).
6. **Financial Feasibility** (key: `financial`, 10%) — Logika di balik angka dan proyeksi pertumbuhan.

### FORMAT OUTPUT & BAHASA
Output HARUS JSON murni, TANPA markdown text.
Gunakan bahasa Indonesia secara penuh dan profesional.

Contoh Format JSON Valid:
{
  "dimensions": [
    {
      "key": "problem_solution",
      "name": "Masalah & Solusi",
      "weight": 0.25,
      "score": 8.0,
      "feedback": "Masalah yang diangkat sangat nyata, namun solusi X yang dijelaskan pada halaman 3 masih terlalu abstrak dalam hal implementasi teknis..."
    },
    ...
  ],
  "overall_feedback": "Rencana bisnis ini memiliki fundamental yang kuat pada bagian Y, namun sangat lemah pada...",
  "summary": "Ringkasan eksekutif tentang kelayakan bisnis...",
  "strengths": ["Prinsip unik dalam produk X", "Analisis pasar TAM yang detail"],
  "improvements": ["Lengkapi proyeksi arus kas mendalam", "Detailkan strategi akuisisi pelanggan (CAC)"]
}
"""
