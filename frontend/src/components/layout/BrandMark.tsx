import { cn } from '../../lib/cn'

interface BrandMarkProps {
  tone: 'dark' | 'light'
  collapsible?: boolean
  className?: string
}

export function BrandMark({ tone, collapsible = false, className }: BrandMarkProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <span
        aria-hidden
        className="flex size-9 shrink-0 items-center justify-center rounded-md bg-navy-600 text-body-sm font-bold tracking-wide text-neutral-0 ring-1 ring-navy-500"
      >
        ES
      </span>
      <span className={cn('flex flex-col leading-none', collapsible && 'sr-only xl:not-sr-only')}>
        <span className={cn('text-label uppercase', tone === 'dark' ? 'text-navy-300' : 'text-secondary')}>
          Excelsoft
        </span>
        <span
          className={cn('mt-1 text-body font-semibold', tone === 'dark' ? 'text-neutral-0' : 'text-navy-800')}
        >
          Sales Intelligence
        </span>
      </span>
    </div>
  )
}
