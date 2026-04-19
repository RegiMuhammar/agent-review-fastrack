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

function formatDimensionLabel(value, fallback = 'Dimensi') {
  if (!value) {
    return fallback
  }

  return String(value)
    .replace(/[_-]+/g, ' ')
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(' ')
}

function clampScore(value) {
  const numeric = Number.parseFloat(value)

  if (!Number.isFinite(numeric)) {
    return 0
  }

  return Math.min(Math.max(numeric, 0), 10)
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
  const scoreOverall = toDisplayText(result.score_overall)
  const overallFeedback = toDisplayText(result.overall_feedback)
  const journalTitle = title !== '-' ? title : toDisplayText(analysis?.doc_name)
  const metadataAuthors = Array.isArray(result?.metadata?.authors) ? result.metadata.authors : []
  const authorName = cleanMarkdownText(
    metadataAuthors.length > 0
      ? metadataAuthors.join(', ')
      : result.author || analysis?.author_name || analysis?.author || analysis?.user?.name
  )
  const referenceUrls = references
    .map((item) => {
      if (typeof item === 'string') {
        return item.trim()
      }

      if (item && typeof item === 'object' && typeof item.url === 'string') {
        return item.url.trim()
      }

      return ''
    })
    .filter((item) => item.length > 0)

  const dimensionDetails = dimensions.map((dimension, index) => {
    const label = formatDimensionLabel(
      dimension?.label || dimension?.name || dimension?.key,
      `Dimensi ${index + 1}`
    )
    const score = clampScore(dimension?.score)
    const weight = Number.parseFloat(dimension?.weight)

    return {
      id: `${dimension?.key || 'dimension'}-${index}`,
      label,
      score,
      weight: Number.isFinite(weight) ? weight : null,
      feedback: dimension?.feedback || '-',
    }
  })

  const chartDimensions = dimensionDetails.length > 0 ? dimensionDetails : []
  const radarSize = 320
  const radarCenter = radarSize / 2
  const radarRadius = 102

  const toRadarPoint = (index, total, ratio) => {
    const angle = (-Math.PI / 2) + (index / total) * Math.PI * 2
    const distance = radarRadius * ratio

    return {
      x: radarCenter + Math.cos(angle) * distance,
      y: radarCenter + Math.sin(angle) * distance,
    }
  }

  const radarLevels = [0.2, 0.4, 0.6, 0.8, 1]
  const radarDataPoints =
    chartDimensions.length > 0
      ? chartDimensions
          .map((item, index) => {
            const point = toRadarPoint(index, chartDimensions.length, item.score / 10)
            return `${point.x},${point.y}`
          })
          .join(' ')
      : ''

  const tableOfContents = [
    { id: 'title-author', label: 'Title & Author' },
    { id: 'summary', label: 'Summary' },
    { id: 'profile-dimensions', label: 'Profil Dimensi' },
    { id: 'strengths', label: 'Kekuatan' },
    { id: 'overall-feedback', label: 'Overall Feedback' },
    { id: 'dimensions', label: 'Dimensi Penilaian' },
    { id: 'improvements', label: 'Area Perbaikan' },
    { id: 'references', label: 'Referensi' },
    { id: 'feedback-analysis', label: 'Feedback Analisis' },
  ]

  function handleTableOfContentsClick(event, id) {
    event.preventDefault()

    const target = document.getElementById(id)

    if (!target) {
      return
    }

    target.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    })
  }

  return (
    <div className="w-full">
      <AlertPopup
        open={alertState.open}
        title={alertState.title}
        description={alertState.description}
        variant={alertState.title === 'Feedback Terkirim' ? 'success' : 'error'}
        onConfirm={() => setAlertState({ open: false, title: '', description: '' })}
      />

      <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)] lg:items-start">
        <aside className="order-1 lg:sticky lg:top-8">
          <Card className="border-[#5E74C9]/16 bg-white/95">
            <CardHeader>
              <CardTitle className="text-base text-[#2E3F86]">Daftar Isi</CardTitle>
            </CardHeader>
            <CardContent>
              <nav className="grid gap-1">
                {tableOfContents.map((item) => (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    onClick={(event) => handleTableOfContentsClick(event, item.id)}
                    className="rounded-lg px-2 py-1.5 text-sm text-[#4f64a4] transition-colors hover:bg-[#eef2ff] hover:text-[#2E3F86]"
                  >
                    {item.label}
                  </a>
                ))}
              </nav>
            </CardContent>
          </Card>
        </aside>

        <div className="order-2 flex flex-col gap-4">
          <Card id="title-author" className="border-[#5E74C9]/16 bg-white/90">
            <CardHeader>
              <CardTitle className="text-4xl text-[#2E3F86]">{isLoading ? 'Memuat judul jurnal...' : journalTitle}</CardTitle>
              <CardDescription className="text-xl">Author: {authorName}</CardDescription>
            </CardHeader>
          </Card>

          <Card id="summary" className="border-[#5E74C9]/16 bg-white/95">
            <CardHeader>
              <CardTitle className="text-base text-[#2E3F86]">Summary</CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4">
              <div className="grid gap-4 rounded-xl border border-[#5E74C9]/14 bg-[#f8faff] p-4 sm:grid-cols-[160px_1fr] sm:items-start">
                <div>
                  <p className="text-5xl font-semibold leading-none text-[#2E3F86]">{scoreOverall}</p>
                  <p className="mt-1 text-sm text-[#6A7DB7]">/10</p>
                  <p className="mt-2 text-xs font-semibold uppercase tracking-[0.14em] text-[#6A7DB7]">
                    Skor Keseluruhan
                  </p>
                </div>
                <p className="text-sm leading-relaxed text-[#4f64a4]">{summary}</p>
              </div>
            </CardContent>
          </Card>

          <Card id="profile-dimensions" className="border-[#5E74C9]/16 bg-white/95">
            <CardHeader>
              <CardTitle className="text-base text-[#2E3F86]">Profil Dimensi</CardTitle>
            </CardHeader>
            <CardContent>
              {chartDimensions.length === 0 ? (
                <p className="text-sm text-[#6A7DB7]">Data dimensi belum tersedia.</p>
              ) : (
                <div className="overflow-x-auto">
                  <svg viewBox={`0 0 ${radarSize} ${radarSize}`} className="mx-auto h-80 w-80 text-[#6A7DB7]">
                    {radarLevels.map((level) => {
                      const points = chartDimensions
                        .map((_, index) => {
                          const point = toRadarPoint(index, chartDimensions.length, level)
                          return `${point.x},${point.y}`
                        })
                        .join(' ')

                      return (
                        <polygon
                          key={`radar-level-${level}`}
                          points={points}
                          fill="none"
                          stroke="currentColor"
                          strokeOpacity="0.25"
                          strokeWidth="1"
                        />
                      )
                    })}

                    {chartDimensions.map((item, index) => {
                      const axisPoint = toRadarPoint(index, chartDimensions.length, 1)
                      const labelPoint = toRadarPoint(index, chartDimensions.length, 1.2)
                      const textAnchor = labelPoint.x < radarCenter - 6 ? 'end' : labelPoint.x > radarCenter + 6 ? 'start' : 'middle'

                      return (
                        <g key={`radar-axis-${item.id}`}>
                          <line
                            x1={radarCenter}
                            y1={radarCenter}
                            x2={axisPoint.x}
                            y2={axisPoint.y}
                            stroke="currentColor"
                            strokeOpacity="0.3"
                          />
                          <text
                            x={labelPoint.x}
                            y={labelPoint.y}
                            textAnchor={textAnchor}
                            dominantBaseline="middle"
                            fontSize="11"
                            fill="#4f64a4"
                          >
                            {item.label}
                          </text>
                        </g>
                      )
                    })}

                    <polygon
                      points={radarDataPoints}
                      fill="#5E74C9"
                      fillOpacity="0.2"
                      stroke="#5E74C9"
                      strokeWidth="2"
                    />

                    {chartDimensions.map((item, index) => {
                      const point = toRadarPoint(index, chartDimensions.length, item.score / 10)

                      return (
                        <circle
                          key={`radar-point-${item.id}`}
                          cx={point.x}
                          cy={point.y}
                          r="3.5"
                          fill="#5E74C9"
                        />
                      )
                    })}
                  </svg>
                </div>
              )}
            </CardContent>
          </Card>

          <Card id="strengths" className="border-[#5E74C9]/16 bg-white/95">
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

          <Card id="overall-feedback" className="border-[#5E74C9]/16 bg-white/95">
            <CardHeader>
              <CardTitle className="text-base text-[#2E3F86]">Overall Feedback</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm leading-relaxed text-[#4f64a4]">{overallFeedback}</p>
            </CardContent>
          </Card>

          <Card id="dimensions" className="border-[#5E74C9]/16 bg-white/95">
            <CardHeader>
              <CardTitle className="text-base text-[#2E3F86]">Dimensi Penilaian</CardTitle>
            </CardHeader>
            <CardContent>
              {dimensions.length === 0 ? (
                <p className="text-sm text-[#6A7DB7]">Belum ada detail dimensi.</p>
              ) : (
                <div className="grid gap-3">
                  {dimensionDetails.map((dimension) => (
                    <article
                      key={dimension.id}
                      className="rounded-lg border border-[#5E74C9]/14 bg-[#f8faff] px-3 py-2"
                    >
                      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                        <p className="text-sm font-medium text-[#2E3F86]">{dimension.label}</p>
                        <p className="text-xs font-semibold text-[#4f64a4]">
                          {dimension.score.toFixed(1)} / 10
                          {dimension.weight !== null ? `  •  bobot ${Math.round(dimension.weight * 100)}%` : ''}
                        </p>
                      </div>
                      <div className="h-2 w-full overflow-hidden rounded-full bg-[#d9e2ff]">
                        <div
                          className="h-full rounded-full bg-[#5E74C9]"
                          style={{ width: `${(dimension.score / 10) * 100}%` }}
                        />
                      </div>
                      <p className="mt-2 text-sm text-[#4f64a4]">{dimension.feedback}</p>
                    </article>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <Card id="improvements" className="border-[#5E74C9]/16 bg-white/95">
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

          <Card id="references" className="border-[#5E74C9]/16 bg-white/95">
            <CardHeader>
              <CardTitle className="text-base text-[#2E3F86]">Referensi</CardTitle>
            </CardHeader>
            <CardContent>
              {referenceUrls.length === 0 ? (
                <p className="text-sm text-[#6A7DB7]">-</p>
              ) : (
                <ul className="list-disc pl-5 text-sm text-[#4f64a4]">
                  {referenceUrls.map((url, index) => (
                    <li key={`reference-${index}`}>
                      <a
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="break-all text-[#4f64a4] underline underline-offset-2 hover:text-[#2E3F86]"
                      >
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>

          <Card
            id="feedback-analysis"
            className="mt-4 overflow-hidden border-0 bg-linear-to-br from-[#e9efff] via-[#f5f8ff] to-[#eefaf5] shadow-sm"
          >
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

      </div>
    </div>
  )
}

export default AnalisisJurnalPage
