import { QueryClient } from '@tanstack/react-query'
import { isApiError } from '../api/client'

const isClientError = (error: unknown) =>
  isApiError(error) && error.status >= 400 && error.status < 500

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error) => !isClientError(error) && failureCount < 2,
    },
  },
})
