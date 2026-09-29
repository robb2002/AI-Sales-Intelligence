import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, ExternalLink, Pencil, Plus, RefreshCw, Sparkles, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { isApiError } from '../../api/client'
import { getScan } from '../../api/scans'
import {
  addOrganizationSource,
  getOrganization,
  listOrganizationSources,
  rejectOrganizationSource,
  startOrganizationScan,
  updateOrganization,
} from '../../api/organizations'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { FieldLabel, Input, Select } from '../../components/ui/Input'
import { Skeleton } from '../../components/ui/Skeleton'
import { TrackingToggle } from '../../components/ui/TrackingToggle'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import type { OrganizationDetail, ScanDetail } from '../../types/api'
import { useCurrentUser } from '../auth/useCurrentUser'
import { DeleteOrganizationModal } from './DeleteOrganizationModal'
import { OrganizationFormModal } from './OrganizationFormModal'
import { PeerCompetitorsCard } from './PeerCompetitorsCard'
import { scanOutcomeSummary } from './scanOutcomeCopy'

const TYPE_LABELS: Record<string, string> = {
  university: 'University',
  college: 'College',
  k12_district: 'K-12 district',
  public_sector_education: 'Public-sector education',
  edtech_company: 'EdTech company',
}

const PAGE_CATEGORIES = [
  { value: 'procurement', label: 'Procurement' },
  { value: 'technology', label: 'Technology' },
  { value: 'digital_learning', label: 'Digital learning' },
  { value: 'assessment', label: 'Assessment' },
  { value: 'funding', label: 'Funding' },
  { value: 'leadership', label: 'Leadership' },
  { value: 'strategic_initiative', label: 'Strategic initiative' },
  { value: 'partnership', label: 'Partnership' },
  { value: 'news', label: 'News hub' },
] as const


function hostLabel(url: string | null): string | null {
  if (!url) return null
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function OrganizationDetailPage() {
  const { organizationId = '' } = useParams()
  const navigate = useNavigate()
  const { data: user } = useCurrentUser()
  const isManager = user?.role === 'SALES_MANAGER'
  const queryClient = useQueryClient()
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const [scanId, setScanId] = useState<string | null>(null)
  const [scanError, setScanError] = useState<string | null>(null)
  const [addOpen, setAddOpen] = useState(false)
  const [pageUrl, setPageUrl] = useState('')
  const [pageCategory, setPageCategory] = useState('technology')
  const [pageTitle, setPageTitle] = useState('')
  const [sourceError, setSourceError] = useState<string | null>(null)

  const orgQuery = useQuery({
    queryKey: ['organizations', organizationId],
    queryFn: () => getOrganization(organizationId),
    enabled: Boolean(organizationId),
    // Keep this page live without a manual reload for two cases the UI can't otherwise learn
    // about on its own: (a) a manager's scheduled trigger is armed and waiting to fire, and
    // (b) a scan — started by that trigger, by another tab, or by Scan All — is in flight for
    // this organization. 15s while only watching a future trigger; 5s (matching the existing
    // manual Scan Now poll elsewhere on this page) once a scan is actually running.
    refetchInterval: (query) => {
      const data = query.state.data as OrganizationDetail | undefined
      if (!data) return false
      const scanStatus = data.last_scan?.status
      if (scanStatus === 'queued' || scanStatus === 'running') return 5000
      if (data.scheduled_scan_at) return 15000
      return false
    },
  })

  const sourcesQuery = useQuery({
    queryKey: ['organization-sources', organizationId],
    queryFn: () => listOrganizationSources(organizationId, { status: ['approved'] }),
    enabled: Boolean(organizationId),
  })

  useDocumentTitle(orgQuery.data?.name ?? 'Organization')

  const scanQuery = useQuery({
    queryKey: ['scans', scanId],
    queryFn: () => getScan(scanId!),
    enabled: Boolean(scanId),
    refetchInterval: (q) => {
      const status = (q.state.data as ScanDetail | undefined)?.status
      // 5s matches dashboard batch polling; avoids auth/DB pressure during long scans.
      return status === 'queued' || status === 'running' ? 5000 : false
    },
  })

  useEffect(() => {
    const status = scanQuery.data?.status
    if (status === 'succeeded' || status === 'partial' || status === 'failed' || status === 'interrupted') {
      void queryClient.invalidateQueries({ queryKey: ['organizations', organizationId] })
      void queryClient.invalidateQueries({ queryKey: ['organization-sources', organizationId] })
      void queryClient.invalidateQueries({ queryKey: ['signals'] })
      void queryClient.invalidateQueries({ queryKey: ['opportunities'] })
    }
  }, [scanQuery.data?.status, organizationId, queryClient])

  const trackingMutation = useMutation({
    mutationFn: (status: 'active' | 'inactive') =>
      updateOrganization(organizationId, { tracking_status: status }),
    onMutate: async (status) => {
      await queryClient.cancelQueries({ queryKey: ['organizations', organizationId] })
      const previous = queryClient.getQueryData(['organizations', organizationId])
      queryClient.setQueryData(['organizations', organizationId], (current: unknown) => {
        if (!current || typeof current !== 'object') return current
        return { ...(current as object), tracking_status: status }
      })
      queryClient.setQueriesData({ queryKey: ['organizations', 'list'] }, (current: unknown) => {
        if (!current || typeof current !== 'object') return current
        const page = current as { data?: Array<{ organization_id: string; tracking_status: string }> }
        if (!Array.isArray(page.data)) return current
        return {
          ...page,
          data: page.data.map((org) =>
            org.organization_id === organizationId ? { ...org, tracking_status: status } : org,
          ),
        }
      })
      return { previous }
    },
    onError: (_err, _status, context) => {
      if (context?.previous !== undefined) {
        queryClient.setQueryData(['organizations', organizationId], context.previous)
      }
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['organizations', organizationId], updated)
      void queryClient.invalidateQueries({ queryKey: ['organizations', 'active'] })
    },
  })

  const addSourceMutation = useMutation({
    mutationFn: () =>
      addOrganizationSource(organizationId, {
        url: pageUrl.trim(),
        page_category: pageCategory,
        source_title: pageTitle.trim() || null,
      }),
    onSuccess: () => {
      setSourceError(null)
      setPageUrl('')
      setPageTitle('')
      setPageCategory('technology')
      setAddOpen(false)
      void queryClient.invalidateQueries({ queryKey: ['organization-sources', organizationId] })
    },
    onError: (err) => {
      setSourceError(isApiError(err) ? err.message : 'The page could not be added.')
    },
  })

  const rejectSourceMutation = useMutation({
    mutationFn: (organizationSourceId: string) =>
      rejectOrganizationSource(organizationId, organizationSourceId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['organization-sources', organizationId] })
    },
  })

  const scanMutation = useMutation({
    mutationFn: () => startOrganizationScan(organizationId),
    onMutate: () => {
      setScanError(null)
    },
    onSuccess: (scan) => {
      setScanId(scan.scan_id)
      // Seed cache so progress UI appears before the first poll round-trip.
      queryClient.setQueryData(['scans', scan.scan_id], {
        ...scan,
        sources: [],
        error_detail: null,
        changes: {},
      } satisfies ScanDetail)
    },
    onError: (err) => {
      setScanError(isApiError(err) ? err.message : 'Scan could not be started.')
    },
  })

  if (orgQuery.isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-40 w-full rounded-lg" />
      </div>
    )
  }

  if (orgQuery.isError || !orgQuery.data) {
    return (
      <ErrorState
        description={isApiError(orgQuery.error) ? orgQuery.error.message : 'Organization not found.'}
        reference={isApiError(orgQuery.error) ? orgQuery.error.requestId : null}
        onRetry={() => void orgQuery.refetch()}
        retrying={orgQuery.isFetching}
      />
    )
  }

  const org = orgQuery.data
  const sources = sourcesQuery.data?.data ?? []
  const scanStatus = scanQuery.data?.status
  const scanRunning = scanStatus === 'queued' || scanStatus === 'running'
  const scanBusy = scanMutation.isPending || scanRunning
  const scanDoneOk =
    !scanBusy && (scanStatus === 'succeeded' || scanStatus === 'partial') && scanQuery.data
  const scanOutcome = scanDoneOk ? scanOutcomeSummary(scanQuery.data) : null
  const orgActive = org.tracking_status === 'active'
  const websiteHost = hostLabel(org.website_url)

  return (
    <div className="space-y-6">
      <header className="space-y-3">
        <Link to="/organizations" className="text-caption font-medium text-navy-600 hover:underline">
          ‹ Organizations
        </Link>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 flex-1 space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-h1 font-semibold text-navy-700">{org.name}</h1>
              <Badge variant={orgActive ? 'soft-positive' : 'soft-neutral'}>
                {orgActive ? 'Active' : 'Inactive'}
              </Badge>
            </div>
            <p className="text-body-sm text-secondary">
              {TYPE_LABELS[org.organization_type] ?? org.organization_type}
              {org.state_code ? ` · ${org.state_code}` : ''}
              {websiteHost && org.website_url ? (
                <>
                  {' · '}
                  <a
                    href={org.website_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 text-navy-600 hover:underline"
                  >
                    {websiteHost}
                    <ExternalLink className="size-3.5" />
                  </a>
                </>
              ) : null}
            </p>
            {org.scheduled_scan_at && (
              <p className="text-caption font-medium text-indigo-600">
                Next scheduled scan{' '}
                {new Date(org.scheduled_scan_at).toLocaleString(undefined, {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                })}
              </p>
            )}
            <p className="text-caption text-muted">
              {org.last_scanned_at
                ? `Last scanned ${new Date(org.last_scanned_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}`
                : 'Not scanned yet'}
              {' · '}
              {org.signal_count} signals · {org.opportunity_count} opportunities
              {sources.length > 0 ? ` · ${sources.length} approved page sources` : ''}
            </p>
            {!orgActive && (
              <p className="text-caption text-muted">
                {isManager
                  ? 'Turn tracking on to enable Scan Now for this organization.'
                  : 'A Sales Manager must turn tracking on before Scan Now is available.'}
              </p>
            )}
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {isManager && (
              <>
                <Button variant="secondary" icon={Pencil} onClick={() => setEditOpen(true)}>
                  Edit
                </Button>
                <TrackingToggle
                  active={orgActive}
                  loading={trackingMutation.isPending}
                  pendingStatus={trackingMutation.variables ?? null}
                  onChange={(status) => trackingMutation.mutate(status)}
                />
                <Button
                  variant="danger"
                  icon={Trash2}
                  disabled={scanBusy}
                  onClick={() => setDeleteOpen(true)}
                >
                  Delete
                </Button>
              </>
            )}
            <Button
              variant="ai"
              icon={Sparkles}
              onClick={() =>
                void navigate(`/advisor?organization_id=${org.organization_id}`)
              }
            >
              Ask Advisor
            </Button>
            <Button
              variant="primary"
              icon={RefreshCw}
              loading={scanBusy}
              disabled={!orgActive || scanBusy}
              onClick={() => scanMutation.mutate()}
            >
              Scan Now
            </Button>
          </div>
        </div>
      </header>

      {scanError && (
        <Alert variant="error" title="Scan failed to start">
          {scanError}
        </Alert>
      )}
      {trackingMutation.isError && (
        <Alert variant="error" title="Tracking could not be updated">
          {isApiError(trackingMutation.error)
            ? trackingMutation.error.message
            : 'Try again in a moment.'}
        </Alert>
      )}
      {scanMutation.isPending && (
        <Alert variant="info" title="Starting scan">
          Contacting the server. Progress will appear here in a moment.
        </Alert>
      )}
      {scanRunning && (
        <Alert variant="info" title="Scan in progress">
          Stage: {scanQuery.data?.stage ?? 'starting'}. You can leave this page; progress continues on
          the server.
        </Alert>
      )}
      {scanOutcome && (
        <Alert variant="success" title={scanOutcome.title}>
          <p>{scanOutcome.summary}</p>
          {scanOutcome.failedSourceNote && (
            <p className="mt-1">{scanOutcome.failedSourceNote}</p>
          )}
          {(scanOutcome.signalsCreated > 0 || scanOutcome.opportunitiesCreated > 0) && (
            <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1">
              {scanOutcome.signalsCreated > 0 && (
                <Link
                  to={`/signals?organization_id=${org.organization_id}`}
                  className="font-medium text-navy-600 hover:underline"
                >
                  View signals
                </Link>
              )}
              {scanOutcome.opportunitiesCreated > 0 && (
                <Link
                  to={`/opportunities?organization_id=${org.organization_id}`}
                  className="font-medium text-navy-600 hover:underline"
                >
                  View opportunities
                </Link>
              )}
            </p>
          )}
        </Alert>
      )}
      {!scanBusy && scanStatus === 'failed' && (
        <Alert variant="error" title="Scan failed">
          {scanQuery.data?.error_detail ?? 'See scan detail for more.'}
        </Alert>
      )}

      {org.ipeds && (
        <div className="rounded-none border-y border-default bg-surface-sunken px-4 py-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-label font-medium tracking-wide text-secondary uppercase">
              Institutional reference (NCES IPEDS)
            </p>
            <Badge variant="soft-neutral">Reference data</Badge>
          </div>
          <p className="mt-1 text-body-sm text-primary">
            Unit {org.ipeds.unit_id ?? '—'}
            {org.ipeds.collection_year ? ` · ${org.ipeds.collection_year}` : ''}
            {org.ipeds.release ? ` · ${org.ipeds.release}` : ''}
          </p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-default">
            <div className="flex flex-wrap gap-4 text-body font-medium">
              <span className="border-b-2 border-navy-600 pb-2 text-navy-600">Sources</span>
              <Link
                to={`/signals?organization_id=${org.organization_id}`}
                className="pb-2 text-secondary hover:text-navy-600"
              >
                Signals
              </Link>
              <Link
                to={`/opportunities?organization_id=${org.organization_id}`}
                className="pb-2 text-secondary hover:text-navy-600"
              >
                Opportunities
              </Link>
            </div>
            {isManager && (
              <Button
                variant="secondary"
                size="sm"
                icon={Plus}
                className="mb-1"
                onClick={() => {
                  setSourceError(null)
                  setAddOpen((open) => !open)
                }}
              >
                {addOpen ? 'Cancel' : 'Add official page'}
              </Button>
            )}
          </div>

          {isManager && addOpen && (
            <Card className="space-y-4 p-4">
              <div>
                <p className="text-body font-medium text-primary">Add official page</p>
                <p className="mt-1 text-body-sm text-secondary">
                  Same-domain public pages only (for example news or procurement). The URL is
                  live-checked before save. SAM.gov and other APIs are collected automatically on
                  Scan Now — do not paste them here.
                </p>
              </div>
              {sourceError && (
                <Alert variant="error" title="Could not add page">
                  {sourceError}
                </Alert>
              )}
              <div>
                <FieldLabel htmlFor="page-url">Page URL</FieldLabel>
                <Input
                  id="page-url"
                  value={pageUrl}
                  onChange={(e) => setPageUrl(e.target.value)}
                  placeholder={org.website_url ? `${org.website_url.replace(/\/$/, '')}/…` : 'https://…'}
                  disabled={addSourceMutation.isPending}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <FieldLabel htmlFor="page-category">Category</FieldLabel>
                  <Select
                    id="page-category"
                    value={pageCategory}
                    onChange={(e) => setPageCategory(e.target.value)}
                    disabled={addSourceMutation.isPending}
                  >
                    {PAGE_CATEGORIES.map((item) => (
                      <option key={item.value} value={item.value}>
                        {item.label}
                      </option>
                    ))}
                  </Select>
                </div>
                <div>
                  <FieldLabel htmlFor="page-title">Title (optional)</FieldLabel>
                  <Input
                    id="page-title"
                    value={pageTitle}
                    onChange={(e) => setPageTitle(e.target.value)}
                    placeholder="Leave blank to use the page title"
                    disabled={addSourceMutation.isPending}
                    maxLength={200}
                  />
                </div>
              </div>
              <div className="flex justify-end">
                <Button
                  variant="primary"
                  loading={addSourceMutation.isPending}
                  disabled={!pageUrl.trim()}
                  onClick={() => {
                    setSourceError(null)
                    addSourceMutation.mutate()
                  }}
                >
                  {addSourceMutation.isPending ? 'Verifying page…' : 'Add page'}
                </Button>
              </div>
            </Card>
          )}

          {rejectSourceMutation.isError && (
            <Alert variant="error" title="Could not reject page">
              {isApiError(rejectSourceMutation.error)
                ? rejectSourceMutation.error.message
                : 'Try again in a moment.'}
            </Alert>
          )}

          {sourcesQuery.isLoading && <Skeleton className="h-32 w-full rounded-lg" />}
          {sourcesQuery.isSuccess && sources.length === 0 && !addOpen && (
            <EmptyState
              icon={Building2}
              title="No approved page sources yet"
              description={
                isManager
                  ? orgActive
                    ? 'Run Scan Now to discover same-domain pages, or add an official page URL. Registry sources such as SAM.gov are collected during the scan, not listed as page rows.'
                    : 'Activate tracking, then run Scan Now — or add an official page URL now.'
                  : orgActive
                    ? 'Run Scan Now to discover same-domain pages. Only a Sales Manager can add official page URLs. Registry sources such as SAM.gov are collected during the scan.'
                    : 'A Sales Manager must activate tracking before you can run Scan Now.'
              }
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  <Button
                    variant="primary"
                    icon={RefreshCw}
                    loading={scanBusy}
                    disabled={!orgActive || scanBusy}
                    onClick={() => scanMutation.mutate()}
                  >
                    Scan Now
                  </Button>
                  {isManager && (
                    <Button variant="secondary" icon={Plus} onClick={() => setAddOpen(true)}>
                      Add official page
                    </Button>
                  )}
                </div>
              }
            />
          )}
          {sources.length > 0 && (
            <ul className="space-y-2">
              {sources.map((source) => (
                <li key={source.organization_source_id}>
                  <Card className="p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="text-body font-medium text-primary">
                          {source.source_title || source.page_category}
                        </p>
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-1 inline-flex items-center gap-1 break-all text-body-sm text-navy-600 hover:underline"
                        >
                          {source.url}
                          <ExternalLink className="size-3.5 shrink-0" />
                        </a>
                        <p className="mt-1 text-caption text-muted">
                          {source.page_category} · {source.document_count} documents ·{' '}
                          {source.extraction_status}
                        </p>
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge variant="soft-positive">Approved</Badge>
                        {isManager && (
                          <Button
                            variant="tertiary"
                            size="sm"
                            loading={
                              rejectSourceMutation.isPending &&
                              rejectSourceMutation.variables === source.organization_source_id
                            }
                            onClick={() => rejectSourceMutation.mutate(source.organization_source_id)}
                          >
                            Reject
                          </Button>
                        )}
                      </div>
                    </div>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </div>

        <aside className="space-y-4">
          {org.market_role === 'target' && (
            <PeerCompetitorsCard organizationId={org.organization_id} />
          )}
          <Card className="p-4">
            <p className="text-label font-medium tracking-wide text-secondary uppercase">Coverage</p>
            <ul className="mt-3 space-y-2 text-body-sm text-primary">
              <li>Official website: {websiteHost ?? 'Not set'}</li>
              <li>Approved pages: {sources.length}</li>
              <li>Tracking: {org.tracking_status}</li>
              <li>Market role: {org.market_role}</li>
            </ul>
          </Card>
          {!isManager && (
            <Alert variant="info" title="View only">
              Sales representatives can view organizations and run Scan Now. A Sales Manager adds,
              edits, or deletes organization identity.
            </Alert>
          )}
        </aside>
      </div>

      <OrganizationFormModal
        mode="edit"
        initial={org}
        open={editOpen}
        isManager={isManager}
        onClose={() => setEditOpen(false)}
        onSaved={() => {
          void queryClient.invalidateQueries({ queryKey: ['organizations'] })
        }}
      />
      <DeleteOrganizationModal
        open={deleteOpen}
        organizationId={org.organization_id}
        organizationName={org.name}
        marketRole={org.market_role}
        onClose={() => setDeleteOpen(false)}
        onDeleted={() => {
          void queryClient.invalidateQueries({ queryKey: ['organizations'] })
          void queryClient.invalidateQueries({ queryKey: ['competitors'] })
          void queryClient.invalidateQueries({ queryKey: ['signals'] })
          void queryClient.invalidateQueries({ queryKey: ['opportunities'] })
          void queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          void navigate(org.market_role === 'competitor' ? '/competitors' : '/organizations')
        }}
      />
    </div>
  )
}
