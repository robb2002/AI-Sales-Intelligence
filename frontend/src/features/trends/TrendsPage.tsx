import { useQuery } from '@tanstack/react-query'
import { CalendarOff, Eye, MousePointerClick, TrendingUp } from 'lucide-react'
import { useMemo } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { isApiError } from '../../api/client'
import { getTrends } from '../../api/trends'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Select } from '../../components/ui/Input'
import { Skeleton } from '../../components/ui/Skeleton'
import { cn } from '../../lib/cn'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import type { SignalType, TrendsResponse } from '../../types/api'
import {
  ORG_TYPE_LABELS,
  SIGNAL_TYPE_DOT,
  SIGNAL_TYPE_LABELS,
  SIGNAL_TYPES,
} from '../intelligence/labels'

const TYPE_FILL: Record<SignalType, string> = {
  procurement: 'var(--color-signal-procurement)',
  technology_initiative: 'var(--color-signal-technology)',
  leadership_change: 'var(--color-signal-leadership)',
  funding_budget: 'var(--color-signal-funding)',
  strategic_announcement: 'var(--color-signal-strategic)',
  competitor_vendor: 'var(--color-signal-competitor)',
  contract_renewal: 'var(--color-signal-contract)',
}

const TYPE_SHORT: Record<SignalType, string> = {
  procurement: 'Procurement',
  technology_initiative: 'Technology',
  leadership_change: 'Leadership',
  funding_budget: 'Funding',
  strategic_announcement: 'Strategic',
  competitor_vendor: 'Vendor',
  contract_renewal: 'Contract',
}

const WINDOW_OPTIONS = [
  { value: '3', label: 'Last 3 months' },
  { value: '6', label: 'Last 6 months' },
  { value: '12', label: 'Last 12 months' },
] as const

function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  } catch {
    return false
  }
}

function formatMonthKey(key: string): string {
  const [year, month] = key.split('-').map(Number)
  if (!year || !month) return key
  const date = new Date(Date.UTC(year, month - 1, 1))
  return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric', timeZone: 'UTC' })
}

function monthBounds(monthKey: string): { from: string; to: string } {
  const [year, month] = monthKey.split('-').map(Number)
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate()
  return {
    from: `${monthKey}-01`,
    to: `${monthKey}-${String(lastDay).padStart(2, '0')}`,
  }
}

function signalsHref(params: Record<string, string | undefined>): string {
  const search = new URLSearchParams()
  search.set('market_role', 'target')
  search.set('state', 'validated')
  search.set('from_trends', '1')
  for (const [key, value] of Object.entries(params)) {
    if (value) search.set(key, value)
  }
  return `/signals?${search.toString()}`
}

function SummaryStrip({ data, months }: { data: TrendsResponse; months: number }) {
  const dated = data.totals.signals - data.totals.undated
  const items = [
    { label: 'Validated signals', value: data.totals.signals, hint: 'In this window' },
    { label: 'Target organizations', value: data.totals.organizations, hint: 'With ≥1 signal' },
    { label: 'Dated in window', value: dated, hint: 'Placed on a month' },
    { label: 'Undated', value: data.totals.undated, hint: 'No publication date' },
  ]
  return (
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <Card key={item.label} className="p-4">
          <p className="text-label text-secondary uppercase">{item.label}</p>
          <p className="mt-2 text-metric tabular-nums text-primary">{item.value}</p>
          <p className="mt-1 text-caption text-muted">{item.hint}</p>
        </Card>
      ))}
      <p className="sr-only">
        Observing the last {months} months for target organizations only. Not a forecast.
      </p>
    </div>
  )
}

function TypeMix({ data }: { data: TrendsResponse }) {
  const totals = useMemo(() => {
    const counts = Object.fromEntries(SIGNAL_TYPES.map((t) => [t, 0])) as Record<SignalType, number>
    for (const row of data.by_signal_type) {
      for (const type of SIGNAL_TYPES) {
        counts[type] += row.counts[type] ?? 0
      }
    }
    return SIGNAL_TYPES.map((type) => ({ type, count: counts[type] })).filter((row) => row.count > 0)
  }, [data.by_signal_type])

  if (totals.length === 0) return null

  const sum = totals.reduce((acc, row) => acc + row.count, 0)

  return (
    <div className="rounded-lg border border-default bg-surface-sunken px-4 py-3">
      <p className="text-label font-medium tracking-wide text-secondary uppercase">
        Type mix in this window
      </p>
      <p className="mt-1 text-caption text-muted">
        Dated validated signals only ({sum}). Undated signals are not assigned a type month.
      </p>
      <ul className="mt-3 flex flex-wrap gap-2">
        {totals.map(({ type, count }) => (
          <li key={type}>
            <Badge variant="soft-neutral" className="h-7 gap-1.5 px-2.5">
              <span className={cn('size-2 rounded-full', SIGNAL_TYPE_DOT[type])} aria-hidden />
              <span>{TYPE_SHORT[type]}</span>
              <span className="tabular-nums text-primary">{count}</span>
            </Badge>
          </li>
        ))}
      </ul>
    </div>
  )
}

function TypeLegend() {
  return (
    <ul className="flex flex-wrap gap-x-3 gap-y-1.5">
      {SIGNAL_TYPES.map((type) => (
        <li key={type} className="inline-flex items-center gap-1.5 text-caption text-secondary">
          <span className={cn('size-2.5 rounded-sm', SIGNAL_TYPE_DOT[type])} aria-hidden />
          {TYPE_SHORT[type]}
        </li>
      ))}
    </ul>
  )
}

function MonthTypeTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: Array<{ dataKey?: string; value?: number; color?: string }>
  label?: string
}) {
  if (!active || !payload?.length) return null
  const visible = payload.filter((entry) => (entry.value ?? 0) > 0)
  const monthTotal = visible.reduce((sum, entry) => sum + (entry.value ?? 0), 0)
  return (
    <div className="max-w-xs rounded-md border border-default bg-surface px-3 py-2 text-caption shadow-md">
      <p className="font-medium text-primary">{label}</p>
      <p className="mt-0.5 text-muted">{monthTotal} dated signal{monthTotal === 1 ? '' : 's'}</p>
      <ul className="mt-1.5 space-y-0.5">
        {visible.map((entry) => (
          <li key={String(entry.dataKey)} className="flex items-center gap-2 text-secondary">
            <span
              className="size-2.5 shrink-0 rounded-sm"
              style={{ background: entry.color }}
              aria-hidden
            />
            {SIGNAL_TYPE_LABELS[entry.dataKey as SignalType] ?? entry.dataKey}: {entry.value}
          </li>
        ))}
      </ul>
      <p className="mt-2 flex items-center gap-1 text-navy-600">
        <MousePointerClick className="size-3.5" strokeWidth={1.75} aria-hidden />
        Click a segment to open signals
      </p>
    </div>
  )
}

function BucketTooltip({
  active,
  payload,
  monthKeys,
}: {
  active?: boolean
  payload?: Array<{
    payload?: {
      label: string
      total: number
      organizations: number
      by_month: number[]
      clickable: boolean
    }
  }>
  monthKeys: string[]
}) {
  if (!active || !payload?.length) return null
  const row = payload[0]?.payload
  if (!row) return null
  return (
    <div className="max-w-xs rounded-md border border-default bg-surface px-3 py-2 text-caption shadow-md">
      <p className="font-medium text-primary">{row.label}</p>
      <p className="text-secondary">
        {row.total} signal{row.total === 1 ? '' : 's'} · {row.organizations} organization
        {row.organizations === 1 ? '' : 's'}
      </p>
      <ul className="mt-1 space-y-0.5 text-muted">
        {monthKeys.map((key, i) => (
          <li key={key}>
            {formatMonthKey(key)}: {row.by_month[i] ?? 0}
          </li>
        ))}
      </ul>
      {row.clickable ? (
        <p className="mt-2 flex items-center gap-1 text-navy-600">
          <MousePointerClick className="size-3.5" strokeWidth={1.75} aria-hidden />
          Click to open signals
        </p>
      ) : (
        <p className="mt-2 text-muted">No drill-down for unrecorded state</p>
      )}
    </div>
  )
}

function SignalsByMonthChart({
  data,
  window,
}: {
  data: TrendsResponse
  window: TrendsResponse['window']
}) {
  const navigate = useNavigate()
  const chartData = useMemo(
    () =>
      data.by_signal_type.map((row) => ({
        month: formatMonthKey(row.month),
        monthKey: row.month,
        ...row.counts,
      })),
    [data.by_signal_type],
  )

  return (
    <Card className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-label font-medium tracking-wide text-secondary uppercase">
            Signals by month and type
          </h2>
          <p className="mt-1 text-body-sm text-secondary">
            Stacked by signal type. Click a segment to open the underlying signals for that month.
          </p>
        </div>
        <span className="inline-flex items-center gap-1.5 rounded-md bg-surface-sunken px-2.5 py-1 text-caption text-secondary">
          <Eye className="size-3.5" strokeWidth={1.75} aria-hidden />
          Observed counts · click to drill down
        </span>
      </div>
      <TypeLegend />
      <figure className="m-0">
        <div
          className="h-80 w-full"
          role="img"
          aria-label="Monthly validated signal counts by type"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, bottom: 4, left: 0 }}>
              <CartesianGrid
                vertical={false}
                stroke="var(--color-border-default)"
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="month"
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--color-secondary)', fontSize: 11 }}
              />
              <YAxis
                allowDecimals={false}
                tickLine={false}
                axisLine={false}
                width={32}
                tick={{ fill: 'var(--color-secondary)', fontSize: 11 }}
              />
              <Tooltip content={<MonthTypeTooltip />} cursor={{ fill: 'var(--color-surface-sunken)' }} />
              {SIGNAL_TYPES.map((type) => (
                <Bar
                  key={type}
                  dataKey={type}
                  name={TYPE_SHORT[type]}
                  stackId="signals"
                  fill={TYPE_FILL[type]}
                  maxBarSize={48}
                  isAnimationActive={!prefersReducedMotion()}
                  animationDuration={240}
                  cursor="pointer"
                  onClick={(entry) => {
                    const monthKey = (entry as { monthKey?: string })?.monthKey
                    if (!monthKey) return
                    const bounds = monthBounds(monthKey)
                    void navigate(
                      signalsHref({
                        signal_type: type,
                        date_from: bounds.from,
                        date_to: bounds.to,
                        month_focus: monthKey,
                      }),
                    )
                  }}
                />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>
      </figure>
      <TypeMix data={data} />
      <p className="text-caption text-muted">
        Window {window.date_from} → {window.date_to} (UTC). State and vertical totals also include
        undated signals.
      </p>
    </Card>
  )
}

function HorizontalBucketChart({
  title,
  description,
  rows,
  monthKeys,
  onBarClick,
}: {
  title: string
  description: string
  rows: Array<{
    key: string
    label: string
    total: number
    organizations: number
    by_month: number[]
    clickable: boolean
  }>
  monthKeys: string[]
  onBarClick: (key: string) => void
}) {
  const data = rows.map((row) => ({
    ...row,
    labelShort: row.label.length > 18 ? `${row.label.slice(0, 16)}…` : row.label,
  }))
  const max = Math.max(...data.map((row) => row.total), 1)

  return (
    <Card className="space-y-3">
      <div>
        <h2 className="text-label font-medium tracking-wide text-secondary uppercase">{title}</h2>
        <p className="mt-1 text-body-sm text-secondary">{description}</p>
      </div>
      <figure className="m-0">
        <div className="h-60 w-full" role="img" aria-label={title}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              layout="vertical"
              data={data}
              margin={{ top: 4, right: 36, bottom: 4, left: 8 }}
            >
              <XAxis type="number" domain={[0, max]} allowDecimals={false} hide />
              <YAxis
                type="category"
                dataKey="labelShort"
                width={112}
                tickLine={false}
                axisLine={false}
                tick={{ fill: 'var(--color-secondary)', fontSize: 11 }}
              />
              <Tooltip
                content={<BucketTooltip monthKeys={monthKeys} />}
                cursor={{ fill: 'var(--color-surface-sunken)' }}
              />
              <Bar
                dataKey="total"
                fill="var(--color-navy-500)"
                radius={[0, 4, 4, 0]}
                barSize={14}
                isAnimationActive={!prefersReducedMotion()}
                animationDuration={240}
                cursor="pointer"
                onClick={(entry) => {
                  const row = entry as unknown as { key?: string; clickable?: boolean }
                  if (row.clickable && row.key) onBarClick(row.key)
                }}
              >
                <LabelList
                  dataKey="total"
                  position="right"
                  className="fill-[var(--color-secondary)] text-[11px] tabular-nums"
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </figure>
    </Card>
  )
}

export function TrendsPage() {
  useDocumentTitle('Trends')
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const rawMonths = params.get('months') ?? '6'
  const months = rawMonths === '3' || rawMonths === '12' ? Number(rawMonths) : 6

  const query = useQuery({
    queryKey: ['trends', months],
    queryFn: () => getTrends(months),
  })

  const stateRows = useMemo(() => {
    if (!query.data) return []
    return query.data.by_state.map((row) => ({
      key: row.state_code ?? '__null__',
      label: row.state_code ?? 'State not recorded',
      total: row.total,
      organizations: row.organizations,
      by_month: row.by_month,
      clickable: row.state_code != null,
    }))
  }, [query.data])

  const verticalRows = useMemo(() => {
    if (!query.data) return []
    return query.data.by_organization_type.map((row) => ({
      key: row.organization_type,
      label: ORG_TYPE_LABELS[row.organization_type] ?? row.organization_type,
      total: row.total,
      organizations: row.organizations,
      by_month: row.by_month,
      clickable: true,
    }))
  }, [query.data])

  const windowLabel =
    WINDOW_OPTIONS.find((option) => option.value === String(months))?.label ?? `Last ${months} months`

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-h2 font-semibold text-navy-700">Trends</h1>
            <Badge variant="soft-neutral">Target orgs only</Badge>
            <Badge variant="outline-navy">Observed · not a forecast</Badge>
          </div>
          {query.data ? (
            <p className="text-body-sm text-secondary">
              Validated signals from {query.data.totals.organizations} target organization
              {query.data.totals.organizations === 1 ? '' : 's'} in {windowLabel.toLowerCase()}, by
              the month the source published them. Competitors are excluded — this is buyer activity,
              not the dashboard’s full portfolio total.
            </p>
          ) : (
            !query.isError && (
              <p className="text-body-sm text-secondary">
                Observed monthly counts from stored validated signals on target organizations. Not a
                forecast.
              </p>
            )
          )}
        </div>
        <label className="block">
          <span className="mb-1.5 block text-label text-secondary uppercase">Window</span>
          <Select
            value={String(months)}
            onChange={(e) => {
              const next = new URLSearchParams(params)
              next.set('months', e.target.value)
              setParams(next, { replace: true })
            }}
            className="w-44"
          >
            {WINDOW_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </Select>
        </label>
      </div>

      {query.data?.data_origin === 'cached' && (
        <Alert variant="cached" title="Showing cached data">
          Some counted signals come from the cached fallback dataset. Affected figures still open
          the underlying signal list.
        </Alert>
      )}

      {query.isLoading && (
        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-24 w-full rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-80 w-full rounded-lg" />
          <div className="grid gap-4 lg:grid-cols-2">
            <Skeleton className="h-60 w-full rounded-lg" />
            <Skeleton className="h-60 w-full rounded-lg" />
          </div>
        </div>
      )}

      {query.isError && (
        <ErrorState
          description={isApiError(query.error) ? query.error.message : 'Trends could not be loaded.'}
          reference={isApiError(query.error) ? query.error.requestId : null}
          onRetry={() => void query.refetch()}
          retrying={query.isFetching}
        />
      )}

      {query.data && query.data.totals.signals === 0 && (
        <Card>
          <EmptyState
            icon={TrendingUp}
            title="No trend data yet"
            description="Trends appear after scans collect validated signals from target organizations."
            action={
              <Link to="/organizations" className="text-body font-medium text-navy-600 hover:underline">
                Go to Organizations
              </Link>
            }
          />
        </Card>
      )}

      {query.data && query.data.totals.signals > 0 && (
        <>
          <SummaryStrip data={query.data} months={months} />

          <SignalsByMonthChart data={query.data} window={query.data.window} />

          <div className="grid gap-4 lg:grid-cols-2">
            <HorizontalBucketChart
              title="By state"
              description="Target organizations only. Bars with no activity still appear. Click a bar to open signals."
              rows={stateRows}
              monthKeys={query.data.month_keys}
              onBarClick={(key) => {
                if (key === '__null__') return
                void navigate(
                  signalsHref({
                    state_code: key,
                    date_from: query.data.window.date_from,
                    date_to: query.data.window.date_to,
                  }),
                )
              }}
            />
            <HorizontalBucketChart
              title="By vertical"
              description="Organization type of the target. Click a bar to open signals."
              rows={verticalRows}
              monthKeys={query.data.month_keys}
              onBarClick={(key) => {
                void navigate(
                  signalsHref({
                    organization_type: key,
                    date_from: query.data.window.date_from,
                    date_to: query.data.window.date_to,
                  }),
                )
              }}
            />
          </div>

          {query.data.totals.undated > 0 && (
            <p className="flex items-start gap-2 text-caption text-muted">
              <CalendarOff className="mt-0.5 size-4 shrink-0" strokeWidth={1.75} aria-hidden />
              <span>
                {query.data.totals.undated} signal
                {query.data.totals.undated === 1 ? '' : 's'} have no publication date and are not
                placed in a month. They still count in the state and vertical totals.
              </span>
            </p>
          )}
        </>
      )}
    </div>
  )
}
