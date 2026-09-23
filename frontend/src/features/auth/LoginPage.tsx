import { SignIn, useAuth } from '@clerk/react'
import {
  ArrowRightCircle,
  BarChart3,
  FileText,
  GitMerge,
  Radio,
  Sparkles,
  Target,
  type LucideIcon,
} from 'lucide-react'
import { Navigate, useLocation, useSearchParams } from 'react-router'
import { BrandMark } from '../../components/layout/BrandMark'
import { Alert } from '../../components/ui/Alert'
import { Skeleton } from '../../components/ui/Skeleton'
import { cn } from '../../lib/cn'
import { useDocumentTitle } from '../../lib/useDocumentTitle'

interface Step {
  icon: LucideIcon
  title: string
  description: string
}

const PIPELINE: Step[] = [
  {
    icon: Radio,
    title: 'Detect',
    description: 'Signals from approved public sources such as SAM.gov and official organization websites.',
  },
  {
    icon: GitMerge,
    title: 'Connect',
    description: 'Related signals are grouped, with the stated reason they belong together.',
  },
  {
    icon: BarChart3,
    title: 'Score',
    description: 'Transparent rules compute every score. AI explains the number, never sets it.',
  },
  {
    icon: FileText,
    title: 'Evidence',
    description: 'Every claim opens to the public source, date, and snippet it came from.',
  },
]

const LAYERS: Array<{ icon: LucideIcon; label: string; className: string }> = [
  { icon: FileText, label: 'Observed fact', className: 'border-navy-600 text-navy-100' },
  { icon: Sparkles, label: 'AI interpretation', className: 'border-indigo-500 text-indigo-300' },
  { icon: Target, label: 'Potential opportunity', className: 'border-amber-600 text-amber-500' },
  { icon: ArrowRightCircle, label: 'Recommended action', className: 'border-navy-600 text-navy-100' },
]

function BrandPanel() {
  return (
    <section
      aria-label="About Excelsoft Sales Intelligence"
      className="hidden flex-col justify-between gap-12 bg-navy-800 p-12 lg:flex xl:p-16"
    >
      <BrandMark tone="dark" />

      <div className="max-w-lg">
        <p className="text-label text-navy-300 uppercase">For Excelsoft&apos;s US sales team</p>
        <h2 className="mt-3 text-display text-neutral-0">
          Public signals, connected into potential opportunities.
        </h2>
        <p className="mt-4 text-body-lg text-navy-200">
          Follow what US education organizations publish, see why related signals belong together,
          and open the evidence behind every score.
        </p>

        <ol className="mt-10">
          {PIPELINE.map(({ icon: Icon, title, description }, index) => (
            <li key={title} className="relative flex gap-4 pb-6 last:pb-0">
              {index < PIPELINE.length - 1 && (
                <span aria-hidden className="absolute top-11 bottom-1 left-5 w-px bg-navy-600" />
              )}
              <span className="flex size-10 shrink-0 items-center justify-center rounded-lg border border-navy-600 bg-navy-900">
                <Icon aria-hidden className="size-5 text-navy-200" strokeWidth={1.75} />
              </span>
              <div className="pt-0.5">
                <p className="text-body font-semibold text-neutral-0">{title}</p>
                <p className="mt-0.5 text-body-sm text-navy-300">{description}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <div>
        <p className="text-label text-navy-300 uppercase">Every insight is labelled</p>
        <ul className="mt-3 flex flex-wrap gap-2">
          {LAYERS.map(({ icon: Icon, label, className }) => (
            <li
              key={label}
              className={cn(
                'inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-caption font-medium',
                className,
              )}
            >
              <Icon aria-hidden className="size-3.5" strokeWidth={1.75} />
              {label}
            </li>
          ))}
        </ul>
        <p className="mt-6 text-caption text-navy-300">
          Sign-in is handled by Clerk. Passwords never reach our servers.
        </p>
      </div>
    </section>
  )
}

function SignInSkeleton() {
  return (
    <div className="space-y-4 rounded-xl border border-default bg-surface p-8 shadow-xs">
      <Skeleton className="mx-auto h-6 w-48" />
      <Skeleton className="mx-auto h-4 w-64" />
      <Skeleton className="mt-6 h-10 w-full rounded-md" />
      <Skeleton className="h-10 w-full rounded-md" />
      <Skeleton className="h-10 w-full rounded-md" />
    </div>
  )
}

export function LoginPage() {
  const { isLoaded, isSignedIn } = useAuth()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  useDocumentTitle('Sign in')

  const from = (location.state as { from?: string } | null)?.from ?? '/'
  if (isLoaded && isSignedIn) return <Navigate to={from} replace />

  const sessionExpired = searchParams.get('reason') === 'expired'

  return (
    <div className="grid min-h-screen bg-app lg:grid-cols-2">
      <BrandPanel />

      <main className="flex items-center justify-center px-6 py-12 sm:px-12">
        <div className="w-full max-w-100">
          <BrandMark tone="light" className="mb-8 lg:hidden" />

          {sessionExpired && (
            <Alert variant="info" title="Your session expired" className="mb-4">
              Sign in again to continue.
            </Alert>
          )}

          <SignIn
            routing="path"
            path="/login"
            withSignUp
            fallbackRedirectUrl={from}
            signUpFallbackRedirectUrl={from}
            fallback={<SignInSkeleton />}
          />

          <p className="mt-6 text-center text-caption text-secondary">
            Access requires a Sales Representative or Sales Manager role granted by your team.
          </p>
        </div>
      </main>
    </div>
  )
}
