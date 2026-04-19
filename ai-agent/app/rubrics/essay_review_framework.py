"""
essay_review_framework.py — Framework Evaluasi Essay
Berisi definisi Toulmin, Fallacy Scan, Academic Engagement, serta 6 dimensi Analytic Scoring.
"""

ESSAY_EVALUATION_FRAMEWORK = """### FRAMEWORK EVALUASI ESSAY

Gunakan tiga framework evaluasi berikut secara berurutan untuk menganalisis dokumen:

#### 1. Toulmin Model (Struktur Argumen)
Identifikasi klaim utama dalam esai. Untuk setiap klaim, evaluasi ketersediaan dan kualitas dari:
- **Claim**: Pernyataan/posisi yang ingin dibuktikan.
- **Evidence/Data**: Fakta atau data pendukung.
- **Warrant**: (FOKUS UTAMA) Asumsi atau alasan logis yang menghubungkan evidence dengan claim. Apakah eksplisit atau tersembunyi?
- **Backing**: Dukungan tambahan untuk warrant.
- **Qualifier**: Batasan atau nuansa argumen (misal: "sebagian besar", "dalam kondisi tertentu").
- **Rebuttal**: Respons terhadap kemungkinan bantahan.

#### 2. Logical Fallacy Scan
Deteksi keberadaan kecacatan nalar secara ketat (hanya flag jika teks menunjukkannya dengan sangat jelas). Fokus pada daftar tetap berikut:
- Strawman
- Ad Hominem
- False Dichotomy
- Hasty Generalization
- Slippery Slope
- Circular Reasoning
Jika tidak ada yang terdeteksi, abaikan dan jangan paksakan. 

#### 3. Academic Engagement
Evaluasi respons penulis terhadap pihak luar:
- **They Say**: Bagaimana naskah mengutip, memposisikan, atau mewakili pandangan/literatur lain.
- **I Say**: Posisi argumen orisinal dari penulis.
- Kehadiran **Counterargument** mandiri dan cara sanggahannya yang sopan namun tegas (bila ada).

---

### ANALYTIC SCORING (6 Dimensi)

Integrasikan hasil analisa Anda dari tiga framework di atas ke dalam narasi tanggapan (feedback) pada enam dimensi analitis ini:

1. **Thesis Clarity** (key: `thesis_clarity`, 20%) — Ketajaman klaim utama (Toulmin Claim).
2. **Argument Coherence** (key: `argument_coherence`, 25%) — Hubungan logis (Toulmin Warrant/Backing), ketiadaan kesalahan logika (Fallacy Scan).
3. **Evidence Quality** (key: `evidence_quality`, 20%) — Kualitas dan relevansi data empiris atau konseptual pendukung awal.
4. **Structure & Organization** (key: `structure_organization`, 15%) — Organisasi paragraf, alur naratif khas essay, pembuka-isi-penutup.
5. **Writing Style & Clarity** (key: `writing_style_clarity`, 10%) — Gaya bahasa artikulatif, tanpa jargon rumit.
6. **Citation & Academic Integrity** (key: `citation_integrity`, 10%) — Penggunaan sumber eksternal untuk memperkuat poin, membedakan kutipan ('They Say') dengan opini ('I Say').

### FORMAT OUTPUT & BAHASA (BILINGUAL)
Output HARUS JSON murni, TANPA markdown text.
Gunakan label dua bahasa pada atribut nama dan deskripsi, contoh bahasa standar:
"Nama Atribut (English Name)" atau "Penjelasan [ID]. Explanation [EN]."
Gabungkan umpan balik dalam format bilingual (indonesia, lalu dipisah paragraf/titik untuk english).

Contoh Format JSON Valid:
{
  "dimensions": [
    {
      "key": "thesis_clarity",
      "name": "Kejelasan Tesis / Thesis Clarity",
      "weight": 0.2,
      "score": 8.0,
      "feedback": "Tesis dinyatakan dengan cukup baik. ... [EN] The thesis is stated fairly well. ..."
    },
    {
      "key": "argument_coherence",
      "name": "Koherensi Argumen / Argument Coherence",
      "weight": 0.25,
      "score": 7.5,
      "feedback": "Bebas dari fallacy, warrant logis. [EN] Free of fallacies, logical warrant."
    },
    ... (lengkapi 6 dimensi dengan key yang tepat sesuai di atas) ...
  ],
  "overall_feedback": "Tinjauan Keseluruhan... [EN] Overall review...",
  "summary": "Ringkasan Eksekutif... [EN] Executive summary...",
  "strengths": [
    "Kekuatan 1 [ID] / Strength 1 [EN]",
    "Kekuatan 2 [ID] / Strength 2 [EN]",
    "Kekuatan 3 [ID] / Strength 3 [EN]"
  ],
  "improvements": [
    "Saran 1 [ID] / Advice 1 [EN] — Prioritas tinggi",
    "Saran 2 [ID] / Advice 2 [EN]",
    "Saran 3 [ID] / Advice 3 [EN]"
  ]
}
"""
