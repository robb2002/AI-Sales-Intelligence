import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '../../components/ui/Card'
import type { CompetitorItem } from '../../types/api'

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

function shortName(name: string): string {
  return name.length > 22 ? `${name.slice(0, 20)}…` : name
}

function ChartTooltip({
  active,
  payload,
}: {
  active?: boolean
  payload?: Array<{ payload?: { name: string; count: number } }>
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div className="rounded-md border border-default bg-surface px-3 py-2 text-caption shadow-md">
      <p className="font-medium text-primary">{row.name}</p>
      <p className="text-secondary">
        {row.count} validated signal{row.count === 1 ? '' : 's'}
      </p>
    </div>
  )
}

export function CompetitorActivityChart({ competitors }: { competitors: CompetitorItem[] }) {
  const data = [...competitors]
    .map((c) => ({
      name: c.name,
      label: shortName(c.name),
      count: c.validated_signal_count,
    }))
    .sort((a, b) => b.count - a.count)

  const total = data.reduce((sum, row) => sum + row.count, 0)
  if (data.length === 0 || total === 0) {
    return (
      <Card className="space-y-2">
        <h3 className="text-h3 text-primary">Competitor activity</h3>
        <p className="text-body-sm text-secondary">
          No validated competitor signals yet. Context only — not customer opportunities.
        </p>
      </Card>
    )
  }

  return (
    <Card className="space-y-3">
      <div>
        <h3 className="text-h3 text-primary">Competitor activity</h3>
        <p className="mt-1 text-body-sm text-secondary">
          Validated signals per tracked competitor. Competitive intelligence only — not sales
          opportunities.
        </p>
      </div>
      <figure className="m-0">
        <div
          className="h-60 w-full"
          role="img"
          aria-label={`Validated signals by competitor. Total ${total}.`}
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
                width={120}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--color-secondary)', fontSize: 11 }}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: 'var(--color-surface-sunken)' }} />
              <Bar
                dataKey="count"
                radius={[0, 4, 4, 0]}
                barSize={16}
                fill="var(--color-signal-competitor)"
                isAnimationActive={!prefersReducedMotion()}
                animationDuration={240}
              >
                {data.map((row) => (
                  <Cell key={row.name} fill="var(--color-signal-competitor)" />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </Card>
  )
}
