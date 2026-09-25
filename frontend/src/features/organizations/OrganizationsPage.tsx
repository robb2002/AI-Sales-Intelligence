import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Building2, ExternalLink, Plus, Search } from 'lucide-react'
import { useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { isApiError } from '../../api/client'
import { listOrganizations, updateOrganization } from '../../api/organizations'
import { Alert } from '../../components/ui/Alert'
import { Badge } from '../../components/ui/Badge'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ErrorState } from '../../components/ui/ErrorState'
import { Input, Select } from '../../components/ui/Input'
import { Skeleton } from '../../components/ui/Skeleton'
import { TrackingToggle } from '../../components/ui/TrackingToggle'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { useCurrentUser } from '../auth/useCurrentUser'
import { OrganizationFormModal } from './OrganizationFormModal'

const TYPE_LABELS: Record<string, string> = {
  university: 'University',
  college: 'College',
  k12_district: 'K-12 district',
  public_sector_education: 'Public-sector education',
}

function formatScanTime(value: string | null): string {
  if (!value) return 'Never scanned'
  return `Last scanned ${new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })}`
}

export function OrganizationsPage() {
  useDocumentTitle('Organizations')
  const { data: user } = useCurrentUser()
  const isManager = user?.role === 'SALES_MANAGER'
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const q = params.get('q') ?? ''
  const organizationType = params.get('organization_type') ?? ''
  const trackingStatus = params.get('tracking_status') ?? ''
  const [formOpen, setFormOpen] = useState(false)

  const query = useQuery({
    queryKey: ['organizations', 'list', q, organizationType, trackingStatus],
    queryFn: () =>
      listOrganizations({
        q: q.trim().length >= 2 ? q.trim() : undefined,
        organization_type: organizationType ? [organizationType] : undefined,
        tracking_status: trackingStatus ? [trackingStatus] : undefined,
        sort: 'name',
        limit: 100,
      }),
  })

  const activateMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'inactive' }) =>
      updateOrganization(id, { tracking_status: status }),
    onMutate: async ({ id, status }) => {
      await queryClient.cancelQueries({ queryKey: ['organizations'] })
      const previous = queryClient.getQueriesData({ queryKey: ['organizations'] })
      queryClient.setQueriesData({ queryKey: ['organizations'] }, (current: unknown) => {
        if (!current || typeof current !== 'object') return current
        const page = current as { data?: Array<{ organization_id: string; tracking_status: string }> }
        if (!Array.isArray(page.data)) {
          const detail = current as { organization_id?: string; tracking_status?: string }
          if (detail.organization_id === id) {
            return { ...detail, tracking_status: status }
          }
          return current
        }
        return {
          ...page,
          data: page.data.map((org) =>
            org.organization_id === id ? { ...org, tracking_status: status } : org,
          ),
        }
      })
      return { previous }
    },
    onError: (_err, _vars, context) => {
      for (const [key, data] of context?.previous ?? []) {
        queryClient.setQueryData(key, data)
      }
    },
    onSuccess: (updated) => {
      queryClient.setQueryData(['organizations', updated.organization_id], updated)
      queryClient.setQueriesData({ queryKey: ['organizations', 'list'] }, (current: unknown) => {
        if (!current || typeof current !== 'object') return current
        const page = current as { data?: Array<{ organization_id: string }> }
        if (!Array.isArray(page.data)) return current
        return {
          ...page,
          data: page.data.map((org) =>
            org.organization_id === updated.organization_id ? { ...org, ...updated } : org,
          ),
        }
      })
      void queryClient.invalidateQueries({ queryKey: ['organizations', 'active'] })
    },
  })

  const filtersActive = Boolean(organizationType || trackingStatus || q.trim())

  const rows = useMemo(() => query.data?.data ?? [], [query.data])

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-h2 font-semibold text-navy-700">Organizations</h1>
          <p className="mt-1 text-body-sm text-secondary">
            Tracked US education organizations. Both roles can view; managers add and activate.
          </p>
        </div>
        {isManager && (
          <Button variant="primary" icon={Plus} onClick={() => setFormOpen(true)}>
            Add organization
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted" />
          <Input
            className="pl-9"
            placeholder="Search organizations"
            value={q}
            onChange={(e) => {
              const next = new URLSearchParams(params)
              if (e.target.value) next.set('q', e.target.value)
              else next.delete('q')
              setParams(next, { replace: true })
            }}
          />
        </div>
        <Select
          value={organizationType}
          onChange={(e) => {
            const next = new URLSearchParams(params)
            if (e.target.value) next.set('organization_type', e.target.value)
            else next.delete('organization_type')
            setParams(next, { replace: true })
          }}
          className="w-48"
        >
          <option value="">All types</option>
          {Object.entries(TYPE_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        <Select
          value={trackingStatus}
          onChange={(e) => {
            const next = new URLSearchParams(params)
            if (e.target.value) next.set('tracking_status', e.target.value)
            else next.delete('tracking_status')
            setParams(next, { replace: true })
          }}
          className="w-40"
        >
          <option value="">All tracking</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </Select>
      </div>

      {activateMutation.isError && (
        <Alert variant="error" title="Tracking could not be updated">
          {isApiError(activateMutation.error)
            ? activateMutation.error.message
            : 'Try again in a moment.'}
        </Alert>
      )}

      {query.isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-lg" />
          ))}
        </div>
      )}

      {query.isError && (
        <ErrorState
          description={isApiError(query.error) ? query.error.message : 'Organizations could not be loaded.'}
          reference={isApiError(query.error) ? query.error.requestId : null}
          onRetry={() => void query.refetch()}
          retrying={query.isFetching}
        />
      )}

      {query.isSuccess && rows.length === 0 && (
        <EmptyState
          icon={Building2}
          title={filtersActive ? 'No organizations match these filters' : 'No organizations yet'}
          description={
            filtersActive
              ? 'Try clearing a filter or widening the search.'
              : isManager
                ? 'Add an organization with a real official website to start tracking.'
                : 'Ask a Sales Manager to add organizations to the tracked set.'
          }
          action={
            filtersActive ? (
              <button
                type="button"
                className="text-body font-medium text-navy-600 hover:underline"
                onClick={() => setParams({}, { replace: true })}
              >
                Clear filters
              </button>
            ) : isManager ? (
              <Button variant="primary" icon={Plus} onClick={() => setFormOpen(true)}>
                Add organization
              </Button>
            ) : undefined
          }
        />
      )}

      {query.isSuccess && rows.length > 0 && (
        <ul className="space-y-3">
          {rows.map((org) => (
            <li key={org.organization_id}>
              <Card variant="interactive" className="p-5">
                <div className="flex flex-wrap items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <Link
                        to={`/organizations/${org.organization_id}`}
                        className="text-body font-semibold text-navy-700 hover:underline"
                      >
                        {org.name}
                      </Link>
                      <Badge
                        variant={org.tracking_status === 'active' ? 'soft-positive' : 'soft-neutral'}
                      >
                        {org.tracking_status === 'active' ? 'Active' : 'Inactive'}
                      </Badge>
                      <Badge variant="soft-neutral">
                        {TYPE_LABELS[org.organization_type] ?? org.organization_type}
                      </Badge>
                    </div>
                    <p className="mt-1 text-body-sm text-secondary">
                      {[org.state_code, org.market_role === 'competitor' ? 'Competitor' : null]
                        .filter(Boolean)
                        .join(' · ') || 'US education organization'}
                      {org.website_url && (
                        <>
                          {' · '}
                          <a
                            href={org.website_url}
                            target="_blank"
                            rel="noreferrer"
                            className="inline-flex items-center gap-1 text-navy-600 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            Website
                            <ExternalLink className="size-3.5" />
                          </a>
                        </>
                      )}
                    </p>
                    <p className="mt-2 text-caption text-muted">
                      {org.signal_count} signals · {org.opportunity_count} opportunities ·{' '}
                      {formatScanTime(org.last_scanned_at)}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center gap-2">
                    {isManager && (
                      <TrackingToggle
                        size="sm"
                        active={org.tracking_status === 'active'}
                        loading={
                          activateMutation.isPending &&
                          activateMutation.variables?.id === org.organization_id
                        }
                        pendingStatus={
                          activateMutation.isPending &&
                          activateMutation.variables?.id === org.organization_id
                            ? activateMutation.variables.status
                            : null
                        }
                        onChange={(status) =>
                          activateMutation.mutate({
                            id: org.organization_id,
                            status,
                          })
                        }
                      />
                    )}
                    <Link
                      to={`/organizations/${org.organization_id}`}
                      className="inline-flex h-8 items-center justify-center rounded-md border border-default bg-surface px-3 text-body-sm font-medium text-navy-600 hover:bg-surface-sunken"
                    >
                      Open
                    </Link>
                  </div>
                </div>
              </Card>
            </li>
          ))}
        </ul>
      )}

      <OrganizationFormModal
        mode="create"
        open={formOpen}
        onClose={() => setFormOpen(false)}
        onSaved={(id) => {
          void queryClient.invalidateQueries({ queryKey: ['organizations'] })
          void navigate(`/organizations/${id}`)
        }}
      />
    </div>
  )
}
