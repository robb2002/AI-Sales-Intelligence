import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Card } from '../../components/ui/Card'

interface Point {
  date: string
  count: number
}

function parseDay(value: string): Date {
  return new Date(`${value}T00:00:00Z`)
}

function formatDay(value: string, long = false): string {
  const parsed = parseDay(value)
  if (Number.isNaN(parsed.getTime())) return value
  return parsed.toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: long ? 'numeric' : undefined,
    timeZone: 'UTC',
  })
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
  label,
}: {
  active?: boolean
  payload?: Array<{ value?: number | string }>
  label?: string | number
}) {
  if (!active || !payload?.length) return null
  const value = Number(payload[0]?.value ?? 0)
  return (
    <div className="rounded-md border border-default bg-surface px-3 py-2 text-caption shadow-md">
      <p className="font-medium text-primary">{formatDay(String(label), true)}</p>
      <p className="text-secondary">
        {value} signal{value === 1 ? '' : 's'}
      </p>
    </div>
  )
}

export function SignalVolumeChart({ data }: { data: Point[] }) {
  const total = data.reduce((sum, p) => sum + p.count, 0)
  const peak = data.reduce<Point | null>((best, p) => (!best || p.count > best.count ? p : best), null)
  const first = data[0]
  const last = data[data.length - 1]

  if (data.length === 0 || total === 0) {
    return (
      <Card className="space-y-2">
        <h3 className="text-h3 text-primary">Signal volume</h3>
        <p className="text-body-sm text-secondary">
          No signals were recorded in the last {data.length || 30} days.
        </p>
      </Card>
    )
  }

  const summary =
    `${total} signal${total === 1 ? '' : 's'} recorded between ${formatDay(first.date, true)} and ` +
    `${formatDay(last.date, true)}. Busiest day: ${formatDay(peak!.date, true)} with ${peak!.count}.`

  return (
    <Card className="space-y-3">
      <div>
        <h3 className="text-h3 text-primary">Signal volume</h3>
        <p className="mt-1 text-body-sm text-secondary">{summary}</p>
      </div>
      <figure className="m-0">
        <div className="h-60 w-full" role="img" aria-label={summary}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={data} margin={{ top: 8, right: 12, bottom: 24, left: 8 }}>
              <CartesianGrid vertical={false} stroke="var(--color-neutral-200)" strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(v: string) => formatDay(v)}
                tickLine={false}
                axisLine={false}
                interval="preserveStartEnd"
                minTickGap={32}
                tick={{ fill: 'var(--color-secondary)', fontSize: 12 }}
                label={{
                  value: 'Date',
                  position: 'insideBottom',
                  offset: -16,
                  fill: 'var(--color-secondary)',
                  fontSize: 12,
                }}
              />
              <YAxis
                allowDecimals={false}
                tickCount={5}
                tickLine={false}
                axisLine={false}
                width={44}
                tick={{ fill: 'var(--color-secondary)', fontSize: 12 }}
                label={{
                  value: 'Signals per day',
                  angle: -90,
                  position: 'insideLeft',
                  fill: 'var(--color-secondary)',
                  fontSize: 12,
                  style: { textAnchor: 'middle' },
                }}
              />
              <Tooltip content={<ChartTooltip />} />
              <Area
                type="monotone"
                dataKey="count"
                name="Signals"
                stroke="var(--color-navy-600)"
                strokeWidth={2}
                fill="var(--color-navy-600)"
                fillOpacity={0.08}
                isAnimationActive={!prefersReducedMotion()}
                animationDuration={240}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </Card>
  )
}
