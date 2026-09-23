import { Check, Info } from 'lucide-react'
import { useEffect, useState } from 'react'
import { BrandMark } from '../../components/layout/BrandMark'
import { Button } from '../../components/ui/Button'
import { Card } from '../../components/ui/Card'
import { useDocumentTitle } from '../../lib/useDocumentTitle'
import { useIdentity } from './useIdentity'
import { useSignOut } from './useSignOut'

interface NoRolePageProps {
  code: 'USER_NOT_PROVISIONED' | 'USER_WITHOUT_ROLE'
  onRetry: () => void
  retrying: boolean
}

const REASONS: Record<NoRolePageProps['code'], string> = {
  USER_NOT_PROVISIONED: 'You are signed in, but no application role has been granted to this account yet.',
  USER_WITHOUT_ROLE: 'You are signed in, but this account does not have a valid application role.',
 
}

export function NoRolePage({ code, onRetry, retrying }: NoRolePageProps) {
  const identity = useIdentity()
  const signOut = useSignOut()
  const [copied, setCopied] = useState(false)
  useDocumentTitle('Access pending')

  useEffect(() => {
    if (!copied) return
    const timer = window.setTimeout(() => setCopied(false), 2000)
    return () => window.clearTimeout(timer)
  }, [copied])

  const copyAccountId = async () => {
    if (!identity.clerkUserId) return
    try {
      await navigator.clipboard.writeText(identity.clerkUserId)
      setCopied(true)
    } catch {
      setCopied(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-app px-6 py-12">
      <div className="w-full max-w-120">
        <BrandMark tone="light" className="mb-8 justify-center" />
        <Card className="p-8">
          <div className="flex size-12 items-center justify-center rounded-full bg-navy-50">
            <Info aria-hidden className="size-6 text-navy-600" strokeWidth={1.75} />
          </div>
          <h1 className="mt-5 text-h2 text-primary">Your account does not have access yet</h1>
          <p className="mt-2 text-body text-secondary">{REASONS[code]}</p>
          <p className="mt-2 text-body text-secondary">
          Ask your team lead to grant the Sales Representative or Sales Manager role. Share the
          account ID below so they can find you.</p>

          <dl className="mt-6 space-y-4 rounded-lg border border-default bg-surface-sunken p-4">
            {identity.email && (
              <div>
                <dt className="text-label text-secondary uppercase">Signed in as</dt>
                <dd className="mt-1 text-body break-all text-primary">{identity.email}</dd>
              </div>
            )}
            {identity.clerkUserId && (
              <div>
                <dt className="text-label text-secondary uppercase">Account ID</dt>
                <dd className="mt-1 flex items-center justify-between gap-3">
                  <code className="font-mono text-body-sm break-all text-primary">
                    {identity.clerkUserId}
                  </code>
                  <Button
                    size="sm"
                    variant="tertiary"
                    icon={copied ? Check : undefined}
                    onClick={() => void copyAccountId()}
                    aria-live="polite"
                  >
                    {copied ? 'Copied' : 'Copy'}
                  </Button>
                </dd>
              </div>
            )}
          </dl>

          <div className="mt-8 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
            <Button variant="secondary" onClick={() => void signOut()}>
              Sign out
            </Button>
            <Button variant="primary" onClick={onRetry} loading={retrying}>
              Check access again
            </Button>
          </div>
        </Card>
      </div>
    </main>
  )
}
