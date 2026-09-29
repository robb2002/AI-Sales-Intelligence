import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '../../components/ui/Card'
import { SCORE_BAND_LABELS } from '../intelligence/labels'
import type { ScoreBand } from '../../types/api'

const BAND_ORDER: ScoreBand[] = ['high', 'medium', 'low', 'monitor']

const BAND_FILL: Record<ScoreBand, string> = {
  high: 'var(--color-amber-500)',
  medium: 'var(--color-navy-500)',
  low: 'var(--color-neutral-500)',
  monitor: 'var(--color-neutral-400)',
}

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload?: { label: string; count: number } }>
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div className="rounded-md border border-default bg-surface px-3 py-2 text-caption shadow-md">
      <p className="font-medium text-primary">{row.label}</p>
      <p className="text-secondary">
        {row.count} potential opportunit{row.count === 1 ? 'y' : 'ies'}
      </p>
    </div>
  )
}

export function ScoreBandChart({ byBand }: { byBand: Record<ScoreBand, number> }) {
  const data = BAND_ORDER.map((band) => ({
    band,
    label: SCORE_BAND_LABELS[band],
    count: byBand[band] ?? 0,
  }))
  const total = data.reduce((sum, row) => sum + row.count, 0)

  if (total === 0) {
    return (
      <Card className="space-y-2">
        <h3 className="text-h3 text-primary">Score band distribution</h3>
        <p className="text-body-sm text-secondary">No potential opportunities to chart yet.</p>
      </Card>
    )
  }

  return (
    <Card className="space-y-3">
      <div>
        <h3 className="text-h3 text-primary">Score band distribution</h3>
        <p className="mt-1 text-body-sm text-secondary">
          {total} potential opportunit{total === 1 ? 'y' : 'ies'} by rules score band.
        </p>
      </div>
      <figure className="m-0">
        <div
          className="h-60 w-full"
          role="img"
          aria-label={`Opportunity counts by score band. Total ${total}.`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 8, right: 12, bottom: 8, left: 8 }}>
              <XAxis
                dataKey="label"
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--color-secondary)', fontSize: 12 }}
              />
              <YAxis
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                width={36}
                tick={{ fill: 'var(--color-secondary)', fontSize: 12 }}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--color-surface-sunken)' }} />
              <Bar
                dataKey="count"
                radius={[4, 4, 0, 0]}
                barSize={36}
                isAnimationActive={!prefersReducedMotion()}
                animationDuration={240}
              >
                {data.map((row) => (
                  <Cell key={row.band} fill={BAND_FILL[row.band]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </Card>
  )
}
