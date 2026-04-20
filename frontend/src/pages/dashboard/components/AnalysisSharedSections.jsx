import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

export function StatBox({ label, value, toDisplayText }) {
  return (
    <div className="rounded-xl border border-[#ccdae9] bg-[#f6fbff] px-4 py-3">
      <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-[#6f8aa5]">{label}</p>
      <p className="mt-1 text-sm font-medium text-[#1f4a63]">{toDisplayText(value)}</p>
    </div>
  )
}

export function DefaultHeader({ isLoading, title, authorName }) {
  return (
    <Card id="title-author" className="border-[#5E74C9]/16 bg-white/90">
      <CardHeader>
        <CardTitle className="text-4xl text-[#2E3F86]">{isLoading ? 'Memuat judul jurnal...' : title}</CardTitle>
        <CardDescription className="text-xl">Penulis: {authorName}</CardDescription>
      </CardHeader>
    </Card>
  )
}

export function BizplanHeader({ isLoading, companyName, title, fundingAsk, metadata, customerSegments, toDisplayText }) {
  return (
    <Card
      id="title-author"
      className="overflow-hidden border-0 bg-linear-to-br from-[#eff7f5] via-[#f7fbff] to-[#eef5ff] shadow-sm"
    >
      <CardHeader className="gap-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <CardDescription className="text-sm font-semibold uppercase tracking-[0.16em] text-[#5e8c7f]">
              Ringkasan Investasi
            </CardDescription>
            <CardTitle className="text-4xl text-[#18485b]">
              {isLoading ? 'Memuat business plan...' : companyName}
            </CardTitle>
            <p className="text-base text-[#4b6b79]">{title}</p>
          </div>
          <div className="rounded-2xl border border-[#bfdad1] bg-white/80 px-4 py-3 text-right">
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#6f8aa5]">Pendanaan</p>
            <p className="mt-1 text-lg font-semibold text-[#1f4a63]">{toDisplayText(fundingAsk)}</p>
          </div>
        </div>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <StatBox label="Industri" value={metadata.industry} toDisplayText={toDisplayText} />
          <StatBox label="Tahap Bisnis" value={metadata.business_stage} toDisplayText={toDisplayText} />
          <StatBox label="Geografi" value={metadata.geography} toDisplayText={toDisplayText} />
          <StatBox
            label="Target Pelanggan"
            value={customerSegments.length > 0 ? customerSegments.join(', ') : '-'}
            toDisplayText={toDisplayText}
          />
        </div>
      </CardHeader>
    </Card>
  )
}

export function SummaryCard({ scoreOverall, summary }) {
  return (
    <Card id="summary" className="border-[#5E74C9]/16 bg-white/95">
      <CardHeader>
        <CardTitle className="text-base text-[#2E3F86]">Ringkasan</CardTitle>
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
  )
}

export function DimensionsRadar({ chartDimensions, radarSize, radarCenter, radarDataPoints, radarLevels, toRadarPoint }) {
  return (
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
                const textAnchor =
                  labelPoint.x < radarCenter - 6 ? 'end' : labelPoint.x > radarCenter + 6 ? 'start' : 'middle'

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

              <polygon points={radarDataPoints} fill="#5E74C9" fillOpacity="0.2" stroke="#5E74C9" strokeWidth="2" />

              {chartDimensions.map((item, index) => {
                const point = toRadarPoint(index, chartDimensions.length, item.score / 10)
                return <circle key={`radar-point-${item.id}`} cx={point.x} cy={point.y} r="3.5" fill="#5E74C9" />
              })}
            </svg>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

export function SharedSections({ dimensionDetails, strengths, improvements, overallFeedback, referenceUrls }) {
  return (
    <>
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
          <CardTitle className="text-base text-[#2E3F86]">Feedback Keseluruhan</CardTitle>
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
          {dimensionDetails.length === 0 ? (
            <p className="text-sm text-[#6A7DB7]">Belum ada detail dimensi.</p>
          ) : (
            <div className="grid gap-3">
              {dimensionDetails.map((dimension) => (
                <article key={dimension.id} className="rounded-lg border border-[#5E74C9]/14 bg-[#f8faff] px-3 py-2">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="text-sm font-medium text-[#2E3F86]">{dimension.label}</p>
                    <p className="text-xs font-semibold text-[#4f64a4]">
                      {dimension.score.toFixed(1)} / 10
                      {dimension.weight !== null ? ` | bobot ${Math.round(dimension.weight * 100)}%` : ''}
                    </p>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-[#d9e2ff]">
                    <div className="h-full rounded-full bg-[#5E74C9]" style={{ width: `${(dimension.score / 10) * 100}%` }} />
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
    </>
  )
}
