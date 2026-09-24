import { cn } from '../../lib/cn'

interface InitialsAvatarProps {
  initials: string
  className?: string
}

export function InitialsAvatar({ initials, className }: InitialsAvatarProps) {
  return (
    <span
      aria-hidden
      className={cn(
        'flex size-9 shrink-0 items-center justify-center rounded-full bg-navy-100 text-caption font-semibold text-navy-700',
        className,
      )}
    >
      {initials}
    </span>
  )
}
