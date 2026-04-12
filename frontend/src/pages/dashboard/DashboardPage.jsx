import { useEffect, useState } from 'react'
import { LogOut, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchMe, logout } from '@/lib/api'
import { clearAuthSession, getAuthToken, getAuthUser, setAuthSession } from '@/lib/auth'

function DashboardPage() {
  const navigate = useNavigate()
  const [user, setUser] = useState(getAuthUser())
  const [isFetchingProfile, setIsFetchingProfile] = useState(true)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    const token = getAuthToken()

    if (!token) {
      navigate('/login', { replace: true })
      return
    }

    async function loadProfile() {
      setErrorMessage('')

      try {
        const response = await fetchMe(token)
        const profileUser = response?.data?.user

        if (profileUser) {
          setUser(profileUser)
          setAuthSession({ token, user: profileUser })
        }
      } catch (error) {
        clearAuthSession()
        navigate('/login', { replace: true })
        setErrorMessage(error.message || 'Sesi berakhir. Silakan login ulang.')
      } finally {
        setIsFetchingProfile(false)
      }
    }

    loadProfile()
  }, [navigate])

  async function handleLogout() {
    const token = getAuthToken()
    setIsLoggingOut(true)

    try {
      if (token) {
        await logout(token)
      }
    } catch {
      // Even if API logout fails, local session should still be cleared.
    } finally {
      clearAuthSession()
      navigate('/login', { replace: true })
      setIsLoggingOut(false)
    }
  }

  return (
    <main className="w-full">
      <div className="flex w-full flex-col gap-6">
        <header className="flex flex-col items-start justify-between gap-4 rounded-3xl border border-amber-200/70 bg-white/80 p-6 shadow-[0_20px_60px_rgba(120,75,20,0.12)] backdrop-blur sm:flex-row sm:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-900">
              <Sparkles className="size-3.5" />
              DASHBOARD
            </p>
            <h1 className="mt-3 text-2xl font-semibold text-stone-900 sm:text-3xl">
              Halo, {user?.name || 'Developer'}
            </h1>
            <p className="mt-1 text-sm text-stone-600">
              Selamat datang kembali di Agent Review Fasttrack.
            </p>
          </div>

          <Button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="h-10 bg-stone-900 text-white hover:bg-stone-800"
          >
            <LogOut className="mr-1 size-4" />
            {isLoggingOut ? 'Keluar...' : 'Logout'}
          </Button>
        </header>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <Card className="border-amber-100 bg-white/90">
            <CardHeader>
              <CardTitle className="text-sm text-stone-700">Email akun</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base font-medium text-stone-900">{user?.email || '-'}</p>
            </CardContent>
          </Card>

          <Card className="border-amber-100 bg-white/90">
            <CardHeader>
              <CardTitle className="text-sm text-stone-700">Status</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base font-medium text-emerald-700">Aktif</p>
            </CardContent>
          </Card>

          <Card className="border-amber-100 bg-white/90 sm:col-span-2 lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-sm text-stone-700">Aksi selanjutnya</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-base text-stone-900">Hubungkan menu ini ke fitur analisis proyek.</p>
            </CardContent>
          </Card>
        </section>

        {isFetchingProfile ? (
          <p className="text-sm text-stone-600">Mengambil data akun...</p>
        ) : null}

        {errorMessage ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {errorMessage}
          </p>
        ) : null}
      </div>
    </main>
  )
}

export default DashboardPage
