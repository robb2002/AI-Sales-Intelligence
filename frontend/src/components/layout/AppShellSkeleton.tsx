import { Skeleton } from '../ui/Skeleton'

export function AppShellSkeleton() {
  return (
    <div className="min-h-screen bg-app" aria-busy="true">
      <span role="status" className="sr-only">
        Loading your workspace
      </span>
      <div className="fixed inset-y-0 left-0 w-18 border-r border-navy-700 bg-navy-800 xl:w-65">
        <div className="h-16 bg-navy-900" />
        <div className="space-y-2 p-3 pt-6">
          {Array.from({ length: 5 }, (_, index) => (
            <Skeleton key={index} tone="dark" className="h-11 rounded-md" />
          ))}
        </div>
      </div>
      <div className="ml-18 xl:ml-65">
        <div className="flex h-16 items-center justify-between border-b border-default bg-surface px-6">
          <Skeleton className="h-6 w-64" />
          <Skeleton className="size-9 rounded-full" />
        </div>
        <div className="mx-auto max-w-360 space-y-6 p-8">
          <Skeleton className="h-28 w-full rounded-lg" />
          <div className="grid gap-6 lg:grid-cols-2">
            <Skeleton className="h-48 rounded-lg" />
            <Skeleton className="h-48 rounded-lg" />
          </div>
        </div>
      </div>
    </div>
  )
}
