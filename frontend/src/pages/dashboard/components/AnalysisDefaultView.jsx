import {
  DefaultHeader,
  DimensionsRadar,
  SharedSections,
  SummaryCard,
} from './AnalysisSharedSections'

export default function AnalysisDefaultView(props) {
  const {
    isLoading,
    journalTitle,
    authorName,
    scoreOverall,
    summary,
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
    referenceUrls,
  } = props

  return (
    <>
      <DefaultHeader isLoading={isLoading} title={journalTitle} authorName={authorName} />

      <SummaryCard scoreOverall={scoreOverall} summary={summary} />

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
