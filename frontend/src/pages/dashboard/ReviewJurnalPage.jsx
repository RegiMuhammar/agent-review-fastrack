import { useState } from 'react'
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
import { createAnalysis } from '@/lib/api'
import { getAuthToken } from '@/lib/auth'

function ReviewJurnalPage() {
  const navigate = useNavigate()
  const [namaJurnal, setNamaJurnal] = useState('')
  const [tipeJurnal, setTipeJurnal] = useState('essay')
  const [uploadFile, setUploadFile] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')

  async function handleSubmit(event) {
    event.preventDefault()

    const token = getAuthToken()

    if (!token) {
      setErrorMessage('Sesi login tidak ditemukan. Silakan login ulang.')
      return
    }

    if (!uploadFile) {
      setErrorMessage('File jurnal wajib diupload.')
      return
    }

    setIsSubmitting(true)
    setErrorMessage('')
    setSuccessMessage('')

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
      setSuccessMessage('Dokumen berhasil diupload.')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal mengirim data jurnal.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl">
      <Card className="border-amber-200/70 bg-white/85 shadow-[0_20px_60px_rgba(120,75,20,0.12)] backdrop-blur">
        <CardHeader>
          <CardTitle className="text-xl text-stone-900">Review Jurnal</CardTitle>
          <CardDescription>
            Lengkapi data jurnal untuk proses review.
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="grid gap-5" onSubmit={handleSubmit}>
            <div className="grid gap-2">
              <Label htmlFor="nama-jurnal">Nama Jurnal</Label>
              <Input
                id="nama-jurnal"
                type="text"
                placeholder="Contoh: Analisis Transformasi Digital"
                value={namaJurnal}
                onChange={(event) => setNamaJurnal(event.target.value)}
                required
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="tipe-jurnal">Tipe Jurnal</Label>
              <select
                id="tipe-jurnal"
                value={tipeJurnal}
                onChange={(event) => setTipeJurnal(event.target.value)}
                className="h-10 rounded-lg border border-input bg-background px-3 text-sm text-stone-900 outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                required
              >
                <option value="essay">Essay</option>
                <option value="research">Research</option>
                <option value="bizplan">Bizplan</option>
              </select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="upload-file">Upload File</Label>
              <Input
                id="upload-file"
                type="file"
                accept="application/pdf,.pdf"
                onChange={(event) => setUploadFile(event.target.files?.[0] ?? null)}
                required
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
                disabled={isSubmitting}
                className="h-10 w-full bg-amber-700 text-white hover:bg-amber-800 sm:w-auto"
              >
                {isSubmitting ? 'Menyimpan...' : 'Simpan Data Jurnal'}
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
    </div>
  )
}

export default ReviewJurnalPage
