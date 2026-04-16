# Adaptasi `essay_reviewer` ke `ai-review-engine`

Dokumen ini merangkum cara mengadaptasi pola pipeline dari `essay_reviewer` ke `ai-review-engine`, terutama untuk meningkatkan alur `research` agar:

- hasil search lebih relevan,
- context ke LLM lebih kecil dan lebih tajam,
- token tidak boros karena seluruh `raw_markdown` tidak selalu dikirim mentah,
- arsitektur tetap cocok dengan bentuk pipeline `ai-review-engine` yang sekarang.

## Ringkasan Pendapat

Menurutku arah yang kamu usulkan sudah tepat:

`extract -> metadata -> search/retrieval prep -> search -> rank -> score -> generate`

Untuk dokumen `research`, metadata setelah ekstraksi memang sebaiknya jadi fondasi retrieval. Judul, abstrak, keywords, dan sinyal domain jauh lebih efektif untuk membangun query pencarian dibanding langsung melempar potongan dokumen besar ke LLM. Pendekatan ini memberi dua keuntungan besar:

1. Kualitas search naik karena query dibangun dari inti paper, bukan dari isi mentah yang noisy.
2. Konsumsi token turun karena LLM reviewer cukup melihat ringkasan terstruktur + potongan relevan, bukan seluruh dokumen.

## Temuan Dari Dua Project

### Yang sudah bagus di `essay_reviewer`

`essay_reviewer` sudah punya urutan yang secara konsep cocok untuk `research`:

- `pdf_extractor`
- `metadata_extractor`
- `domain_router`
- `query_generator`
- `search_executor`
- `relevance_ranker`
- `essay_reviewer`
- `report_generator`

Hal yang paling penting dari sana:

- metadata diekstrak lebih awal,
- query search dibangun dari `title`, `abstract`, `keywords`, dan `domain`,
- hasil search tidak langsung dipakai mentah, tetapi diranking lagi,
- reviewer menerima `top_references`, bukan semua hasil search.

### Keterbatasan `essay_reviewer`

Walau arahnya bagus, masih ada beberapa hal yang perlu diperbaiki jika dibawa ke `ai-review-engine`:

- reviewer masih memakai potongan `markdown_content` cukup besar,
- ranking search masih berbasis LLM penuh sehingga tetap bisa mahal,
- belum ada pemisahan context untuk kebutuhan yang berbeda, misalnya metadata context vs review context,
- abstrak dan judul sudah dipakai, tetapi belum ada strategi chunking dokumen utama untuk bukti yang benar-benar relevan ke review.

### Kondisi `ai-review-engine` saat ini

Di `ai-review-engine`, alur saat ini masih:

`extract -> essay_agent -> score -> generate`

dan `essay_agent` hanya menyiapkan:

- `agent_context = raw_markdown[:6000]`
- `search_queries = []`

Artinya saat ini masalah utamanya memang ada di sini:

- context dibatasi secara kasar, bukan secara semantik,
- metadata belum diekstrak sebagai state inti,
- `research` masih fallback ke `essay_agent`,
- retrieval eksternal belum menjadi bagian arsitektur nyata,
- node scoring masih berpotensi menerima context yang terlalu besar atau tidak fokus.

## Rekomendasi Arsitektur Baru

### Prinsip utama

Pisahkan pipeline menjadi tiga lapisan context:

1. `document facts`
   - fakta inti hasil ekstraksi: title, abstract, authors, keywords, page_count, section map
2. `retrieval context`
   - query search, hasil search terdedup, ranked references, selected evidence
3. `review context`
   - paket kecil yang benar-benar dikirim ke LLM reviewer

Jangan jadikan `raw_markdown` sebagai context utama review. Jadikan dia sumber data mentah yang hanya dipetik sebagian jika memang diperlukan.

### Flow yang disarankan

Untuk `doc_type="research"`:

```text
START
  -> extract
  -> metadata_extract
  -> document_profile
  -> route_by_doc_type
      -> research_retrieval_prep
      -> search_execute
      -> search_rank
      -> evidence_select
      -> research_score
      -> generate
END
```

Untuk `essay` dan `bizplan`, kamu bisa tetap memakai jalur lebih sederhana, tetapi idealnya node `metadata_extract` tetap dipakai karena murah dan berguna untuk semua tipe dokumen.

## Node Yang Disarankan

### 1. `extract`

Tetap pertahankan node ini sebagai pintu masuk:

- download PDF,
- ekstrak markdown,
- hitung page count,
- validasi minimum.

Tambahan yang berguna:

- simpan `raw_markdown`,
- simpan `document_head` = 3000-4000 karakter awal,
- simpan `document_tail` = 1000-2000 karakter akhir,
- jika memungkinkan simpan section split ringan seperti heading list.

Tujuannya bukan agar semua dipakai LLM, tapi agar langkah berikutnya tidak selalu membaca full text.

### 2. `metadata_extract`

Node ini harus ditambahkan tepat setelah `extract`.

Output minimal:

- `title`
- `abstract`
- `authors`
- `keywords`
- `doc_summary_seed`

`doc_summary_seed` adalah ringkasan sangat pendek hasil ekstraksi metadata, misalnya 3-5 bullet atau 400-700 karakter yang merangkum:

- topik utama,
- metode,
- objek studi,
- keluaran atau klaim utama.

Kalau abstrak sudah bagus, node ini bisa sangat hemat token karena hanya membaca kepala dokumen, seperti yang dilakukan `essay_reviewer`.

### 3. `document_profile`

Ini node baru yang menurutku penting dan belum eksplisit ada di kedua project.

Tugasnya:

- klasifikasi domain/subdomain,
- deteksi jenis bukti dominan,
- deteksi section penting,
- turunkan intent retrieval.

Contoh output:

- `domain`
- `sub_domain`
- `paper_type` seperti `empirical`, `survey`, `method`, `case-study`
- `retrieval_focus`
  - `prior_work`
  - `benchmark`
  - `methodology`
  - `application`

Node ini berguna agar search tidak hanya berdasar judul, tapi juga berdasar apa yang perlu diverifikasi.

### 4. `research_retrieval_prep`

Node ini menyusun query dari metadata, bukan dari isi panjang dokumen.

Input:

- `title`
- `abstract`
- `keywords`
- `domain`
- `sub_domain`
- `paper_type`
- `retrieval_focus`

Output:

- `search_queries`
- `query_rationale`

Strategi query yang kusarankan:

- 1 query sangat presisi dari title,
- 1 query dari abstrak yang disingkat,
- 1 query method-oriented,
- 1 query problem-oriented,
- 1 query broader survey/state-of-the-art.

Kalau `doc_type != research`, node ini bisa skip atau generate query yang lebih sederhana.

### 5. `search_execute`

Ambil pola dari `essay_reviewer`:

- `SemanticScholar` untuk paper discovery,
- `arXiv` untuk preprint teknis,
- `Tavily` atau web search untuk implementasi, benchmark, atau konteks umum.

Saran penting:

- jangan tarik terlalu banyak result,
- limit per source 3-5,
- dedup berdasarkan DOI, URL, atau normalized title.

### 6. `search_rank`

Jangan langsung kirim semua hasil search ke reviewer.

Buat ranking bertingkat:

1. heuristic filtering murah
   - title similarity
   - keyword overlap
   - year recency
2. optional LLM rerank kecil
   - hanya pada 5-8 kandidat terbaik

Ini lebih efisien daripada memakai LLM untuk semua hasil.

Output:

- `ranked_results`
- `top_references`

Idealnya hanya 3-6 referensi terbaik yang dibawa ke node review.

### 7. `evidence_select`

Ini node kunci untuk hemat token.

Tugasnya memilih bukti internal dari dokumen yang relevan untuk review, bukan mengirim seluruh `raw_markdown`.

Input:

- `raw_markdown`
- `abstract`
- `paper_type`
- `retrieval_focus`
- `top_references`

Output:

- `review_context`
- `evidence_chunks`

Strategi yang kusarankan:

- selalu ambil `abstract`,
- ambil `introduction` singkat,
- ambil `method` bila ada,
- ambil `results/conclusion` bila ada,
- total target context misalnya 2500-4500 karakter, bukan 6000 karakter mentah dari awal dokumen saja.

Kalau section parsing belum ada, fallback yang aman:

- head excerpt,
- middle excerpt,
- tail excerpt,
- ditambah metadata terstruktur.

## Bentuk Context Yang Disarankan ke LLM

Jangan kirim:

- seluruh `raw_markdown`
- semua hasil search
- semua snippet referensi

Kirim paket context yang ringkas seperti ini:

```text
PAPER METADATA
- Title: ...
- Abstract: ...
- Keywords: ...
- Domain: ...
- Paper type: ...

SELECTED INTERNAL EVIDENCE
- Intro excerpt: ...
- Method excerpt: ...
- Result/conclusion excerpt: ...

TOP RELATED REFERENCES
- Ref 1: title + year + 1 snippet
- Ref 2: title + year + 1 snippet
- Ref 3: title + year + 1 snippet

REVIEW INSTRUCTIONS
- Score novelty, significance, methodology, clarity, prior work, contribution
```

Model akan jauh lebih stabil jika diberi `evidence packet` seperti itu.

## Kenapa Metadata Harus Sebelum Search

Ini inti usulanmu, dan aku setuju penuh.

Kalau setelah `extract` langsung masuk ke review, ada tiga masalah:

- LLM harus menebak inti paper dari dokumen mentah,
- query search jadi lemah atau bahkan tidak ada,
- token habis untuk memahami dokumen, bukan untuk menilai dokumen.

Kalau `extract -> metadata` lebih dulu:

- query search bisa dibangun dari title + abstract + keyword,
- domain dan subdomain lebih mudah dipastikan,
- search ranking bisa lebih presisi,
- node review tinggal menerima konteks yang sudah dipadatkan.

Untuk `research`, abstrak hampir selalu merupakan kompresi terbaik dari isi paper. Jadi abstrak harus menjadi pusat semua langkah awal:

- routing,
- retrieval,
- ranking,
- dan review context assembly.

## Rekomendasi State Baru

`ReviewEngineState` di `ai-review-engine` sebaiknya diperluas. Tidak perlu semua langsung diimplementasikan, tapi desainnya sebaiknya mengarah ke sini:

```python
class ReviewEngineState(TypedDict):
    analysis_id: str
    file_url: str
    doc_type: Literal["essay", "research", "bizplan"]

    raw_markdown: str
    page_count: int
    is_valid: bool
    error: str | None

    title: str | None
    abstract: str
    authors: list[str]
    keywords: list[str]
    document_head: str
    document_tail: str

    domain: str | None
    sub_domain: str | None
    paper_type: str | None
    retrieval_focus: list[str]

    search_queries: dict[str, list[str]]
    search_results: list[dict]
    ranked_results: list[dict]
    top_references: list[dict]

    evidence_chunks: list[dict]
    review_context: str

    dimension_scores: dict[str, float]
    score_overall: float | None
    dimensions_feedback: list[dict]
    overall_feedback: str
    summary: str

    final_result: dict | None
```

## Saran Routing

`doc_type` dari request user tetap penting dan jangan dihilangkan. Itu memberi jalur bisnis yang jelas.

Tetapi untuk `research`, gunakan metadata untuk memperhalus perilaku pipeline, bukan untuk mengganti `doc_type`.

Artinya:

- `doc_type` menentukan jalur utama graph,
- metadata menentukan strategi retrieval dan review di dalam jalur itu.

Contoh:

- `doc_type="research"` + `paper_type="survey"` -> cari survey/paper landmark
- `doc_type="research"` + `paper_type="empirical"` -> cari benchmark dan prior work
- `doc_type="research"` + `sub_domain="nlp"` -> prioritaskan arXiv dan Semantic Scholar dengan istilah teknis NLP

## Strategi Efisiensi Token

Ini bagian paling penting agar LLM tidak memakan seluruh context.

### Aturan 1: metadata lebih dulu, full text belakangan

Gunakan `title + abstract + keywords` untuk:

- routing,
- query generation,
- ranking awal,
- dan bahkan draft review plan.

Jangan gunakan full text di tahap-tahap ini kecuali fallback.

### Aturan 2: pisahkan raw document dari review context

`raw_markdown` tetap disimpan di state, tetapi jangan langsung dikirim ke model scoring. Buat `review_context` yang sudah dirakit dari bagian paling relevan.

### Aturan 3: ranking bertahap

Lebih murah:

- 15 hasil search
- dedup jadi 8
- heuristic rank jadi 5
- LLM rerank jadi 3

daripada:

- kirim 15 hasil sekaligus ke LLM review.

### Aturan 4: gunakan excerpt berbasis section

Untuk paper ilmiah, potongan paling bernilai biasanya:

- abstract,
- introduction,
- method,
- results,
- conclusion.

Bukan 6000 karakter pertama.

### Aturan 5: batasi referensi yang masuk ke prompt final

Masukkan maksimal 3-5 referensi, masing-masing hanya:

- title,
- year,
- source,
- snippet 1-2 kalimat.

Itu biasanya sudah cukup untuk menilai prior work dan positioning.

## Desain Minimal Yang Paling Worth It

Kalau mau implementasi bertahap tanpa refactor besar, menurutku urutan paling bernilai adalah:

1. Tambah `metadata_extract` setelah `extract`.
2. Tambah `research_agent` khusus untuk `doc_type="research"`.
3. Ubah `research_agent` agar membangun `search_queries` dari `title`, `abstract`, `keywords`.
4. Tambah `search_execute` dan `search_rank`.
5. Tambah `evidence_select` agar `score` menerima `review_context`, bukan `raw_markdown[:6000]`.

Dengan 5 langkah itu saja, kualitas arsitektur akan naik cukup jauh.

## Step-by-Step Adaptasi

Bagian ini sengaja dibuat lebih operasional supaya kamu bisa prompting AI secara bertahap, lalu berhenti di setiap checkpoint untuk verifikasi manual sebelum lanjut.

Prinsip eksekusinya:

- kerjakan satu fase kecil per kali prompting,
- setelah coding selesai, lakukan validasi output dan struktur kode,
- baru lanjut ke fase berikutnya,
- jangan gabungkan terlalu banyak node baru dalam satu langkah.

### Fase 0 - Baseline dan pembacaan kondisi sekarang

Tujuan:

- memastikan perilaku pipeline saat ini dipahami dulu,
- mengunci baseline sebelum refactor,
- menghindari perubahan terlalu banyak sekaligus.

Yang dikerjakan:

- review `ReviewEngineState` yang sekarang,
- review `builder.py`,
- review `extract.py`, `essay_agent.py`, `score.py`, `generate.py`,
- dokumentasikan flow aktual dan field state yang benar-benar dipakai.

Hasil yang diharapkan:

- daftar field state existing,
- daftar node existing,
- daftar titik yang akan disentuh pada fase berikutnya.

Checkpoint verifikasi:

- pipeline existing masih dipahami end-to-end,
- tidak ada asumsi yang salah soal alur `extract -> essay_agent -> score -> generate`.

Contoh prompt AI:

```text
Analisa pipeline `ai-review-engine/ai-agent` saat ini tanpa mengubah kode.
Fokus ke:
- `app/graph/state.py`
- `app/graph/builder.py`
- semua node yang dipakai builder

Tolong ringkas:
1. alur graph yang berjalan sekarang,
2. field state yang dipakai tiap node,
3. titik paling tepat untuk menyisipkan `metadata_extract`,
4. risiko refactor paling awal.

Jangan coding dulu, hanya analisis dan rekomendasi patch kecil fase pertama.
```

### Fase 1 - Tambah `metadata_extract` tanpa mengubah behavior utama

Tujuan:

- menambahkan ekstraksi metadata sebagai fondasi baru,
- tetapi belum mengubah jalur review secara besar.

Yang dikerjakan:

- tambah field state:
  - `abstract`
  - `authors`
  - `keywords`
  - opsional `document_head`
  - opsional `document_tail`
- buat node baru `metadata_extract.py`,
- sisipkan node ini setelah `extract`,
- untuk sementara `essay_agent` dan `score` boleh tetap bekerja seperti sebelumnya.

Scope implementasi yang aman:

- metadata node membaca `raw_markdown`,
- hanya menggunakan bagian awal dokumen,
- jika gagal, fallback tetap aman dan pipeline tidak rusak.

Hasil yang diharapkan:

- state sudah punya metadata dasar,
- `builder.py` sudah berubah menjadi:
  - `extract -> metadata_extract -> route -> ...`

Checkpoint verifikasi:

- graph berhasil compile,
- request lama tetap bisa jalan,
- `title`, `abstract`, `keywords` muncul di state/final logging bila tersedia,
- kalau metadata gagal, pipeline tetap lanjut.

Contoh prompt AI:

```text
Implementasikan fase 1 adaptasi secara minimal dan aman.

Target:
- tambah node `metadata_extract`
- update `ReviewEngineState`
- update `builder.py` agar `metadata_extract` berjalan setelah `extract`

Batasan:
- jangan ubah logic scoring dulu
- jangan ubah route API
- jangan tambahkan search dulu
- fallback harus aman jika metadata extraction gagal

Setelah coding, jelaskan:
1. file yang diubah,
2. field state baru,
3. bagaimana fallback bekerja,
4. cara verifikasi manual sederhana.
```

### Fase 2 - Pisahkan jalur `research` dari `essay`

Tujuan:

- menghentikan `research` agar tidak lagi full fallback ke `essay_agent`,
- memberi tempat khusus untuk logic retrieval-oriented.

Yang dikerjakan:

- buat `research_agent.py`,
- update routing di `builder.py`,
- biarkan `essay` tetap memakai `essay_agent`,
- untuk sementara `research_agent` cukup menyiapkan:
  - context metadata,
  - placeholder `search_queries`,
  - atau `review_plan`.

Hasil yang diharapkan:

- `doc_type="research"` punya node sendiri,
- struktur graph sudah siap untuk fase retrieval berikutnya.

Checkpoint verifikasi:

- `essay` flow tetap normal,
- `research` masuk ke `research_agent`,
- state untuk `research` sudah berbeda dari `essay`.

Contoh prompt AI:

```text
Implementasikan fase 2 adaptasi.

Target:
- buat `app/graph/nodes/research_agent.py`
- update `builder.py` supaya `doc_type="research"` diarahkan ke `research_agent`

Perilaku `research_agent` untuk sementara:
- gunakan metadata (`title`, `abstract`, `keywords`) sebagai context utama
- jangan pakai `raw_markdown[:6000]` sebagai default context
- siapkan output state yang akan berguna untuk fase search berikutnya

Jangan implementasi search dulu.
Fokus hanya pada pemisahan jalur research dengan perubahan sekecil mungkin.
```

### Fase 3 - Tambah `document_profile` atau profiling ringan

Tujuan:

- membuat metadata lebih bernilai untuk retrieval,
- menurunkan intent search dari isi paper.

Yang dikerjakan:

- tambah node `document_profile.py` atau gabungkan profiling ringan di `research_agent`,
- hasilkan:
  - `domain`
  - `sub_domain`
  - `paper_type`
  - `retrieval_focus`

Catatan:

- kalau ingin bertahap, profiling ini bisa dibuat sangat sederhana dulu,
- misalnya hanya `domain`, `sub_domain`, dan `retrieval_focus`.

Hasil yang diharapkan:

- search nanti tidak hanya berbasis title,
- query generation jadi lebih terarah.

Checkpoint verifikasi:

- output profile masuk akal pada 2-3 contoh dokumen,
- fallback ke nilai default tersedia jika klasifikasi gagal.

Contoh prompt AI:

```text
Implementasikan fase 3: profiling dokumen research secara ringan.

Target:
- buat node baru atau helper yang menghasilkan `domain`, `sub_domain`, `paper_type`, dan `retrieval_focus`
- gunakan `title`, `abstract`, `keywords` sebagai input utama

Batasan:
- desain fallback default jika hasil klasifikasi tidak yakin
- jangan ubah score node dulu
- jangan tambahkan external API selain LLM yang sudah ada

Tolong sertakan juga contoh struktur output state yang dihasilkan node ini.
```

### Fase 4 - Tambah query generation berbasis metadata

Tujuan:

- membuat search nanti dibangun dari inti paper,
- bukan dari chunk dokumen yang kasar.

Yang dikerjakan:

- tambah `search_queries` berbentuk `dict[str, list[str]]`,
- buat node seperti `research_retrieval_prep.py` atau letakkan di `research_agent`,
- generate query dari:
  - title,
  - abstract,
  - keywords,
  - domain/subdomain,
  - retrieval_focus.

Hasil yang diharapkan:

- query per sumber sudah siap,
- minimal untuk:
  - `semanticscholar`
  - `arxiv`
  - `tavily`

Checkpoint verifikasi:

- query terlihat masuk akal,
- tidak terlalu panjang,
- tidak generik,
- ada perbedaan query untuk problem, method, dan broader context.

Contoh prompt AI:

```text
Implementasikan fase 4: query generation berbasis metadata untuk dokumen research.

Target:
- hasilkan `search_queries` dari `title`, `abstract`, `keywords`, `domain`, `sub_domain`, `retrieval_focus`
- format output:
  {
    "semanticscholar": [...],
    "arxiv": [...],
    "tavily": [...]
  }

Batasan:
- jangan jalankan search beneran dulu
- fokus pada pembentukan query yang ringkas dan relevan
- buat fallback query jika metadata minim
```

### Fase 5 - Implement `search_execute`

Tujuan:

- mulai menghidupkan retrieval eksternal,
- tetapi tetap terkendali dari sisi kompleksitas dan token.

Yang dikerjakan:

- tambahkan tool atau service untuk search,
- buat node `search_execute`,
- batasi jumlah hasil per sumber,
- lakukan dedup dasar.

Saran rollout:

- aktifkan satu sumber dulu, misalnya `SemanticScholar`,
- setelah stabil baru tambah `arXiv`,
- terakhir baru `Tavily`.

Hasil yang diharapkan:

- `search_results` tersedia di state,
- format hasil sudah konsisten untuk semua sumber.

Checkpoint verifikasi:

- node tetap aman jika API gagal,
- pipeline bisa lanjut tanpa search result,
- hasil dedup tidak terlalu noisy.

Contoh prompt AI:

```text
Implementasikan fase 5: search executor bertahap untuk jalur research.

Mulai dari satu source dulu jika perlu.
Target:
- buat `search_execute` node
- jalankan query dari `search_queries`
- simpan hasil ke `search_results`
- pastikan pipeline tetap jalan kalau search gagal

Batasan:
- limit hasil sedikit dulu
- dedup sederhana berdasarkan URL atau title normalized
- jangan ubah prompt scoring dulu
```

### Fase 6 - Implement ranking dan seleksi referensi

Tujuan:

- mencegah semua hasil search masuk ke prompt final,
- memilih hanya referensi yang paling relevan.

Yang dikerjakan:

- buat `search_rank.py`,
- lakukan heuristic rank terlebih dahulu,
- optional LLM rerank hanya untuk kandidat teratas,
- hasilkan `top_references`.

Hasil yang diharapkan:

- ada pemisahan jelas antara `search_results` mentah dan `top_references`,
- prompt review nanti hanya menerima 3-5 referensi terbaik.

Checkpoint verifikasi:

- ranking terasa masuk akal,
- referensi paling atas sesuai title/abstract paper,
- kalau ranking gagal, fallback ke hasil dedup awal.

Contoh prompt AI:

```text
Implementasikan fase 6: ranking hasil search untuk jalur research.

Target:
- buat node ranking
- outputkan `ranked_results` dan `top_references`

Strategi:
- prioritaskan heuristic filtering murah dulu
- LLM rerank boleh optional dan hanya untuk sedikit kandidat

Jangan kirim semua search result ke scoring.
Fokus pada pipeline ranking yang aman dan hemat token.
```

### Fase 7 - Implement `evidence_select`

Tujuan:

- membangun `review_context` kecil dan tajam,
- menghentikan praktik mengirim `raw_markdown[:6000]` mentah ke reviewer.

Yang dikerjakan:

- buat node `evidence_select.py`,
- ambil potongan internal dokumen yang relevan,
- gabungkan dengan metadata dan `top_references`,
- hasilkan:
  - `evidence_chunks`
  - `review_context`

Hasil yang diharapkan:

- `score` tidak lagi bergantung pada potongan awal dokumen,
- context lebih seimbang antara abstract, method, result, dan referensi.

Checkpoint verifikasi:

- `review_context` lebih kecil dari full markdown,
- tetapi tetap kaya informasi,
- isi context dapat dibaca manusia dan terasa relevan.

Contoh prompt AI:

```text
Implementasikan fase 7: node `evidence_select`.

Target:
- bangun `review_context` dari metadata + selected internal excerpts + top references
- jangan gunakan seluruh `raw_markdown`
- prioritaskan abstract, intro, method, result/conclusion jika tersedia

Batasan:
- ukuran context harus ringkas
- jika section parsing belum akurat, gunakan fallback head/middle/tail excerpt

Setelah coding, tampilkan contoh bentuk `review_context` yang dihasilkan.
```

### Fase 8 - Update `score.py` agar memakai `review_context`

Tujuan:

- mengubah node penilaian agar benar-benar memakai arsitektur baru,
- bukan context mentah warisan fase MVP.

Yang dikerjakan:

- ubah `score.py` agar input utama adalah:
  - `review_context`
  - `top_references`
  - `doc_type`
- buat prompt khusus `research` jika belum ada,
- pertahankan kompatibilitas `essay` bila perlu.

Hasil yang diharapkan:

- scoring untuk `research` berbasis paket evidence,
- token lebih hemat,
- prior work/retrieval ikut memengaruhi kualitas review.

Checkpoint verifikasi:

- output scoring tetap valid JSON,
- kualitas feedback lebih spesifik,
- tidak ada ketergantungan ke `raw_markdown[:6000]`.

Contoh prompt AI:

```text
Implementasikan fase 8: refactor `score.py` agar jalur research memakai `review_context`.

Target:
- `score.py` membaca `review_context` dan `top_references`
- buat prompt atau branch logic khusus untuk `doc_type="research"`
- pertahankan kompatibilitas untuk `essay` sebisa mungkin

Batasan:
- jangan refactor generate node besar-besaran
- fokus agar scoring research sudah memanfaatkan arsitektur baru
```

### Fase 9 - Rapikan `generate.py` dan output akhir

Tujuan:

- memastikan hasil akhir sudah memuat data yang berguna untuk frontend dan validasi,
- tanpa membocorkan context berlebihan.

Yang dikerjakan:

- update `generate.py`,
- tampilkan metadata penting,
- tampilkan referensi terpilih,
- tampilkan summary dan feedback,
- jangan kirim seluruh `review_context` kecuali memang perlu debugging internal.

Hasil yang diharapkan:

- `final_result` lebih informatif,
- hasil bisa divalidasi dari sisi backend/frontend.

Checkpoint verifikasi:

- payload callback tetap bersih,
- field penting tersedia,
- ukuran response tidak berlebihan.

Contoh prompt AI:

```text
Implementasikan fase 9: rapikan `generate.py` untuk output research pipeline.

Target:
- masukkan metadata penting
- masukkan top references yang sudah terpilih
- pertahankan format result yang tetap nyaman dipakai backend

Jangan masukkan seluruh raw markdown atau full review context ke output final kecuali benar-benar diperlukan.
```

### Fase 10 - Hardening dan validasi akhir

Tujuan:

- memastikan pipeline baru stabil,
- meminimalkan regresi setelah beberapa fase refactor.

Yang dikerjakan:

- tambah logging per node,
- tambah fallback bila node retrieval gagal,
- cek linter,
- tambah test minimal untuk state flow dan routing,
- verifikasi 2-3 dokumen contoh.

Checklist validasi akhir:

- `essay` tidak rusak,
- `research` tidak lagi memakai fallback penuh ke `essay_agent`,
- metadata keluar dengan baik,
- search query relevan,
- search result bisa kosong tanpa mematikan pipeline,
- `review_context` lebih kecil dan lebih fokus dari `raw_markdown`,
- scoring tetap menghasilkan JSON valid,
- final callback tetap stabil.

Contoh prompt AI:

```text
Lakukan hardening untuk pipeline research yang baru diimplementasikan.

Fokus:
- cek fallback setiap node
- cek linter di file yang berubah
- tambahkan test ringan yang paling bernilai
- pastikan `essay` flow lama tidak ikut rusak

Tolong prioritaskan bug/risk nyata dan perubahan kecil yang aman.
```

## Urutan Prompting Yang Disarankan

Kalau kamu ingin benar-benar bertahap, urutan prompting paling aman menurutku adalah:

1. Fase 1 - `metadata_extract`
2. Fase 2 - `research_agent`
3. Fase 3 - `document_profile`
4. Fase 4 - query generation
5. Fase 5 - `search_execute`
6. Fase 6 - `search_rank`
7. Fase 7 - `evidence_select`
8. Fase 8 - refactor `score.py`
9. Fase 9 - update `generate.py`
10. Fase 10 - hardening

Kalau mau lebih konservatif lagi, pecah fase 5 dan fase 6 menjadi beberapa prompt kecil per sumber search.

## Strategi Verifikasi Per Fase

Supaya validasi kamu ringan tetapi tetap efektif, gunakan pola ini tiap selesai satu fase:

1. Verifikasi struktur
   - file baru sudah ada,
   - builder/routing sesuai rencana,
   - state field baru tidak bentrok.
2. Verifikasi perilaku
   - jalankan satu request contoh,
   - lihat state/output/log yang berubah.
3. Verifikasi fallback
   - bayangkan node gagal,
   - pastikan pipeline tidak runtuh total jika failure memang seharusnya graceful.
4. Verifikasi token discipline
   - cek apakah node baru justru mengirim lebih banyak context,
   - pastikan `review_context` tetap paket ringkas.

## Catatan Penting Saat Prompting AI

Agar AI coding assistant lebih konsisten, sebaiknya tiap prompt selalu menyebut:

- file target yang boleh diubah,
- file yang jangan disentuh dulu,
- tujuan fase saat ini,
- batasan perubahan,
- output verifikasi yang kamu minta setelah coding.

Formula prompt yang bagus:

```text
Kerjakan fase X saja.

Tujuan:
- ...

File yang boleh diubah:
- ...

Jangan ubah:
- ...

Batasan:
- ...

Setelah selesai:
1. jelaskan perubahan,
2. sebutkan risiko,
3. berikan cara verifikasi manual,
4. jangan lanjut ke fase berikutnya.
```

## Setup Preparation Sebelum Mulai Adaptasi

Bagian ini penting supaya proses prompting dan implementasi bertahap tidak gagal hanya karena environment, dependency, atau credential belum siap.

Tujuan setup preparation:

- memastikan tiap fase punya prasyarat teknis yang jelas,
- mengurangi error palsu saat prompting AI,
- memisahkan error arsitektur dari error setup,
- membuat proses verifikasi lebih konsisten.

## Checklist Persiapan Global

Sebelum mulai fase coding apa pun, sebaiknya cek ini dulu.

### 1. Python environment

Pastikan environment `ai-review-engine/ai-agent` sudah bisa menjalankan service dasar.

Checklist:

- Python versi sesuai project,
- virtual environment aktif,
- dependency dasar sudah terpasang,
- FastAPI app bisa start,
- import LangGraph dan dependency LLM tidak error.

Verifikasi minimal:

```text
- app bisa boot
- import node existing tidak error
- graph builder bisa di-import
```

### 2. Dependency baseline

Untuk adaptasi ini, dependency akan terbagi menjadi beberapa lapisan.

Lapisan minimal awal:

- `fastapi`
- `uvicorn`
- `langgraph`
- `langchain`
- `httpx`
- `pymupdf4llm`
- `pymupdf` atau `fitz`
- `pydantic`
- `pydantic-settings`

Lapisan metadata dan LLM:

- `langchain-openai` atau `langchain-anthropic`
- `langchain-groq` jika tetap dipakai sekarang

Lapisan retrieval:

- `tavily-python`
- `arxiv`
- `semanticscholar`

Lapisan opsional ranking/heuristic:

- `rapidfuzz` atau library serupa untuk similarity ringan,
- `python-dotenv` bila belum ada.

Saran praktis:

- jangan aktifkan semua tool dulu kalau belum dipakai,
- install bertahap sesuai fase agar debugging lebih mudah.

### 3. File `.env` dan source of truth config

Sebelum mulai, pastikan semua config dibaca dari satu tempat, idealnya `app/core/config.py`.

Jangan menyebar pembacaan env di banyak file tanpa kontrol.

Checklist:

- semua API key dibaca lewat settings/config,
- ada default yang aman untuk fitur opsional,
- tidak ada hardcoded API key,
- ada `.env.example` yang diperbarui.

### 4. Feature flag sederhana

Ini sangat kusarankan agar tiap fase aman diuji tanpa langsung mengaktifkan semua integrasi.

Contoh flag yang berguna:

- `ENABLE_METADATA_EXTRACT=true`
- `ENABLE_RESEARCH_AGENT=true`
- `ENABLE_SEARCH=false`
- `ENABLE_SEMANTIC_SCHOLAR=false`
- `ENABLE_ARXIV=false`
- `ENABLE_TAVILY=false`
- `ENABLE_LLM_RERANK=false`
- `ENABLE_EVIDENCE_SELECT=true`

Dengan flag seperti ini, kamu bisa prompting AI untuk coding node lebih dulu, lalu mengaktifkan runtime-nya belakangan.

### 5. Logging dan observability

Sebelum retrieval aktif, pastikan logging per node cukup jelas.

Minimal setiap fase sebaiknya bisa menjawab:

- node mana yang jalan,
- node mana yang skip,
- node mana yang gagal,
- fallback mana yang dipakai.

Kalau ini belum ada, debugging hasil prompting akan sangat melelahkan.

## Setup Per Fase

Berikut persiapan yang sebaiknya kamu penuhi sebelum menjalankan prompt AI di tiap fase.

### Fase 0 - Baseline analysis

Persiapan:

- tidak butuh API key baru,
- tidak butuh dependency baru,
- cukup pastikan repo bisa dibaca dan app bisa di-import.

Yang perlu dicek:

- `app/graph/state.py`
- `app/graph/builder.py`
- `app/graph/nodes/*.py`
- `app/core/config.py`

Risiko umum:

- config tersebar di beberapa file,
- env variable naming belum konsisten,
- dependency ada tapi belum terdaftar rapi.

### Fase 1 - `metadata_extract`

Persiapan teknis:

- pilih provider metadata extraction:
  - OpenAI,
  - Anthropic,
  - atau Groq jika memang ingin dipakai,
- pastikan API key provider itu tersedia.

Env yang minimal disiapkan:

```env
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
LLM_PROVIDER=openai
LLM_MODEL_METADATA=
ENABLE_METADATA_EXTRACT=true
```

Catatan:

- tidak semua key harus terisi,
- cukup isi yang benar-benar dipakai oleh implementasi metadata node.

Saran penting:

- metadata extraction sebaiknya pakai model yang murah dan stabil,
- jangan gunakan model termahal hanya untuk ekstraksi title/abstract.

Verifikasi setup:

- panggilan LLM sederhana bisa jalan,
- node metadata bisa fallback jika API key belum ada atau provider gagal.

### Fase 2 - `research_agent`

Persiapan teknis:

- tidak wajib API key baru jika hanya memanfaatkan metadata yang sudah ada,
- cukup pastikan env feature flag siap.

Env yang berguna:

```env
ENABLE_RESEARCH_AGENT=true
DEFAULT_DOC_TYPE=essay
```

Kalau `research_agent` juga melakukan reasoning LLM ringan, tambahkan:

```env
LLM_MODEL_RESEARCH_AGENT=
```

Verifikasi setup:

- route `research` bisa diaktifkan tanpa mengganggu `essay`,
- jika `ENABLE_RESEARCH_AGENT=false`, fallback behavior tetap jelas.

### Fase 3 - `document_profile`

Persiapan teknis:

- butuh provider LLM jika profiling berbasis prompt,
- atau tidak butuh API tambahan jika profiling dibuat rule-based.

Env yang disarankan:

```env
ENABLE_DOCUMENT_PROFILE=true
LLM_MODEL_PROFILE=
```

Saran:

- fase ini bagus dimulai dengan LLM sederhana,
- jika nanti mahal, baru sebagian logic dipindah ke heuristic.

Verifikasi setup:

- node bisa menghasilkan default profile saat key kosong,
- field `domain`, `sub_domain`, `paper_type`, `retrieval_focus` tidak menyebabkan crash jika kosong.

### Fase 4 - Query generation

Persiapan teknis:

- biasanya cukup pakai provider LLM yang sama,
- belum butuh API search aktif.

Env yang disarankan:

```env
ENABLE_QUERY_GENERATION=true
LLM_MODEL_QUERY=
MAX_SEARCH_QUERIES_PER_SOURCE=3
```

Saran:

- query generation tidak perlu model besar,
- batasi jumlah query sejak awal agar biaya search tetap terkendali.

Verifikasi setup:

- output query konsisten,
- jika metadata tipis, fallback query tetap terbentuk.

### Fase 5 - `search_execute`

Ini fase yang mulai sensitif terhadap setup eksternal.

Persiapan teknis:

- tentukan tool yang mau diaktifkan dulu,
- siapkan API key hanya untuk tool yang benar-benar dipakai pada fase itu,
- tambahkan timeout dan graceful fallback.

Env yang disarankan:

```env
ENABLE_SEARCH=false
ENABLE_SEMANTIC_SCHOLAR=false
ENABLE_ARXIV=false
ENABLE_TAVILY=false

SEMANTIC_SCHOLAR_API_KEY=
TAVILY_API_KEY=

SEARCH_TIMEOUT_SECONDS=20
SEARCH_MAX_RESULTS_PER_SOURCE=3
```

Catatan tool:

- `arXiv` biasanya tidak memerlukan API key,
- `Semantic Scholar` bisa jalan lebih baik dengan key,
- `Tavily` memerlukan API key.

Strategi rollout yang kusarankan:

1. nyalakan `Semantic Scholar` dulu,
2. lalu `arXiv`,
3. terakhir `Tavily`.

Alasannya:

- `Semantic Scholar` paling dekat dengan use case prior work,
- `arXiv` bagus untuk technical paper,
- `Tavily` lebih cocok sebagai pelengkap konteks umum.

Verifikasi setup:

- satu tool aktif dulu sampai stabil,
- jika tool error, pipeline tidak berhenti total,
- ada log hasil jumlah result per source.

### Fase 6 - ranking search

Persiapan teknis:

- tidak wajib API key baru jika ranking awal heuristic,
- kalau mau LLM rerank, butuh model tambahan atau reuse provider utama.

Env yang disarankan:

```env
ENABLE_SEARCH_RANK=true
ENABLE_LLM_RERANK=false
LLM_MODEL_RERANK=
TOP_K_SEARCH_RESULTS=8
TOP_K_REFERENCES=3
```

Dependency opsional:

- `rapidfuzz`

Saran:

- mulai dari heuristic ranking dulu,
- baru nyalakan `ENABLE_LLM_RERANK=true` setelah hasil awal cukup stabil.

Verifikasi setup:

- ranking masih menghasilkan `top_references` meskipun rerank LLM dimatikan,
- perubahan `TOP_K_REFERENCES` memengaruhi output dengan jelas.

### Fase 7 - `evidence_select`

Persiapan teknis:

- tidak butuh API eksternal jika berbasis slicing/section parsing,
- butuh LLM jika ingin evidence selection yang lebih semantik.

Env yang disarankan:

```env
ENABLE_EVIDENCE_SELECT=true
LLM_MODEL_EVIDENCE=
MAX_REVIEW_CONTEXT_CHARS=4500
MAX_INTERNAL_EVIDENCE_CHARS=3000
MAX_REFERENCE_SNIPPET_CHARS=400
```

Saran:

- mulai dari heuristic evidence selection,
- misalnya abstract + heading-based excerpt + tail excerpt,
- baru upgrade ke LLM selection jika benar-benar perlu.

Verifikasi setup:

- `review_context` selalu lebih kecil dari `raw_markdown`,
- panjang context mengikuti env limit,
- node tetap jalan walau section parsing tidak sempurna.

### Fase 8 - refactor `score.py`

Persiapan teknis:

- pastikan model scoring sudah tersedia,
- tentukan model mana untuk `research` dan mana untuk `essay`.

Env yang disarankan:

```env
LLM_MODEL_SCORE=
LLM_MODEL_SCORE_RESEARCH=
ENABLE_RESEARCH_SCORING=true
```

Saran:

- jika budget terbatas, gunakan 1 model scoring untuk semua,
- jika ingin kualitas lebih baik, buat model khusus `research`.

Verifikasi setup:

- scoring JSON valid,
- fallback error handling tetap rapi,
- scoring tetap bisa jalan meski `top_references` kosong.

### Fase 9 - `generate.py`

Persiapan teknis:

- tidak butuh API key baru,
- yang penting field state final sudah stabil.

Env opsional:

```env
INCLUDE_DEBUG_FIELDS=false
INCLUDE_TOP_REFERENCES=true
```

Saran:

- jangan expose `review_context` ke output final default,
- kalau perlu debugging, pakai flag.

Verifikasi setup:

- ukuran payload tetap masuk akal,
- output final cukup informatif untuk validasi.

### Fase 10 - hardening

Persiapan teknis:

- siapkan test command,
- siapkan lint command,
- siapkan 2-3 sample document untuk verifikasi manual.

Checklist:

- ada contoh dokumen `essay`,
- ada contoh dokumen `research`,
- ada contoh dokumen yang buruk atau minim metadata,
- ada satu kasus tanpa search result.

Env tambahan yang berguna:

```env
LOG_LEVEL=INFO
FAIL_OPEN_ON_SEARCH_ERROR=true
FAIL_OPEN_ON_METADATA_ERROR=true
```

Verifikasi setup:

- kamu bisa menguji skenario sukses dan gagal,
- fallback behavior bisa dibaca dari log.

## Template `.env` Yang Disarankan

Berikut contoh template `.env` yang lebih siap untuk adaptasi bertahap:

```env
# Core app
LOG_LEVEL=INFO

# LLM provider
LLM_PROVIDER=openai
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=

# Models per task
LLM_MODEL_METADATA=
LLM_MODEL_PROFILE=
LLM_MODEL_QUERY=
LLM_MODEL_EVIDENCE=
LLM_MODEL_SCORE=
LLM_MODEL_SCORE_RESEARCH=
LLM_MODEL_RERANK=

# Feature flags
ENABLE_METADATA_EXTRACT=true
ENABLE_RESEARCH_AGENT=true
ENABLE_DOCUMENT_PROFILE=false
ENABLE_QUERY_GENERATION=false
ENABLE_SEARCH=false
ENABLE_SEMANTIC_SCHOLAR=false
ENABLE_ARXIV=false
ENABLE_TAVILY=false
ENABLE_SEARCH_RANK=false
ENABLE_LLM_RERANK=false
ENABLE_EVIDENCE_SELECT=false
ENABLE_RESEARCH_SCORING=false

# Search APIs
SEMANTIC_SCHOLAR_API_KEY=
TAVILY_API_KEY=

# Limits
SEARCH_TIMEOUT_SECONDS=20
SEARCH_MAX_RESULTS_PER_SOURCE=3
MAX_SEARCH_QUERIES_PER_SOURCE=3
TOP_K_SEARCH_RESULTS=8
TOP_K_REFERENCES=3
MAX_REVIEW_CONTEXT_CHARS=4500
MAX_INTERNAL_EVIDENCE_CHARS=3000
MAX_REFERENCE_SNIPPET_CHARS=400

# Fallback behavior
FAIL_OPEN_ON_SEARCH_ERROR=true
FAIL_OPEN_ON_METADATA_ERROR=true
INCLUDE_DEBUG_FIELDS=false
INCLUDE_TOP_REFERENCES=true
```

## Urutan Aktivasi Env Yang Aman

Jangan aktifkan semua flag sekaligus.

Urutan yang lebih aman:

1. `ENABLE_METADATA_EXTRACT=true`
2. `ENABLE_RESEARCH_AGENT=true`
3. `ENABLE_DOCUMENT_PROFILE=true`
4. `ENABLE_QUERY_GENERATION=true`
5. `ENABLE_SEARCH=true` + satu provider dulu
6. `ENABLE_SEARCH_RANK=true`
7. `ENABLE_EVIDENCE_SELECT=true`
8. `ENABLE_RESEARCH_SCORING=true`
9. `ENABLE_LLM_RERANK=true` kalau memang dibutuhkan

Dengan pola ini, kalau terjadi error kamu akan lebih mudah tahu error-nya berasal dari fase mana.

## Persiapan Non-Env Yang Sering Dilupakan

Selain API key dan `.env`, ada beberapa hal yang sering bikin proses adaptasi gagal atau membingungkan saat prompting AI:

- sample PDF untuk uji manual belum disiapkan,
- naming field state belum konsisten,
- belum ada keputusan provider LLM utama,
- belum ada batas token atau batas karakter per context,
- belum ada fallback strategy yang disepakati,
- prompt AI terlalu besar dan meminta banyak fase sekaligus.

Saran praktis sebelum mulai:

- pilih satu provider LLM utama dulu,
- pilih satu tool search pertama dulu,
- tentukan naming state final dulu,
- siapkan 2-3 sample PDF untuk regression check,
- aktifkan log yang cukup verbose untuk fase adaptasi.

## Template Prompt Dengan Persiapan Step

Supaya AI coding assistant tidak lupa prasyarat setup, kamu bisa pakai format prompt seperti ini:

```text
Kerjakan fase X saja.

Sebelum coding:
1. cek apakah dependency dan env yang dibutuhkan fase ini sudah ada,
2. jika belum ada, tambahkan setup minimal yang diperlukan,
3. jangan aktifkan fitur fase berikutnya.

Tujuan:
- ...

File yang boleh diubah:
- ...

Jangan ubah:
- ...

Batasan:
- ...

Environment/feature flag yang harus dipakai:
- ...

Setelah selesai:
1. jelaskan perubahan setup,
2. jelaskan perubahan kode,
3. berikan langkah verifikasi manual,
4. sebutkan env/API key apa yang wajib ada untuk mencoba fase ini.
```

## Rekomendasi Integrasi ke File yang Ada

### `app/graph/builder.py`

Ubah flow dari:

`extract -> essay_agent -> score -> generate`

menjadi minimal:

`extract -> metadata_extract -> route_by_doc_type -> agent/retrieval path -> score -> generate`

Untuk `research`, rute ideal:

`extract -> metadata_extract -> document_profile -> research_agent -> search_execute -> search_rank -> evidence_select -> score -> generate`

### `app/graph/nodes/extract.py`

Tetap fokus pada extraction dan validity. Jangan bebani node ini dengan logika metadata atau review.

### `app/graph/nodes/essay_agent.py`

Node ini jangan lagi menjadi tempat default semua tipe dokumen. Pisahkan:

- `essay_agent.py`
- `research_agent.py`
- `bizplan_agent.py`

Minimal `research_agent` harus punya perilaku yang berbeda dari essay.

### `app/graph/nodes/score.py`

Node ini sebaiknya membaca:

- `review_context`
- `top_references`
- `doc_type`

bukan `agent_context` generik yang diambil dari awal dokumen saja.

### `app/api/routes.py`

Route tidak perlu banyak berubah. Justru bagus karena sudah hanya mengirim:

- `analysis_id`
- `file_url`
- `doc_type`

Ini cukup. Perubahan terbesar ada di graph dan state.

## Arsitektur yang Paling Aku Sarankan

Kalau diringkas, arsitektur yang paling sehat untuk kebutuhanmu adalah:

```text
extract
  -> metadata_extract
  -> document_profile
  -> route_by_doc_type
      -> research_agent
      -> search_execute
      -> search_rank
      -> evidence_select
      -> score
      -> generate
```

Dengan prinsip:

- metadata adalah pusat retrieval,
- abstract adalah inti kompresi awal,
- search dipakai untuk memperkaya prior work dan positioning,
- full markdown hanya jadi sumber bukti terpilih,
- prompt akhir harus menerima `review_context` yang kecil, padat, dan terstruktur.

## Kesimpulan

Secara arsitektur, `essay_reviewer` layak dijadikan referensi, tetapi jangan dicopy mentah ke `ai-review-engine`.

Yang sebaiknya diadopsi:

- metadata extraction lebih awal,
- domain/profile inference,
- query generation berbasis metadata,
- search + rank sebelum review,
- hanya referensi teratas yang masuk ke prompt.

Yang sebaiknya diperbaiki saat adaptasi:

- jangan kirim chunk awal dokumen sebagai satu-satunya context,
- tambahkan node `evidence_select`,
- bedakan `raw_markdown`, `retrieval state`, dan `review_context`,
- gunakan jalur `research` yang benar-benar khusus.

Kalau targetmu adalah review paper ilmiah yang efisien dan relevan, maka `extract -> metadata -> retrieval -> selected evidence -> review` adalah arsitektur yang paling masuk akal.
