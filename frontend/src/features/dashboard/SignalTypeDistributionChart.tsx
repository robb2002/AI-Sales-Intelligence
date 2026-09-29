import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '../../components/ui/Card'
import { SIGNAL_TYPE_LABELS, SIGNAL_TYPES } from '../intelligence/labels'
import type { SignalType } from '../../types/api'

const TYPE_FILL: Record<SignalType, string> = {
  procurement: 'var(--color-signal-procurement)',
  technology_initiative: 'var(--color-signal-technology)',
  leadership_change: 'var(--color-signal-leadership)',
  funding_budget: 'var(--color-signal-funding)',
  strategic_announcement: 'var(--color-signal-strategic)',
  competitor_vendor: 'var(--color-signal-competitor)',
  contract_renewal: 'var(--color-signal-contract)',
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
        {row.count} validated signal{row.count === 1 ? '' : 's'}
      </p>
    </div>
  )
}

export function SignalTypeDistributionChart({ byType }: { byType: Record<SignalType, number> }) {
  const data = SIGNAL_TYPES.map((type) => ({
    type,
    label: SIGNAL_TYPE_LABELS[type],
    count: byType[type] ?? 0,
  }))
  const total = data.reduce((sum, row) => sum + row.count, 0)

  if (total === 0) {
    return (
      <Card className="space-y-2">
        <h3 className="text-h3 text-primary">Signal type distribution</h3>
        <p className="text-body-sm text-secondary">No validated signals to chart yet.</p>
      </Card>
    )
  }

  return (
    <Card className="space-y-3">
      <div>
        <h3 className="text-h3 text-primary">Signal type distribution</h3>
        <p className="mt-1 text-body-sm text-secondary">
          {total} validated signal{total === 1 ? '' : 's'} across seven types.
        </p>
      </div>
      <figure className="m-0">
        <div
          className="h-60 w-full"
          role="img"
          aria-label={`Signal counts by type. Total ${total}.`}
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={data}
              margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
            >
              <XAxis type="number" allowDecimals={false} hide />
              <YAxis
                type="category"
                dataKey="label"
                width={128}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--color-secondary)', fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--color-surface-sunken)' }} />
              <Bar
                dataKey="count"
                radius={[0, 4, 4, 0]}
                barSize={14}
                isAnimationActive={!prefersReducedMotion()}
                animationDuration={240}
              >
                {data.map((row) => (
                  <Cell key={row.type} fill={TYPE_FILL[row.type]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </Card>
  )
}
