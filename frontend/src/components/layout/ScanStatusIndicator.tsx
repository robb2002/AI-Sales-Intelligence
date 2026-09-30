import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { getDashboard } from '../../api/dashboard'
import { scanStatusChip } from '../../features/dashboard/scanStatusCopy'
import { cn } from '../../lib/cn'

const DOT: Record<string, string> = {
  muted: 'bg-neutral-400',
  positive: 'bg-status-positive',
  ai: 'bg-status-ai animate-pulse',
  opportunity: 'bg-status-opportunity',
  risk: 'bg-status-risk',
}

const TEXT: Record<string, string> = {
  muted: 'text-muted',
  positive: 'text-status-positive',
  ai: 'text-status-ai',
  opportunity: 'text-status-opportunity',
  risk: 'text-status-risk',
}

export function ScanStatusIndicator() {
  const { data } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    staleTime: 10_000,
    // Keep the header chip current for scheduler-started runs without a full page refresh.
    refetchInterval: (query) => (query.state.data?.scan_status.running ? 3_000 : 5_000),
  })

  const scan = data?.scan_status
  if (!scan) {
    return (
      <span
        className="hidden items-center gap-1.5 sm:inline-flex"
        title="Loading scan status"
        aria-label="Loading scan status"
      >
        <span className="size-1.5 rounded-full bg-neutral-300" aria-hidden />
        <span className="text-caption text-muted">…</span>
      </span>
    )
  }

  const chip = scanStatusChip(scan)

  return (
    <Link
      to="/#scanning"
      className="hidden items-center gap-1.5 rounded-md px-1.5 py-1 sm:inline-flex hover:bg-navy-50 focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-focus-ring"
      title={chip.title}
      aria-label={`Scan status: ${chip.label}. Open scanning section.`}
    >
      <span className={cn('size-1.5 shrink-0 rounded-full', DOT[chip.tone])} aria-hidden />
      <span className={cn('max-w-[11rem] truncate text-caption', TEXT[chip.tone])}>{chip.label}</span>
    </Link>
  )
}
