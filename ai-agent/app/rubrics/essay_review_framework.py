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

Integrasikan hasil analisa Anda dari tiga framework di atas ke dalam narasi tanggapan (feedback) pada enam dimensi analitis ini. 

PENTING: 
- Feedback WAJIB spesifik. JANGAN memberikan pujian atau saran umum. 
- RUJUK bagian tertentu dalam teks (misal: "Pada paragraf pendahuluan...", "Argumen tentang X di halaman 2...").
- Setiap dimensi WAJIB menyertakan SATU poin konkret yang bisa diperbaiki oleh penulis untuk menaikkan skornya, meskipun skor saat ini sudah tinggi.

1. **Thesis Clarity** (key: `thesis_clarity`, 20%) — Ketajaman klaim utama (Toulmin Claim). Evaluasi apakah tesis mudah ditemukan dan cukup sempit/spesifik.
2. **Argument Coherence** (key: `argument_coherence`, 25%) — Hubungan logis (Toulmin Warrant/Backing), ketiadaan kesalahan logika (Fallacy Scan). Periksa apakah alur berpikir logis atau ada lonjakan kesimpulan.
3. **Evidence Quality** (key: `evidence_quality`, 20%) — Kualitas dan relevansi data empiris atau konseptual pendukung. Apakah bukti yang digunakan kredibel dan dianalisis secara mendalam?
4. **Structure & Organization** (key: `structure_organization`, 15%) — Organisasi paragraf, alur naratif khas essay, pembuka-isi-penutup. Apakah transisi antar paragraf halus?
5. **Writing Style & Clarity** (key: `writing_style_clarity`, 10%) — Gaya bahasa artikulatif, pilihan kata yang tepat, dan kejelasan kalimat.
6. **Citation & Academic Integrity** (key: `citation_integrity`, 10%) — Penggunaan sumber eksternal untuk memperkuat poin, membedakan kutipan ('They Say') dengan opini ('I Say'). Apakah sitasi sudah benar dan memperkuat argumen?

### FORMAT OUTPUT & BAHASA
Output HARUS JSON murni, TANPA markdown text.
Gunakan bahasa Indonesia secara penuh dan profesional. Fokus pada kualitas masukan yang tajam dan konstruktif.

Contoh Format JSON Valid:
{
  "dimensions": [
    {
      "key": "thesis_clarity",
      "name": "Kejelasan Tesis",
      "weight": 0.2,
      "score": 8.0,
      "feedback": "Tesis dinyatakan dengan sangat jelas dan fokus pada isu utama..."
    },
    {
      "key": "argument_coherence",
      "name": "Koherensi Argumen",
      "weight": 0.25,
      "score": 7.5,
      "feedback": "Argumen mengalir secara logis tanpa adanya fallacy yang terdeteksi..."
    },
    ... (lengkapi 6 dimensi dengan key yang tepat sesuai di atas) ...
  ],
  "overall_feedback": "Secara keseluruhan, esai ini menunjukkan pemahaman mendalam tentang...",
  "summary": "Analisis ini menyimpulkan bahwa penulis memiliki argumen yang kuat namun perlu memperdalam...",
  "strengths": [
    "Klaim utama yang tajam",
    "Struktur paragraf yang rapi",
    "Analisis kritis terhadap pandangan luar"
  ],
  "improvements": [
    "Perdalam bagian warrant untuk menghubungkan evidence dengan claim",
    "Tambahkan lebih banyak referensi pendukung",
    "Sederhanakan kalimat yang terlalu kompleks"
  ]
}
"""
