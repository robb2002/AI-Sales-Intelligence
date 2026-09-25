import { ExternalLink } from 'lucide-react'
import { useState } from 'react'
import type { EvidenceItem as EvidenceItemType } from '../../types/api'
import { formatSignalDate } from '../../features/intelligence/labels'
import { cn } from '../../lib/cn'
import { Badge } from '../ui/Badge'

export function EvidenceItemCard({ item }: { item: EvidenceItemType }) {
  const [expanded, setExpanded] = useState(false)
  const long = item.snippet.length > 280
  const snippet = !long || expanded ? item.snippet : `${item.snippet.slice(0, 280).trimEnd()}…`
  const dateLabel = formatSignalDate(item.date, item.date_status)

  return (
    <article className="rounded-lg border border-default bg-surface p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-body-sm font-medium text-primary">{item.source_name}</p>
          <p className="mt-0.5 text-caption text-secondary">
            {item.date_status === 'unavailable' ? 'Date unavailable' : `Published ${dateLabel}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {item.data_origin === 'cached' && <Badge variant="soft-neutral">Cached</Badge>}
          <a
            href={item.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-caption font-medium text-navy-600 hover:underline"
          >
            Open source
            <ExternalLink aria-hidden className="size-3.5" strokeWidth={1.75} />
          </a>
        </div>
      </div>
      <blockquote
        className={cn(
          'mt-3 border-l-2 border-navy-200 bg-surface-sunken px-3 py-2 text-body-sm text-neutral-700',
        )}
      >
        “{snippet}”
      </blockquote>
      {long && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-caption font-medium text-navy-600 hover:underline"
        >
          {expanded ? 'Show less' : 'Show more'}
        </button>
      )}
      <p className="mt-3 text-caption text-secondary">
        <span className="font-medium">Supports:</span> {item.relationship}
      </p>
    </article>
  )
}

export function EvidenceList({
  items,
  heading,
}: {
  items: EvidenceItemType[]
  heading?: string
}) {
  const title = heading ?? `${items.length} source${items.length === 1 ? '' : 's'}`
  if (items.length === 0) {
    return (
      <p className="text-body-sm text-secondary">No evidence rows are stored for this item.</p>
    )
  }
  return (
    <div>
      <p className="text-label text-secondary uppercase">{title}</p>
      <div className="mt-3 space-y-3">
        {items.map((item) => (
          <EvidenceItemCard key={item.evidence_id} item={item} />
        ))}
      </div>
    </div>
  )
}
