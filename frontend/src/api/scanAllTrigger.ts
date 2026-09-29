import type { ScanAllTriggerResponse } from '../types/api'
import { apiRequest } from './client'

export function getScanAllSchedule(): Promise<ScanAllTriggerResponse> {
  return apiRequest<ScanAllTriggerResponse>('/api/v1/scan-all-schedule')
}

/** Manager only. `scheduled_at: null` clears an existing schedule. */
export function updateScanAllSchedule(scheduledAt: string | null): Promise<ScanAllTriggerResponse> {
  return apiRequest<ScanAllTriggerResponse>('/api/v1/scan-all-schedule', {
    method: 'PATCH',
    body: JSON.stringify({ scheduled_at: scheduledAt }),
  })
}
