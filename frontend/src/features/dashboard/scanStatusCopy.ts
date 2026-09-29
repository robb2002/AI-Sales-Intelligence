import type { DashboardResponse, DashboardScanState } from '../../types/api'

type Tone = 'muted' | 'positive' | 'ai' | 'opportunity' | 'risk'

type ScanChip = {
  label: string
  tone: Tone
  title: string
}

/** Portfolio-oriented chip copy (UI_UX_DESIGN §24 + soft attention wording). */
export function scanStatusChip(
  scan: DashboardResponse['scan_status'],
): ScanChip {
  const { state, last_status: lastStatus, sources_failed: failed } = scan

  if (state === 'running') {
    return {
      label: 'Scan in progress',
      tone: 'ai',
      title: 'A portfolio or organization scan is running',
    }
  }
  if (state === 'never_scanned') {
    return {
      label: 'No scans yet',
      tone: 'muted',
      title: 'No completed scans yet',
    }
  }
  if (state === 'current') {
    return {
      label: 'All scans current',
      tone: 'positive',
      title: 'Latest finished scan cohort completed successfully',
    }
  }
  if (state === 'partial') {
    if (lastStatus === 'interrupted') {
      return {
        label: 'Scan interrupted',
        tone: 'opportunity',
        title: 'A scan stopped before finishing — run Scan All or Scan Now again',
      }
    }
    return {
      label: 'Needs attention',
      tone: 'opportunity',
      title:
        failed > 0
          ? 'Some organization scans need a re-run; open Scanning for details'
          : 'One or more organizations need a re-scan; open Scanning for details',
    }
  }
  // failed — rare: whole latest cohort had no successful org runs
  return {
    label: 'Last scan failed',
    tone: 'risk',
    title: 'The latest finished scan cohort did not succeed',
  }
}

export function scanStatusMetricLabel(state: DashboardScanState, lastStatus: string | null): string {
  if (state === 'never_scanned') return 'No scans yet'
  if (state === 'current') return 'All scans current'
  if (state === 'running') return 'Scan in progress'
  if (state === 'partial' && lastStatus === 'interrupted') return 'Scan interrupted'
  if (state === 'partial') return 'Needs attention'
  return 'Last scan failed'
}
