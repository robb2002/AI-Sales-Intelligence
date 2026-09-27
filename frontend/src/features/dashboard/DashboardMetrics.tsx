import { Archive } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { Skeleton } from '../../components/ui/Skeleton'
import { cn } from '../../lib/cn'
import type { DashboardResponse, DashboardScanState, ScoreBand } from '../../types/api'
import { SCORE_BAND_LABELS, formatUpdatedAt } from '../intelligence/labels'

const BAND_ORDER: ScoreBand[] = ['high', 'medium', 'low', 'monitor']

const SCAN_STATE: Record<
  DashboardScanState,
  { label: string; variant: 'soft-neutral' | 'soft-positive' | 'soft-ai' | 'soft-opportunity' | 'soft-risk' }
> = {
  never_scanned: { label: 'Never scanned', variant: 'soft-neutral' },
  current: { label: 'All scans current', variant: 'soft-positive' },
  running: { label: 'Scan running', variant: 'soft-ai' },
  partial: { label: 'Partially complete', variant: 'soft-opportunity' },
  failed: { label: 'Last scan failed', variant: 'soft-risk' },
}

function MetricCard({
  label,
  to,
  cached,
  children,
}: {
  label: string
  to?: string
  cached?: boolean
  children: ReactNode
}) {
  return (
    <Card
      variant={to ? 'interactive' : 'default'}
      className={cn('relative p-5 focus-within:ring-2 focus-within:ring-focus-ring')}
    >
      <div className="flex items-center justify-between gap-2">
        <h3 className="text-label text-secondary uppercase">
          {to ? (
            <Link
              to={to}
              className="after:absolute after:inset-0 after:rounded-lg focus-visible:outline-hidden"
            >
              {label}
            </Link>
          ) : (
            label
          )}
        </h3>
        {cached && (
          <span title="Includes cached fallback data">
            <Archive aria-label="Includes cached data" className="size-3.5 text-neutral-500" strokeWidth={1.75} />
          </span>
        )}
      </div>
      {children}
    </Card>
  )
}

function Value({ value, empty }: { value: number; empty: boolean }) {
  return (
    <p className="mt-2 text-metric tabular-nums text-primary">
      {empty ? <span aria-label="No data yet">—</span> : value}
    </p>
  )
}

export function DashboardMetrics({
  data,
  empty,
}: {
  data: DashboardResponse
  empty: boolean
}) {
  const cached = data.data_origin === 'cached'
  const { opportunities, signals, competitor_vendor: vendor, scan_status: scan } = data
  const scanState = SCAN_STATE[scan.state]
  const hint = <p className="mt-1 text-caption text-secondary">No data yet</p>

  return (
    <div className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4">
      <MetricCard label="Potential opportunities" to="/opportunities" cached={cached}>
        <Value value={opportunities.total} empty={empty} />
        {empty ? (
          hint
        ) : (
          <>
            <p className="mt-1 text-caption text-secondary">
              {BAND_ORDER.map((b) => `${opportunities.by_band[b] ?? 0} ${SCORE_BAND_LABELS[b].toLowerCase()}`).join(
                ' · ',
              )}
            </p>
            <p className="mt-0.5 text-caption text-secondary">
              {opportunities.new_count} new this week
            </p>
          </>
        )}
      </MetricCard>

      <MetricCard label="Validated signals" to="/signals?state=validated" cached={cached}>
        <Value value={signals.validated_total} empty={empty} />
        {empty ? (
          hint
        ) : (
          <p className="mt-1 text-caption text-secondary">
            {signals.recent_count} in the last {signals.recent_window_days} days
          </p>
        )}
      </MetricCard>

      <MetricCard label="Competitor/vendor activity" to="/signals?signal_type=competitor_vendor" cached={cached}>
        <Value value={vendor.validated_total} empty={empty} />
        {empty ? (
          hint
        ) : (
          <p className="mt-1 text-caption text-secondary">
            {vendor.new_in_window} new in the last {signals.recent_window_days} days
          </p>
        )}
      </MetricCard>

      <MetricCard label="Scan status">
        <div className="mt-2 flex items-center gap-2">
          <Badge variant={scanState.variant}>{scanState.label}</Badge>
        </div>
        <p className="mt-2 text-caption text-secondary">
          {scan.last_finished_at
            ? `Last finished ${formatUpdatedAt(scan.last_finished_at)}`
            : scan.running
              ? 'First scan in progress'
              : 'No completed scan yet'}
        </p>
        <p className="mt-0.5 text-caption text-secondary">
          {scan.sources_failed} failed source{scan.sources_failed === 1 ? '' : 's'}
        </p>
        <a
          href="#scanning"
          className="mt-2 inline-block text-caption font-medium text-navy-600 hover:underline focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden"
        >
          Manage scans
        </a>
      </MetricCard>
    </div>
  )
}

export function DashboardMetricsSkeleton() {
  return (
    <div
      className="grid gap-6 sm:grid-cols-2 xl:grid-cols-4"
      aria-busy="true"
      aria-label="Loading dashboard metrics"
    >
      {[0, 1, 2, 3].map((i) => (
        <Card key={i} className="p-5">
          <Skeleton className="h-3 w-32" />
          <Skeleton className="mt-3 h-8 w-16" />
          <Skeleton className="mt-3 h-3 w-40" />
        </Card>
      ))}
    </div>
  )
}
