import { useEffect, useMemo, useState } from 'react'
import { Eye, FileText, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  deleteAnalysis,
  getAnalysis,
  getAnalysisFileBlob,
  listAnalyses,
} from '@/lib/api'
import { getAuthToken } from '@/lib/auth'

function formatDate(value) {
  if (!value) {
    return '-'
  }

  return new Date(value).toLocaleString('id-ID', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

function HistoryJurnalPage() {
  const [items, setItems] = useState([])
  const [selectedDetail, setSelectedDetail] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [actionLoadingId, setActionLoadingId] = useState(null)

  const token = useMemo(() => getAuthToken(), [])

  async function loadHistory() {
    if (!token) {
      setErrorMessage('Token login tidak ditemukan. Silakan login ulang.')
      setIsLoading(false)
      return
    }

    setErrorMessage('')

    try {
      const response = await listAnalyses(token)
      setItems(response?.data?.analyses ?? [])
    } catch (error) {
      setErrorMessage(error.message || 'Gagal mengambil daftar jurnal.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadHistory()
  }, [])

  async function handleDelete(analysisId) {
    if (!token) {
      return
    }

    const confirmed = window.confirm('Yakin ingin menghapus dokumen ini?')

    if (!confirmed) {
      return
    }

    setActionLoadingId(analysisId)

    try {
      await deleteAnalysis(token, analysisId)
      setItems((prev) => prev.filter((item) => item.id !== analysisId))
      if (selectedDetail?.id === analysisId) {
        setSelectedDetail(null)
      }
    } catch (error) {
      setErrorMessage(error.message || 'Gagal menghapus dokumen.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleShowDetail(analysisId) {
    if (!token) {
      return
    }

    setActionLoadingId(analysisId)

    try {
      const response = await getAnalysis(token, analysisId)
      setSelectedDetail(response?.data?.analysis ?? null)
      setErrorMessage('')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal mengambil detail dokumen.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleShowPdf(analysisId) {
    if (!token) {
      return
    }

    setActionLoadingId(analysisId)

    try {
      const blob = await getAnalysisFileBlob(token, analysisId)
      const fileUrl = URL.createObjectURL(blob)
      window.open(fileUrl, '_blank', 'noopener,noreferrer')
      window.setTimeout(() => URL.revokeObjectURL(fileUrl), 10000)
      setErrorMessage('')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal menampilkan file PDF.')
    } finally {
      setActionLoadingId(null)
    }
  }

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-4">
      <Card className="border-[#5E74C9]/16 bg-white/90">
        <CardHeader>
          <CardTitle className="text-xl text-[#2E3F86]">History Jurnal</CardTitle>
          <CardDescription>
            Daftar dokumen yang sudah pernah kamu input.
          </CardDescription>
        </CardHeader>
      </Card>

      {errorMessage ? (
        <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          {errorMessage}
        </p>
      ) : null}

      {selectedDetail ? (
        <Card className="border-[#5E74C9]/16 bg-white/95">
          <CardHeader>
            <CardTitle className="text-base text-[#2E3F86]">Detail Dokumen</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-1 text-sm text-[#6A7DB7]">
            <p>Nama: {selectedDetail.doc_name}</p>
            <p>Tipe: {selectedDetail.doc_type}</p>
            <p>Status: {selectedDetail.status}</p>
            <p>Dibuat: {formatDate(selectedDetail.created_at)}</p>
            <p>Terakhir diubah: {formatDate(selectedDetail.updated_at)}</p>
          </CardContent>
        </Card>
      ) : null}

      {isLoading ? <p className="text-sm text-[#6A7DB7]">Memuat data...</p> : null}

      {!isLoading && items.length === 0 ? (
        <Card className="border-dashed border-[#5E74C9]/16 bg-white/85">
          <CardContent className="py-8 text-center text-sm text-[#6A7DB7]">
            Belum ada data jurnal yang tersimpan.
          </CardContent>
        </Card>
      ) : null}

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {items.map((item) => (
          <Card key={item.id} className="border-[#5E74C9]/16 bg-white/90">
            <CardHeader>
              <CardTitle className="line-clamp-2 text-base text-[#2E3F86]">
                {item.doc_name}
              </CardTitle>
              <CardDescription>
                {item.doc_type} • {formatDate(item.created_at)}
              </CardDescription>
            </CardHeader>
            <CardContent className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                disabled={actionLoadingId === item.id}
                onClick={() => handleShowDetail(item.id)}
              >
                <FileText className="mr-1 size-4" />
                Detail
              </Button>
              <Button
                type="button"
                variant="secondary"
                className="flex-1"
                disabled={actionLoadingId === item.id}
                onClick={() => handleShowPdf(item.id)}
              >
                <Eye className="mr-1 size-4" />
                Show
              </Button>
              <Button
                type="button"
                variant="destructive"
                className="px-3"
                disabled={actionLoadingId === item.id}
                onClick={() => handleDelete(item.id)}
              >
                <Trash2 className="size-4" />
              </Button>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  )
}

export default HistoryJurnalPage
