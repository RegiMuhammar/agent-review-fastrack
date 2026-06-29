import { useEffect, useRef, useState } from 'react'
import {
  ArrowRight,
  BadgeCheck,
  ChevronLeft,
  ChevronRight,
  FileScan,
  ShieldCheck,
  Sparkles,
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

      <section
        id="home"
        className="relative min-h-[calc(100svh-4rem)] overflow-hidden bg-[linear-gradient(130deg,#edf1ff_0%,#f6f8ff_42%,#ffffff_100%)] flex flex-col"
      >
        {/* Background Video */}
        <video
          autoPlay
          loop
          muted
          playsInline
          className="pointer-events-none absolute inset-0 h-full w-full object-cover"
        >
          <source
            src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260302_085640_276ea93b-d7da-4418-a09b-2aa5b490e838.mp4"
            type="video/mp4"
          />
        </video>
        {/* Overlay for text readability */}
        <div className="pointer-events-none absolute inset-0 bg-white/10 backdrop-blur-[1px]" />

        {/* Spacer between navbar and hero content */}
        <div className="flex-1 min-h-8 sm:min-h-12 lg:min-h-16 shrink-0" />

        {/* Hero Content — centered */}
        <div className="relative z-10 mx-auto flex max-w-3xl flex-col items-center px-4 text-center sm:px-6">
          {/* Badge */}
          <p className="animate-fade-up inline-flex items-center gap-2 rounded-full bg-[#5E74C9]/10 px-4 py-1.5 text-xs font-semibold text-[#5E74C9]">
            <Sparkles className="size-3.5" />
            Powered by AI Agent Pipeline
          </p>

          {/* Headline */}
          <h1 className="mt-6 font-bold leading-[1.05] tracking-tight text-[#2E3F86] text-[40px] min-[400px]:text-[44px] sm:text-6xl lg:text-7xl">
            <span className="animate-fade-up block">Review Dokumen</span>
            <span className="animate-fade-up block [animation-delay:100ms]">
              10x Lebih Cepat.
            </span>
          </h1>

          {/* Description */}
          <p className="animate-fade-up [animation-delay:220ms] mt-5 max-w-lg text-[#6A7DB7] text-sm sm:text-base lg:text-lg leading-relaxed">
            Upload PDF — dapatkan skor mendalam, feedback naratif,
            <br className="hidden sm:block" />
            dan referensi relevan dalam hitungan menit.{' '}
            <span className="font-medium text-[#2E3F86]">Bukan minggu.</span>
          </p>

          {/* CTA Buttons */}
          <div className="animate-fade-up [animation-delay:340ms] mt-6 flex flex-wrap items-center justify-center gap-3">
            <Button asChild size="lg" className="bg-[#5E74C9] text-white text-sm font-medium px-7 py-3 rounded-full hover:bg-[#5166B8] hover:shadow-lg transition-all">
              <Link to="/register">
                Mulai Review Gratis
                <ArrowRight className="ml-1.5 size-4" />
              </Link>
            </Button>
            <Button asChild size="lg" variant="outline" className="border-[#5E74C9]/25 text-[#5E74C9] text-sm font-medium px-7 py-3 rounded-full hover:bg-[#5E74C9]/8 hover:text-[#4C61A8] transition-colors">
              <a href="#tech">Lihat Demo</a>
            </Button>
          </div>
        </div>

        {/* Spacer between content and mockup */}
        <div className="flex-1 min-h-10 sm:min-h-12 lg:min-h-16 shrink-0" />

        {/* Dashboard Mockup */}
        <div className="animate-hero-rise [animation-delay:500ms] relative z-0 w-[92%] sm:w-[84%] lg:w-[72%] max-w-5xl mx-auto shrink-0 -mb-10 sm:-mb-20 lg:-mb-32">
          <div className="rounded-t-2xl overflow-hidden bg-[#1a1a1c] shadow-[0_-20px_80px_rgba(0,0,0,0.25)] ring-1 ring-white/10">
            {/* Browser Title Bar */}
            <div className="bg-[#242427] border-b border-white/5 px-4 py-2.5 flex items-center gap-3">
              {/* Traffic lights */}
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#ff5f57]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#febc2e]" />
                <span className="w-2.5 h-2.5 rounded-full bg-[#28c840]" />
              </div>
              {/* URL bar */}
              <div className="flex-1 flex justify-center">
                <div className="bg-[#1a1a1c] rounded-md px-6 py-1 text-[10px] text-white/60 flex items-center gap-1.5">
                  <ShieldCheck className="w-3 h-3 text-white/40" />
                  jurnal-ai-fasttrack.app
                </div>
              </div>
              {/* Spacer for symmetry */}
              <div className="w-[52px]" />
            </div>
            {/* Screenshot */}
            <img
              src="/Demo.png"
              alt="Dashboard Jurnal AI Fasttrack — menampilkan hasil review dokumen dengan skor, profil dimensi, dan feedback naratif"
              className="w-full block"
              loading="eager"
            />
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
