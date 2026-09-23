import {
  AlertCircle,
  AlertTriangle,
  Archive,
  CheckCircle2,
  Info,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

type AlertVariant = 'info' | 'success' | 'attention' | 'error' | 'ai' | 'cached'

const variants: Record<AlertVariant, { classes: string; icon: LucideIcon; iconClass: string }> = {
  info: { classes: 'bg-navy-50 border-navy-100 border-l-navy-600', icon: Info, iconClass: 'text-navy-600' },
  success: { classes: 'bg-green-50 border-green-100 border-l-green-600', icon: CheckCircle2, iconClass: 'text-green-600' },
  attention: { classes: 'bg-amber-50 border-amber-100 border-l-amber-600', icon: AlertTriangle, iconClass: 'text-amber-600' },
  error: { classes: 'bg-red-50 border-red-100 border-l-red-600', icon: AlertCircle, iconClass: 'text-red-600' },
  ai: { classes: 'bg-indigo-50 border-indigo-100 border-l-indigo-600', icon: Sparkles, iconClass: 'text-indigo-600' },
  cached: { classes: 'bg-surface-sunken border-default border-l-neutral-400', icon: Archive, iconClass: 'text-neutral-500' },
}

interface AlertProps {
  variant?: AlertVariant
  title: string
  children?: ReactNode
  action?: ReactNode
  className?: string
}

export function Alert({ variant = 'info', title, children, action, className }: AlertProps) {
  const { classes, icon: Icon, iconClass } = variants[variant]
  return (
    <div
      role={variant === 'error' ? 'alert' : 'status'}
      className={cn('flex items-start gap-3 rounded-lg border border-l-3 p-4', classes, className)}
    >
      <Icon aria-hidden className={cn('size-5 shrink-0', iconClass)} strokeWidth={1.75} />
      <div className="min-w-0 flex-1">
        <p className="text-body font-medium text-primary">{title}</p>
        {children && <div className="mt-1 text-body-sm text-neutral-600">{children}</div>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  )
}
