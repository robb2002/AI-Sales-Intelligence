import { useQueryClient } from '@tanstack/react-query'
import { useEffect, useRef } from 'react'
import { isApiError } from '../../api/client'
import { useSignOut } from './useSignOut'

const isUnauthenticated = (error: unknown) => isApiError(error) && error.status === 401

export function useSessionExpiry(currentError: unknown) {
  const queryClient = useQueryClient()
  const signOut = useSignOut()
  const handled = useRef(false)

  useEffect(() => {
    const expire = (error: unknown) => {
      if (handled.current || !isUnauthenticated(error)) return
      handled.current = true
      void signOut('expired')
    }

    expire(currentError)

    const unsubscribeQueries = queryClient.getQueryCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') expire(event.action.error)
    })
    const unsubscribeMutations = queryClient.getMutationCache().subscribe((event) => {
      if (event.type === 'updated' && event.action.type === 'error') expire(event.action.error)
    })
    return () => {
      unsubscribeQueries()
      unsubscribeMutations()
    }
  }, [currentError, queryClient, signOut])
}
