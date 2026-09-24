import { useAuth } from '@clerk/react'
import { Navigate, useLocation } from 'react-router'
import { isApiError } from '../api/client'
import { AppShell } from '../components/layout/AppShell'
import { AppShellSkeleton } from '../components/layout/AppShellSkeleton'
import { NoRolePage } from '../features/auth/NoRolePage'
import { SessionErrorPage } from '../features/auth/SessionErrorPage'
import { useCurrentUser } from '../features/auth/useCurrentUser'
import { useSessionExpiry } from '../features/auth/useSessionExpiry'

export function RequireAuth() {
  const { isLoaded, isSignedIn } = useAuth()
  const location = useLocation()

  if (!isLoaded) return <AppShellSkeleton />
  if (!isSignedIn) {
    return <Navigate to="/login" replace state={{ from: `${location.pathname}${location.search}` }} />
  }
  return <SessionGate />
}

function SessionGate() {
  const { data: user, error, isPending, isFetching, refetch } = useCurrentUser()
  useSessionExpiry(error)

  const retry = () => void refetch()

  if (isApiError(error) && error.status === 401) return <AppShellSkeleton />
  if (isApiError(error) && (error.code === 'USER_NOT_PROVISIONED' || error.code === 'USER_WITHOUT_ROLE')) {
    return <NoRolePage code={error.code} onRetry={retry} retrying={isFetching} />
  }
  if (user) return <AppShell user={user} />
  if (isPending) return <AppShellSkeleton />
  return <SessionErrorPage error={error} onRetry={retry} retrying={isFetching} />
}
