import { useRef, useState } from 'react'
import { FileText, Paperclip } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import AlertPopup from '@/components/ui/alert-popup'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { createAnalysis } from '@/lib/api'
import { getAuthToken } from '@/lib/auth'

function ReviewJurnalPage() {
  const navigate = useNavigate()
  const fileInputRef = useRef(null)
  const [namaJurnal, setNamaJurnal] = useState('')
  const [tipeJurnal, setTipeJurnal] = useState('essay')
  const [uploadFile, setUploadFile] = useState(null)
  const [isDraggingFile, setIsDraggingFile] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [successMessage, setSuccessMessage] = useState('')
  const [alertState, setAlertState] = useState({
    open: false,
    title: '',
    description: '',
  })

  function handleSelectFile(file) {
    if (!file) {
      return
    }

    setUploadFile(file)
    setErrorMessage('')
  }

  function handleInputFileChange(event) {
    handleSelectFile(event.target.files?.[0] ?? null)
  }

  function handleDropFile(event) {
    event.preventDefault()
    setIsDraggingFile(false)
    handleSelectFile(event.dataTransfer.files?.[0] ?? null)
  }

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
      const response = await createAnalysis(token, {
        docName: namaJurnal,
        docType: tipeJurnal,
        file: uploadFile,
      })

      const createdAnalysisId = response?.data?.analysis?.id

      if (createdAnalysisId) {
        setAlertState({
          open: true,
          title: 'Upload Berhasil',
          description: 'Dokumen berhasil diupload. Anda akan diarahkan ke halaman history.',
        })
        return
      }

      setNamaJurnal('')
      setTipeJurnal('essay')
      setUploadFile(null)
      event.target.reset()
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
      setSuccessMessage('Dokumen berhasil diupload.')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal mengirim data jurnal.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="w-full">
      <AlertPopup
        open={alertState.open}
        title={alertState.title}
        description={alertState.description}
        variant="success"
        onConfirm={() => {
          setAlertState({ open: false, title: '', description: '' })
          navigate('/history-jurnal')
        }}
      />

      <Card className="border-[#5E74C9]/16 bg-white/85 shadow-[0_20px_60px_rgba(94,116,201,0.11)] backdrop-blur">
        <CardHeader>
          <CardTitle className="text-xl text-[#2E3F86]">Review Jurnal</CardTitle>
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
                className="h-10 rounded-lg border border-input bg-background px-3 text-sm text-[#2E3F86] outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
                required
              >
                <option value="essay">Essay</option>
                <option value="research">Research</option>
                <option value="bizplan">Bizplan</option>
              </select>
            </div>

            <div className="grid gap-2">
              <Label htmlFor="upload-file" className="gap-1.5">
                <Paperclip className="size-3.5" />
                Paper PDF *
              </Label>

              <input
                ref={fileInputRef}
                id="upload-file"
                type="file"
                accept="application/pdf,.pdf"
                onChange={handleInputFileChange}
                className="sr-only"
                required
              />

              <label
                htmlFor="upload-file"
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
                className="h-10 w-full bg-[#5E74C9] text-white hover:bg-[#5166B8] sm:w-auto"
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
