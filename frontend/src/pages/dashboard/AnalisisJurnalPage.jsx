import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'

import AlertPopup from '@/components/ui/alert-popup'
import { getAnalysis, listAnalysisFeedbacks, submitAnalysisFeedback } from '@/lib/api'
import { getAuthToken, getAuthUser } from '@/lib/auth'

import AnalysisDetailContent from './components/AnalysisDetailContent'

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

function normalizeList(value) {
  return Array.isArray(value) ? value : []
}

function normalizeResult(rawResult) {
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
}

function AnalisisJurnalPage() {
  const navigate = useNavigate()
  const { analysisId } = useParams()
  const token = useMemo(() => getAuthToken(), [])
  const authUser = useMemo(() => getAuthUser(), [])

  const [analysis, setAnalysis] = useState(null)
  const [feedbackForm, setFeedbackForm] = useState({ rating: 0, comment: '' })
  const [isLoading, setIsLoading] = useState(true)
  const [isFeedbackSubmitting, setIsFeedbackSubmitting] = useState(false)
  const [isFeedbackLocked, setIsFeedbackLocked] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [alertState, setAlertState] = useState({ open: false, title: '', description: '' })

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

      setFeedbackForm({ rating: 0, comment: '' })
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

  const result = normalizeResult(analysis?.result_json)
  const hasResultData = Object.keys(result).length > 0
  const dimensions = normalizeList(result.dimensions)
  const strengths = normalizeList(result.strengths)
  const improvements = normalizeList(result.improvements)
  const references = normalizeList(result.references)
  const docType = result?.doc_type || analysis?.doc_type || 'essay'

  const title = cleanMarkdownText(result.title)
  const summary = toDisplayText(result.summary)
  const scoreOverall = toDisplayText(result.score_overall)
  const overallFeedback = toDisplayText(result.overall_feedback)
  const journalTitle = title !== '-' ? title : toDisplayText(analysis?.doc_name)
  const metadataAuthors = normalizeList(result?.metadata?.authors)
  const bizplanMetadata = result?.metadata && typeof result.metadata === 'object' ? result.metadata : {}
  const bizplanProfile = result?.profile && typeof result.profile === 'object' ? result.profile : {}
  const businessSnapshot = result?.business_snapshot && typeof result.business_snapshot === 'object' ? result.business_snapshot : {}
  const financialMetrics = result?.financial_metrics && typeof result.financial_metrics === 'object' ? result.financial_metrics : {}
  const unitEconomicsSignals =
    result?.unit_economics_signals && typeof result.unit_economics_signals === 'object'
      ? result.unit_economics_signals
      : {}
  const marketValidation = result?.market_validation && typeof result.market_validation === 'object' ? result.market_validation : {}
  const competitionInsights = result?.competition_insights && typeof result.competition_insights === 'object' ? result.competition_insights : {}
  const financialRedFlags = normalizeList(result?.financial_red_flags)
  const marketRedFlags = normalizeList(result?.market_red_flags)
  const companyName = cleanMarkdownText(bizplanMetadata.company_name || businessSnapshot.company_name || journalTitle)
  const customerSegments = normalizeList(businessSnapshot.target_customer || bizplanProfile.target_customer)
  const revenueModels = normalizeList(businessSnapshot.revenue_model || financialMetrics.revenue_model)
  const pricingSignals = normalizeList(financialMetrics.pricing || bizplanProfile.pricing_signals)
  const directCompetitors = normalizeList(competitionInsights.direct_competitors)
  const authorName = cleanMarkdownText(
    docType === 'bizplan'
      ? companyName
      : metadataAuthors.length > 0
        ? metadataAuthors.join(', ')
        : result.author || analysis?.author_name || analysis?.author || analysis?.user?.name
  )
  const referenceUrls = references
    .map((item) => (typeof item === 'string' ? item.trim() : typeof item?.url === 'string' ? item.url.trim() : ''))
    .filter((item) => item.length > 0)

  const dimensionDetails = dimensions.map((dimension, index) => ({
    id: `${dimension?.key || 'dimension'}-${index}`,
    label: formatDimensionLabel(dimension?.label || dimension?.name || dimension?.key, `Dimensi ${index + 1}`),
    score: clampScore(dimension?.score),
    weight: Number.isFinite(Number.parseFloat(dimension?.weight)) ? Number.parseFloat(dimension?.weight) : null,
    feedback: dimension?.feedback || '-',
  }))

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
    ...(docType === 'bizplan'
      ? [
          { id: 'title-author', label: 'Ringkasan Investasi' },
          { id: 'summary', label: 'Ringkasan' },
          { id: 'business-snapshot', label: 'Model Bisnis' },
          { id: 'financial-health', label: 'Kesehatan Finansial' },
          { id: 'market-validation', label: 'Validasi Pasar' },
        ]
      : [
          { id: 'title-author', label: 'Judul & Author' },
          { id: 'summary', label: 'Ringkasan' },
        ]),
    { id: 'profile-dimensions', label: 'Profil Dimensi' },
    { id: 'strengths', label: 'Kekuatan' },
    { id: 'overall-feedback', label: 'Feedback Keseluruhan' },
    { id: 'dimensions', label: 'Dimensi Penilaian' },
    { id: 'improvements', label: 'Area Perbaikan' },
    { id: 'references', label: 'Referensi' },
    { id: 'feedback-analysis', label: 'Feedback Analisis' },
  ]

  function handleTableOfContentsClick(event, id) {
    event.preventDefault()
    const target = document.getElementById(id)
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
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

      <AnalysisDetailContent
        tableOfContents={tableOfContents}
        handleTableOfContentsClick={handleTableOfContentsClick}
        docType={docType}
        isLoading={isLoading}
        journalTitle={journalTitle}
        authorName={authorName}
        companyName={companyName}
        bizplanProfile={bizplanProfile}
        businessSnapshot={businessSnapshot}
        bizplanMetadata={bizplanMetadata}
        customerSegments={customerSegments}
        scoreOverall={scoreOverall}
        summary={summary}
        revenueModels={revenueModels}
        pricingSignals={pricingSignals}
        financialMetrics={financialMetrics}
        financialRedFlags={financialRedFlags}
        unitEconomicsSignals={unitEconomicsSignals}
        marketValidation={marketValidation}
        competitionInsights={competitionInsights}
        directCompetitors={directCompetitors}
        marketRedFlags={marketRedFlags}
        referenceUrls={referenceUrls}
        normalizeList={normalizeList}
        chartDimensions={chartDimensions}
        radarSize={radarSize}
        radarCenter={radarCenter}
        radarDataPoints={radarDataPoints}
        radarLevels={radarLevels}
        toRadarPoint={toRadarPoint}
        strengths={strengths}
        overallFeedback={overallFeedback}
        dimensionDetails={dimensionDetails}
        improvements={improvements}
        feedbackForm={feedbackForm}
        setFeedbackForm={setFeedbackForm}
        handleSubmitFeedback={handleSubmitFeedback}
        isFeedbackSubmitting={isFeedbackSubmitting}
        isFeedbackLocked={isFeedbackLocked}
        hasResultData={hasResultData}
        errorMessage={errorMessage}
        onBack={() => navigate('/history-jurnal')}
        toDisplayText={toDisplayText}
      />
    </div>
  )
}

export default AnalisisJurnalPage
