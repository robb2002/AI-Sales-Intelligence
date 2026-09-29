import { Sparkles } from 'lucide-react'
import { splitInsightProse } from '../../features/intelligence/readableProse'
import { cn } from '../../lib/cn'
import { AiLabel, type AiLabelKind } from './AiPanel'
import { RichText } from './RichText'

/** Lead + bullets from stored text only (no invented content). */
export function ReadableAiBody({
  text,
  tone = 'light',
}: {
  text: string
  tone?: 'light' | 'dark'
}) {
  const { lead, bullets } = splitInsightProse(text)
  if (!lead) return null

  return (
    <div className="flex gap-2.5">
      <Sparkles
        aria-hidden
        className={cn(
          'mt-1 size-4 shrink-0',
          tone === 'dark' ? 'text-indigo-400' : 'text-indigo-600',
        )}
        strokeWidth={1.75}
      />
      <div className="min-w-0 space-y-2.5">
        <p
          className={cn(
            'text-body-lg font-medium leading-relaxed',
            tone === 'dark' ? 'text-on-ai' : 'text-primary',
          )}
        >
          <RichText
            text={lead}
            strongClassName={
              tone === 'dark' ? 'font-semibold text-indigo-200' : 'font-semibold text-navy-800'
            }
          />
        </p>
        {bullets.length > 0 && (
          <ul
            className={cn(
              'list-disc space-y-1.5 pl-4 text-body leading-relaxed',
              tone === 'dark' ? 'text-on-ai-muted' : 'text-secondary',
            )}
          >
            {bullets.map((bullet, index) => (
              <li key={index}>
                <RichText
                  text={bullet}
                  strongClassName={
                    tone === 'dark'
                      ? 'font-semibold text-on-ai'
                      : 'font-semibold text-primary'
                  }
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

/** Light-surface AI interpretation block (signal detail, etc.). */
export function ReadableInterpretation({
  text,
  label = 'interpretation',
}: {
  text: string
  label?: AiLabelKind
}) {
  const { lead } = splitInsightProse(text)
  if (!lead) return null

  return (
    <aside className="rounded-lg border-l-[3px] border-l-indigo-500 bg-surface-ai-subtle px-4 py-3">
      <AiLabel kind={label} tone="light" />
      <div className="mt-2">
        <ReadableAiBody text={text} tone="light" />
      </div>
    </aside>
  )
}
