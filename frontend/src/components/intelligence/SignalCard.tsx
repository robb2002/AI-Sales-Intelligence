import { Link } from 'react-router'
import type { SignalState, SignalSummary, SignalType } from '../../types/api'
import {
  SIGNAL_STATE_LABELS,
  SIGNAL_TYPE_DOT,
  SIGNAL_TYPE_ICONS,
  SIGNAL_TYPE_LABELS,
  formatSignalDate,
} from '../../features/intelligence/labels'
import { cn } from '../../lib/cn'
import { Badge } from '../ui/Badge'
import { AiLabel } from './AiPanel'

export function SignalTypeBadge({ signalType }: { signalType: SignalType }) {
  const Icon = SIGNAL_TYPE_ICONS[signalType]
  return (
    <Badge variant="soft-neutral" className="gap-1.5">
      <span className={cn('size-1.5 rounded-full', SIGNAL_TYPE_DOT[signalType])} />
      <Icon aria-hidden className="size-3" strokeWidth={1.75} />
      {SIGNAL_TYPE_LABELS[signalType]}
    </Badge>
  )
}

export function SignalStateBadge({ state }: { state: SignalState }) {
  if (state === 'validated') return <Badge variant="soft-positive">{SIGNAL_STATE_LABELS[state]}</Badge>
  if (state === 'merged') return <Badge variant="outline-navy">{SIGNAL_STATE_LABELS[state]}</Badge>
  return (
    <Badge
      variant="soft-neutral"
      className={state === 'rejected' || state === 'superseded' ? 'text-muted' : undefined}
    >
      {SIGNAL_STATE_LABELS[state]}
    </Badge>
  )
}

export function SignalCard({
  signal,
  aiSummary,
}: {
  signal: SignalSummary
  aiSummary?: string | null
}) {
  const Icon = SIGNAL_TYPE_ICONS[signal.signal_type]
  return (
    <Link
      to={`/signals/${signal.signal_id}`}
      className={cn(
        'flex gap-4 rounded-lg border border-default bg-surface p-5 shadow-xs',
        'transition-shadow duration-120 ease-out hover:shadow-sm',
        'focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:outline-hidden',
      )}
    >
      <div className="flex size-8 shrink-0 items-center justify-center rounded-md bg-surface-sunken text-navy-600">
        <Icon aria-hidden className="size-4" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="text-body font-medium text-primary">{signal.title}</h3>
          <SignalTypeBadge signalType={signal.signal_type} />
          <SignalStateBadge state={signal.state} />
        </div>
        <p className="mt-1 text-caption text-secondary">
          <span className="font-medium text-navy-600">{signal.organization_name}</span>
          {' · '}
          {formatSignalDate(signal.date, signal.date_status)}
          {' · '}
          {signal.source_count} source{signal.source_count === 1 ? '' : 's'}
          {signal.data_origin === 'cached' ? ' · Cached' : ''}
        </p>
        <p className="mt-2 line-clamp-2 text-body-sm text-secondary">{signal.summary}</p>
        {aiSummary ? (
          <div className="mt-3 border-t border-default pt-3">
            <AiLabel kind="interpretation" tone="light" />
            <p className="mt-1 line-clamp-1 text-body-sm text-secondary">{aiSummary}</p>
          </div>
        ) : null}
      </div>
    </Link>
  )
}
