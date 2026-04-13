import { ArrowRight, BadgeCheck, FileScan, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

function HomePage() {
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
