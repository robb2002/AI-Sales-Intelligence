import { useQuery } from '@tanstack/react-query'
import { getCurrentUser } from '../../api/me'

export const currentUserQueryKey = ['me'] as const

export function useCurrentUser() {
  return useQuery({
    queryKey: currentUserQueryKey,
    queryFn: getCurrentUser,
    staleTime: 5 * 60_000,
  })
}
