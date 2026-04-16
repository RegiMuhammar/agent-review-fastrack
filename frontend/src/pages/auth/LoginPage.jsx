import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'

import AuthShell from '@/components/auth/AuthShell'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { login } from '@/lib/api'
import { setAuthSession } from '@/lib/auth'

function LoginPage() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setErrorMessage('')
    setIsSubmitting(true)

    try {
      const response = await login({ email, password })
      const authData = response?.data

      if (!authData?.token || !authData?.user) {
        throw new Error('Respon login tidak lengkap.')
      }

      setAuthSession({
        token: authData.token,
        user: authData.user,
      })

      navigate('/dashboard', { replace: true })
    } catch (error) {
      setErrorMessage(error.message || 'Login gagal. Silakan coba lagi.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthShell
      mode="login"
      title="Selamat datang kembali"
      subtitle="Masuk untuk melanjutkan analisis jurnalmu."
    >
      <Card className="bg-white/85 shadow-none ring-0">
        <CardHeader className="px-0 sm:px-1">
          <CardTitle className="text-base text-[#2E3F86]">Login akun</CardTitle>
          <CardDescription>
            Gunakan email dan password yang terdaftar.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 px-0 sm:px-1">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <Label htmlFor="login-email">Email</Label>
              <Input
                id="login-email"
                type="email"
                placeholder="nama@company.com"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <div className="flex items-center justify-between gap-3">
                <Label htmlFor="login-password">Password</Label>
                <a
                  href="#"
                  className="text-xs font-medium text-[#5E74C9] transition-colors hover:text-[#5166B8]"
                >
                  Lupa password?
                </a>
              </div>
              <Input
                id="login-password"
                type="password"
                placeholder="Masukkan password"
                autoComplete="current-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </div>

            <div className="flex items-center gap-2 text-sm text-[#6A7DB7]">
              <input
                id="remember"
                type="checkbox"
                className="size-4 rounded border-[#5E74C9]/28 text-[#5E74C9] focus:ring-[#5E74C9]"
              />
              <Label htmlFor="remember" className="text-sm font-normal">
                Tetap masuk di perangkat ini
              </Label>
            </div>

            {errorMessage ? (
              <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {errorMessage}
              </p>
            ) : null}

            <Button
              type="submit"
              disabled={isSubmitting}
              className="h-10 w-full bg-[#5E74C9] text-white hover:bg-[#5166B8]"
            >
              {isSubmitting ? 'Memproses...' : 'Masuk'}
            </Button>
          </form>

          <p className="text-center text-sm text-[#6A7DB7]">
            Belum punya akun?{' '}
            <Link
              to="/register"
              className="font-semibold text-[#5E74C9] hover:text-[#5166B8]"
            >
              Daftar sekarang
            </Link>
          </p>
        </CardContent>
      </Card>
    </AuthShell>
  )
}

export default LoginPage
