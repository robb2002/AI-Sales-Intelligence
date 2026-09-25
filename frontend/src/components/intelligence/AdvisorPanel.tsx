import { SearchX, Sparkles } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { askAdvisor } from '../../api/advisor'
import { isApiError } from '../../api/client'
import { AiLabel, AiPanel } from '../intelligence/AiPanel'
import { EvidenceList } from '../intelligence/EvidenceList'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'
import { cn } from '../../lib/cn'
import type { AdvisorStatus, EvidenceItem } from '../../types/api'

const SUGGESTED = [
  'Summarize what we know about this organization from collected sources.',
  'Which signals look most relevant for EdTech sales research?',
  'Explain the opportunity score using the stored factors.',
  'What should I research next, based only on collected evidence?',
]

type Turn =
  | { role: 'user'; text: string }
  | {
      role: 'advisor'
      status: AdvisorStatus
      text: string
      evidence: EvidenceItem[]
    }

export function AdvisorPanel({
  scopeType,
  scopeId,
  scopeLabel,
  className,
  compact = false,
}: {
  scopeType: 'organization' | 'opportunity'
  scopeId: string
  scopeLabel: string
  className?: string
  compact?: boolean
}) {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [turns, setTurns] = useState<Turn[]>([])
  const [draft, setDraft] = useState('')
  const [pending, setPending] = useState(false)
  const [phase, setPhase] = useState<'searching' | 'composing'>('searching')
  const [error, setError] = useState<string | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [turns, pending])

  async function send(message: string) {
    const trimmed = message.trim()
    if (!trimmed || pending) return
    setError(null)
    setDraft('')
    setTurns((prev) => [...prev, { role: 'user', text: trimmed }])
    setPending(true)
    setPhase('searching')
    const phaseTimer = window.setTimeout(() => setPhase('composing'), 900)
    try {
      const response = await askAdvisor({
        scope_type: scopeType,
        scope_id: scopeId,
        message: trimmed,
        session_id: sessionId,
      })
      setSessionId(response.session_id)
      setTurns((prev) => [
        ...prev,
        {
          role: 'advisor',
          status: response.advisor_status,
          text: response.answer.text,
          evidence: response.evidence,
        },
      ])
    } catch (err) {
      setError(isApiError(err) ? err.message : 'The Advisor could not answer.')
    } finally {
      window.clearTimeout(phaseTimer)
      setPending(false)
    }
  }

  return (
    <section
      className={cn(
        'flex flex-col rounded-lg border border-indigo-500/40 bg-surface-ai text-on-ai',
        compact ? 'max-h-[70vh]' : 'min-h-[420px]',
        className,
      )}
    >
      <header className="flex items-center gap-2 border-b border-indigo-500/30 px-4 py-3">
        <AiLabel kind="advisor" />
        <Badge variant="soft-ai">{scopeLabel}</Badge>
      </header>

      <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
        {turns.length === 0 && !pending && (
          <div className="space-y-3">
            <p className="text-body-sm text-on-ai-muted">
              Ask about collected evidence for this {scopeType}. The Advisor does not search the open
              web.
            </p>
            <div className="flex flex-wrap gap-2">
              {SUGGESTED.map((q) => (
                <Button
                  key={q}
                  type="button"
                  variant="secondary"
                  size="sm"
                  className="max-w-full whitespace-normal text-left"
                  onClick={() => void send(q)}
                >
                  {q}
                </Button>
              ))}
            </div>
          </div>
        )}

        {turns.map((turn, index) =>
          turn.role === 'user' ? (
            <div key={`u-${index}`} className="flex justify-end">
              <div className="max-w-[80%] rounded-lg rounded-br-sm bg-navy-50 px-3 py-2 text-body text-navy-900">
                {turn.text}
              </div>
            </div>
          ) : (
            <AdvisorMessage key={`a-${index}`} turn={turn} />
          ),
        )}

        {pending && (
          <AiPanel label="advisor" className="!bg-transparent !p-0 !shadow-none">
            <p className="flex items-center gap-2 text-body-sm text-indigo-300">
              <span className="inline-flex gap-1" aria-hidden>
                <span className="size-1.5 animate-pulse rounded-full bg-indigo-400" />
                <span className="size-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:150ms]" />
                <span className="size-1.5 animate-pulse rounded-full bg-indigo-400 [animation-delay:300ms]" />
              </span>
              {phase === 'searching' ? 'Searching evidence…' : 'Composing answer…'}
            </p>
          </AiPanel>
        )}

        {error && <p className="text-body-sm text-red-300">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <form
        className="border-t border-indigo-500/30 p-3"
        onSubmit={(e) => {
          e.preventDefault()
          void send(draft)
        }}
      >
        <div className="flex items-end gap-2">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void send(draft)
              }
            }}
            rows={2}
            disabled={pending}
            placeholder="Ask about collected signals or evidence…"
            className="min-h-10 max-h-[120px] flex-1 resize-y rounded-md border border-default bg-surface px-3 py-2 text-body text-primary placeholder:text-muted"
          />
          <Button type="submit" variant="ai" icon={Sparkles} loading={pending} disabled={!draft.trim()}>
            Ask
          </Button>
        </div>
        {pending && (
          <p className="mt-2 text-caption text-on-ai-muted">Waiting for the Advisor response…</p>
        )}
      </form>
    </section>
  )
}

function AdvisorMessage({
  turn,
}: {
  turn: Extract<Turn, { role: 'advisor' }>
}) {
  if (turn.status === 'insufficient_evidence') {
    return (
      <div className="rounded-lg border border-default bg-surface-sunken p-5 text-primary">
        <div className="flex gap-3">
          <SearchX className="size-5 shrink-0 text-neutral-500" aria-hidden />
          <div>
            <p className="text-body font-medium">Insufficient evidence</p>
            <p className="mt-1 text-body-sm text-secondary">{turn.text}</p>
            <Link
              to="/organizations"
              className="mt-3 inline-block text-body-sm font-medium text-navy-600 hover:underline"
            >
              Run a scan
            </Link>
          </div>
        </div>
      </div>
    )
  }

  if (turn.status === 'unavailable') {
    return (
      <div className="rounded-lg border border-default bg-surface-sunken p-4 text-primary">
        <p className="text-body font-medium">AI explanation unavailable</p>
        <p className="mt-1 text-body-sm text-secondary">{turn.text}</p>
      </div>
    )
  }

  return (
    <AiPanel label="advisor">
      <p className="max-w-[68ch] whitespace-pre-wrap text-body-lg">{turn.text}</p>
      {turn.evidence.length > 0 && (
        <div className="mt-4">
          <EvidenceList items={turn.evidence} heading="SOURCES" />
        </div>
      )}
    </AiPanel>
  )
}
