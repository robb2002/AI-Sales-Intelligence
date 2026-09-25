import type { LucideIcon } from 'lucide-react'
import {
  Cpu,
  FileClock,
  FileSignature,
  Landmark,
  Megaphone,
  UserCog,
  Users,
} from 'lucide-react'
import type { ScoreBand, SignalState, SignalType } from '../../types/api'

export const SIGNAL_TYPE_LABELS: Record<SignalType, string> = {
  procurement: 'Procurement',
  technology_initiative: 'Technology initiatives',
  leadership_change: 'Leadership changes',
  funding_budget: 'Funding/budget',
  strategic_announcement: 'Strategic announcements',
  competitor_vendor: 'Competitor/vendor',
  contract_renewal: 'Contract/renewal',
}

export const SIGNAL_TYPE_ICONS: Record<SignalType, LucideIcon> = {
  procurement: FileSignature,
  technology_initiative: Cpu,
  leadership_change: UserCog,
  funding_budget: Landmark,
  strategic_announcement: Megaphone,
  competitor_vendor: Users,
  contract_renewal: FileClock,
}

export const SIGNAL_TYPE_DOT: Record<SignalType, string> = {
  procurement: 'bg-signal-procurement',
  technology_initiative: 'bg-signal-technology',
  leadership_change: 'bg-signal-leadership',
  funding_budget: 'bg-signal-funding',
  strategic_announcement: 'bg-signal-strategic',
  competitor_vendor: 'bg-signal-competitor',
  contract_renewal: 'bg-signal-contract',
}

export const SIGNAL_TYPES = Object.keys(SIGNAL_TYPE_LABELS) as SignalType[]

export const SIGNAL_STATE_LABELS: Record<SignalState, string> = {
  detected: 'Detected',
  validated: 'Validated',
  rejected: 'Rejected',
  merged: 'Merged',
  superseded: 'Superseded',
}

export const SCORE_BAND_LABELS: Record<ScoreBand, string> = {
  high: 'High',
  medium: 'Medium',
  low: 'Low',
  monitor: 'Monitor',
}

export const FACTOR_LABELS: Record<string, string> = {
  procurement_relevance: 'Procurement relevance',
  related_signal_strength: 'Related signal strength',
  assessment_edtech_relevance: 'Assessment/EdTech relevance',
  recency: 'Recency',
  source_reliability: 'Source reliability',
}

export const FACTOR_HINTS: Record<string, string> = {
  procurement_relevance: 'Points when procurement, contract, or funding signals are present.',
  related_signal_strength: 'Points from how many different validated signal types are connected.',
  assessment_edtech_relevance: 'Points from EdTech terms found in stored snippets.',
  recency: 'Points from the newest signal date in the group.',
  source_reliability: 'Points from the strongest source reliability label in the group.',
}

export const ORG_TYPE_LABELS: Record<string, string> = {
  university: 'University',
  college: 'College',
  k12_district: 'K-12 district',
  public_sector_education: 'Public-sector education',
}

export function formatSignalDate(date: string | null, dateStatus: string): string {
  if (dateStatus === 'unavailable' || !date) return 'Date unavailable'
  const parsed = new Date(`${date}T00:00:00Z`)
  if (Number.isNaN(parsed.getTime())) return 'Date unavailable'
  return parsed.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  })
}

export function formatUpdatedAt(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })
}
