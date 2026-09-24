import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Circle, LoaderCircle, RefreshCw, DownloadCloud } from 'lucide-react'
import { useEffect, useState } from 'react'
import { listOrganizationSources, listOrganizations, startScanAll, getScanBatch } from '../../api/scans'
import { isApiError } from '../../api/client'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import type { OrganizationSourceItem, ScanBatchResponse, ScanSummary } from '../../types/api'
import { ROLE_LABELS } from '../auth/roles'
import { useCurrentUser } from '../auth/useCurrentUser'
import { useIdentity } from '../auth/useIdentity'
import { getToken } from '@clerk/react'
import { env } from '../../lib/env'

const DISCOVERY_STAGES = [
  { key: 'discovering', label: 'Discovering sources' },
  { key: 'validating_sources', label: 'Validating sources' },
  { key: 'saving_sources', label: 'Saving approved sources' },
  { key: 'extracting', label: 'Extracting content' },
] as const

function stageIndex(stage: string | null | undefined, status: string): number {
  if (status === 'succeeded' || status === 'partial' || status === 'failed' || status === 'interrupted') {
    return DISCOVERY_STAGES.length
  }
  if (!stage) return 0
  const index = DISCOVERY_STAGES.findIndex((item) => item.key === stage)
  return index < 0 ? 0 : index
}

export function DashboardPage() {
  const { data: user } = useCurrentUser()
  const identity = useIdentity()
  const [batch, setBatch] = useState<ScanBatchResponse | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)

  const orgsQuery = useQuery({
    queryKey: ['organizations', 'active'],
    queryFn: () => listOrganizations({ tracking_status: ['active'] }),
  })

  const batchRunning =
    batch != null && (batch.status === 'running' || batch.scans.some((s) => s.status === 'queued' || s.status === 'running'))

  useEffect(() => {
    if (!batchRunning || !batch) return
    const timer = window.setInterval(() => {
      void getScanBatch(batch.batch_id)
        .then(setBatch)
        .catch(() => undefined)
    }, 2000)
    return () => window.clearInterval(timer)
  }, [batch, batchRunning])

  const sourcesQuery = useQuery({
    queryKey: ['organization-sources', orgsQuery.data?.data.map((o) => o.organization_id)],
    enabled: Boolean(orgsQuery.data?.data.length),
    queryFn: async () => {
      const rows = await Promise.all(
        (orgsQuery.data?.data ?? []).map(async (org) => {
          const page = await listOrganizationSources(org.organization_id, { status: ['approved'] })
          return { organization: org, sources: page.data }
        }),
      )
      return rows
    },
    refetchInterval: batchRunning ? 3000 : false,
  })

  async function onScanNow() {
    setScanError(null)
    setStarting(true)
    try {
      const response = await startScanAll()
      setBatch(response)
    } catch (error) {
      setScanError(isApiError(error) ? error.message : 'Scan could not be started.')
    } finally {
      setStarting(false)
    }
  }

  if (!user) return null

  const activeOrgs = orgsQuery.data?.data ?? []

  return (
    <div className="space-y-6">
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-green-50">
            <CheckCircle2 aria-hidden className="size-5 text-status-positive" strokeWidth={1.75} />
          </span>
          <div>
            <h2 className="text-h3 text-primary">Access verified</h2>
            <p className="mt-1 max-w-[68ch] text-body text-secondary">
              Signed in as {identity.name}. The API verified your Clerk session and loaded your role
              from the application database.
            </p>
          </div>
        </div>
        <Badge variant="outline-navy" className="self-start sm:self-center">
          {ROLE_LABELS[user.role]}
        </Badge>
      </Card>

      <Card className="space-y-4">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h2 className="text-h3 text-primary">Source discovery</h2>
            <p className="mt-1 max-w-[68ch] text-body text-secondary">
              Scan Now runs discovery for every active organization (currently ASU and UCF). The LLM
              proposes official-domain URLs; the backend validates before storing.
            </p>
          </div>
          <Button
            variant="secondary"
            icon={RefreshCw}
            loading={starting || batchRunning}
            onClick={() => void onScanNow()}
            disabled={activeOrgs.length === 0}
          >
            {batchRunning ? 'Scan in progress' : 'Scan Now'}
          </Button>
        </div>

        {scanError && <Alert variant="error" title="Scan failed to start">{scanError}</Alert>}

        {activeOrgs.length === 0 && !orgsQuery.isLoading && (
          <EmptyState
            icon={RefreshCw}
            title="No active organizations"
            description="Set tracking_status to active on at least one organization, then run Scan Now."
          />
        )}

        {batch && <ScanBatchPanel batch={batch} />}
      </Card>

      <Card className="space-y-4">
        <div>
          <h2 className="text-h3 text-primary">Approved sources</h2>
          <p className="mt-1 text-body text-secondary">
            Validated official page URLs stored for active organizations.
          </p>
        </div>
        {sourcesQuery.isLoading && <p className="text-body-sm text-muted">Loading sources…</p>}
        {sourcesQuery.data?.map(({ organization, sources }) => (
          <OrganizationSourcesBlock
            key={organization.organization_id}
            organizationId={organization.organization_id}
            name={organization.name}
            sources={sources}
          />
        ))}
        {sourcesQuery.data?.every((row) => row.sources.length === 0) && (
          <EmptyState
            icon={RefreshCw}
            title="No approved sources yet"
            description="Run Scan Now to discover and validate official website pages."
          />
        )}
      </Card>
    </div>
  )
}

function ScanBatchPanel({ batch }: { batch: ScanBatchResponse }) {
  const complete = !['running'].includes(batch.status)
  const approved = batch.scans.reduce((sum, scan) => sum + scan.sources_approved, 0)
  const rejected = batch.scans.reduce((sum, scan) => sum + scan.sources_rejected, 0)

  return (
    <div className="space-y-4 rounded-lg border border-default bg-surface-sunken/40 p-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant={complete ? 'soft-positive' : 'soft-ai'}>{batch.status}</Badge>
        <span className="text-caption text-muted">
          {batch.organization_count} organization{batch.organization_count === 1 ? '' : 's'}
        </span>
      </div>

      {complete && (
        <Alert
          variant={batch.status === 'failed' ? 'error' : batch.status === 'partial' ? 'attention' : 'success'}
          title={
            batch.status === 'failed'
              ? 'Source discovery failed'
              : 'Source discovery complete'
          }
        >
          {approved} approved sources · {rejected} rejected candidates
        </Alert>
      )}

      <ul className="space-y-4">
        {batch.scans.map((scan) => (
          <li key={scan.scan_id} className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-body font-medium text-primary">{scan.organization_name}</p>
              <Badge variant="soft-neutral">{scan.status}</Badge>
            </div>
            <StageStepper scan={scan} />
            <p className="text-caption text-muted">
              Candidates {scan.candidates_found} · Approved {scan.sources_approved} · Rejected{' '}
              {scan.sources_rejected}
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
            <span className={current ? 'font-medium text-primary' : done ? 'text-secondary' : 'text-muted'}>
              {stage.label}
            </span>
          </li>
        )
      })}
    </ol>
  )
}

function OrganizationSourcesBlock({
  organizationId,
  name,
  sources,
}: {
  organizationId: string
  name: string
  sources: OrganizationSourceItem[]
}) {
  const getExtractionBadge = (status: string) => {
    switch (status) {
      case 'extracted':
        return <Badge variant="soft-positive">Content extracted</Badge>
      case 'extracting':
        return <Badge variant="soft-ai" className="animate-pulse">In progress</Badge>
      case 'failed':
        return <Badge variant="soft-error">Extraction failed</Badge>
      default:
        return null
    }
  }

  return (
    <div className="space-y-3 border-t border-default pt-4 first:border-t-0 first:pt-0">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h3 className="text-body font-medium text-primary">{name}</h3>
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
              <p className="mt-2 text-body text-primary">
                {source.source_title || 'Official page'}
              </p>
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
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
