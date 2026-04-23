import { useMemo, useState } from 'react'
import { KeyRound, SearchCheck } from 'lucide-react'
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
import { getAnalysisByAccessCode } from '@/lib/api'
import AnalysisDetailContent from '@/pages/dashboard/components/AnalysisDetailContent'

function toDisplayText(value) {
  if (value === null || value === undefined || value === '') {
    return '-'
  }

  return String(value)
}

function normalizeList(value) {
  return Array.isArray(value) ? value : []
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

function hasBizplanArtifact(value) {
  const text = String(value || '').toLowerCase()
  return (
    text.includes('start of picture text') ||
    text.includes('end of picture text') ||
    text.includes('picture text') ||
    text.includes('image text') ||
    text.includes('ocr text')
  )
}

function sanitizeBizplanHeadline(value, fallback = '-') {
  const text = cleanMarkdownText(value)

  if (text === '-') {
    return fallback
  }

  const withoutMetadata = text
    .replace(/\b(?:industry|industri|geography|geografi|funding ask|pendanaan|target customer|target pelanggan)\b\s*:.*$/i, '')
    .replace(/\s+/g, ' ')
    .trim()

  if (!withoutMetadata || hasBizplanArtifact(withoutMetadata)) {
    return fallback
  }

  return withoutMetadata
}

function sanitizeBizplanTextList(value) {
  const items = normalizeList(value)
    .map((item) => cleanMarkdownText(item))
    .filter((item) => item !== '-' && !hasBizplanArtifact(item))

  return Array.from(new Set(items))
}

function sanitizeBizplanEvidenceList(value) {
  return normalizeList(value)
    .filter((item) => item && typeof item === 'object')
    .map((item) => ({
      ...item,
      title: sanitizeBizplanHeadline(item.title, '-'),
      snippet: cleanMarkdownText(item.snippet),
    }))
    .filter((item) => item.title !== '-' && !hasBizplanArtifact(item.snippet))
}

function normalizeBizplanMarketStatus(status, evidence, marketRedFlags) {
  const normalized = String(status || '').trim().toLowerCase()
  const safeEvidence = sanitizeBizplanEvidenceList(evidence)
  const safeFlags = sanitizeBizplanTextList(marketRedFlags).map((item) => item.toLowerCase())

  if (!normalized) {
    return safeEvidence.length > 0 ? 'partial' : 'unavailable'
  }

  if (normalized === 'validated') {
    if (safeEvidence.length === 0) {
      return 'partial'
    }
    if (safeFlags.some((item) => item.includes('kompetisi') || item.includes('belum cukup relevan'))) {
      return 'partial'
    }
  }

  return normalized
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

function OpenAnalysisResultPage() {
  const navigate = useNavigate()
  const [accessCode, setAccessCode] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isLoadingResult, setIsLoadingResult] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [analysis, setAnalysis] = useState(null)
  const [feedbackForm, setFeedbackForm] = useState({ rating: 0, comment: '' })

  const result = useMemo(() => normalizeResult(analysis?.result_json), [analysis?.result_json])
  const hasResultData = Object.keys(result).length > 0
  const dimensions = normalizeList(result.dimensions)
  const strengths = normalizeList(result?.strengths)
  const improvements = normalizeList(result?.improvements)
  const references = normalizeList(result?.references)
  const docType = result?.doc_type || analysis?.doc_type || 'essay'

  const title = cleanMarkdownText(result.title)
  const summary = toDisplayText(result.summary)
  const scoreOverall = toDisplayText(result.score_overall)
  const overallFeedback = toDisplayText(result.overall_feedback)
  const journalTitle = title !== '-' ? title : toDisplayText(analysis?.doc_name)
  const metadataAuthors = normalizeList(result?.metadata?.authors)
  const bizplanMetadata = result?.metadata && typeof result.metadata === 'object' ? result.metadata : {}
  const bizplanProfile = result?.profile && typeof result.profile === 'object' ? result.profile : {}
  const businessSnapshot =
    result?.business_snapshot && typeof result.business_snapshot === 'object'
      ? result.business_snapshot
      : {}
  const financialMetrics =
    result?.financial_metrics && typeof result.financial_metrics === 'object'
      ? result.financial_metrics
      : {}
  const unitEconomicsSignals =
    result?.unit_economics_signals && typeof result.unit_economics_signals === 'object'
      ? result.unit_economics_signals
      : {}
  const rawMarketValidation =
    result?.market_validation && typeof result.market_validation === 'object'
      ? result.market_validation
      : {}
  const competitionInsights =
    result?.competition_insights && typeof result.competition_insights === 'object'
      ? result.competition_insights
      : {}
  const financialRedFlags = sanitizeBizplanTextList(result?.financial_red_flags)
  const marketRedFlags = sanitizeBizplanTextList(result?.market_red_flags)
  const companyName = sanitizeBizplanHeadline(
    bizplanMetadata.company_name || businessSnapshot.company_name || journalTitle,
    cleanMarkdownText(journalTitle)
  )
  const customerSegments = normalizeList(businessSnapshot.target_customer || bizplanProfile.target_customer)
  const revenueModels = normalizeList(businessSnapshot.revenue_model || financialMetrics.revenue_model)
  const pricingSignals = sanitizeBizplanTextList(financialMetrics.pricing || bizplanProfile.pricing_signals)
  const directCompetitors = sanitizeBizplanTextList(competitionInsights.direct_competitors)
  const marketValidation = {
    ...rawMarketValidation,
    evidence: sanitizeBizplanEvidenceList(rawMarketValidation?.evidence),
    status: normalizeBizplanMarketStatus(
      rawMarketValidation?.status,
      rawMarketValidation?.evidence,
      marketRedFlags
    ),
  }

  const authorName = cleanMarkdownText(
    docType === 'bizplan'
      ? companyName
      : metadataAuthors.length > 0
        ? metadataAuthors.join(', ')
        : result.author || analysis?.owner_name
  )

  const referenceUrls = references
    .map((item) =>
      typeof item === 'string' ? item.trim() : typeof item?.url === 'string' ? item.url.trim() : ''
    )
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
  ]

  function handleTableOfContentsClick(event, id) {
    event.preventDefault()
    const target = document.getElementById(id)
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }

  function handleSubmitFeedback(event) {
    event.preventDefault()
  }

  async function handleSubmit(event) {
    event.preventDefault()

    if (!accessCode.trim()) {
      setErrorMessage('Kode akses wajib diisi.')
      return
    }

    setIsSubmitting(true)
    setIsLoadingResult(true)
    setErrorMessage('')

    try {
      const response = await getAnalysisByAccessCode({
        access_code: accessCode.trim(),
      })

      setAnalysis(response?.data?.analysis ?? null)
    } catch (error) {
      setAnalysis(null)
      setErrorMessage(error.message || 'Kode akses tidak valid atau hasil belum tersedia.')
    } finally {
      setIsSubmitting(false)
      setIsLoadingResult(false)
    }
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(130deg,#edf1ff_0%,#f6f8ff_45%,#ffffff_100%)] px-4 py-10 sm:px-6 lg:px-8">
      <div className="mx-auto grid w-full max-w-4xl gap-6">
        <Card className="border-[#5E74C9]/16 bg-white/90 shadow-[0_20px_60px_rgba(94,116,201,0.11)] backdrop-blur">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-xl text-[#2E3F86]">
              <KeyRound className="size-5 text-[#5E74C9]" />
              Buka Hasil Analisis
            </CardTitle>
            <CardDescription>
              Masukkan kode unik dari email untuk membuka hasil analisis tanpa login.
            </CardDescription>
          </CardHeader>

          <CardContent>
            <form className="grid gap-4 sm:grid-cols-[1fr_auto] sm:items-end" onSubmit={handleSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="analysis-access-code">Kode Akses</Label>
                <Input
                  id="analysis-access-code"
                  type="text"
                  value={accessCode}
                  onChange={(event) => setAccessCode(event.target.value.toUpperCase())}
                  placeholder="Contoh: I2GBG18H7UES"
                  autoComplete="off"
                  required
                />
              </div>

              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-10 w-full bg-[#5E74C9] text-white hover:bg-[#5166B8] sm:w-auto"
              >
                <SearchCheck className="mr-1 size-4" />
                {isSubmitting ? 'Memproses...' : 'Lihat Hasil'}
              </Button>
            </form>

            {errorMessage ? (
              <p className="mt-4 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {errorMessage}
              </p>
            ) : null}
          </CardContent>
        </Card>

        {analysis ? (
          <AnalysisDetailContent
            tableOfContents={tableOfContents}
            handleTableOfContentsClick={handleTableOfContentsClick}
            docType={docType}
            isLoading={isLoadingResult}
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
            isFeedbackSubmitting={false}
            isFeedbackLocked
            hasResultData={hasResultData}
            errorMessage={errorMessage}
            onBack={() => navigate('/')}
            backButtonLabel="Kembali ke Beranda"
            toDisplayText={toDisplayText}
            showFeedbackSection={false}
          />
        ) : null}
      </div>
    </main>
  )
}

export default OpenAnalysisResultPage
