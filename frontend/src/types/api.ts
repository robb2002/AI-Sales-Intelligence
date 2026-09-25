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

export interface OrganizationSummary {
  organization_id: string
  name: string
  organization_type: string
  market_role: string
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
  | 'INTERNAL_ERROR'

export interface ErrorEnvelope {
  error: {
    code: ApiErrorCode
    message: string
    details: Record<string, unknown>
  }
}
