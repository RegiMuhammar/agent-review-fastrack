import { useEffect, useRef, useState } from 'react'
import { FileText, LogOut, Paperclip, Sparkles } from 'lucide-react'
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
import { createAnalysis, fetchMe, logout } from '@/lib/api'
import { clearAuthSession, getAuthToken, getAuthUser, setAuthSession } from '@/lib/auth'

function DashboardPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [user, setUser] = useState(getAuthUser())
  const [namaJurnal, setNamaJurnal] = useState('')
  const [tipeJurnal, setTipeJurnal] = useState('essay')
  const [uploadFile, setUploadFile] = useState(null)
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const [isSubmittingJurnal, setIsSubmittingJurnal] = useState(false)
  const [formErrorMessage, setFormErrorMessage] = useState('')
  const [formSuccessMessage, setFormSuccessMessage] = useState('')
  const [isFetchingProfile, setIsFetchingProfile] = useState(true)
  const [isLoggingOut, setIsLoggingOut] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  function handleSelectFile(file) {
    if (!file) {
      return
    }

    setUploadFile(file)
    setFormErrorMessage('')
  }

  function handleInputFileChange(event) {
    handleSelectFile(event.target.files?.[0] ?? null)
  }

  function handleDropFile(event) {
    event.preventDefault()
    setIsDraggingFile(false)
    handleSelectFile(event.dataTransfer.files?.[0] ?? null)
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

  async function handleSubmitJurnal(event) {
    event.preventDefault()

    const token = getAuthToken()

    if (!token) {
      setFormErrorMessage('Sesi login tidak ditemukan. Silakan login ulang.')
      return
    }

    if (!uploadFile) {
      setFormErrorMessage('File jurnal wajib diupload.')
      return
    }

    setIsSubmittingJurnal(true)
    setFormErrorMessage('')
    setFormSuccessMessage('')

    try {
      await createAnalysis(token, {
        docName: namaJurnal,
        docType: tipeJurnal,
        file: uploadFile,
      })

      setNamaJurnal('')
      setTipeJurnal('essay')
      setUploadFile(null)
      event.target.reset()
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      setFormSuccessMessage('Dokumen berhasil diupload.')
    } catch (error) {
      setFormErrorMessage(error.message || 'Gagal mengirim data jurnal.')
    } finally {
      setIsSubmittingJurnal(false)
    }
  }

  return (
    <main className="w-full">
      <div className="flex w-full flex-col gap-6">
        <header className="flex flex-col items-start justify-between gap-4 rounded-3xl border border-[#5E74C9]/16 bg-white/85 p-6 shadow-[0_20px_60px_rgba(94,116,201,0.11)] backdrop-blur sm:flex-row sm:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full bg-[#5E74C9]/10 px-3 py-1 text-xs font-semibold text-[#5E74C9]">
              <Sparkles className="size-3.5" />
              DASHBOARD
            </p>
            <h1 className="mt-3 text-2xl font-semibold text-[#2E3F86] sm:text-3xl">
              Halo, {user?.name || 'Developer'}
            </h1>
            <p className="mt-1 text-sm text-[#6A7DB7]">
              Selamat datang kembali di Jurnal AI Fasttrack.
            </p>
          </div>

          <Button
            type="button"
            onClick={handleLogout}
            disabled={isLoggingOut}
            className="h-10 bg-[#5E74C9] text-white hover:bg-[#5166B8]"
          >
            <LogOut className="mr-1 size-4" />
            {isLoggingOut ? 'Keluar...' : 'Logout'}
          </Button>
        </header>

        <Card className="border-[#5E74C9]/16 bg-white/85 shadow-[0_20px_60px_rgba(94,116,201,0.11)] backdrop-blur">
          <CardHeader>
            <CardTitle className="text-xl text-[#2E3F86]">Review Jurnal</CardTitle>
            <CardDescription>
              Lengkapi data jurnal untuk proses review.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="grid gap-5" onSubmit={handleSubmitJurnal}>
              <div className="grid gap-2">
                <Label htmlFor="nama-jurnal-dashboard">Nama Jurnal</Label>
                <Input
                  id="nama-jurnal-dashboard"
                  type="text"
                  placeholder="Contoh: Analisis Transformasi Digital"
                  value={namaJurnal}
                  onChange={(event) => setNamaJurnal(event.target.value)}
                  required
                />
              </div>

              <div className="grid gap-2">
                <Label htmlFor="tipe-jurnal-dashboard">Tipe Jurnal</Label>
                <select
                  id="tipe-jurnal-dashboard"
                  value={tipeJurnal}
                  onChange={(event) => setTipeJurnal(event.target.value)}
                  className="h-10 rounded-lg border border-input bg-background px-3 text-sm text-[#2E3F86] outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                  required
                >
                  <option value="essay">Essay</option>
                  <option value="research">Research</option>
                  <option value="bizplan">Bizplan</option>
                </select>
              </div>

              <div className="grid gap-2">
                <Label htmlFor="upload-file-dashboard" className="gap-1.5">
                  <Paperclip className="size-3.5" />
                  Paper PDF *
                </Label>

                <input
                  ref={fileInputRef}
                  id="upload-file-dashboard"
                  type="file"
                  accept="application/pdf,.pdf"
                  onChange={handleInputFileChange}
                  className="sr-only"
                  required
                />

                <label
                  htmlFor="upload-file-dashboard"
                  onDrop={handleDropFile}
                  onDragOver={(event) => event.preventDefault()}
                  onDragEnter={() => setIsDraggingFile(true)}
                  onDragLeave={() => setIsDraggingFile(false)}
                  className={`cursor-pointer rounded-2xl border border-dashed bg-[#5E74C9]/5 p-8 text-center transition-all ${
                    isDraggingFile
                      ? 'border-[#5E74C9] bg-[#5E74C9]/10'
                      : 'border-[#5E74C9]/20 hover:border-[#5E74C9]/35 hover:bg-[#5E74C9]/8'
                  }`}
                >
                  <span className="mx-auto mb-4 flex size-14 items-center justify-center rounded-2xl bg-[#5E74C9]/12 text-[#5E74C9]">
                    <FileText className="size-6" />
                  </span>

                  <p className="text-lg font-medium text-[#2E3F86]">
                    Choose PDF file or drag and drop
                  </p>
                  <p className="mt-1 text-sm text-[#6A7DB7]">
                    Max 10MB • First 15 pages analyzed
                  </p>

                  {uploadFile ? (
                    <p className="mt-3 text-sm font-medium text-[#5E74C9]">
                      {uploadFile.name}
                    </p>
                  ) : null}
                </label>
              </div>

              {formSuccessMessage ? (
                <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-700">
                  {formSuccessMessage}
                </p>
              ) : null}

              {formErrorMessage ? (
                <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                  {formErrorMessage}
                </p>
              ) : null}

              <div className="flex flex-col gap-2 sm:flex-row">
                <Button
                  type="submit"
                  disabled={isSubmittingJurnal}
                  className="h-10 w-full bg-[#5E74C9] text-white hover:bg-[#5166B8] sm:w-auto"
                >
                  {isSubmittingJurnal ? 'Menyimpan...' : 'Simpan Data Jurnal'}
                </Button>
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => navigate('/history-jurnal')}
                >
                  Lihat History Jurnal
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {isFetchingProfile ? (
          <p className="text-sm text-[#6A7DB7]">Mengambil data akun...</p>
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
