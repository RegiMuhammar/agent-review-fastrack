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
    <main className="relative min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_right,_#f8e7cf_0%,_#f4f0e7_45%,_#f7f6f3_100%)] px-4 py-8 sm:px-6 md:px-8">
      <div className="pointer-events-none absolute -left-20 top-6 h-60 w-60 rounded-full bg-amber-200/45 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-0 h-72 w-72 rounded-full bg-orange-300/40 blur-3xl" />

      <div className="relative mx-auto grid w-full max-w-6xl gap-8 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <section className="hidden rounded-3xl border border-amber-200/70 bg-white/70 p-8 shadow-[0_12px_50px_rgba(150,95,30,0.12)] backdrop-blur lg:block">
          <p className="inline-flex items-center gap-2 rounded-full border border-amber-300/70 bg-amber-100/65 px-3 py-1 text-xs font-semibold tracking-wide text-amber-900">
            <Sparkles className="size-3.5" />
            AGENT REVIEW FASTTRACK
          </p>

          <h1 className="mt-5 text-balance text-4xl font-bold tracking-tight text-stone-900">
            Workspace analisa kode yang cepat, rapi, dan siap kolaborasi.
          </h1>
          <p className="mt-3 max-w-xl text-pretty text-stone-600">
            Masuk untuk lanjut review proyek, pantau riwayat analisis, dan bagikan hasil feedback dalam satu alur kerja.
          </p>

          <div className="mt-8 grid gap-3 text-sm">
            <div className="flex items-center gap-3 rounded-xl border border-amber-100 bg-white px-4 py-3 text-stone-700">
              <Zap className="size-4 text-amber-700" />
              Pipeline analisis cepat dengan insight yang bisa dieksekusi.
            </div>
            <div className="flex items-center gap-3 rounded-xl border border-amber-100 bg-white px-4 py-3 text-stone-700">
              <ShieldCheck className="size-4 text-amber-700" />
              Akses akun aman untuk tim developer dan reviewer.
            </div>
          </div>
        </section>

        <section className="animate-in fade-in zoom-in-95 duration-500">
          <div className="rounded-3xl border border-white/70 bg-white/90 p-6 shadow-[0_20px_70px_rgba(99,57,20,0.15)] backdrop-blur sm:p-8">
            <div className="grid grid-cols-2 gap-2 rounded-xl bg-amber-50/90 p-1">
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
              <h2 className="text-2xl font-semibold tracking-tight text-stone-900">
                {title}
              </h2>
              <p className="text-sm text-stone-600">{subtitle}</p>
            </div>

            <div className="mt-6">{children}</div>
          </div>
        </section>
      </div>
    </main>
  )
}

export default AuthShell
