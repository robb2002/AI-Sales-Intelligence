import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ExternalLink, RefreshCw } from 'lucide-react'
import { useState } from 'react'
import { isApiError } from '../../api/client'
import { getPeerCompetitors, refreshPeerCompetitors } from '../../api/peerCompetitors'
import { Alert } from '../../components/ui/Alert'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { Skeleton } from '../../components/ui/Skeleton'

function safeHttpsUrl(url: string): string | null {
  try {
    const parsed = new URL(url)
    return parsed.protocol === 'https:' ? parsed.toString() : null
  } catch {
    return null
  }
}

function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}

export function PeerCompetitorsCard({ organizationId }: { organizationId: string }) {
  const queryClient = useQueryClient()
  const queryKey = ['peer-competitors', organizationId]
  const [announcement, setAnnouncement] = useState('')

  const query = useQuery({
    queryKey,
    queryFn: () => getPeerCompetitors(organizationId),
    enabled: Boolean(organizationId),
  })

  const refresh = useMutation({
    mutationFn: () => refreshPeerCompetitors(organizationId),
    onMutate: () => setAnnouncement(''),
    onSuccess: (data) => {
      queryClient.setQueryData(queryKey, data)
      setAnnouncement('Peer competitors updated')
    },
  })

  const data = query.data
  const notConfigured = data?.configured === false
  const peers = data?.peers ?? []

  return (
    <Card className="space-y-4 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <h2 className="text-h3 font-semibold text-navy-700">Peer competitors</h2>
          <p className="mt-1 text-caption text-muted">
            Context only — found by web search, not a signal or opportunity.
          </p>
        </div>
        <Button
          variant="secondary"
          size="sm"
          icon={RefreshCw}
          loading={refresh.isPending}
          disabled={notConfigured || query.isLoading}
          onClick={() => refresh.mutate()}
        >
          Update
        </Button>
      </div>

      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>

      {refresh.isError && (
        <Alert variant="error" title="Peer competitors could not be updated">
          {isApiError(refresh.error) ? refresh.error.message : 'Try again in a moment.'}
        </Alert>
      )}

      {query.isLoading && (
        <div className="space-y-3" aria-busy="true">
          <Skeleton className="h-16 w-full rounded-lg" />
          <Skeleton className="h-16 w-full rounded-lg" />
          <Skeleton className="h-16 w-full rounded-lg" />
        </div>
      )}

      {query.isError && !data && (
        <Alert
          variant="error"
          title="Peer competitors could not be loaded"
          action={
            <Button variant="secondary" size="sm" onClick={() => void query.refetch()}>
              Retry
            </Button>
          }
        >
          {isApiError(query.error) ? query.error.message : 'Try again in a moment.'}
        </Alert>
      )}

      {notConfigured && (
        <Alert variant="info" title="Web search is not configured on the server yet">
          Peer competitors will be available once a search key is set up.
        </Alert>
      )}

      {data && !notConfigured && (
        <>
          {(data.last_updated_at || data.search_query) && (
            <div className="space-y-0.5 text-caption text-muted">
              {data.last_updated_at && (
                <p>
                  Last updated{' '}
                  {new Date(data.last_updated_at).toLocaleString(undefined, {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  })}
                </p>
              )}
              {data.search_query && <p className="wrap-break-word">Search: “{data.search_query}”</p>}
            </div>
          )}

          {peers.length === 0 ? (
            <p className="text-body-sm text-secondary">
              No peer competitors saved yet. Click Update to search.
            </p>
          ) : (
            <ol className="space-y-3">
              {peers.slice(0, 5).map((peer) => {
                const href = safeHttpsUrl(peer.source_url)
                const label = peer.source_title || hostOf(peer.source_url)
                return (
                  <li key={`${peer.rank}-${peer.source_url}`} className="flex gap-3">
                    <span
                      aria-hidden
                      className="mt-0.5 inline-flex size-6 shrink-0 items-center justify-center rounded-full border border-navy-200 text-caption font-semibold text-navy-600"
                    >
                      {peer.rank}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="text-body font-semibold text-primary">
                        <span className="sr-only">{`Rank ${peer.rank}: `}</span>
                        {peer.name}
                      </p>
                      <blockquote className="mt-1 border-l-2 border-default pl-3 text-body-sm text-secondary italic">
                        {peer.snippet}
                      </blockquote>
                      <p className="mt-1 text-caption">
                        {href ? (
                          <a
                            href={href}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1 break-all text-navy-600 hover:underline"
                          >
                            {label}
                            <ExternalLink aria-hidden className="size-3.5 shrink-0" />
                          </a>
                        ) : (
                          <span className="break-all text-muted">{label}</span>
                        )}
                      </p>
                    </div>
                  </li>
                )
              })}
            </ol>
          )}

          <p className="text-caption text-muted">Source: Google search result</p>
        </>
      )}
    </Card>
  )
}
