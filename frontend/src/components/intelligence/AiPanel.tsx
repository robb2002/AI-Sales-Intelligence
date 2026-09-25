import { Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'

const LABELS = {
  interpretation: 'AI INTERPRETATION',
  explanation: 'AI EXPLANATION',
  correlation: 'WHY THESE SIGNALS ARE CONNECTED',
  recommended: 'RECOMMENDED RESEARCH / ACTION',
  advisor: 'AI SALES ADVISOR',
} as const

export type AiLabelKind = keyof typeof LABELS

export function AiLabel({ kind, tone = 'dark' }: { kind: AiLabelKind; tone?: 'dark' | 'light' }) {
  return (
    <p
      className={cn(
        'flex items-center gap-1.5 text-label uppercase',
        tone === 'dark' ? 'text-indigo-400' : 'text-indigo-600',
      )}
    >
      <Sparkles aria-hidden className="size-3" strokeWidth={1.75} />
      {LABELS[kind]}
    </p>
  )
}

export function AiPanel({
  label,
  children,
  className,
}: {
  label: AiLabelKind
  children: ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        'rounded-xl border-l-[3px] border-l-indigo-500 bg-surface-ai p-6 text-on-ai',
        className,
      )}
    >
      <AiLabel kind={label} tone="dark" />
      <div className="mt-3 max-w-[68ch] text-body-lg text-on-ai">{children}</div>
    </section>
  )
}

export function AiInlineNote({ children }: { children: ReactNode }) {
  return (
    <aside className="rounded-lg border-l-[3px] border-l-indigo-500 bg-surface-ai-subtle px-4 py-3">
      <AiLabel kind="interpretation" tone="light" />
      <p className="mt-2 text-body text-primary">{children}</p>
    </aside>
  )
}
