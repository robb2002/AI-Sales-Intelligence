import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'

interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon: Icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center px-6 py-16 text-center">
      <div className="flex size-16 items-center justify-center rounded-full bg-surface-sunken">
        <Icon aria-hidden className="size-8 text-neutral-400" strokeWidth={1.75} />
      </div>
      <h2 className="mt-4 text-h3 text-primary">{title}</h2>
      <p className="mt-1 max-w-[48ch] text-body-sm text-secondary">{description}</p>
      {action && <div className="mt-6">{action}</div>}
    </div>
  )
}
