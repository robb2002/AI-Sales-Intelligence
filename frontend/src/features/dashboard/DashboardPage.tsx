import { CheckCircle2, LayoutDashboard } from 'lucide-react'
import { Badge } from '../../components/ui/Badge'
import { Card } from '../../components/ui/Card'
import { EmptyState } from '../../components/ui/EmptyState'
import { ROLE_LABELS } from '../auth/roles'
import { useCurrentUser } from '../auth/useCurrentUser'
import { useIdentity } from '../auth/useIdentity'

export function DashboardPage() {
  const { data: user } = useCurrentUser()
  const identity = useIdentity()
  if (!user) return null

  return (
    <div className="space-y-6">
      <Card className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-start gap-4">
          <span className="flex size-10 shrink-0 items-center justify-center rounded-full bg-green-50">
            <CheckCircle2 aria-hidden className="size-5 text-status-positive" strokeWidth={1.75} />
          </span>
          <div>
            <h2 className="text-h3 text-primary">Access verified</h2>
            <p className="mt-1 max-w-[68ch] text-body text-secondary">
              Signed in as {identity.name}. The API verified your Clerk session and loaded your role
              from the application database.
            </p>
          </div>
        </div>
        <Badge variant="outline-navy" className="self-start sm:self-center">
          {ROLE_LABELS[user.role]}
        </Badge>
      </Card>

      <Card className="p-0">
        <EmptyState
          icon={LayoutDashboard}
          title="Command center arrives in a later phase"
          description="Opportunity, signal, and scan metrics appear here once the pipeline stores real public data. Nothing is shown before then."
        />
      </Card>
    </div>
  )
}
