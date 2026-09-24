import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type BadgeVariant =
  | 'solid-opportunity'
  | 'soft-opportunity'
  | 'soft-positive'
  | 'soft-risk'
  | 'soft-ai'
  | 'soft-neutral'
  | 'outline-navy'
  | 'outline-navy-dark'

const variantClasses: Record<BadgeVariant, string> = {
  'solid-opportunity': 'bg-amber-600 text-neutral-0 border-transparent',
  'soft-opportunity': 'bg-amber-50 text-amber-700 border-amber-100',
  'soft-positive': 'bg-green-50 text-green-700 border-green-100',
  'soft-risk': 'bg-red-50 text-red-700 border-red-100',
  'soft-ai': 'bg-indigo-100 text-indigo-700 border-indigo-200',
  'soft-neutral': 'bg-surface-sunken text-neutral-600 border-default',
  'outline-navy': 'bg-transparent text-navy-600 border-navy-200',
  'outline-navy-dark': 'bg-transparent text-navy-200 border-navy-600',
}

interface BadgeProps {
  variant?: BadgeVariant
  className?: string
  children: ReactNode
}

export function Badge({ variant = 'soft-neutral', className, children }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex h-5.5 items-center gap-1 rounded-full border px-2.5 text-caption font-medium whitespace-nowrap',
        variantClasses[variant],
        className,
      )}
    >
      {children}
    </span>
  )
}
