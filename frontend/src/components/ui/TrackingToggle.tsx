import { cn } from '../../lib/cn'
import { Spinner } from './Spinner'

interface TrackingToggleProps {
  active: boolean
  loading?: boolean
  /** Status being applied while loading (needed when optimistic UI already flipped `active`). */
  pendingStatus?: 'active' | 'inactive' | null
  disabled?: boolean
  size?: 'sm' | 'md'
  onChange: (next: 'active' | 'inactive') => void
  className?: string
}

/**
 * Segmented tracking control — text labels, not color alone.
 * Matches Button heights (h-8 / h-10) for row alignment with Edit.
 */
export function TrackingToggle({
  active,
  loading = false,
  pendingStatus = null,
  disabled = false,
  size = 'md',
  onChange,
  className,
}: TrackingToggleProps) {
  const isDisabled = disabled || loading
  const compact = size === 'sm'
  const loadingLabel =
    pendingStatus === 'active'
      ? 'Activating…'
      : pendingStatus === 'inactive'
        ? 'Deactivating…'
        : 'Updating…'

  return (
    <div
      role="group"
      aria-label="Tracking status"
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center rounded-md border border-default bg-surface p-0.5',
        compact ? 'h-8' : 'h-10',
        isDisabled && 'cursor-not-allowed opacity-60',
        className,
      )}
    >
      {loading ? (
        <span
          className={cn(
            'inline-flex h-full items-center justify-center gap-2 rounded-sm bg-surface-sunken px-3 text-body-sm font-medium text-secondary',
            compact ? 'min-w-40' : 'min-w-44',
          )}
        >
          <Spinner className="size-4 shrink-0" />
          {loadingLabel}
        </span>
      ) : (
        <>
          <Segment
            pressed={!active}
            disabled={isDisabled}
            onClick={() => onChange('inactive')}
          >
            Inactive
          </Segment>
          <Segment
            pressed={active}
            disabled={isDisabled}
            onClick={() => onChange('active')}
          >
            Active
          </Segment>
        </>
      )}
    </div>
  )
}

function Segment({
  pressed,
  disabled,
  onClick,
  children,
}: {
  pressed: boolean
  disabled: boolean
  onClick: () => void
  children: string
}) {
  return (
    <button
      type="button"
      role="radio"
      aria-checked={pressed}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        'inline-flex h-full items-center justify-center rounded-sm px-3 text-body-sm font-medium whitespace-nowrap',
        'transition-colors duration-120 ease-out',
        'focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-1 focus-visible:outline-hidden',
        'disabled:cursor-not-allowed',
        pressed
          ? 'bg-navy-600 text-inverse shadow-sm'
          : 'bg-transparent text-secondary hover:bg-surface-sunken hover:text-primary',
      )}
    >
      {children}
    </button>
  )
}
