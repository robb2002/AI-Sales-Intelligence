import type { LucideIcon } from 'lucide-react'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'

interface PendingPageProps {
  icon: LucideIcon
  name: string
}

export function PendingPage({ icon, name }: PendingPageProps) {
  return (
    <Card className="p-0">
      <EmptyState
        icon={icon}
        title="Not built yet"
        description={`The ${name} view is built in a later phase of the implementation plan.`}
      />
    </Card>
  )
}
