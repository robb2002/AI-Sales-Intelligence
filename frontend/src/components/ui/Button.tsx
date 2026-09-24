import type { LucideIcon } from 'lucide-react'
import type { ButtonHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'
import { Spinner } from './Spinner'

type Variant = 'primary' | 'secondary' | 'tertiary' | 'ai' | 'danger' | 'link'
type Size = 'sm' | 'md' | 'lg'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
  icon?: LucideIcon
  loading?: boolean
}

const variantClasses: Record<Variant, string> = {
  primary: 'bg-navy-600 text-inverse hover:bg-navy-700',
  secondary: 'border border-default bg-surface text-navy-600 hover:bg-surface-sunken',
  tertiary: 'bg-transparent text-neutral-600 hover:bg-surface-sunken',
  ai: 'bg-indigo-600 text-inverse hover:bg-indigo-700',
  danger: 'bg-red-600 text-inverse hover:bg-red-700',
  link: 'bg-transparent px-0 text-navy-600 hover:underline',
}

const sizeClasses: Record<Size, string> = {
  sm: 'h-8 px-3 text-body-sm',
  md: 'h-10 px-4 text-body',
  lg: 'h-12 px-6 text-body',
}

const iconSizes: Record<Size, string> = { sm: 'size-4', md: 'size-5', lg: 'size-5' }

export function Button({
  variant = 'secondary',
  size = 'md',
  icon: Icon,
  loading = false,
  disabled,
  className,
  children,
  type = 'button',
  ...rest
}: ButtonProps) {
  const isDisabled = disabled || loading
  return (
    <button
      type={type}
      disabled={isDisabled}
      aria-busy={loading || undefined}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-md font-medium whitespace-nowrap',
        'transition-colors duration-120 ease-out active:translate-y-px',
        'focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:outline-hidden',
        'disabled:cursor-not-allowed disabled:opacity-50 disabled:active:translate-y-0',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...rest}
    >
      {loading ? (
        <Spinner className={iconSizes[size]} />
      ) : (
        Icon && <Icon aria-hidden className={iconSizes[size]} strokeWidth={1.75} />
      )}
      {children}
    </button>
  )
}
