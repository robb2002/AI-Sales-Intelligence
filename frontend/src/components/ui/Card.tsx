import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

type CardVariant = 'default' | 'interactive' | 'attention'

const variantClasses: Record<CardVariant, string> = {
  default: '',
  interactive: 'cursor-pointer transition-shadow duration-120 ease-out hover:shadow-sm',
  attention: 'border-l-4 border-l-status-opportunity',
}

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: CardVariant
}

export function Card({ variant = 'default', className, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        'rounded-lg border border-default bg-surface p-6 shadow-xs',
        variantClasses[variant],
        className,
      )}
      {...rest}
    />
  )
}
