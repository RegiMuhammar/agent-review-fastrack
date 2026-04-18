import { useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  BadgeCheck,
  ChevronLeft,
  ChevronRight,
  FileScan,
  ShieldCheck,
  Star,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { listPublicFeedbacks } from '@/lib/api'

function HomePage() {
  const [feedbacks, setFeedbacks] = useState([])
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(true)
  const feedbackCarouselRef = useRef(null)

  function moveFeedbackCarousel(direction) {
    const container = feedbackCarouselRef.current

    if (!container) {
      return
    }

    const scrollAmount = container.clientWidth * 0.9
    const maxScrollLeft = Math.max(container.scrollWidth - container.clientWidth, 0)
    const isAtStart = container.scrollLeft <= 8
    const isAtEnd = container.scrollLeft >= maxScrollLeft - 8

    if (direction === 'prev') {
      if (isAtStart) {
        container.scrollTo({ left: maxScrollLeft, behavior: 'smooth' })
        return
      }

      container.scrollBy({ left: -scrollAmount, behavior: 'smooth' })
      return
    }

    if (isAtEnd) {
      container.scrollTo({ left: 0, behavior: 'smooth' })
      return
    }

    container.scrollBy({ left: scrollAmount, behavior: 'smooth' })
  }

  async function loadFeedbacks() {
    setIsFeedbackLoading(true)

    try {
      const response = await listPublicFeedbacks({ page: 1, limit: 18 })

      setFeedbacks(response?.data?.feedbacks ?? [])
    } catch {
      setFeedbacks([])
    } finally {
      setIsFeedbackLoading(false)
    }
  }

  useEffect(() => {
    loadFeedbacks()
  }, [])

  useEffect(() => {
    if (feedbacks.length <= 1) {
      return
    }

    const timer = window.setInterval(() => {
      moveFeedbackCarousel('next')
    }, 4000)

    return () => window.clearInterval(timer)
  }, [feedbacks.length])

  return (
    <main className="min-h-screen bg-[linear-gradient(130deg,#edf1ff_0%,#f6f8ff_42%,#ffffff_100%)] text-[#2E3F86]">
      <header className="sticky top-0 z-20 border-b border-[#5E74C9]/10 bg-white/75 backdrop-blur">
        <div className="mx-auto flex w-full max-w-7xl items-center justify-between px-4 py-4 sm:px-6 lg:px-8">
          <a href="#home" className="text-sm font-bold tracking-[0.16em] text-[#5E74C9]">
            JURNAL AI FASTTRACK
          </a>

          <nav className="hidden items-center gap-6 text-sm font-medium text-[#5C70B2] md:flex">
            <a href="#home" className="transition-colors hover:text-[#4C61A8]">Home</a>
            <a href="#about" className="transition-colors hover:text-[#4C61A8]">About Us</a>
            <a href="#tech" className="transition-colors hover:text-[#4C61A8]">Tech Overview</a>
          </nav>

          <div className="flex items-center gap-2">
            <Button asChild variant="ghost" className="text-[#5E74C9] hover:bg-[#5E74C9]/10 hover:text-[#4C61A8]">
              <Link to="/login">Masuk</Link>
            </Button>
            <Button asChild className="bg-[#5E74C9] text-white hover:bg-[#5166B8]">
              <Link to="/register">Daftar</Link>
            </Button>
          </div>
        </div>
      </header>

      <section id="home" className="relative overflow-hidden px-4 py-20 sm:px-6 sm:py-24 lg:px-8 lg:py-28">
        <div className="pointer-events-none absolute -left-20 top-10 h-72 w-72 rounded-full bg-[#5E74C9]/12 blur-3xl" />
        <div className="pointer-events-none absolute -right-20 bottom-0 h-80 w-80 rounded-full bg-[#5E74C9]/10 blur-3xl" />

        <div className="relative mx-auto grid w-full max-w-7xl gap-10 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-[#5E74C9]/10 px-3 py-1 text-xs font-semibold text-[#5E74C9]">
              <BadgeCheck className="size-3.5" />
              Platform Profil Jurnal Berbasis AI
            </p>
            <h1 className="mt-5 text-balance text-4xl font-bold leading-tight text-[#2E3F86] sm:text-5xl">
              Profil singkat tim kami untuk percepatan review jurnal yang akurat.
            </h1>
            <p className="mt-4 max-w-2xl text-pretty text-base text-[#6A7DB7] sm:text-lg">
              Kami membangun alur review jurnal end-to-end: upload dokumen PDF,
              validasi cerdas, serta histori analisis yang mudah dipantau dalam satu dashboard.
            </p>

            <div className="mt-7 flex flex-col gap-3 sm:flex-row">
              <Button asChild size="lg" className="bg-[#5E74C9] text-white hover:bg-[#5166B8]">
                <Link to="/login">
                  Mulai Sekarang
                  <ArrowRight className="ml-1 size-4" />
                </Link>
              </Button>
              <Button asChild size="lg" variant="outline" className="border-[#5E74C9]/25 text-[#5E74C9] hover:bg-[#5E74C9]/8 hover:text-[#4C61A8]">
                <a href="#about">Pelajari Lebih Lanjut</a>
              </Button>
            </div>
          </div>

          <div className="space-y-4 text-[#5C70B2]">
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-white/85 p-5 shadow-[0_10px_30px_rgba(94,116,201,0.08)]">
              <h3 className="text-sm font-semibold text-[#2E3F86]">Misi Kami</h3>
              <p className="mt-2 text-sm">
                Membantu akademisi dan peneliti mendapatkan proses review lebih cepat tanpa mengorbankan kualitas.
              </p>
            </div>
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-white/85 p-5 shadow-[0_10px_30px_rgba(94,116,201,0.08)]">
              <h3 className="text-sm font-semibold text-[#2E3F86]">Fokus Produk</h3>
              <p className="mt-2 text-sm">
                Validasi dokumen, manajemen histori, dan pengalaman pengguna yang sederhana namun profesional.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section id="about" className="border-t border-[#5E74C9]/10 bg-white px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto grid w-full max-w-7xl gap-8 sm:grid-cols-2">
          <div>
            <h2 className="text-2xl font-semibold text-[#2E3F86]">About Us</h2>
            <p className="mt-2 text-sm text-[#6A7DB7]">
              Jurnal AI Fasttrack adalah tim produk yang fokus di automasi analisis dokumen akademik untuk workflow yang lebih terstruktur.
            </p>
          </div>
          <div className="grid gap-3 text-sm text-[#5C70B2]">
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-[#f8faff] p-4 shadow-[0_8px_22px_rgba(94,116,201,0.07)]">
              <p>Didukung antarmuka modern berbasis React + shadcn.</p>
            </div>
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-[#f8faff] p-4 shadow-[0_8px_22px_rgba(94,116,201,0.07)]">
              <p>Integrasi API Laravel untuk autentikasi dan manajemen dokumen.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="tech" className="border-t border-[#5E74C9]/10 bg-[#eaf0ff] px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl">
          <h2 className="text-2xl font-semibold text-[#2E3F86]">Tech Overview</h2>
          <div className="mt-6 grid gap-6 sm:grid-cols-3">
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-white/85 p-5 shadow-[0_10px_30px_rgba(94,116,201,0.08)]">
              <FileScan className="size-5 text-[#5E74C9]" />
              <h3 className="mt-3 text-sm font-semibold text-[#2E3F86]">Document Pipeline</h3>
              <p className="mt-2 text-sm text-[#6A7DB7]">Upload PDF, validasi ukuran/halaman, dan simpan histori otomatis.</p>
            </div>
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-white/85 p-5 shadow-[0_10px_30px_rgba(94,116,201,0.08)]">
              <ShieldCheck className="size-5 text-[#5E74C9]" />
              <h3 className="mt-3 text-sm font-semibold text-[#2E3F86]">Secure Access</h3>
              <p className="mt-2 text-sm text-[#6A7DB7]">Autentikasi token berbasis Laravel Sanctum untuk session aman.</p>
            </div>
            <div className="rounded-2xl border border-[#5E74C9]/15 bg-white/85 p-5 shadow-[0_10px_30px_rgba(94,116,201,0.08)]">
              <BadgeCheck className="size-5 text-[#5E74C9]" />
              <h3 className="mt-3 text-sm font-semibold text-[#2E3F86]">Fast UI</h3>
              <p className="mt-2 text-sm text-[#6A7DB7]">Responsif untuk desktop/mobile dengan performa tinggi.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-[#5E74C9]/10 bg-white px-4 py-16 sm:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl">
          <h2 className="text-2xl font-semibold text-[#2E3F86]">Feedback Pengguna</h2>
          <p className="mt-2 text-sm text-[#6A7DB7]">Ringkasan masukan dari pengguna Jurnal AI Fasttrack.</p>

          {isFeedbackLoading ? (
            <div className="mt-6 rounded-2xl border border-[#5E74C9]/15 bg-[#f7f9ff] p-6 text-sm text-[#6A7DB7]">
              Memuat feedback...
            </div>
          ) : feedbacks.length === 0 ? (
            <div className="mt-6 rounded-2xl border border-dashed border-[#5E74C9]/20 bg-[#f7f9ff] p-6 text-sm text-[#6A7DB7]">
              Belum ada feedback yang ditampilkan.
            </div>
          ) : (
            <div className="mt-6 grid grid-cols-[auto_1fr_auto] items-center gap-2 sm:gap-3">
              <Button
                type="button"
                variant="outline"
                size="icon"
                className="h-10 w-10 border-[#5E74C9]/20 text-[#2E3F86]"
                disabled={isFeedbackLoading || feedbacks.length <= 1}
                onClick={() => moveFeedbackCarousel('prev')}
                aria-label="Feedback sebelumnya"
              >
                <ChevronLeft className="size-5" />
              </Button>

              <div
                ref={feedbackCarouselRef}
                className="flex snap-x snap-mandatory gap-4 overflow-x-auto pb-2 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
              >
                {feedbacks.map((feedback, index) => (
                  <article
                    key={`${feedback.name}-${feedback.rating}-${index}`}
                    className="min-w-[85%] snap-start rounded-2xl border border-[#5E74C9]/15 bg-linear-to-br from-[#ffffff] to-[#f3f7ff] p-5 shadow-[0_12px_26px_rgba(94,116,201,0.08)] sm:min-w-[48%] lg:min-w-[32%]"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-semibold text-[#2E3F86]">{feedback.name}</p>
                      <span className="inline-flex items-center gap-1 rounded-full bg-[#5E74C9]/12 px-2.5 py-1 text-xs font-semibold text-[#2E3F86]">
                        <Star className="size-3.5 fill-current" />
                        {feedback.rating}/5
                      </span>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-[#5C70B2]">
                      {feedback.comment || 'Tanpa komentar'}
                    </p>
                  </article>
                ))}
              </div>

              <Button
                type="button"
                size="icon"
                className="h-10 w-10 bg-[#5E74C9] text-white hover:bg-[#5166B8]"
                disabled={isFeedbackLoading || feedbacks.length <= 1}
                onClick={() => moveFeedbackCarousel('next')}
                aria-label="Feedback berikutnya"
              >
                <ChevronRight className="size-5" />
              </Button>
            </div>
          )}
        </div>
      </section>

      <footer className="bg-[#141a3d] px-4 py-8 text-[#c8d3ff] sm:px-6 lg:px-8">
        <div className="mx-auto flex w-full max-w-7xl flex-col items-start justify-between gap-2 text-sm sm:flex-row sm:items-center">
          <p>© {new Date().getFullYear()} Jurnal AI Fasttrack. All rights reserved.</p>
          <p className="text-[#9fb1ff]">Built with React, shadcn/ui, and Laravel API.</p>
        </div>
      </footer>
    </main>
  )
}

export default HomePage
