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

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'AUTH_MISSING'
  | 'AUTH_INVALID'
  | 'AUTH_EXPIRED'
  | 'USER_NOT_PROVISIONED'
  | 'USER_WITHOUT_ROLE'
  | 'INSUFFICIENT_PERMISSION'
  | 'NOT_FOUND'
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
