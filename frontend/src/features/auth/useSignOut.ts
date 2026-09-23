import { useClerk } from '@clerk/react'
import { useQueryClient } from '@tanstack/react-query'
import { useCallback } from 'react'

export function useSignOut() {
  const { signOut } = useClerk()
  const queryClient = useQueryClient()

  return useCallback(
    async (reason?: 'expired') => {
      await signOut({ redirectUrl: reason === 'expired' ? '/login?reason=expired' : '/login' })
      queryClient.clear()
    },
    [signOut, queryClient],
  )
}
