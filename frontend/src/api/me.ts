import type { CurrentUser } from '../types/api'
import { apiRequest } from './client'

export function getCurrentUser(): Promise<CurrentUser> {
  return apiRequest<CurrentUser>('/api/v1/me')
}
