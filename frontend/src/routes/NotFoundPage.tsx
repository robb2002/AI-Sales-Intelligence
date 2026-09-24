import { Info } from 'lucide-react'
import { Link } from 'react-router'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'

export function NotFoundPage() {
  return (
    <Card className="p-0">
      <EmptyState
        icon={Info}
        title="Page not found"
        description="This address does not match any page in the application."
        action={
          <Link
            to="/"
            className="inline-flex h-10 items-center rounded-md bg-navy-600 px-4 text-body font-medium text-inverse hover:bg-navy-700 focus-visible:ring-2 focus-visible:ring-focus-ring focus-visible:ring-offset-2 focus-visible:outline-hidden"
          >
            Back to the dashboard
          </Link>
        }
      />
    </Card>
  )
}
