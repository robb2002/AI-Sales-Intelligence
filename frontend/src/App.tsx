import { ClerkProvider } from '@clerk/react'
import { QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'
import { BrowserRouter, useNavigate } from 'react-router'
import { ErrorState } from './components/ui/ErrorState'
import { clerkAppearance } from './lib/clerkAppearance'
import { env, missingEnvVars } from './lib/env'
import { queryClient } from './lib/queryClient'
import { AppRoutes } from './routes/AppRoutes'

function ClerkProviderWithRouter({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  return (
    <ClerkProvider
      publishableKey={env.clerkPublishableKey}
      routerPush={(to) => navigate(to)}
      routerReplace={(to) => navigate(to, { replace: true })}
      signInUrl="/login"
      signUpUrl="/login"
      signInFallbackRedirectUrl="/"
      signUpFallbackRedirectUrl="/"
      afterSignOutUrl="/login"
      appearance={clerkAppearance}
    >
      {children}
    </ClerkProvider>
  )
}

function MissingConfiguration() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-app">
      <ErrorState
        title="Frontend configuration is incomplete"
        description={`Set ${missingEnvVars.join(' and ')} in frontend/.env (copy frontend/.env.example), then restart the dev server.`}
      />
    </main>
  )
}

export function App() {
  if (missingEnvVars.length > 0) return <MissingConfiguration />

  return (
    <BrowserRouter>
      <ClerkProviderWithRouter>
        <QueryClientProvider client={queryClient}>
          <AppRoutes />
        </QueryClientProvider>
      </ClerkProviderWithRouter>
    </BrowserRouter>
  )
}
