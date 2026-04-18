import { useEffect, useMemo, useState } from 'react'
import { Eye, FileText, Trash2 } from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import AlertPopup from '@/components/ui/alert-popup'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  deleteAnalysis,
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

function getStatusPillClass(status) {
  if (status === 'done') {
    return 'border-emerald-200 bg-emerald-50 text-emerald-700'
  }

  if (status === 'failed') {
    return 'border-red-200 bg-red-50 text-red-700'
  }

  if (status === 'processing') {
    return 'border-blue-200 bg-blue-50 text-blue-700'
  }

  return 'border-amber-200 bg-amber-50 text-amber-700'
}

function HistoryJurnalPage() {
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [actionLoadingId, setActionLoadingId] = useState(null)
  const [deleteTargetId, setDeleteTargetId] = useState(null)

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

    const intervalId = window.setInterval(() => {
      loadHistory()
    }, 4000)

    return () => {
      window.clearInterval(intervalId)
    }
  }, [])

  async function handleDelete(analysisId) {
    if (!token) {
      return
    }

    setActionLoadingId(analysisId)

    try {
      await deleteAnalysis(token, analysisId)
      setItems((prev) => prev.filter((item) => item.id !== analysisId))
    } catch (error) {
      setErrorMessage(error.message || 'Gagal menghapus dokumen.')
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
      <AlertPopup
        open={deleteTargetId !== null}
        title="Hapus Dokumen?"
        description="Dokumen yang dihapus tidak bisa dikembalikan."
        variant="error"
        confirmLabel="Hapus"
        cancelLabel="Batal"
        destructive
        onCancel={() => setDeleteTargetId(null)}
        onConfirm={async () => {
          const targetId = deleteTargetId
          setDeleteTargetId(null)

          if (targetId !== null) {
            await handleDelete(targetId)
          }
        }}
      />

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
              <div>
                <span
                  className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-semibold ${getStatusPillClass(item.status)}`}
                >
                  {item.status}
                </span>
              </div>
            </CardHeader>
            <CardContent className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                className="flex-1"
                disabled={actionLoadingId === item.id}
                onClick={() => navigate(`/analisis/${item.id}`)}
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
                onClick={() => setDeleteTargetId(item.id)}
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
