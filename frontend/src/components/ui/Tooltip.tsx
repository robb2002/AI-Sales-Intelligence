import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface TooltipProps {
  content: string
  children: ReactNode
  side?: 'right' | 'bottom'
  className?: string
  wrapperClassName?: string
}

const sideClasses = {
  right: 'left-full top-1/2 ml-1.5 -translate-y-1/2',
  bottom: 'top-full left-1/2 mt-1.5 -translate-x-1/2',
}

export function Tooltip({ content, children, side = 'right', className, wrapperClassName }: TooltipProps) {
  return (
    <span className={cn('group/tooltip relative inline-flex', wrapperClassName)}>
      {children}
      <span
        role="tooltip"
        className={cn(
          'pointer-events-none absolute z-40 rounded-sm bg-surface-ai px-2.5 py-2 text-caption whitespace-nowrap text-inverse shadow-md',
          'opacity-0 transition-opacity duration-120 ease-out',
          'group-hover/tooltip:opacity-100 group-hover/tooltip:delay-150 group-focus-within/tooltip:opacity-100',
          sideClasses[side],
          className,
        )}
      >
        {content}
      </span>
    </span>
  )
}
