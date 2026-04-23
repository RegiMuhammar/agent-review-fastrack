import { useEffect, useState } from 'react'
import { Building2, Save, UserRound } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

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
import { fetchMe, updateProfile } from '@/lib/api'
import { clearAuthSession, getAuthToken, getAuthUser, setAuthSession } from '@/lib/auth'

function ProfilePage() {
  const navigate = useNavigate()
  const [user, setUser] = useState(getAuthUser())
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [password, setPassword] = useState('')
  const [passwordConfirmation, setPasswordConfirmation] = useState('')
  const [isLoadingProfile, setIsLoadingProfile] = useState(true)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  function applyUserToForm(profileUser) {
    setName(profileUser?.name || '')
    setEmail(profileUser?.email || '')
    setCompanyName(profileUser?.company_name || '')
  }

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

        if (!profileUser) {
          throw new Error('Data profile tidak ditemukan.')
        }

        setUser(profileUser)
        applyUserToForm(profileUser)
        setAuthSession({ token, user: profileUser })
      } catch (error) {
        clearAuthSession()
        navigate('/login', { replace: true })
        setErrorMessage(error.message || 'Sesi berakhir. Silakan login ulang.')
      } finally {
        setIsLoadingProfile(false)
      }
    }

    if (user) {
      applyUserToForm(user)
    }

    loadProfile()
  }, [navigate])

  async function handleSubmit(event) {
    event.preventDefault()

    const token = getAuthToken()

    if (!token) {
      setErrorMessage('Sesi login tidak ditemukan. Silakan login ulang.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage('')
    setSuccessMessage('')

    try {
      const payload = {
        name,
        email,
        company_name: companyName || null,
      }

      if (password) {
        payload.password = password
        payload.password_confirmation = passwordConfirmation
      }

      const response = await updateProfile(token, payload)
      const updatedUser = response?.data?.user

      if (!updatedUser) {
        throw new Error('Respon update profile tidak lengkap.')
      }

      setUser(updatedUser)
      setPassword('')
      setPasswordConfirmation('')
      setAuthSession({ token, user: updatedUser })
      setSuccessMessage('Profile berhasil diperbarui.')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal memperbarui profile.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="w-full">
      <div className="flex w-full flex-col gap-6">
        <header className="flex flex-col items-start justify-between gap-4 rounded-3xl border border-[#5E74C9]/16 bg-white/85 p-6 shadow-[0_20px_60px_rgba(94,116,201,0.11)] backdrop-blur sm:flex-row sm:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-[#5E74C9]/10 px-3 py-1 text-xs font-semibold text-[#5E74C9]">
              <UserRound className="size-3.5" />
              PROFILE
            </p>
            <h1 className="mt-3 text-2xl font-semibold text-[#2E3F86] sm:text-3xl">
              Edit Profile
            </h1>
            <p className="mt-1 text-sm text-[#6A7DB7]">
              Kelola data akun Anda yang digunakan untuk login.
            </p>
          </div>
        </header>

        <Card className="border-[#5E74C9]/16 bg-white/85 shadow-[0_20px_60px_rgba(94,116,201,0.11)] backdrop-blur">
          <CardHeader>
            <CardTitle className="text-xl text-[#2E3F86]">Informasi Akun</CardTitle>
            <CardDescription>
              Data yang dapat diubah: nama, email, nama perusahaan, dan password.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="grid gap-5" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="profile-name">Nama</Label>
                <Input
                  id="profile-name"
                  type="text"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Nama lengkap"
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="profile-email">Email</Label>
                <Input
                  id="profile-email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="nama@company.com"
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="profile-company" className="gap-1.5">
                  <Building2 className="size-3.5" />
                  Nama Perusahaan
                </Label>
                <Input
                  id="profile-company"
                  type="text"
                  value={companyName}
                  onChange={(event) => setCompanyName(event.target.value)}
                  placeholder="Opsional"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="profile-password">Password Baru</Label>
                <Input
                  id="profile-password"
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Kosongkan jika tidak ingin ganti"
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="profile-password-confirmation">Konfirmasi Password Baru</Label>
                <Input
                  id="profile-password-confirmation"
                  type="password"
                  value={passwordConfirmation}
                  onChange={(event) => setPasswordConfirmation(event.target.value)}
                  placeholder="Ulangi password baru"
                />
              </div>

              {successMessage ? (
                <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {successMessage}
                </p>
              ) : null}

              {errorMessage ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {errorMessage}
                </p>
              ) : null}

              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  type="submit"
                  disabled={isSubmitting || isLoadingProfile}
                  className="h-10 w-full bg-[#5E74C9] text-white hover:bg-[#5166B8] sm:w-auto"
                >
                  <Save className="mr-1 size-4" />
                  {isSubmitting ? 'Menyimpan...' : 'Simpan Perubahan'}
                </Button>
                <Button type="button" variant="outline" onClick={() => navigate('/dashboard')}>
                  Kembali ke Dashboard
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {isLoadingProfile ? (
          <p className="text-sm text-[#6A7DB7]">Mengambil data profile...</p>
        ) : null}
      </div>
    </main>
  )
}

export default ProfilePage
