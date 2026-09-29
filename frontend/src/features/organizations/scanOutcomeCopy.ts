import type { ScanDetail } from '../../types/api'

export type ScanOutcomeSummary = {
  title: string
  summary: string
  failedSourceNote: string | null
  signalsCreated: number
  opportunitiesCreated: number
}

function asCount(value: unknown): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0
}

/** Success-style completion copy for succeeded / partial org scans. */
export function scanOutcomeSummary(scan: ScanDetail): ScanOutcomeSummary {
  const changes = scan.changes ?? {}
  const signalsCreated = asCount(changes.signals_created)
  const signalsUpdated = asCount(changes.signals_updated)
  const opportunitiesCreated = asCount(changes.opportunities_created)
  const opportunitiesUpdated = asCount(changes.opportunities_updated)
  const pagesRefreshed = scan.documents_collected ?? 0

  const parts: string[] = []
  if (signalsCreated > 0) {
    parts.push(`${signalsCreated} new signal${signalsCreated === 1 ? '' : 's'}`)
  }
  if (signalsUpdated > 0) {
    parts.push(`${signalsUpdated} signal${signalsUpdated === 1 ? '' : 's'} updated`)
  }
  if (opportunitiesCreated > 0) {
    parts.push(
      `${opportunitiesCreated} potential opportunit${opportunitiesCreated === 1 ? 'y' : 'ies'}`,
    )
  }
  if (opportunitiesUpdated > 0) {
    parts.push(
      `${opportunitiesUpdated} opportunit${opportunitiesUpdated === 1 ? 'y' : 'ies'} updated`,
    )
  }
  if (pagesRefreshed > 0) {
    parts.push(`${pagesRefreshed} page${pagesRefreshed === 1 ? '' : 's'} refreshed`)
  }

  const summary =
    parts.length > 0
      ? parts.join(' · ')
      : 'No new signals this run. Existing intelligence is up to date.'

  const failedNames = (scan.sources ?? [])
    .filter((row) => row.status === 'failed')
    .map((row) => row.source_name)
    .filter(Boolean)
  let failedSourceNote: string | null = null
  if (failedNames.length > 0) {
    const shown = failedNames.slice(0, 3)
    const extra = failedNames.length - shown.length
    const list = shown.join(', ') + (extra > 0 ? `, +${extra} more` : '')
    failedSourceNote = `Could not refresh: ${list}. Open approved sources below for detail.`
  }

  return {
    title: 'Scan completed',
    summary,
    failedSourceNote,
    signalsCreated,
    opportunitiesCreated,
  }
}
