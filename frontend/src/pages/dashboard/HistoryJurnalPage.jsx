import { useEffect, useMemo, useState } from 'react'
import { Eye, FileText, MessageSquareText, Star, Trash2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import {
  deleteAnalysis,
  getAnalysis,
  getAnalysisFileBlob,
  listAnalysisFeedbacks,
  listAnalyses,
  submitAnalysisFeedback,
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
  const [feedbacks, setFeedbacks] = useState([])
  const [feedbackForm, setFeedbackForm] = useState({
    rating: 0,
    comment: '',
  })
  const [isFeedbackLoading, setIsFeedbackLoading] = useState(false)
  const [isFeedbackSubmitting, setIsFeedbackSubmitting] = useState(false)
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

  async function loadFeedbacks(analysisId, ownerUserId) {
    if (!token) {
      return
    }

    setIsFeedbackLoading(true)

    try {
      const response = await listAnalysisFeedbacks(token, analysisId)
      const feedbackItems = response?.data?.feedbacks ?? []
      setFeedbacks(feedbackItems)

      const myFeedback = feedbackItems.find(
        (feedbackItem) => feedbackItem.user_id === ownerUserId
      )

      if (myFeedback) {
        setFeedbackForm({
          rating: myFeedback.rating,
          comment: myFeedback.comment || '',
        })
      } else {
        setFeedbackForm({
          rating: 0,
          comment: '',
        })
      }
    } catch (error) {
      setErrorMessage(error.message || 'Gagal mengambil feedback.')
    } finally {
      setIsFeedbackLoading(false)
    }
  }

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
      const analysisDetail = response?.data?.analysis ?? null
      setSelectedDetail(analysisDetail)

      if (analysisDetail?.id) {
        await loadFeedbacks(analysisDetail.id, analysisDetail.user_id)
      }

      setErrorMessage('')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal mengambil detail dokumen.')
    } finally {
      setActionLoadingId(null)
    }
  }

  async function handleSubmitFeedback(event) {
    event.preventDefault()

    if (!token || !selectedDetail?.id) {
      return
    }

    if (!feedbackForm.rating) {
      setErrorMessage('Silakan pilih rating terlebih dahulu.')
      return
    }

    setIsFeedbackSubmitting(true)

    try {
      await submitAnalysisFeedback(token, selectedDetail.id, {
        rating: feedbackForm.rating,
        comment: feedbackForm.comment.trim() || null,
      })

      await loadFeedbacks(selectedDetail.id, selectedDetail.user_id)
      setErrorMessage('')
    } catch (error) {
      setErrorMessage(error.message || 'Gagal menyimpan feedback.')
    } finally {
      setIsFeedbackSubmitting(false)
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
        <div className="grid gap-4 lg:grid-cols-2">
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

          <Card className="overflow-hidden border-0 bg-linear-to-br from-[#e9efff] via-[#f5f8ff] to-[#eefaf5] shadow-sm">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base text-[#2E3F86]">
                <MessageSquareText className="size-4" />
                Feedback Analisis
              </CardTitle>
              <CardDescription>
                Nilai kualitas hasil analisis dan tambahkan komentar.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid gap-4" onSubmit={handleSubmitFeedback}>
                <div className="grid gap-2">
                  <p className="text-sm font-medium text-[#2E3F86]">Rating</p>
                  <div className="flex flex-wrap gap-2">
                    {[1, 2, 3, 4, 5].map((score) => {
                      const active = feedbackForm.rating === score

                      return (
                        <Button
                          key={score}
                          type="button"
                          variant={active ? 'default' : 'outline'}
                          className={
                            active
                              ? 'bg-[#2E3F86] text-white hover:bg-[#22367c]'
                              : 'border-[#2E3F86]/25 text-[#2E3F86] hover:bg-[#eef2ff]'
                          }
                          onClick={() =>
                            setFeedbackForm((prev) => ({
                              ...prev,
                              rating: score,
                            }))
                          }
                        >
                          <Star className="size-4" />
                          {score}
                        </Button>
                      )
                    })}
                  </div>
                </div>

                <div className="grid gap-2">
                  <p className="text-sm font-medium text-[#2E3F86]">Komentar</p>
                  <Textarea
                    value={feedbackForm.comment}
                    onChange={(event) =>
                      setFeedbackForm((prev) => ({
                        ...prev,
                        comment: event.target.value,
                      }))
                    }
                    placeholder="Tulis masukan atau saran terkait hasil analisis..."
                    className="min-h-28 border-[#5E74C9]/20 bg-white/85 text-[#2E3F86] placeholder:text-[#7f8fbe]"
                    maxLength={2000}
                  />
                </div>

                <Button
                  type="submit"
                  className="w-full bg-[#2E3F86] text-white hover:bg-[#22367c]"
                  disabled={isFeedbackSubmitting}
                >
                  {isFeedbackSubmitting ? 'Menyimpan...' : 'Simpan Feedback'}
                </Button>
              </form>
            </CardContent>
          </Card>
        </div>
      ) : null}

      {selectedDetail ? (
        <Card className="border-[#5E74C9]/16 bg-white/95">
          <CardHeader>
            <CardTitle className="text-base text-[#2E3F86]">Feedback Tersimpan</CardTitle>
            <CardDescription>
              Feedback yang sudah diberikan untuk dokumen ini.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {isFeedbackLoading ? (
              <p className="text-sm text-[#6A7DB7]">Memuat feedback...</p>
            ) : feedbacks.length === 0 ? (
              <p className="rounded-lg border border-dashed border-[#5E74C9]/20 bg-[#f7f9ff] px-3 py-4 text-sm text-[#6A7DB7]">
                Belum ada feedback untuk dokumen ini.
              </p>
            ) : (
              <div className="grid gap-3">
                {feedbacks.map((feedback) => (
                  <article
                    key={feedback.id}
                    className="rounded-xl border border-[#5E74C9]/15 bg-linear-to-r from-white to-[#f6f8ff] p-4"
                  >
                    <div className="mb-2 flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-[#2E3F86]">
                        {feedback?.user?.name || 'Pengguna'}
                      </p>
                      <div className="inline-flex items-center gap-1 rounded-full bg-[#2E3F86]/10 px-2.5 py-1 text-xs font-medium text-[#2E3F86]">
                        <Star className="size-3.5 fill-current" />
                        {feedback.rating}/5
                      </div>
                    </div>
                    <p className="text-sm leading-relaxed text-[#4f64a4]">
                      {feedback.comment || 'Tanpa komentar'}
                    </p>
                    <p className="mt-3 text-xs text-[#7f8fbe]">
                      {formatDate(feedback.created_at)}
                    </p>
                  </article>
                ))}
              </div>
            )}
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
