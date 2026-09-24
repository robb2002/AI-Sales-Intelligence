import { AlertCircle } from 'lucide-react'
import type { ReactNode } from 'react'
import { Button } from './Button'

interface ErrorStateProps {
  title?: string
  description: string
  reference?: string | null
  onRetry?: () => void
  retrying?: boolean
  secondaryAction?: ReactNode
}

export function ErrorState({
  title = 'Something went wrong',
  description,
  reference,
  onRetry,
  retrying = false,
  secondaryAction,
}: ErrorStateProps) {
  return (
    <div role="alert" className="flex flex-col items-center px-6 py-16 text-center">
      <AlertCircle aria-hidden className="size-8 text-status-risk" strokeWidth={1.75} />
      <h2 className="mt-4 text-h2 text-primary">{title}</h2>
      <p className="mt-2 max-w-[48ch] text-body-sm text-secondary">{description}</p>
      {reference && (
        <p className="mt-2 text-caption text-secondary">
          Reference <span className="font-mono">{reference}</span>
        </p>
      )}
      {(onRetry || secondaryAction) && (
        <div className="mt-6 flex items-center gap-3">
          {onRetry && (
            <Button variant="primary" onClick={onRetry} loading={retrying}>
              Retry
            </Button>
          )}
          {secondaryAction}
        </div>
      )}
    </div>
  )
}
