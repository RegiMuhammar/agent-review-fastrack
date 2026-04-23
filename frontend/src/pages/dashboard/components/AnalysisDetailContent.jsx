import { Star } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'

import AnalysisBizplanView from './AnalysisBizplanView'
import AnalysisDefaultView from './AnalysisDefaultView'

function TableOfContents({ items, onClick }) {
  return (
    <aside className="order-1 lg:sticky lg:top-8">
      <Card className="border-[#5E74C9]/16 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#2E3F86]">Daftar Isi</CardTitle>
        </CardHeader>
        <CardContent>
          <nav className="grid gap-1">
            {items.map((item) => (
              <a
                key={item.id}
                href={`#${item.id}`}
                onClick={(event) => onClick(event, item.id)}
                className="rounded-lg px-2 py-1.5 text-sm text-[#4f64a4] transition-colors hover:bg-[#eef2ff] hover:text-[#2E3F86]"
              >
                {item.label}
              </a>
            ))}
          </nav>
        </CardContent>
      </Card>
    </aside>
  )
}

function FeedbackSection({ feedbackForm, setFeedbackForm, handleSubmitFeedback, isFeedbackSubmitting, isFeedbackLocked }) {
  return (
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
            {isFeedbackLocked ? 'Feedback Sudah Dikirim' : isFeedbackSubmitting ? 'Menyimpan...' : 'Simpan Feedback'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}

export default function AnalysisDetailContent(props) {
  const {
    tableOfContents,
    handleTableOfContentsClick,
    docType,
    isLoading,
    journalTitle,
    authorName,
    companyName,
    bizplanProfile,
    businessSnapshot,
    bizplanMetadata,
    customerSegments,
    scoreOverall,
    summary,
    revenueModels,
    pricingSignals,
    financialMetrics,
    financialRedFlags,
    unitEconomicsSignals,
    marketValidation,
    competitionInsights,
    directCompetitors,
    marketRedFlags,
    referenceUrls,
    normalizeList,
    chartDimensions,
    radarSize,
    radarCenter,
    radarDataPoints,
    radarLevels,
    toRadarPoint,
    strengths,
    overallFeedback,
    dimensionDetails,
    improvements,
    feedbackForm,
    setFeedbackForm,
    handleSubmitFeedback,
    isFeedbackSubmitting,
    isFeedbackLocked,
    hasResultData,
    errorMessage,
    onBack,
    backButtonLabel = 'Kembali ke History',
    toDisplayText,
    showFeedbackSection = true,
    showBackButton = true,
  } = props

  return (
    <div className="grid gap-4 lg:grid-cols-[240px_minmax(0,1fr)] lg:items-start">
      <TableOfContents items={tableOfContents} onClick={handleTableOfContentsClick} />

      <div className="order-2 flex flex-col gap-4">
        {docType === 'bizplan' ? (
          <AnalysisBizplanView
            isLoading={isLoading}
            companyName={companyName}
            journalTitle={journalTitle}
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
            dimensionDetails={dimensionDetails}
            strengths={strengths}
            improvements={improvements}
            overallFeedback={overallFeedback}
            toDisplayText={toDisplayText}
          />
        ) : (
          <AnalysisDefaultView
            isLoading={isLoading}
            journalTitle={journalTitle}
            authorName={authorName}
            scoreOverall={scoreOverall}
            summary={summary}
            chartDimensions={chartDimensions}
            radarSize={radarSize}
            radarCenter={radarCenter}
            radarDataPoints={radarDataPoints}
            radarLevels={radarLevels}
            toRadarPoint={toRadarPoint}
            dimensionDetails={dimensionDetails}
            strengths={strengths}
            improvements={improvements}
            overallFeedback={overallFeedback}
            referenceUrls={referenceUrls}
          />
        )}

        {showFeedbackSection ? (
          <FeedbackSection
            feedbackForm={feedbackForm}
            setFeedbackForm={setFeedbackForm}
            handleSubmitFeedback={handleSubmitFeedback}
            isFeedbackSubmitting={isFeedbackSubmitting}
            isFeedbackLocked={isFeedbackLocked}
          />
        ) : null}

        <div className="flex flex-col gap-3">
          {!isLoading && !hasResultData && <p className="text-sm text-[#6A7DB7]">Hasil analisis belum tersedia.</p>}
          {errorMessage && <p className="text-sm text-red-600">{errorMessage}</p>}
          {showBackButton ? (
            <div className="flex justify-end">
              <Button type="button" variant="outline" onClick={onBack}>
                {backButtonLabel}
              </Button>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  )
}
