import { useEffect, useMemo, useState } from 'react'
import { Star } from 'lucide-react'
import { useNavigate, useParams } from 'react-router-dom'

import { Button } from '@/components/ui/button'
import AlertPopup from '@/components/ui/alert-popup'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { getAnalysis, listAnalysisFeedbacks, submitAnalysisFeedback } from '@/lib/api'
import { getAuthToken, getAuthUser } from '@/lib/auth'

function toDisplayText(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return String(value)
}

function cleanMarkdownText(value) {
  const text = toDisplayText(value)

  if (text === '-') {
    return text
  }

  return text
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/_(.*?)_/g, '$1')
    .replace(/`(.*?)`/g, '$1')
    .trim()
}

function AnalisisJurnalPage() {
  const navigate = useNavigate()
  const { analysisId } = useParams()
  const token = useMemo(() => getAuthToken(), [])
  const authUser = useMemo(() => getAuthUser(), [])

  const [analysis, setAnalysis] = useState(null)
  const [feedbackForm, setFeedbackForm] = useState({
    rating: 0,
    comment: '',
  })
  const [isLoading, setIsLoading] = useState(true)
  const [isFeedbackSubmitting, setIsFeedbackSubmitting] = useState(false)
  const [isFeedbackLocked, setIsFeedbackLocked] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [alertState, setAlertState] = useState({
    open: false,
    title: '',
    description: '',
  })

  useEffect(() => {
    if (!token) {
      navigate('/login', { replace: true })
      return
    }

    if (!analysisId) {
      setErrorMessage('ID analisis tidak ditemukan.')
      setIsLoading(false)
      return
    }

    let isStopped = false

    async function loadAnalysis() {
      try {
        const [analysisResponse, feedbackResponse] = await Promise.all([
          getAnalysis(token, analysisId),
          listAnalysisFeedbacks(token, analysisId),
        ])

        if (isStopped) {
          return
        }

        const analysisData = analysisResponse?.data?.analysis ?? null
        const feedbacks = feedbackResponse?.data?.feedbacks ?? []
        const hasMyFeedback = feedbacks.some((item) => item.user_id === authUser?.id)

        setAnalysis(analysisData)
        setIsFeedbackLocked(hasMyFeedback)
        setErrorMessage('')
      } catch (error) {
        if (!isStopped) {
          setErrorMessage(error.message || 'Gagal mengambil data analisis.')
        }
      } finally {
        if (!isStopped) {
          setIsLoading(false)
        }
      }
    }

    loadAnalysis()

    return () => {
      isStopped = true
    }
  }, [analysisId, authUser?.id, navigate, token])

  async function handleSubmitFeedback(event) {
    event.preventDefault()

    if (!token || !analysis?.id) {
      return
    }

    if (!feedbackForm.rating) {
      setErrorMessage('Silakan pilih rating terlebih dahulu.')
      return
    }

    if (isFeedbackLocked) {
      setErrorMessage('Feedback untuk analisis ini sudah pernah dikirim.')
      return
    }

    setIsFeedbackSubmitting(true)

    try {
      await submitAnalysisFeedback(token, analysis.id, {
        rating: feedbackForm.rating,
        comment: feedbackForm.comment.trim() || null,
      })

      setFeedbackForm({
        rating: 0,
        comment: '',
      })
      setIsFeedbackLocked(true)
      setErrorMessage('')
      setAlertState({
        open: true,
        title: 'Feedback Terkirim',
        description: 'Terima kasih, feedback Anda berhasil disimpan.',
      })
    } catch (error) {
      setErrorMessage(error.message || 'Gagal menyimpan feedback.')
      setAlertState({
        open: true,
        title: 'Gagal Menyimpan Feedback',
        description: error.message || 'Terjadi kesalahan saat menyimpan feedback.',
      })
    } finally {
      setIsFeedbackSubmitting(false)
    }
  }

  const rawResult = analysis?.result_json
  const result = (() => {
    if (!rawResult) {
      return {}
    }

    if (typeof rawResult === 'string') {
      try {
        return JSON.parse(rawResult)
      } catch {
        return {}
      }
    }

    if (typeof rawResult === 'object') {
      return rawResult
    }

    return {}
  })()

  const hasResultData = Object.keys(result).length > 0
  const dimensions = Array.isArray(result.dimensions) ? result.dimensions : []
  const strengths = Array.isArray(result.strengths) ? result.strengths : []
  const improvements = Array.isArray(result.improvements) ? result.improvements : []
  const references = Array.isArray(result.references) ? result.references : []

  const title = cleanMarkdownText(result.title)
  const summary = toDisplayText(result.summary)
  const docType = toDisplayText(result.doc_type)
  const pageCount = toDisplayText(result.page_count)
  const analysisIdFromResult = toDisplayText(result.analysis_id)
  const scoreOverall = toDisplayText(result.score_overall)
  const overallFeedback = toDisplayText(result.overall_feedback)

  return (
    <div className="mx-auto flex w-full max-w-4xl flex-col gap-4">
      <AlertPopup
        open={alertState.open}
        title={alertState.title}
        description={alertState.description}
        variant={alertState.title === 'Feedback Terkirim' ? 'success' : 'error'}
        onConfirm={() => setAlertState({ open: false, title: '', description: '' })}
      />

      <Card className="border-[#5E74C9]/16 bg-white/90">
        <CardHeader>
          <CardTitle className="text-xl text-[#2E3F86]">Analisis</CardTitle>
          <CardDescription>Hasil analisis berdasarkan output AI.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm text-[#6A7DB7]">
          {isLoading ? <p>Memuat analisis...</p> : null}
          {analysis ? <p>Dokumen: {analysis.doc_name}</p> : null}
          {analysis ? <p>Status: {analysis.status}</p> : null}
          {analysis ? <p>Skor keseluruhan: {scoreOverall}</p> : null}
          {!isLoading && analysis?.status === 'done' && !hasResultData ? (
            <p className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-700">
              Analisis selesai, tetapi result JSON belum tersedia.
            </p>
          ) : null}
          {errorMessage ? (
            <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
              {errorMessage}
            </p>
          ) : null}
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Title</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-[#4f64a4]">{title}</p>
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Info Dokumen</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-2 text-sm text-[#4f64a4]">
          <p>Doc Type: {docType}</p>
          <p>Page Count: {pageCount}</p>
          <p>Analysis ID: {analysisIdFromResult}</p>
          <p>Score Overall: {scoreOverall}</p>
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-[#4f64a4]">{summary}</p>
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Overall Feedback</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-[#4f64a4]">{overallFeedback}</p>
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Dimensi Penilaian</CardTitle>
        </CardHeader>
        <CardContent>
          {dimensions.length === 0 ? (
            <p className="text-sm text-[#6A7DB7]">Belum ada detail dimensi.</p>
          ) : (
            <div className="grid gap-2">
              {dimensions.map((dimension, index) => (
                <article
                  key={`${dimension?.key || 'dimension'}-${index}`}
                  className="rounded-lg border border-[#5E74C9]/14 bg-[#f8faff] px-3 py-2"
                >
                  <p className="text-sm font-medium text-[#2E3F86]">
                    {dimension?.label || dimension?.key || 'Dimensi'}
                  </p>
                  <p className="text-xs text-[#6A7DB7]">Skor: {dimension?.score ?? '-'}</p>
                  <p className="mt-1 text-sm text-[#4f64a4]">{dimension?.feedback || '-'}</p>
                </article>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Kekuatan</CardTitle>
        </CardHeader>
        <CardContent>
          {strengths.length === 0 ? (
            <p className="text-sm text-[#6A7DB7]">-</p>
          ) : (
            <ul className="list-disc pl-5 text-sm text-[#4f64a4]">
              {strengths.map((item, index) => (
                <li key={`strength-${index}`}>{item}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Area Perbaikan</CardTitle>
        </CardHeader>
        <CardContent>
          {improvements.length === 0 ? (
            <p className="text-sm text-[#6A7DB7]">-</p>
          ) : (
            <ul className="list-disc pl-5 text-sm text-[#4f64a4]">
              {improvements.map((item, index) => (
                <li key={`improvement-${index}`}>{item}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Referensi</CardTitle>
        </CardHeader>
        <CardContent>
          {references.length === 0 ? (
            <p className="text-sm text-[#6A7DB7]">-</p>
          ) : (
            <ul className="list-disc pl-5 text-sm text-[#4f64a4]">
              {references.map((item, index) => (
                <li key={`reference-${index}`}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <Card className="overflow-hidden border-0 bg-linear-to-br from-[#e9efff] via-[#f5f8ff] to-[#eefaf5] shadow-sm">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Feedback Analisis</CardTitle>
          <CardDescription>Nilai kualitas hasil analisis dan tambahkan komentar.</CardDescription>
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
              disabled={isFeedbackSubmitting || isFeedbackLocked}
            >
              {isFeedbackLocked
                ? 'Feedback Sudah Dikirim'
                : isFeedbackSubmitting
                  ? 'Menyimpan...'
                  : 'Simpan Feedback'}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="flex justify-end">
        <Button type="button" variant="outline" onClick={() => navigate('/history-jurnal')}>
          Kembali ke History
        </Button>
      </div>
    </div>
  )
}

export default AnalisisJurnalPage
