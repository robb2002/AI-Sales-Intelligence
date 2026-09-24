import { isApiError } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { ErrorState } from '../../components/ui/ErrorState'
import { useSignOut } from './useSignOut'

interface SessionErrorPageProps {
  error: unknown
  onRetry: () => void
  retrying: boolean
}

function describe(error: unknown): string {
  if (isApiError(error) && error.code === 'NETWORK_ERROR') {
    return 'The API could not be reached. Check that the backend is running, then retry.'
  }
  if (isApiError(error) && error.status >= 500) {
    return 'The server could not load your account. Try again in a moment.'
  }
  return 'Your account could not be loaded.'
}

export function SessionErrorPage({ error, onRetry, retrying }: SessionErrorPageProps) {
  const signOut = useSignOut()
  return (
    <main className="flex min-h-screen items-center justify-center bg-app">
      <ErrorState
        description={describe(error)}
        reference={isApiError(error) ? error.requestId : null}
        onRetry={onRetry}
        retrying={retrying}
        secondaryAction={
          <Button variant="secondary" onClick={() => void signOut()}>
            Sign out
          </Button>
        }
      />
    </main>
  )
}
