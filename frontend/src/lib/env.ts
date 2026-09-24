const clerkPublishableKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY?.trim() ?? ''
const apiBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim().replace(/\/+$/, '') ?? ''

export const env = { clerkPublishableKey, apiBaseUrl }

export const missingEnvVars: string[] = [
  ...(clerkPublishableKey ? [] : ['VITE_CLERK_PUBLISHABLE_KEY']),
  ...(apiBaseUrl ? [] : ['VITE_API_BASE_URL']),
]
