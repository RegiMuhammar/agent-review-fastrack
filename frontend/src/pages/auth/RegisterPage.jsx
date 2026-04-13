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
import { register } from '@/lib/api'
import { setAuthSession } from '@/lib/auth'

function RegisterPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()
    setErrorMessage('')

    if (password !== passwordConfirmation) {
      setErrorMessage('Konfirmasi password tidak sama.')
      return
    }

    setIsSubmitting(true)

    try {
      const response = await register({
        name,
        email,
        password,
      })

      const authData = response?.data

      if (!authData?.token || !authData?.user) {
        throw new Error('Respon registrasi tidak lengkap.')
      }

      setAuthSession({
        token: authData.token,
        user: authData.user,
      })

      navigate('/dashboard', { replace: true })
    } catch (error) {
      setErrorMessage(error.message || 'Registrasi gagal. Silakan coba lagi.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <AuthShell
      mode="register"
      title="Buat akun baru"
      subtitle="Daftar untuk mulai menggunakan Jurnal AI Fasttrack."
    >
      <Card className="bg-white/85 shadow-none ring-0">
        <CardHeader className="px-0 sm:px-1">
          <CardTitle className="text-base text-[#2E3F86]">Registrasi</CardTitle>
          <CardDescription>
            Isi data di bawah untuk membuat akun baru.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-4 px-0 sm:px-1">
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-1.5">
              <Label htmlFor="register-name">Nama lengkap</Label>
              <Input
                id="register-name"
                type="text"
                placeholder="Nama lengkap"
                autoComplete="name"
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
              />
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="register-email">Email</Label>
              <Input
                id="register-email"
                type="email"
                placeholder="nama@company.com"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label htmlFor="register-password">Password</Label>
                <Input
                  id="register-password"
                  type="password"
                  placeholder="Minimal 8 karakter"
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="register-password-confirmation">
                  Konfirmasi password
                </Label>
                <Input
                  id="register-password-confirmation"
                  type="password"
                  placeholder="Ulangi password"
                  autoComplete="new-password"
                  value={passwordConfirmation}
                  onChange={(event) => setPasswordConfirmation(event.target.value)}
                  required
                />
              </div>
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
              {isSubmitting ? 'Memproses...' : 'Buat akun'}
            </Button>
          </form>

          <p className="text-center text-sm text-[#6A7DB7]">
            Sudah punya akun?{' '}
            <Link
              to="/login"
              className="font-semibold text-[#5E74C9] hover:text-[#5166B8]"
            >
              Login di sini
            </Link>
          </p>
        </CardContent>
      </Card>
    </AuthShell>
  )
}

export default RegisterPage
