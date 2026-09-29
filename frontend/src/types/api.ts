export type Role = 'SALES_REP' | 'SALES_MANAGER'

export interface CurrentUser {
  user_id: string
  clerk_user_id: string
  email: string
  role: Role
}

export interface HealthResponse {
  status: 'ok'
}

export type ScanStatus =
  | 'queued'
  | 'running'
  | 'succeeded'
  | 'partial'
  | 'failed'
  | 'interrupted'

export type ScanStage =
  | 'discovering'
  | 'validating_sources'
  | 'saving_sources'
  | 'collecting'
  | 'extracting'
  | 'validating'
  | 'deduplicating'
  | 'correlating'
  | 'scoring'

export type SignalType =
  | 'procurement'
  | 'technology_initiative'
  | 'leadership_change'
  | 'funding_budget'
  | 'strategic_announcement'
  | 'competitor_vendor'
  | 'contract_renewal'

export type SignalState = 'detected' | 'validated' | 'rejected' | 'merged' | 'superseded'

export type ScoreBand = 'high' | 'medium' | 'low' | 'monitor'

export type DataOrigin = 'live' | 'cached'

export type OrganizationType =
  | 'university'
  | 'college'
  | 'k12_district'
  | 'public_sector_education'
  | 'edtech_company'

export type MarketRole = 'target' | 'competitor'

export interface OrganizationSummary {
  organization_id: string
  name: string
  organization_type: OrganizationType | string
  market_role: MarketRole | string
  tracking_status: 'active' | 'inactive' | string
  state_code: string | null
  website_url: string | null
  signal_count: number
  opportunity_count: number
  last_scanned_at: string | null
  data_origin?: DataOrigin
}

export interface OrganizationIpeds {
  content_layer: 'fact'
  source_name: string
  source_url: string
  unit_id: string | null
  collection_year: string | null
  release: 'final' | 'provisional' | null
  attributes: Array<{ key: string; label: string; value: string }>
}

export interface OrganizationDetail extends OrganizationSummary {
  ipeds: OrganizationIpeds | null
  last_scan: ScanSummary | null
}

export interface OrganizationSummaryPage {
  data: OrganizationSummary[]
  total: number
  limit: number
  offset: number
}

export interface OrganizationSourceItem {
  organization_source_id: string
  organization_id: string
  url: string
  source_title: string | null
  page_category: string
  status: 'approved' | 'rejected'
  extraction_status: 'pending' | 'extracting' | 'extracted' | 'failed'
  document_count: number
  is_official: boolean
  rejection_reason: string | null
  last_validated_at: string
}

export interface OrganizationSourcePage {
  data: OrganizationSourceItem[]
  total: number
  limit: number
  offset: number
}

export interface ScanSummary {
  scan_id: string
  batch_id: string | null
  organization_id: string
  organization_name: string
  trigger: string
  requested_by_email: string | null
  status: ScanStatus
  stage: ScanStage | null
  started_at: string | null
  finished_at: string | null
  candidates_found: number
  sources_approved: number
  sources_rejected: number
  documents_collected: number
  joined_existing?: boolean
}

export interface ScanSummaryPage {
  data: ScanSummary[]
  total: number
  limit: number
  offset: number
}

export interface ScanDetail extends ScanSummary {
  sources: Array<{ source_name: string; status: string; detail: string | null }>
  error_detail: string | null
  changes: Record<string, unknown>
}

export interface ScanBatchResponse {
  batch_id: string
  status: string
  scan_ids: string[]
  organization_count: number
  scans: ScanSummary[]
}

export interface EvidenceItem {
  evidence_id: string
  source_name: string
  source_url: string
  date: string | null
  date_status: 'available' | 'unavailable'
  snippet: string
  relationship: string
  relationship_layer: 'interpretation'
  data_origin: DataOrigin
  retrieved_at: string
}

export interface SignalSummary {
  signal_id: string
  organization_id: string
  organization_name: string
  signal_type: SignalType
  state: SignalState
  title: string
  summary: string
  summary_layer: 'fact'
  date: string | null
  date_status: 'available' | 'unavailable'
  source_count: number
  data_origin: DataOrigin
}

export interface SignalAiSummary {
  text: string
  content_layer: 'interpretation'
  evidence_ids: string[]
}

export interface SignalDetail extends SignalSummary {
  rejection_reason: string | null
  opportunity_ids: string[]
  ai_summary: SignalAiSummary | null
  evidence: EvidenceItem[]
}

export interface SignalPage {
  data: SignalSummary[]
  total: number
  limit: number
  offset: number
}

export interface ScoreFactor {
  key: string
  points: number
  max_points: number
}

export interface ScoreExplanation {
  text: string
  content_layer: 'interpretation'
  evidence_ids: string[]
}

export interface ScorePayload {
  value: number
  band: ScoreBand
  weight_version: string
  factors: ScoreFactor[]
  explanation: ScoreExplanation | null
  explanation_status: 'ready' | 'unavailable'
  previous_value: number | null
  scored_at: string | null
}

export interface CorrelationPayload {
  text: string
  content_layer: 'interpretation'
  evidence_ids: string[]
}

export interface RecommendedActionPayload {
  text: string
  content_layer: 'recommended_action'
  evidence_ids: string[]
}

export interface OpportunitySummary {
  opportunity_id: string
  organization_id: string
  organization_name: string
  organization_type: string
  state_code: string | null
  score: ScorePayload
  signal_count: number
  updated_at: string
  data_origin: DataOrigin
}

export interface OpportunityDetail extends OpportunitySummary {
  label: 'potential_opportunity'
  signals: SignalSummary[]
  correlation: CorrelationPayload
  recommended_action: RecommendedActionPayload | null
  evidence: EvidenceItem[]
}

export interface OpportunityPage {
  data: OpportunitySummary[]
  total: number
  limit: number
  offset: number
}

export type AdvisorStatus =
  | 'answered'
  | 'insufficient_evidence'
  | 'out_of_scope'
  | 'unavailable'

export type ContentLayer =
  | 'fact'
  | 'interpretation'
  | 'potential_opportunity'
  | 'recommended_action'

export interface AdvisorSegment {
  text: string
  content_layer: ContentLayer
  evidence_ids: string[]
}

export interface AdvisorAnswerBody {
  text: string
  segments: AdvisorSegment[]
}

export interface AdvisorAnswerResponse {
  session_id: string
  scope_type: 'organization' | 'opportunity'
  scope_id: string
  advisor_status: AdvisorStatus
  answer: AdvisorAnswerBody
  evidence: EvidenceItem[]
  data_origin: DataOrigin
}

export interface AdvisorTurnUser {
  role: 'user'
  text: string
  created_at: string
}

export interface AdvisorTurnAdvisor {
  role: 'advisor'
  answer: AdvisorAnswerBody
  advisor_status: AdvisorStatus
  evidence: EvidenceItem[]
  created_at: string
}

export interface AdvisorSessionResponse {
  session_id: string
  scope_type: 'organization' | 'opportunity'
  scope_id: string
  turns: Array<AdvisorTurnUser | AdvisorTurnAdvisor>
}

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'AUTH_MISSING'
  | 'AUTH_INVALID'
  | 'AUTH_EXPIRED'
  | 'USER_NOT_PROVISIONED'
  | 'USER_WITHOUT_ROLE'
  | 'INSUFFICIENT_PERMISSION'
  | 'NOT_FOUND'
  | 'CONFLICT'
  | 'SCAN_RATE_LIMITED'
  | 'ADVISOR_RATE_LIMITED'
  | 'SEARCH_NOT_CONFIGURED'
  | 'SEARCH_RATE_LIMITED'
  | 'SEARCH_FAILED'
  | 'INTERNAL_ERROR'

export interface ErrorEnvelope {
  error: {
    code: ApiErrorCode
    message: string
    details: Record<string, unknown>
  }
}

export type DashboardScanState = 'never_scanned' | 'current' | 'running' | 'partial' | 'failed'

export interface DashboardInsight {
  text: string
  content_layer: 'interpretation'
  evidence_ids: string[]
  evidence: EvidenceItem[]
}

export interface DashboardResponse {
  generated_at: string
  data_origin: DataOrigin
  opportunities: {
    total: number
    by_band: Record<ScoreBand, number>
    new_since: string
    new_count: number
  }
  signals: {
    validated_total: number
    by_type: Record<SignalType, number>
    recent_window_days: number
    recent_count: number
  }
  competitor_vendor: {
    validated_total: number
    new_in_window: number
  }
  scan_status: {
    state: DashboardScanState
    last_finished_at: string | null
    running: boolean
    last_status: ScanStatus | null
    sources_failed: number
  }
  prioritized_opportunities: OpportunitySummary[]
  recent_signals: SignalSummary[]
  signal_volume: Array<{ date: string; count: number }>
  ai_insights: DashboardInsight[]
}

export type PersonaMode =
  | 'auto'
  | 'email'
  | 'call_prep'
  | 'competitor'
  | 'daily_briefing'
  | 'research'

export type PersonaLayer = 'fact' | 'interpretation' | 'recommended_action'

export interface PersonaHistoryTurn {
  role: 'user' | 'assistant'
  text: string
}

export type PersonaScopeKind = 'auto' | 'organization' | 'general'

export interface PersonaRequest {
  message: string
  history: PersonaHistoryTurn[]
  organization_id: string | null
  mode: PersonaMode
  scope?: PersonaScopeKind
}

export type PersonaBlock =
  | { type: 'heading'; text: string }
  | { type: 'paragraph'; text: string; layer?: string; refs?: number[] }
  | {
      type: 'bullets'
      items: Array<{ text: string; layer?: PersonaLayer; refs?: number[] }>
    }
  | {
      type: 'table'
      headers: string[]
      rows: string[][]
      layer?: string
      refs?: number[]
    }
  | { type: 'email'; subject: string; body: string }

export type PersonaSourceKind =
  | 'stored_evidence'
  | 'official_website'
  | 'live_lookup'
  | 'system_data'

export interface PersonaSource {
  ref: number
  label: string
  url: string | null
  kind: PersonaSourceKind
  snippet: string | null
}

export interface PersonaResponse {
  status: 'answered' | 'unavailable'
  answer: { text: string; blocks: PersonaBlock[] }
  sources: PersonaSource[]
  follow_ups: string[]
  used: { organizations: string[]; live_lookup: boolean }
  data_origin: DataOrigin
}

export interface CompetitorSignal extends SignalSummary {
  evidence: EvidenceItem[]
}

export interface CompetitorItem {
  organization_id: string
  name: string
  website_url: string | null
  tracking_status: 'active' | 'inactive' | string
  last_scanned_at: string | null
  validated_signal_count: number
  signals: CompetitorSignal[]
}

export interface CompetitorsResponse {
  generated_at: string
  data_origin: DataOrigin
  totals: {
    competitors: number
    validated_signals: number
    new_in_window: number
    window_days: number
  }
  competitors: CompetitorItem[]
}

export interface PeerCompetitor {
  rank: number
  name: string
  source_title: string | null
  source_url: string
  snippet: string
  retrieved_at: string
}

export interface PeerCompetitorsResponse {
  organization_id: string
  configured: boolean
  last_updated_at: string | null
  search_query: string | null
  data_origin: 'live' | 'cached'
  peers: PeerCompetitor[]
}

export interface TrendsResponse {
  generated_at: string
  data_origin: DataOrigin
  window: {
    months: number
    date_from: string
    date_to: string
  }
  month_keys: string[]
  totals: {
    signals: number
    undated: number
    organizations: number
  }
  by_signal_type: Array<{
    month: string
    counts: Record<SignalType, number>
  }>
  by_state: Array<{
    state_code: string | null
    organizations: number
    total: number
    undated: number
    by_month: number[]
  }>
  by_organization_type: Array<{
    organization_type: string
    organizations: number
    total: number
    undated: number
    by_month: number[]
  }>
}
