import { getToken } from '@clerk/react'
import { env } from '../lib/env'
import type { ApiErrorCode, ErrorEnvelope } from '../types/api'

export type ClientErrorCode = ApiErrorCode | 'NETWORK_ERROR'

export class ApiError extends Error {
  readonly status: number
  readonly code: ClientErrorCode
  readonly details: Record<string, unknown>
  readonly requestId: string | null

  constructor(
    status: number,
    code: ClientErrorCode,
    message: string,
    details: Record<string, unknown> = {},
    requestId: string | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
    this.requestId = requestId
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

const networkError = () => new ApiError(0, 'NETWORK_ERROR', 'The server could not be reached.')

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  let token: string | null
  try {
    token = await getToken()
  } catch {
    throw networkError()
  }

  const headers = new Headers(init.headers)
  headers.set('Accept', 'application/json')
  if (init.body !== undefined) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}${path}`, { ...init, headers })
  } catch {
    throw networkError()
  }

  const requestId = response.headers.get('X-Request-ID')

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as ErrorEnvelope | null
    throw new ApiError(
      response.status,
      body?.error?.code ?? 'INTERNAL_ERROR',
      body?.error?.message ?? 'The request failed.',
      body?.error?.details ?? {},
      requestId,
    )
  }

  return (await response.json()) as T
}
