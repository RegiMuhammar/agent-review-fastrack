import { Sparkles, ShieldCheck, Zap } from 'lucide-react'
import { Link } from 'react-router-dom'

import { Button } from '@/components/ui/button'

function AuthShell({
  mode,
  title,
  subtitle,
  children,
}) {
  return (
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,#e9eeff_0%,#f5f8ff_45%,#ffffff_100%)] px-4 py-8 sm:px-6 md:px-8">
      <div className="pointer-events-none absolute -left-20 top-6 h-60 w-60 rounded-full bg-[#5E74C9]/18 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-72 w-72 rounded-full bg-[#5E74C9]/14 blur-3xl" />

      <div className="relative mx-auto grid w-full max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <section className="hidden rounded-3xl border border-[#5E74C9]/18 bg-white/70 p-8 shadow-[0_12px_50px_rgba(94,116,201,0.11)] backdrop-blur lg:block">
          <p className="inline-flex items-center gap-2 rounded-full border border-[#5E74C9]/20 bg-[#5E74C9]/8 px-3 py-1 text-xs font-semibold tracking-wide text-[#5E74C9]">
            <Sparkles className="size-3.5" />
            JURNAL AI FASTTRACK
          </p>

          <h1 className="mt-5 text-balance text-4xl font-bold tracking-tight text-[#2E3F86]">
            Workspace analisa jurnal yang cepat, rapi, dan siap kolaborasi.
          </h1>
          <p className="mt-3 max-w-xl text-pretty text-[#6A7DB7]">
            Masuk untuk lanjut review jurnal dan pantau riwayat analisis.
          </p>

          <div className="mt-8 grid gap-3 text-sm">
            <div className="flex items-center gap-3 rounded-xl border border-[#5E74C9]/14 bg-white px-4 py-3 text-[#5C70B2]">
              <Zap className="size-4 text-[#5E74C9]" />
              Pipeline analisis cepat dengan insight yang bisa dieksekusi.
            </div>
            <div className="flex items-center gap-3 rounded-xl border border-[#5E74C9]/14 bg-white px-4 py-3 text-[#5C70B2]">
              <ShieldCheck className="size-4 text-[#5E74C9]" />
              Akses akun aman untuk tim developer dan reviewer.
            </div>
          </div>
        </section>

        <section className="animate-in fade-in zoom-in-95 duration-500">
          <div className="rounded-3xl border border-white/70 bg-white/90 p-6 shadow-[0_20px_70px_rgba(94,116,201,0.12)] backdrop-blur sm:p-8">
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-[#5E74C9]/8 p-1">
              <Button
                asChild
                variant={mode === 'login' ? 'default' : 'ghost'}
                className="h-9"
              >
                <Link to="/login">Login</Link>
              </Button>
              <Button
                asChild
                variant={mode === 'register' ? 'default' : 'ghost'}
                className="h-9"
              >
                <Link to="/register">Register</Link>
              </Button>
            </div>

            <div className="mt-6 space-y-1.5">
              <h2 className="text-2xl font-semibold tracking-tight text-[#2E3F86]">
                {title}
              </h2>
              <p className="text-sm text-[#6A7DB7]">{subtitle}</p>
            </div>

            <div className="mt-6">{children}</div>
          </div>
        </section>
      </div>
    </main>
  )
}

export default AuthShell
