import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

import {
  BizplanHeader,
  DimensionsRadar,
  SharedSections,
  StatBox,
  SummaryCard,
} from './AnalysisSharedSections'

function BizplanSections({
  companyName,
  metadata,
  profile,
  businessSnapshot,
  customerSegments,
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
  toDisplayText,
}) {
  return (
    <>
      <Card id="business-snapshot" className="border-[#1f6d67]/12 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#18485b]">Model Bisnis</CardTitle>
          <CardDescription>Gambaran singkat perusahaan, pelanggan, dan monetisasi.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4 lg:grid-cols-2">
          <div className="rounded-xl border border-[#d5ebe6] bg-[#f5fbfa] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5e8c7f]">Profil Inti</p>
            <div className="mt-3 space-y-2 text-sm text-[#335866]">
              <p><span className="font-medium text-[#18485b]">Perusahaan:</span> {toDisplayText(companyName)}</p>
              <p><span className="font-medium text-[#18485b]">Industri:</span> {toDisplayText(businessSnapshot.industry || metadata.industry)}</p>
              <p><span className="font-medium text-[#18485b]">Geografi:</span> {toDisplayText(businessSnapshot.geography || metadata.geography)}</p>
              <p><span className="font-medium text-[#18485b]">Tahap:</span> {toDisplayText(businessSnapshot.business_stage || metadata.business_stage)}</p>
            </div>
          </div>
          <div className="rounded-xl border border-[#dbe4f6] bg-[#f7f9ff] p-4">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#6A7DB7]">Pelanggan & Pendapatan</p>
            <div className="mt-3 space-y-3 text-sm text-[#3f5c93]">
              <p><span className="font-medium text-[#2E3F86]">Target pelanggan:</span> {customerSegments.length > 0 ? customerSegments.join(', ') : '-'}</p>
              <p><span className="font-medium text-[#2E3F86]">Model pendapatan:</span> {revenueModels.length > 0 ? revenueModels.join(', ') : '-'}</p>
              <p><span className="font-medium text-[#2E3F86]">Pendanaan yang dicari:</span> {toDisplayText(profile.funding_ask || businessSnapshot.funding_ask)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card id="financial-health" className="border-[#d39d2c]/14 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#7c5412]">Kesehatan Finansial</CardTitle>
          <CardDescription>Unit economics, burn, runway, dan asumsi break-even.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatBox label="Burn Rate" value={financialMetrics.burn_rate} toDisplayText={toDisplayText} />
            <StatBox
              label="Runway"
              value={financialMetrics.runway_months ? `${financialMetrics.runway_months} bulan` : '-'}
              toDisplayText={toDisplayText}
            />
            <StatBox label="Break-even" value={financialMetrics.break_even_timeline} toDisplayText={toDisplayText} />
            <StatBox label="Rasio LTV/CAC" value={unitEconomicsSignals.ltv_cac_ratio} toDisplayText={toDisplayText} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-[#f0dcc0] bg-[#fffbf3] p-4 text-sm text-[#7a5a20]">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#bb8c32]">Metrik Inti</p>
              <div className="mt-3 space-y-2">
                <p><span className="font-medium">Model pendapatan:</span> {revenueModels.length > 0 ? revenueModels.join(', ') : '-'}</p>
                <p><span className="font-medium">Sinyal harga:</span> {pricingSignals.length > 0 ? pricingSignals.join(', ') : '-'}</p>
                <p><span className="font-medium">CAC:</span> {toDisplayText(financialMetrics.cac)}</p>
                <p><span className="font-medium">LTV:</span> {toDisplayText(financialMetrics.ltv)}</p>
                <p><span className="font-medium">Margin Kotor:</span> {toDisplayText(financialMetrics.gross_margin)}</p>
              </div>
            </div>
            <div className="rounded-xl border border-[#f1d5d5] bg-[#fff7f7] p-4 text-sm text-[#8a4c4c]">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#bf5b5b]">Red Flag Finansial</p>
              {financialRedFlags.length === 0 ? (
                <p className="mt-3">Tidak ada red flag finansial yang menonjol.</p>
              ) : (
                <ul className="mt-3 list-disc space-y-2 pl-5">
                  {financialRedFlags.map((item, index) => (
                    <li key={`financial-flag-${index}`}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card id="market-validation" className="border-[#2e8b7d]/14 bg-white/95">
        <CardHeader>
          <CardTitle className="text-base text-[#1f6d67]">Validasi Pasar & Kompetisi</CardTitle>
          <CardDescription>Reality check eksternal dari pencarian pasar dan pemain pembanding.</CardDescription>
        </CardHeader>
        <CardContent className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <StatBox label="Status Validasi" value={marketValidation.status} toDisplayText={toDisplayText} />
            <StatBox
              label="Kompetitor"
              value={directCompetitors.length > 0 ? directCompetitors.length : '-'}
              toDisplayText={toDisplayText}
            />
            <StatBox
              label="Bukti Eksternal"
              value={normalizeList(marketValidation.evidence).length > 0 ? normalizeList(marketValidation.evidence).length : '-'}
              toDisplayText={toDisplayText}
            />
            <StatBox
              label="Referensi Web"
              value={referenceUrls.length > 0 ? referenceUrls.length : '-'}
              toDisplayText={toDisplayText}
            />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-xl border border-[#d5ebe6] bg-[#f5fbfa] p-4 text-sm text-[#335866]">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#5e8c7f]">Ringkasan Pasar</p>
              <p className="mt-3 leading-relaxed">{toDisplayText(marketValidation.market_size_summary)}</p>
              {normalizeList(marketValidation.evidence).length > 0 && (
                <ul className="mt-3 list-disc space-y-2 pl-5">
                  {normalizeList(marketValidation.evidence).slice(0, 3).map((item, index) => (
                    <li key={`market-evidence-${index}`}>
                      <span className="font-medium">{toDisplayText(item?.title)}</span>
                      {item?.snippet ? ` - ${item.snippet}` : ''}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div className="rounded-xl border border-[#dbe4f6] bg-[#f7f9ff] p-4 text-sm text-[#3f5c93]">
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#6A7DB7]">Kompetisi</p>
              <p className="mt-3"><span className="font-medium text-[#2E3F86]">Kompetitor langsung:</span> {directCompetitors.length > 0 ? directCompetitors.join(', ') : '-'}</p>
              <p className="mt-2 leading-relaxed"><span className="font-medium text-[#2E3F86]">Risiko utama:</span> {toDisplayText(competitionInsights.key_risk)}</p>
              {marketRedFlags.length > 0 && (
                <ul className="mt-3 list-disc space-y-2 pl-5">
                  {marketRedFlags.map((item, index) => (
                    <li key={`market-flag-${index}`}>{item}</li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  )
}

export default function AnalysisBizplanView(props) {
  const {
    isLoading,
    companyName,
    journalTitle,
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
    dimensionDetails,
    strengths,
    improvements,
    overallFeedback,
    toDisplayText,
  } = props

  return (
    <>
      <BizplanHeader
        isLoading={isLoading}
        companyName={companyName}
        title={journalTitle}
        fundingAsk={bizplanProfile.funding_ask || businessSnapshot.funding_ask}
        metadata={bizplanMetadata}
        customerSegments={customerSegments}
        toDisplayText={toDisplayText}
      />

      <SummaryCard scoreOverall={scoreOverall} summary={summary} />

      <BizplanSections
        companyName={companyName}
        metadata={bizplanMetadata}
        profile={bizplanProfile}
        businessSnapshot={businessSnapshot}
        customerSegments={customerSegments}
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
        toDisplayText={toDisplayText}
      />

      <DimensionsRadar
        chartDimensions={chartDimensions}
        radarSize={radarSize}
        radarCenter={radarCenter}
        radarDataPoints={radarDataPoints}
        radarLevels={radarLevels}
        toRadarPoint={toRadarPoint}
      />

      <SharedSections
        dimensionDetails={dimensionDetails}
        strengths={strengths}
        improvements={improvements}
        overallFeedback={overallFeedback}
        referenceUrls={referenceUrls}
      />
    </>
  )
}
