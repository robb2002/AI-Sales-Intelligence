import { useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Circle, LoaderCircle, RefreshCw, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { getDashboard } from '../../api/dashboard'
import {
  getScanBatch,
  listOrganizationSources,
  listOrganizations,
  listScans,
  startScanAll,
} from '../../api/scans'
import { isApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { AiPanel } from '../../components/intelligence/AiPanel'
import { EvidenceList } from '../../components/intelligence/EvidenceList'
import { OpportunityCard } from '../../components/intelligence/OpportunityCard'
import { SignalCard } from '../../components/intelligence/SignalCard'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { Skeleton } from '../../components/ui/Skeleton'
import { ErrorState } from '../../components/ui/ErrorState'
import type {
  DashboardInsight,
  DashboardResponse,
  OrganizationSourceItem,
  ScanBatchResponse,
  ScanSummary,
} from '../../types/api'
import { useCurrentUser } from '../auth/useCurrentUser'
import { DashboardMetrics, DashboardMetricsSkeleton } from './DashboardMetrics'
import { splitInsightProse } from '../intelligence/readableProse'
import { ScoreBandChart } from './ScoreBandChart'
import { SignalTypeDistributionChart } from './SignalTypeDistributionChart'
import { SignalVolumeChart } from './SignalVolumeChart'

const DISCOVERY_STAGES = [
  { key: 'discovering', label: 'Discovering sources' },
  { key: 'validating_sources', label: 'Validating sources' },
  { key: 'saving_sources', label: 'Saving approved sources' },
  { key: 'extracting', label: 'Extracting content' },
] as const

const DASHBOARD_STALE_MS = 60_000
const BATCH_POLL_MS = 5_000
const SOURCES_POLL_MS = 8_000
const SOURCES_FETCH_CONCURRENCY = 2

async function mapPool<T, R>(
  items: T[],
  concurrency: number,
  worker: (item: T) => Promise<R>,
): Promise<R[]> {
  const results: R[] = new Array(items.length)
  let next = 0
  async function run(): Promise<void> {
    while (next < items.length) {
      const index = next
      next += 1
      results[index] = await worker(items[index])
    }
  }
  const runners = Array.from({ length: Math.min(concurrency, items.length) }, () => run())
  await Promise.all(runners)
  return results
}

function stageIndex(stage: string | null | undefined, status: string): number {
  if (status === 'succeeded' || status === 'partial' || status === 'failed' || status === 'interrupted') {
    return DISCOVERY_STAGES.length
  }
  if (!stage) return 0
  const index = DISCOVERY_STAGES.findIndex((item) => item.key === stage)
  return index < 0 ? 0 : index
}

function formatScanTime(value: string | null): string {
  if (!value) return ''
  return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}

export function DashboardPage() {
  const { data: user } = useCurrentUser()
  const queryClient = useQueryClient()
  const [batch, setBatch] = useState<ScanBatchResponse | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const [scanningOpen, setScanningOpen] = useState(false)

  const dashboardQuery = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    staleTime: DASHBOARD_STALE_MS,
    refetchInterval: (query) => (query.state.data?.scan_status.running ? 5000 : false),
  })

  const orgsQuery = useQuery({
    queryKey: ['organizations', 'active'],
    queryFn: () => listOrganizations({ tracking_status: ['active'] }),
    staleTime: DASHBOARD_STALE_MS,
  })

  const latestScanQuery = useQuery({
    queryKey: ['scans', 'latest'],
    queryFn: () => listScans({ limit: 1 }),
    staleTime: DASHBOARD_STALE_MS,
  })
  const latestScan = latestScanQuery.data?.data[0] ?? null

  const batchRunning =
    batch != null &&
    (batch.status === 'running' || batch.scans.some((s) => s.status === 'queued' || s.status === 'running'))

  useEffect(() => {
    if (batch || !latestScan?.batch_id) return
    if (latestScan.status !== 'queued' && latestScan.status !== 'running') return
    void getScanBatch(latestScan.batch_id)
      .then(setBatch)
      .catch(() => undefined)
  }, [batch, latestScan])

  const wasRunning = useRef(false)
  useEffect(() => {
    if (wasRunning.current && !batchRunning) {
      void queryClient.invalidateQueries({ queryKey: ['scans', 'latest'] })
      void queryClient.invalidateQueries({ queryKey: ['organization-sources'] })
      void queryClient.invalidateQueries({ queryKey: ['signals'] })
      void queryClient.invalidateQueries({ queryKey: ['opportunities'] })
      void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
    }
    wasRunning.current = batchRunning
  }, [batchRunning, queryClient])

  // Non-overlapping batch poll: wait for the previous GET to finish, then wait 5s.
  useEffect(() => {
    if (!batchRunning || !batch) return
    let cancelled = false
    const batchId = batch.batch_id

    async function poll(): Promise<void> {
      while (!cancelled) {
        try {
          const next = await getScanBatch(batchId)
          if (!cancelled) setBatch(next)
          const stillRunning =
            next.status === 'running' ||
            next.scans.some((s) => s.status === 'queued' || s.status === 'running')
          if (!stillRunning) break
        } catch {
          // Keep polling; a single failed poll must not kill progress updates.
        }
        if (cancelled) break
        await new Promise((resolve) => window.setTimeout(resolve, BATCH_POLL_MS))
      }
    }

    void poll()
    return () => {
      cancelled = true
    }
  }, [batch?.batch_id, batchRunning])

  useEffect(() => {
    if (batchRunning || starting) setScanningOpen(true)
  }, [batchRunning, starting])

  const activeOrgIds = (orgsQuery.data?.data ?? []).map((o) => o.organization_id).join(',')

  const sourcesQuery = useQuery({
    queryKey: ['organization-sources', 'dashboard', activeOrgIds],
    // Only hit /sources when the Scanning panel is open — avoids starving the scan DB pool.
    enabled: scanningOpen && Boolean(orgsQuery.data?.data.length),
    staleTime: DASHBOARD_STALE_MS,
    queryFn: async () => {
      const orgs = orgsQuery.data?.data ?? []
      return mapPool(orgs, SOURCES_FETCH_CONCURRENCY, async (org) => {
        const page = await listOrganizationSources(org.organization_id, { status: ['approved'] })
        return { organization: org, sources: page.data }
      })
    },
    refetchInterval: scanningOpen && batchRunning ? SOURCES_POLL_MS : false,
  })

  async function onScanNow() {
    setScanError(null)
    setStarting(true)
    try {
      const response = await startScanAll()
      setBatch(response)
      void queryClient.invalidateQueries({ queryKey: ['scans', 'latest'] })
    } catch (error) {
      setScanError(isApiError(error) ? error.message : 'Scan could not be started.')
    } finally {
      setStarting(false)
    }
  }

  if (!user) return null

  const activeOrgs = orgsQuery.data?.data ?? []
  const orgsPending = orgsQuery.isPending
  const sourcesPending = sourcesQuery.isPending && !sourcesQuery.data
  const sourcesRefreshing = sourcesQuery.isFetching && Boolean(sourcesQuery.data)

  return (
    <div className="space-y-8">
      {dashboardQuery.data?.data_origin === 'cached' && (
        <Alert variant="cached" title="Showing cached data">
          Some figures on this dashboard come from the cached fallback dataset because a public source
          was temporarily unavailable. Affected items are labelled.
        </Alert>
      )}

      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-label text-secondary uppercase tracking-wide">Portfolio overview</p>
          <p className="mt-1 max-w-[68ch] text-body-sm text-secondary">
            Situational awareness across opportunities, signals, competitor activity, and scans —
            then prioritized accounts to research next.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="secondary"
            icon={RefreshCw}
            loading={starting || batchRunning}
            onClick={() => void onScanNow()}
            disabled={orgsPending || activeOrgs.length === 0}
          >
            {batchRunning ? 'Scan in progress' : 'Scan All'}
          </Button>
          <a
            href="#scanning"
            className="text-body-sm font-medium text-navy-600 hover:underline focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden"
          >
            Scan details
          </a>
        </div>
      </div>

      {dashboardQuery.isPending && <DashboardMetricsSkeleton />}

      {dashboardQuery.isError && (
        <Card>
          <ErrorState
            title="Dashboard could not be loaded"
            description={
              isApiError(dashboardQuery.error)
                ? dashboardQuery.error.message
                : 'The dashboard request failed.'
            }
            reference={isApiError(dashboardQuery.error) ? dashboardQuery.error.requestId : null}
            onRetry={() => void dashboardQuery.refetch()}
            retrying={dashboardQuery.isFetching}
          />
        </Card>
      )}

      {dashboardQuery.data && <DashboardOverview data={dashboardQuery.data} />}

      {scanError && <Alert variant="error" title="Scan failed to start">{scanError}</Alert>}

      <details
        id="scanning"
        className="scroll-mt-6 group rounded-lg border border-default bg-surface open:shadow-sm"
        open={scanningOpen}
        onToggle={(event) => setScanningOpen(event.currentTarget.open)}
      >
        <summary className="cursor-pointer list-none px-5 py-4 marker:content-none [&::-webkit-details-marker]:hidden">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 id="scanning-heading" className="text-h2 text-primary">
                Scanning
              </h2>
              <p className="mt-1 text-body-sm text-secondary">
                Source discovery, approved pages, and per-organization scan progress.
              </p>
            </div>
            <Badge variant={batchRunning ? 'soft-ai' : 'soft-neutral'}>
              {batchRunning ? 'In progress' : 'Operations'}
            </Badge>
          </div>
        </summary>

        <div className="space-y-6 border-t border-default px-5 py-5">
      <Card className="relative space-y-4 overflow-hidden">
        {(orgsQuery.isFetching || latestScanQuery.isFetching) && !orgsPending && (
          <div className="absolute inset-x-0 top-0 h-0.5 bg-indigo-500" aria-hidden />
        )}
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className="text-h3 text-primary">Source discovery</h3>
            <p className="mt-1 max-w-[68ch] text-body text-secondary">
              Scan All runs for every active organization. It collects official pages and news,
              then refreshes signals and opportunities so you can review what changed.
            </p>
          </div>
          <div className="flex flex-col items-start gap-1 sm:items-end">
            <Button
              variant="secondary"
              icon={RefreshCw}
              loading={starting || batchRunning}
              onClick={() => void onScanNow()}
              disabled={orgsPending || activeOrgs.length === 0}
            >
              {batchRunning ? 'Scan in progress' : 'Scan All'}
            </Button>
            {orgsPending ? (
              <Skeleton className="h-4 w-44" />
            ) : (
              <p className="text-caption text-muted">
                {activeOrgs.length === 0
                  ? 'Activate an organization first.'
                  : `Scans ${activeOrgs.length} active organization${activeOrgs.length === 1 ? '' : 's'}`}
              </p>
            )}
            <LastScanLine
              scan={latestScan}
              loading={latestScanQuery.isPending && !latestScanQuery.data}
            />
          </div>
        </div>

        {!orgsPending && activeOrgs.length === 0 && (
          <EmptyState
            icon={RefreshCw}
            title="No active organizations"
            description="Activate at least one organization, then run Scan All to check signals and opportunities."
          />
        )}

        {batch && <ScanBatchPanel batch={batch} />}
      </Card>

      <Card className="relative space-y-4 overflow-hidden">
        {sourcesRefreshing && (
          <div className="absolute inset-x-0 top-0 h-0.5 bg-indigo-500" aria-hidden />
        )}
        <div>
          <h3 className="text-h3 text-primary">Approved sources</h3>
          <p className="mt-1 text-body text-secondary">
            Validated official page URLs stored for active organizations.
          </p>
        </div>

        {(orgsPending || sourcesPending) && <ApprovedSourcesSkeleton />}

        {!sourcesPending &&
          sourcesQuery.data?.map(({ organization, sources }) => (
            <OrganizationSourcesBlock
              key={organization.organization_id}
              name={organization.name}
              isCompetitor={organization.market_role === 'competitor'}
              sources={sources}
            />
          ))}

        {!sourcesPending &&
          sourcesQuery.isSuccess &&
          sourcesQuery.data.every((row) => row.sources.length === 0) && (
            <EmptyState
              icon={RefreshCw}
              title="No approved sources yet"
              description="Run Scan All to discover and validate official website pages."
            />
          )}

        {!orgsPending && activeOrgs.length === 0 && !sourcesPending && (
          <p className="text-body-sm text-muted">Approved sources appear after you activate organizations and scan.</p>
        )}
      </Card>
        </div>
      </details>
    </div>
  )
}

function DashboardOverview({ data }: { data: DashboardResponse }) {
  const empty =
    data.opportunities.total === 0 &&
    data.signals.validated_total === 0 &&
    data.competitor_vendor.validated_total === 0 &&
    data.prioritized_opportunities.length === 0 &&
    data.recent_signals.length === 0

  return (
    <div className="space-y-8">
      <DashboardMetrics data={data} empty={empty} />

      {empty ? (
        <Card>
          <EmptyState
            icon={RefreshCw}
            title="No intelligence collected yet"
            description="There are no validated signals or potential opportunities yet. Run Scan All to collect public information for your active organizations."
            action={
              <a
                href="#scanning"
                className="text-body font-medium text-navy-600 hover:underline focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden"
              >
                Go to Scanning
              </a>
            }
          />
        </Card>
      ) : (
        <div className="grid gap-8 xl:grid-cols-3">
          <div className="space-y-8 xl:col-span-2">
            <section aria-labelledby="prioritized-heading" className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <h2 id="prioritized-heading" className="text-h2 text-primary">
                  Prioritized potential opportunities
                </h2>
                <Link
                  to="/opportunities"
                  className="text-body-sm font-medium text-navy-600 hover:underline focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden"
                >
                  View all
                </Link>
              </div>
              {data.prioritized_opportunities.length === 0 ? (
                <p className="text-body-sm text-secondary">
                  No potential opportunities have been generated yet. They appear when related
                  validated signals are connected for an organization.
                </p>
              ) : (
                <div className="space-y-3">
                  {data.prioritized_opportunities.slice(0, 5).map((opportunity) => (
                    <OpportunityCard key={opportunity.opportunity_id} opportunity={opportunity} />
                  ))}
                </div>
              )}
            </section>

            <section
              aria-labelledby="distribution-heading"
              className="grid gap-4 lg:grid-cols-2"
            >
              <h2 id="distribution-heading" className="sr-only">
                Portfolio distributions
              </h2>
              <SignalTypeDistributionChart byType={data.signals.by_type} />
              <ScoreBandChart byBand={data.opportunities.by_band} />
            </section>

            <section aria-labelledby="activity-heading" className="space-y-4">
              <div className="flex items-center justify-between gap-4">
                <h2 id="activity-heading" className="text-h2 text-primary">
                  Signal activity
                </h2>
                <Link
                  to="/signals"
                  className="text-body-sm font-medium text-navy-600 hover:underline focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden"
                >
                  View all
                </Link>
              </div>
              <SignalVolumeChart data={data.signal_volume} />
              {data.recent_signals.length === 0 ? (
                <p className="text-body-sm text-secondary">No validated signals to show yet.</p>
              ) : (
                <div className="space-y-3">
                  {data.recent_signals.map((signal) => (
                    <SignalCard key={signal.signal_id} signal={signal} />
                  ))}
                </div>
              )}
            </section>
          </div>

          <aside aria-label="AI insights" className="space-y-4 xl:col-span-1">
            <h2 className="text-h2 text-primary">AI insights</h2>
            <AiInsights insights={data.ai_insights} />
          </aside>
        </div>
      )}
    </div>
  )
}

function AiInsights({ insights }: { insights: DashboardInsight[] }) {
  if (insights.length === 0) {
    return (
      <AiPanel label="interpretation" className="p-5!">
        <p className="text-body text-on-ai">
          Insufficient evidence for portfolio insights right now.
        </p>
        <p className="mt-2 text-body-sm text-on-ai-muted">
          Insights appear when validated signals and opportunities have enough stored evidence.
          Run Scan All, then review opportunities and ask the Advisor about a specific account.
        </p>
      </AiPanel>
    )
  }

  return (
    <AiPanel label="interpretation" className="p-5!">
      <div className="space-y-6">
        {insights.map((insight, index) => {
          const { lead, bullets } = splitInsightProse(insight.text)
          return (
            <div
              key={index}
              className={index > 0 ? 'space-y-3 border-t border-indigo-500/25 pt-5' : 'space-y-3'}
            >
              <div className="flex gap-2.5">
                <Sparkles
                  aria-hidden
                  className="mt-1 size-4 shrink-0 text-indigo-400"
                  strokeWidth={1.75}
                />
                <div className="min-w-0 space-y-2.5">
                  <p className="text-body-lg font-medium leading-relaxed text-on-ai">{lead}</p>
                  {bullets.length > 0 && (
                    <ul className="list-disc space-y-1.5 pl-4 text-body leading-relaxed text-on-ai-muted">
                      {bullets.map((bullet, bulletIndex) => (
                        <li key={bulletIndex}>{bullet}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
              {insight.evidence.length > 0 && (
                <details className="rounded-lg bg-surface p-3 text-primary">
                  <summary className="cursor-pointer text-body-sm font-medium text-navy-600 focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:outline-hidden">
                    View {insight.evidence.length} source{insight.evidence.length === 1 ? '' : 's'}
                  </summary>
                  <div className="mt-3">
                    <EvidenceList items={insight.evidence} heading="SOURCES" />
                  </div>
                </details>
              )}
            </div>
          )
        })}
      </div>
    </AiPanel>
  )
}

function LastScanLine({ scan, loading }: { scan: ScanSummary | null; loading: boolean }) {
  if (loading) return <Skeleton className="h-4 w-52" />
  if (!scan) return <p className="text-caption text-muted">No scans yet</p>

  const running = scan.status === 'queued' || scan.status === 'running'
  const when = formatScanTime(running ? scan.started_at : scan.finished_at ?? scan.started_at)
  const text = running
    ? when
      ? `Scan in progress · ${when}`
      : 'Scan in progress'
    : when
      ? `Last scan: ${when}`
      : 'Last scan'

  return <p className="text-caption text-muted sm:text-right">{text}</p>
}

function ApprovedSourcesSkeleton() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading approved sources">
      {[0, 1].map((block) => (
        <div key={block} className="space-y-3 border-t border-default pt-4 first:border-t-0 first:pt-0">
          <Skeleton className="h-5 w-48" />
          <div className="space-y-3">
            <div className="rounded-md border border-default bg-surface px-3 py-3">
              <div className="flex gap-2">
                <Skeleton className="h-5 w-20 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <Skeleton className="mt-3 h-4 w-3/4" />
              <Skeleton className="mt-2 h-3 w-full" />
              <Skeleton className="mt-2 h-3 w-40" />
            </div>
            <div className="rounded-md border border-default bg-surface px-3 py-3">
              <div className="flex gap-2">
                <Skeleton className="h-5 w-24 rounded-full" />
                <Skeleton className="h-5 w-16 rounded-full" />
              </div>
              <Skeleton className="mt-3 h-4 w-2/3" />
              <Skeleton className="mt-2 h-3 w-5/6" />
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

function ScanBatchPanel({ batch }: { batch: ScanBatchResponse }) {
  const complete = !['running'].includes(batch.status)
  const approved = batch.scans.reduce((sum, scan) => sum + scan.sources_approved, 0)
  const rejected = batch.scans.reduce((sum, scan) => sum + scan.sources_rejected, 0)
  const documents = batch.scans.reduce((sum, scan) => sum + scan.documents_collected, 0)
  const failedOrgs = batch.scans.filter((s) => s.status === 'failed').length
  const partialOrgs = batch.scans.filter((s) => s.status === 'partial').length
  const interruptedOrgs = batch.scans.filter((s) => s.status === 'interrupted').length

  const alertTitle =
    batch.status === 'failed'
      ? 'Scan batch failed'
      : batch.status === 'partial'
        ? 'Scan batch complete with partial results'
        : batch.status === 'interrupted'
          ? 'Scan batch interrupted'
          : 'Scan batch complete'

  const alertBody =
    batch.status === 'failed'
      ? `Organization scan runs failed (${failedOrgs}). This is the batch/org scan outcome — not the same as a single page showing “Extraction failed”.`
      : batch.status === 'partial'
        ? `${partialOrgs} organization${partialOrgs === 1 ? '' : 's'} finished with some source or stage issues. A red “Extraction failed” badge on one URL means only that page could not be stored — other pages and orgs may still succeed.`
        : batch.status === 'interrupted'
          ? `${interruptedOrgs || batch.organization_count} run${(interruptedOrgs || batch.organization_count) === 1 ? '' : 's'} stopped when the server restarted. Start Scan All again after the backend is up.`
          : `${approved} approved sources · ${rejected} rejected candidates · ${documents} new or updated documents`

  return (
    <div className="space-y-4 rounded-lg border border-default bg-surface-sunken/40 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={complete ? (batch.status === 'failed' ? 'soft-risk' : 'soft-positive') : 'soft-ai'}>
          batch: {batch.status}
        </Badge>
        <span className="text-caption text-muted">
          {batch.organization_count} organization{batch.organization_count === 1 ? '' : 's'}
        </span>
      </div>

      {complete && (
        <Alert
          variant={
            batch.status === 'failed'
              ? 'error'
              : batch.status === 'partial' || batch.status === 'interrupted'
                ? 'attention'
                : 'success'
          }
          title={alertTitle}
        >
          {alertBody}
          {batch.status !== 'interrupted' && batch.status !== 'failed' && (
            <span className="mt-1 block text-caption">
              {approved} approved sources · {rejected} rejected candidates · {documents} new or
              updated documents
            </span>
          )}
        </Alert>
      )}

      <p className="text-caption text-muted">
        Tip: “Extraction failed” on a page is per-URL content collection. Batch/org status above is
        the overall scan run for that organization.
      </p>

      <ul className="space-y-4">
        {batch.scans.map((scan) => (
          <li key={scan.scan_id} className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-body font-medium text-primary">{scan.organization_name}</p>
              <Badge
                variant={
                  scan.status === 'failed'
                    ? 'soft-risk'
                    : scan.status === 'partial' || scan.status === 'interrupted'
                      ? 'soft-opportunity'
                      : scan.status === 'succeeded'
                        ? 'soft-positive'
                        : 'soft-neutral'
                }
              >
                org scan: {scan.status}
              </Badge>
            </div>
            <StageStepper scan={scan} />
            <p className="text-caption text-muted">
              Candidates {scan.candidates_found} · Approved {scan.sources_approved} · Rejected{' '}
              {scan.sources_rejected} · New or updated documents {scan.documents_collected}
            </p>
          </li>
        ))}
      </ul>
    </div>
  )
}

function StageStepper({ scan }: { scan: ScanSummary }) {
  const active = stageIndex(scan.stage, scan.status)
  return (
    <ol className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:gap-4">
      {DISCOVERY_STAGES.map((stage, index) => {
        const done = index < active || active >= DISCOVERY_STAGES.length
        const current = index === active && active < DISCOVERY_STAGES.length
        return (
          <li key={stage.key} className="flex items-center gap-2 text-body-sm">
            {done ? (
              <CheckCircle2 className="size-4 text-status-positive" strokeWidth={1.75} />
            ) : current ? (
              <LoaderCircle className="size-4 animate-spin text-status-ai" strokeWidth={1.75} />
            ) : (
              <Circle className="size-4 text-neutral-300" strokeWidth={1.75} />
            )}
            <span
              className={current ? 'font-medium text-primary' : done ? 'text-secondary' : 'text-muted'}
            >
              {stage.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function OrganizationSourcesBlock({
  name,
  isCompetitor = false,
  sources,
}: {
  name: string
  isCompetitor?: boolean
  sources: OrganizationSourceItem[]
}) {
  const getExtractionBadge = (status: string) => {
    switch (status) {
      case 'extracted':
        return <Badge variant="soft-positive">Content extracted</Badge>
      case 'extracting':
        return (
          <Badge variant="soft-ai" className="animate-pulse">
            In progress
          </Badge>
        )
      case 'failed':
        return <Badge variant="soft-risk">This page: extraction failed</Badge>
      default:
        return null
    }
  }

  return (
    <div className="space-y-3 border-t border-default pt-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h3 className="flex flex-wrap items-center gap-2 text-body font-medium text-primary">
          {name}
          {isCompetitor && <Badge variant="soft-neutral">Competitor</Badge>}
        </h3>
      </div>

      {sources.length === 0 ? (
        <p className="text-body-sm text-muted">No approved sources stored yet.</p>
      ) : (
        <ul className="space-y-3">
          {sources.map((source) => (
            <li
              key={source.organization_source_id}
              className="rounded-md border border-default bg-surface px-3 py-3"
            >
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="soft-ai">{source.page_category}</Badge>
                <Badge variant="soft-positive">{source.status}</Badge>
                {getExtractionBadge(source.extraction_status)}
              </div>
              {source.extraction_status === 'failed' && (
                <p className="mt-2 text-caption text-secondary">
                  Only this URL failed content collection. Other pages and the org scan may still
                  succeed. Re-run Scan Now on the organization after the backend is restarted if a
                  page fix was deployed.
                </p>
              )}
              <p className="mt-2 text-body text-primary">{source.source_title || 'Official page'}</p>
              <a
                href={source.url}
                target="_blank"
                rel="noreferrer"
                className="mt-1 break-all text-body-sm text-navy-600 hover:underline"
              >
                {source.url}
              </a>
              <p className="mt-1 text-caption text-muted">
                Last validated {new Date(source.last_validated_at).toLocaleString()}
                {source.document_count > 0 &&
                  ` · ${source.document_count} document${source.document_count === 1 ? '' : 's'} stored`}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
