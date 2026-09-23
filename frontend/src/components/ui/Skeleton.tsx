import { cn } from '../../lib/cn'

interface SkeletonProps {
  className?: string
  tone?: 'light' | 'dark'
}

export function Skeleton({ className, tone = 'light' }: SkeletonProps) {
  return (
    <div
      aria-hidden
      className={cn(
        'animate-shimmer rounded-sm bg-size-[200%_100%]',
        tone === 'light'
          ? 'bg-linear-to-r from-surface-sunken via-neutral-200 to-surface-sunken'
          : 'bg-linear-to-r from-navy-700 via-navy-600 to-navy-700',
        className,
      )}
    />
  )
}
